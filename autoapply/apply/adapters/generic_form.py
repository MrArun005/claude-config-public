"""apply/adapters/generic_form.py — rung 1, platform-agnostic.

Reads whatever form is on the page, maps each control to an answer-bank key
via state/field-aliases.yaml, and fills it. Raises UnknownField on the first
control the table does not recognise, which is what hands control to rung 2.

Two failure modes are kept strictly apart, because they escalate differently:

  * the table has no KEY for this control          -> UnknownField (rung 2 can
                                                      learn the mapping)
  * the table has a key but the bank has no VALUE  -> recorded as unresolved
                                                      (rung 2 cannot invent an
                                                      answer, so the gate must
                                                      block and a human answers)

Nothing is guessed. A select whose options do not contain the bank's answer is
unresolved, not "closest match" — picking "5-10 years" when you said 5 is the
kind of small lie this system exists to avoid.
"""
from __future__ import annotations

import re
from pathlib import Path

from state import questions
from state.answers import (AnswerBank, Filled, TEMPLATE_MARKER,
                           is_placeholder)

from .. import aliases
from ..adapter import UnknownField, load_resolutions
from ..fields import FormField, discover, normalise_label
from ..templates import Unrenderable, render

TEXT_TYPES = frozenset({
    "text", "email", "tel", "url", "number", "search", "textarea",
    "date", "month", "week", "password",
})

# A rung-2 resolution may say "this field is intentionally left blank".
SKIP_KEY = "__skip__"

_YES = ("yes", "true", "y")
_NO = ("no", "false", "n")


class Result:
    """What one pass over the form produced."""

    def __init__(self) -> None:
        self.filled: dict[str, Filled] = {}
        self.unresolved: list[str] = []
        self.required_unfilled: list[str] = []
        self.skipped: list[str] = []
        self.replayed: list[str] = []   # refilled from the checkpoint on resume

    def as_dict(self) -> dict:
        return {
            "filled": {k: v.value for k, v in self.filled.items()},
            "unresolved": self.unresolved,
            "required_unfilled": self.required_unfilled,
            "skipped": self.skipped,
            "replayed": self.replayed,
        }


def _match_option(value, options: tuple[str, ...]) -> str | None:
    """Pick the option that genuinely says `value`, or None. Never approximate."""
    real = [o for o in options if o and o.strip()]
    if not real:
        return None

    if isinstance(value, bool):
        wanted = _YES if value else _NO
        for opt in real:
            if opt.strip().lower() in wanted:
                return opt
        return None

    want = str(value).strip().lower()
    for opt in real:                                    # exact
        if opt.strip() == str(value).strip():
            return opt
    for opt in real:                                    # case-insensitive
        if opt.strip().lower() == want:
            return opt
    # Prefix before substring. Typing "India" into a country picker offers
    # ["British Indian Ocean Territory +246", "India +91"] -- both CONTAIN
    # "india", and a substring rule could pick the wrong country outright.
    starts = [o for o in real if want and o.strip().lower().startswith(want)]
    if len(starts) == 1:
        return starts[0]

    hits = [o for o in real if want and want in o.strip().lower()]
    return hits[0] if len(hits) == 1 else None          # ambiguous -> None


def _alternates(alt) -> list:
    """`select_as` may be a single value or an ordered list of fallbacks.

    Order is the author's preference, most accurate first. Every entry is a
    value the author explicitly pre-approved for this question — the code still
    never invents one.
    """
    if alt is None:
        return []
    if isinstance(alt, (list, tuple)):
        return [a for a in alt if a is not None]
    return [alt]


async def _visible_options(page, container, limit: int = 30) -> list:
    """The options of the dropdown that is actually open, as (locator, text).

    Scoped and visibility-filtered on purpose. A bare
    `[role="option"]` search across the page also matches the phone
    country-code list (intl-tel-input renders 200+ hidden role="option" items),
    and a live GitLab run spent 30s trying to click a hidden Åland Islands entry
    before timing out. Prefer the widget's own menu, then any visible option.
    """
    for scope, selector in ((container, '[class*="select__option"], [role="option"]'),
                            (page, '[class*="select__option"]'),
                            (page, '[role="option"]')):
        try:
            loc = scope.locator(selector)
            count = min(await loc.count(), limit)
        except Exception:
            continue
        out = []
        for i in range(count):
            item = loc.nth(i)
            try:
                if not await item.is_visible():
                    continue
                text = (await item.inner_text()).strip()
            except Exception:
                continue
            if text:
                out.append((item, text))
        if out:
            return out
    return []


async def _selection_took(container, chosen: str) -> bool:
    """Did the widget actually accept `chosen`?

    Compared loosely on purpose, in BOTH directions. A country picker offers
    "India +91" but then displays only "+91", so requiring the displayed text to
    contain the option label rejected a selection that had plainly landed. What
    matters is that something non-placeholder is shown and it relates to what we
    picked -- not that the two strings are equal.
    """
    shown = await _shown_value(container)
    if not shown:
        return False
    low, pick = shown.strip().lower(), chosen.strip().lower()
    if "select..." in low:
        return False
    return low in pick or pick in low or _match_option(chosen, (shown,)) is not None


async def _shown_value(container) -> str:
    """What a combobox is currently displaying as its chosen value.

    React-Select clears its input once a choice is made and renders the value in
    a `singleValue` element, so the input is the wrong place to look. Falls back
    to the container's text, which also carries the question label -- good
    enough for a contains-check, and better than trusting a fill blindly.
    """
    for sel in ('[class*="singleValue"]', '[class*="single-value"]',
                '[class*="multiValue"]', '[class*="multi-value"]'):
        try:
            loc = container.locator(sel)
            if await loc.count():
                return (await loc.first.inner_text()).strip()
        except Exception:
            continue
    try:
        return (await container.inner_text()).strip()
    except Exception:
        return ""


def _as_text(value) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


class GenericFormAdapter:
    """Adapter protocol implementation (see apply/adapter.py)."""

    name = "generic-form"

    def __init__(self, bank: AnswerBank | None = None,
                 template_context: dict | None = None) -> None:
        self.bank = bank or AnswerBank()
        self.template_context = template_context or {}

    # --- rung-1 dispatch ------------------------------------------------
    def matches(self, url: str, html: str) -> bool:
        controls = len(re.findall(r"<(input|select|textarea)\b", html, re.I))
        if re.search(r"<form\b", html, re.I):
            return controls > 0

        # Ashby ships its application with NO <form> element at all: a live
        # Supabase posting has 17 inputs, an upload button and a "Submit
        # Application" button, and not one form tag. Requiring <form> sent that
        # page to rung 3 as if it had no application. So fall back to "enough
        # controls plus something that submits", which a job DESCRIPTION page
        # does not have -- a live SmartRecruiters description page has one
        # input and no submit, and must still be rejected.
        submits = re.search(r"submit application|submit your application|apply now",
                            html, re.I)
        return controls >= 5 and bool(submits)

    # --- the fill pass --------------------------------------------------
    async def apply(self, page, profile: dict, ckpt) -> dict:
        platform = profile.get("platform", "")
        resolutions = load_resolutions()
        result = Result()
        # Grouped choices, keyed by normalised legend: did any option match?
        groups: dict[str, dict] = {}
        # Every question this form asked, so the same gap is never rediscovered
        # silently on the next posting (plan §5.3: escalations are per unique
        # question, not per application).
        seen_questions: list[dict] = []

        found = await discover(page)
        if not ckpt.pending_fields:
            ckpt.pending_fields = [f.signature for f in found]

        for field in found:
            sig = field.signature

            # Resume: REPLAY the stored value, do not skip it. checkpoint.py's
            # contract is "reopen url, replay completed_fields, continue at
            # pending_fields[0]" — and it has to be a replay, because the
            # resumed page is a freshly loaded form with every input empty.
            # Skipping would submit a half-blank application.
            #
            # The value comes from the checkpoint, not the bank: the answer was
            # already selected and approved on the first pass, so re-deriving it
            # would be wasted work and a chance to disagree with itself.
            done = ckpt.completed_fields.get(sig)
            if isinstance(done, dict):
                if done.get("provenance") == "skipped":
                    result.skipped.append(field.describe())
                    continue
                value = done.get("value")
                if value is None:
                    # A grouped option that was NOT the chosen answer: recorded
                    # so the resume knows it was considered, but there is
                    # nothing to re-enter. Replaying it as a filled field put a
                    # None into the gate, which then refused the whole
                    # application for a "placeholder" value.
                    continue
                label = done.get("label") or sig
                try:
                    await self._fill(page, field, value)
                except _Unfillable as exc:
                    result.unresolved.append(f"{field.describe()}: replay failed: {exc}")
                    if field.required:
                        result.required_unfilled.append(field.describe())
                    continue
                result.filled[label] = Filled(sig, value, done.get("provenance"))
                result.replayed.append(label)
                continue

            key = resolutions.get(f"{platform}::{sig}") or aliases.key_for(field)
            seen_questions.append({
                "signature": sig, "question": field.question,
                "option": field.label if field.is_option else None,
                "key": key, "required": field.required,
                "type": field.type, "platform": platform,
            })

            # Deliberately NOT guessing at an unlabelled file input. It is
            # tempting to treat the first upload slot on a job application as
            # the résumé, but the live Supabase form has two file inputs and the
            # real one is properly labelled "Resume" -- the unlabelled one is
            # something else. Guessing would have attached the CV to the wrong
            # slot while the correct field filled anyway.
            if key is None:
                if not field.required:
                    # An unmapped OPTIONAL question is not worth halting the
                    # whole application for -- leaving it blank is an honest
                    # submission. Before this, one optional question the table
                    # did not recognise aborted the run at rung 2 with zero
                    # fields filled, which is how a live GitLab posting failed
                    # on an accessibility-adjustments field.
                    result.unresolved.append(
                        f"{field.describe()}: no mapping (optional, left blank)")
                    continue
                # Record before escalating: this raise leaves apply() entirely,
                # so the log written at the end never runs -- and the question
                # that BLOCKED the application is exactly the one worth keeping.
                questions.record(seen_questions)
                raise UnknownField(sig, field.question or field.name or field.selector)

            if key == SKIP_KEY:
                result.skipped.append(field.describe())
                ckpt.record(sig, {"label": field.label, "key": SKIP_KEY,
                                  "value": None, "provenance": "skipped"},
                            action=f"skip:{sig}")
                continue

            answer = self._answer_for(key, field, result)
            if answer is None:
                result.unresolved.append(f"{field.describe()}: {self._why_no_answer(key)}")
                if field.required:
                    result.required_unfilled.append(field.describe())
                continue

            try:
                entered = await self._fill(page, field, answer.value,
                                           alt=self.bank.select_alt(answer.name))
            except _Unfillable as exc:
                result.unresolved.append(f"{field.describe()}: {exc}")
                if field.required:
                    result.required_unfilled.append(field.describe())
                continue

            if field.is_option:
                # One option of a grouped choice. `entered` is None when this
                # was not the chosen option, which is a normal outcome for two
                # of every three checkboxes -- so it must not count as a filled
                # field, and the group's own bookkeeping decides the rest.
                seen = groups.setdefault(normalise_label(field.group),
                                         {"required": False, "answered": False,
                                          "describe": field.describe()})
                seen["required"] = seen["required"] or field.required
                if entered is not None:
                    seen["answered"] = True
                    result.filled[field.group] = answer
                ckpt.record(sig, {"label": field.label, "key": key,
                                  "value": entered, "provenance": answer.provenance},
                            action=f"option:{key}")
                continue

            label = field.label or field.name or sig
            result.filled[label] = answer
            # Recorded after EVERY field, not every page — the crash-proofing
            # contract in state/checkpoint.py.
            # `entered` not answer.value: for a dropdown these differ, and the
            # replay on resume must re-enter what the control actually accepted.
            ckpt.record(sig, {"label": label, "key": key, "value": entered,
                              "provenance": answer.provenance},
                        action=f"fill:{key}")

        # A required grouped choice where no option matched the bank answer is
        # an unanswered required question, even though every individual checkbox
        # was handled without error. Only the group can see this.
        for norm, seen in groups.items():
            if seen["required"] and not seen["answered"]:
                result.required_unfilled.append(seen["describe"])
                result.unresolved.append(
                    f"{seen['describe']}: no option matched the banked answer")

        questions.record(seen_questions)
        return result.as_dict() | {"_result": result}

    def _why_no_answer(self, key: str) -> str:
        """A stub answer and a missing one both block, but only one is a typo
        away from working — worth telling the human which they have."""
        entry = self.bank.data.get(aliases.source_key(key))
        if entry is None:
            return f"answer bank has no {key!r} key"
        if entry.get("sourced") and is_placeholder(entry.get("value")):
            return (f"answer bank {key!r} is still a placeholder "
                    f"({entry.get('value')!r}) — fix with: python -m state.review")
        return f"no usable answer for {key!r}"

    async def plan(self, page, profile: dict) -> list[dict]:
        """Discover and resolve every field WITHOUT filling anything.

        This is what you run first against a real ATS: it shows the mapping and
        the exact value each control would receive, while making no change to
        the page and sending nothing to the employer.
        """
        platform = profile.get("platform", "")
        resolutions = load_resolutions()
        sink = Result()
        out: list[dict] = []

        for field in await discover(page):
            sig = field.signature
            key = resolutions.get(f"{platform}::{sig}") or aliases.key_for(field)
            row = {"label": field.describe(), "signature": sig,
                   "key": key, "value": None, "provenance": None,
                   "verdict": ""}
            if key is None:
                row["verdict"] = "rung 2 — no mapping for this question"
            elif key == SKIP_KEY:
                row["verdict"] = "skip — intentionally left blank"
            else:
                answer = self._answer_for(key, field, sink)
                if answer is None:
                    row["verdict"] = self._why_no_answer(key)
                else:
                    row["value"] = answer.value
                    row["provenance"] = answer.provenance
                    row["verdict"] = "would fill"
                    if field.type.startswith("select") or field.type == "radio":
                        opt = None
                        for cand in (answer.value,
                                     *_alternates(self.bank.select_alt(answer.name))):
                            opt = _match_option(cand, field.options or ())
                            if opt is not None:
                                break
                        row["value"] = opt if opt is not None else answer.value
                        row["verdict"] = ("would select" if opt is not None
                                          else "no matching option — would park")
            out.append(row)
        return out

    # --- answer selection ----------------------------------------------
    def _answer_for(self, key: str, field: FormField, result: Result) -> Filled | None:
        if key in aliases.DERIVED:
            base = self.bank.lookup(aliases.source_key(key))
            if base is None:
                return None
            part = aliases.derive(key, base.value)
            return Filled(key, part, base.provenance) if part else None

        found = self.bank.lookup(key)
        if found is None:
            return None

        if found.provenance == "template" and isinstance(found.value, tuple) \
                and found.value[0] == TEMPLATE_MARKER:
            path = self.bank.template_path(key)
            if path is None:
                return None
            try:
                return Filled(key, render(path, self.template_context), "template")
            except Unrenderable as exc:
                result.unresolved.append(f"{field.describe()}: {exc}")
                return None
        return found

    async def _fill_combobox(self, page, field: FormField, value, alt):
        """Choose an option in a custom combobox, and verify it actually took.

        page.fill() is useless here. React-Select is a controlled component: the
        text goes into its input, no option is selected, and the form still
        considers the field empty. A live GitLab application reported 22 fields
        filled while every one of its 13 comboboxes came back "Select... This
        field is required."

        So: click to open, type to filter, and click the option whose text
        genuinely matches the answer -- never simply the first one offered. Then
        read the widget back, because a filler that cannot tell success from
        failure is how the earlier false "filled" counts happened.
        """
        sel = field.selector
        # The nearest 'select'-classed ancestor is select__input, which is empty;
        # the chosen value renders in select__control. Getting this wrong made
        # every verification fail even when the choice had landed.
        container = page.locator(sel).locator(
            "xpath=(ancestor::*[contains(@class,'select__control') or "
            "contains(@class,'select__container')])[last()]")

        for candidate in (value, *_alternates(alt)):
            text = _as_text(candidate)
            try:
                await page.click(sel, timeout=5000)
                await page.wait_for_timeout(400)
            except Exception as exc:
                raise _Unfillable(f"could not open the dropdown: "
                                  f"{type(exc).__name__}") from exc

            # Click the matching option directly. Typing to filter re-renders
            # the menu and made captured locators go stale; with the menu simply
            # open, the options are stable. Long lists (country pickers) get one
            # typed pass to narrow them first.
            options = await _visible_options(page, container)
            if len(options) > 15:
                try:
                    await page.type(sel, text[:24], delay=10)
                    await page.wait_for_timeout(450)
                    options = await _visible_options(page, container)
                except Exception:
                    pass
            # Match against the WHOLE option list in one call, not one option at
            # a time. Per-option checks defeat the ambiguity guard: "India"
            # against ["British Indian Ocean Territory +246", "India +91"] looks
            # like a match on either in isolation, and the wrong country would
            # be clicked. Given the full list, prefix beats substring.
            chosen = _match_option(text, tuple(t for _, t in options))
            if chosen is not None:
                for opt, opt_text in options:
                    if opt_text != chosen:
                        continue
                    try:
                        await opt.click(timeout=4000)
                        await page.wait_for_timeout(300)
                    except Exception:
                        break
                    if await _selection_took(container, chosen):
                        return chosen
                    break

            # Commit with Enter rather than clicking an option element. React
            # re-renders the menu as you type, so a locator captured a moment
            # earlier goes stale and the click times out -- a live GitLab run
            # spent 30s on exactly that. Enter selects whatever the widget has
            # highlighted, and the verification below is what keeps it honest.
            try:
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(350)
            except Exception:
                pass

            shown = await _shown_value(container)
            # Only accept it if the widget now DISPLAYS the answer. Without this
            # a silent no-op read as a successful fill, which is how 22 fields
            # were reported filled while the form saw none of them.
            if shown and _match_option(text, (shown,)) is not None:
                return shown

            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

        offered = [t for _, t in await _visible_options(page, container, limit=8)]
        raise _Unfillable(
            f"no option matches {value!r}"
            + (f" (offered: {', '.join(o for o in offered if o)})" if offered else ""))

    # --- the actual typing ----------------------------------------------
    async def _fill(self, page, field: FormField, value, alt=None):
        """Enter `value` into the control. Returns what was actually entered."""
        sel = field.selector
        kind = field.type

        if kind == "file":
            path = Path(str(value)).expanduser()
            if not path.is_file():
                raise _Unfillable(f"file not found: {path}")
            await page.set_input_files(sel, str(path))
            return str(path)

        if kind in ("checkbox", "radio") and field.is_option:
            # One option of a grouped choice ("Yes" / "No" / "Prefer not to
            # say"). Tick it only if THIS option is the answer; the others are
            # left alone. Whether the group ended up answered at all is checked
            # once per group in apply(), because no single option can know.
            chosen = None
            for candidate in (value, *_alternates(alt)):
                if _match_option(candidate, (field.label,)) is not None:
                    chosen = candidate
                    break
            if chosen is None:
                await page.uncheck(sel)
                return None                    # not this option
            await page.check(sel)
            return field.label

        if kind == "checkbox":
            if not isinstance(value, bool):
                # A checkbox needs a true/false answer; a sentence is not one.
                truthy = str(value).strip().lower()
                if truthy not in _YES + _NO:
                    raise _Unfillable(f"not a yes/no answer: {value!r}")
                value = truthy in _YES
            if value:
                await page.check(sel)
            else:
                await page.uncheck(sel)
            return value

        if field.combobox:
            return await self._fill_combobox(page, field, value, alt)

        if kind.startswith("select"):
            opt = None
            for candidate in (value, *_alternates(alt)):
                opt = _match_option(candidate, field.options or ())
                if opt is not None:
                    break
            if opt is None:
                raise _Unfillable(
                    f"no option matches {value!r} (options: "
                    f"{', '.join(o for o in (field.options or ()) if o)})")
            await page.select_option(sel, label=opt)
            return opt

        if kind == "radio":
            group = page.locator(f'input[type=radio][name="{field.name}"]')
            count = await group.count()
            labels = []
            for i in range(count):
                item = group.nth(i)
                labels.append(await item.get_attribute("value") or "")
            opt = None
            for candidate in (value, *_alternates(alt)):
                opt = _match_option(candidate, tuple(labels))
                if opt is not None:
                    break
            if opt is None:
                raise _Unfillable(f"no radio option matches {value!r}")
            await group.nth(labels.index(opt)).check()
            return opt

        if kind == "number":
            # A number input silently rejects "₹14 LPA (negotiable)". The
            # alternate supplies the bare figure. Note what is NOT done here:
            # digits are never *extracted* from prose — that would be the
            # system inventing "14" from a sentence, which is exactly the
            # inference the submit gate exists to prevent. You write both.
            for candidate in (value, *_alternates(alt)):
                if candidate is None:
                    continue
                text = _as_text(candidate).strip()
                try:
                    float(text)
                except ValueError:
                    continue
                await page.fill(sel, text)
                return text
            raise _Unfillable(
                f"{value!r} is not a number; add a numeric `select_as` to the "
                f"answer bank entry")

        if kind in TEXT_TYPES or field.tag == "textarea":
            text = _as_text(value)
            await page.fill(sel, text)
            return text

        raise _Unfillable(f"unsupported control type {kind!r}")


class _Unfillable(Exception):
    """The answer exists but cannot be entered into THIS control."""
