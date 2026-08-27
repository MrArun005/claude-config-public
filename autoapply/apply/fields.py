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
        base = normalise_label(self.label) or self.name or self.selector
        return f"{base}{' *' if self.required else ''} [{self.tag}/{self.type}]"


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
    if (!lbl) lbl = e.getAttribute('aria-label') || e.placeholder || e.name || '';
    return {
      tag: e.tagName.toLowerCase(),
      type: (e.type || e.tagName.toLowerCase()),
      name: e.name || '',
      id: e.id || '',
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
    """Every fillable control on the page, in document order."""
    return [
        FormField(
            tag=r["tag"], type=r["type"], name=r["name"], id=r["id"],
            label=r["label"], required=r["required"],
            options=tuple(r["options"]) if r["options"] is not None else None,
            idx=r["idx"],
        )
        for r in await page.evaluate(_DISCOVER_JS, IDX_ATTR)
    ]


async def has_form(page) -> bool:
    return bool(await page.locator("form").count())
