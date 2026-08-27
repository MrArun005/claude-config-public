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

from state.answers import (AnswerBank, Filled, TEMPLATE_MARKER,
                           is_placeholder)

from .. import aliases
from ..adapter import UnknownField, load_resolutions
from ..fields import FormField, discover
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
        if not re.search(r"<form\b", html, re.I):
            return False
        return bool(re.search(r"<(input|select|textarea)\b", html, re.I))

    # --- the fill pass --------------------------------------------------
    async def apply(self, page, profile: dict, ckpt) -> dict:
        platform = profile.get("platform", "")
        resolutions = load_resolutions()
        result = Result()

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

            if key is None:
                raise UnknownField(sig, field.label or field.name or field.selector)

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

            label = field.label or field.name or sig
            result.filled[label] = answer
            # Recorded after EVERY field, not every page — the crash-proofing
            # contract in state/checkpoint.py.
            # `entered` not answer.value: for a dropdown these differ, and the
            # replay on resume must re-enter what the control actually accepted.
            ckpt.record(sig, {"label": label, "key": key, "value": entered,
                              "provenance": answer.provenance},
                        action=f"fill:{key}")

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
