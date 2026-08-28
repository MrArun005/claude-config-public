"""apply/fields.py — read the form that is actually on the page.

Rung 1 discovers fields at runtime rather than carrying per-platform selector
sets. That is not a stylistic choice: `adapter.cache_resolution(platform,
field_signature, answer_key)` only pays off if a field can be *recognised*
again on the next run, which presupposes a signature computed from the live
DOM. Hardcoded selectors would make that cache dead weight.

The signature strips digits from the name/id, because ATS platforms generate
per-posting ids for custom questions, e.g.

    <label for="q_88213771">How many years of React experience …</label>
    <input id="q_88213771" name="question_88213771[value]">

Keep the digits and every posting looks like a brand-new field, so a resolution
cached on Monday never hits on Tuesday.

Status of that claim: the *mechanism* is verified — p3_test.py proves signatures
stay identical when the generated ids change, which is what makes the rung-2
cache hit. The exact attribute shape above has NOT been checked against a live
posting from this environment (the network policy blocks job boards), so treat
it as a representative pattern rather than a confirmed Greenhouse/Lever literal.
Confirm against a real apply page before relying on the specific spelling.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

# Controls we never fill: hidden state, and the buttons that submit the thing.
SKIP_TYPES = frozenset({"hidden", "submit", "button", "reset", "image"})

# Stamped so a field discovered in one call can still be acted on after the
# list has been filtered/reordered. Only ever used as a last-resort selector.
IDX_ATTR = "data-autoapply-idx"

_SAFE_ID = re.compile(r"^[A-Za-z][\w:.-]*$")
_TRAILING_NOISE = re.compile(r"[\s:*]+$|\(\s*required\s*\)|\(\s*optional\s*\)", re.I)


@dataclass(frozen=True)
class FormField:
    tag: str                       # input | select | textarea
    type: str                      # text | email | checkbox | file | select-one | …
    name: str
    id: str
    label: str                     # best available human label
    required: bool
    options: tuple[str, ...] | None  # <select> choices, else None
    idx: int                       # stamped position, for the fallback selector
    group: str = ""                # enclosing fieldset's legend, when there is
                                   # one: for a choice rendered as several
                                   # checkboxes this holds the QUESTION while
                                   # `label` holds only this OPTION ("Yes")

    @property
    def is_option(self) -> bool:
        """True when this control is one option of a grouped choice.

        A checkbox inside a fieldset whose legend differs from its own label is
        an option, not a question: "Yes" means nothing without the legend.
        """
        return (self.type in ("checkbox", "radio") and bool(self.group)
                and normalise_label(self.group) != normalise_label(self.label))

    @property
    def question(self) -> str:
        """The text a human would call this field's question."""
        return self.group if self.is_option else self.label

    @property
    def selector(self) -> str:
        """Prefer a real selector; fall back to the stamped index.

        `#id` is only safe for ids that are valid CSS identifiers — ATS ids like
        `question[123]` are not, and would silently select nothing.
        """
        if self.id and _SAFE_ID.match(self.id):
            return f"#{self.id}"
        if self.name:
            return f'[name="{self.name}"]'
        return f'[{IDX_ATTR}="{self.idx}"]'

    @property
    def signature(self) -> str:
        return signature(self)

    def describe(self) -> str:
        """Human-readable, for review-queue reasons. Uses the normalised label so
        a form's own "*" marker is not doubled up with ours."""
        base = normalise_label(self.question) or self.name or self.selector
        opt = f" = {normalise_label(self.label)!r}" if self.is_option else ""
        return (f"{base}{opt}{' *' if self.required else ''} "
                f"[{self.tag}/{self.type}]")


def normalise_label(label: str) -> str:
    """Lowercase, collapse whitespace, drop required/optional markers."""
    text = re.sub(r"\s+", " ", (label or "")).strip()
    # Applied twice: "Email * (required)" leaves a trailing " *" after the
    # parenthetical goes, and one pass would keep it.
    for _ in range(2):
        text = _TRAILING_NOISE.sub("", text).strip()
    return text.lower()


def normalise_name(name: str) -> str:
    """Strip the per-posting digits, keeping the structural shape."""
    return re.sub(r"\d+", "", name or "")


def signature(field: FormField) -> str:
    raw = "|".join([
        field.tag,
        field.type,
        normalise_name(field.name),
        normalise_label(field.label),
        # The group matters: "Yes" under one question is a different field from
        # "Yes" under another, and without this they would share a signature,
        # collapse into one during dedupe, and share a cached resolution.
        normalise_label(field.group),
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def platform_of(url: str) -> str:
    """Cache-key namespace: the host, minus a leading www."""
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


# Runs in the page. Stamps an index, then resolves a label the way a human
# reads one: explicit <label for>, then a wrapping <label>, then ARIA, then
# the placeholder, and only then the raw name attribute.
_DISCOVER_JS = """
(idxAttr) => [...document.querySelectorAll('input,select,textarea')]
  .map((e, i) => { e.setAttribute(idxAttr, String(i)); return e; })
  .filter(e => !['hidden','submit','button','reset','image'].includes(e.type))
  .filter(e => !e.disabled)
  .map(e => {
    let lbl = '';
    if (e.id) {
      const l = document.querySelector(`label[for="${CSS.escape(e.id)}"]`);
      if (l) lbl = l.innerText;
    }
    if (!lbl) { const a = e.closest('label'); if (a) lbl = a.innerText; }
    if (!lbl && e.getAttribute('aria-labelledby')) {
      const t = document.getElementById(e.getAttribute('aria-labelledby'));
      if (t) lbl = t.innerText;
    }
    if (!lbl) lbl = e.getAttribute('aria-label') || e.placeholder || '';
    if (!lbl) {
      // Custom comboboxes (React-Select and friends, used by Greenhouse's
      // newer boards) render a bare <input> with no id, no name and no ARIA,
      // wrapped in a div whose only text is "Select...". The real question
      // lives in a sibling ABOVE the widget. Walk up a few levels and take the
      // first label-ish element, but only from an ancestor that owns exactly
      // one control -- otherwise we would steal the neighbouring question's
      // label and answer the wrong box, which is worse than not answering.
      let node = e.parentElement;
      for (let up = 0; up < 5 && node && !lbl; up++, node = node.parentElement) {
        // Count only VISIBLE controls: React-Select pairs its text input with a
        // hidden one, so counting everything sees 2 and bails out one level
        // below the element that actually carries the question.
        // React-Select renders TWO visible inputs (the combobox plus its
        // shadow field), so the wrapper carrying the question sits one level
        // above a node that already owns 2 controls. Allow up to 2, and stop
        // as soon as an ancestor owns more than one <label> -- that ancestor
        // spans several questions, and taking its first label would answer
        // this control with the neighbouring question's label. Verified on a
        // live Greenhouse form: the phone fieldset owns 4 controls and 2
        // labels, and must not be used.
        const owned = node.querySelectorAll(
          'input:not([type=hidden]),select,textarea').length;
        const labels = node.querySelectorAll('label');
        if (owned > 2 || labels.length > 1) break;
        if (labels.length === 1 && labels[0].innerText
            && labels[0].innerText.trim()) {
          lbl = labels[0].innerText;
          break;
        }
      }
    }
    if (!lbl) lbl = e.name || '';
    // A choice rendered as several checkboxes puts the QUESTION in the
    // fieldset's <legend> and each OPTION in its own label, so "Yes" alone is
    // meaningless. Semantic HTML, so read it rather than guess: the legend is
    // the question, the label is the option.
    let group = '';
    const fs = e.closest('fieldset');
    if (fs) {
      const lg = fs.querySelector('legend');
      if (lg && lg.innerText) group = lg.innerText.replace(/\\s+/g, ' ').trim();
    }
    return {
      tag: e.tagName.toLowerCase(),
      type: (e.type || e.tagName.toLowerCase()),
      name: e.name || '',
      id: e.id || '',
      group: group,
      label: lbl.replace(/\\s+/g, ' ').trim(),
      required: !!(e.required || e.getAttribute('aria-required') === 'true'
                   || /\\*|\\(\\s*required\\s*\\)/i.test(lbl)),
      options: e.tagName === 'SELECT'
        ? [...e.options].map(o => o.value || o.text) : null,
      idx: Number(e.getAttribute(idxAttr)),
    };
  })
"""


async def discover(page) -> list[FormField]:
    """Every fillable control on the page, in document order.

    Consecutive controls with an identical signature collapse to one. A
    React-Select widget renders two visible inputs for a single question, so
    without this a form reports "Country" twice, fills it twice, and counts it
    twice towards the gate. Only CONSECUTIVE duplicates are dropped, so a form
    that genuinely asks a same-looking question in two places keeps both.
    """
    return _dedupe([
        FormField(
            tag=r["tag"], type=r["type"], name=r["name"], id=r["id"],
            label=r["label"], required=r["required"],
            options=tuple(r["options"]) if r["options"] is not None else None,
            idx=r["idx"], group=r.get("group", ""),
        )
        for r in await page.evaluate(_DISCOVER_JS, IDX_ATTR)
    ])


def _dedupe(fields: list[FormField]) -> list[FormField]:
    out: list[FormField] = []
    for field in fields:
        if out and out[-1].signature == field.signature:
            continue
        out.append(field)
    return out


async def has_form(page) -> bool:
    return bool(await page.locator("form").count())
