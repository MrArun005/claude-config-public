"""apply/aliases.py — map a discovered field onto an answer-bank key.

Pure lookup, no inference. Either the table names a key for this field or the
caller gets None and the field escalates to rung 2. The table is data
(`state/field-aliases.yaml`) so onboarding a new question is an edit, not a
code change.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from .fields import FormField, normalise_label, normalise_name

TABLE = Path(__file__).resolve().parent.parent / "state" / "field-aliases.yaml"

# Keys the bank does not store directly but that follow mechanically from a
# value it does store. A mechanical split of a sourced value is still sourced —
# nothing is being composed or guessed.
DERIVED: dict[str, tuple[str, str]] = {
    "first_name": ("full_name", "first"),
    "last_name": ("full_name", "last"),
}


# An essay prompt is not a form label. Real ATS forms ask things like "please
# share your rationale or evidence for the high school performance selections
# above…" — 200+ characters that happen to contain a keyword. The bank's short
# answers are never right for those, so anything this long parks for a human.
# Verified against a live Canonical Greenhouse form, where the greedy
# `school|university` rule would otherwise have typed a university name into
# three unrelated essay boxes.
MAX_LABEL_LEN = 120


@lru_cache(maxsize=1)
def _table() -> tuple[dict[str, str],
                      tuple[tuple[re.Pattern[str], str, str | None], ...],
                      tuple[re.Pattern[str], ...]]:
    raw = yaml.safe_load(TABLE.read_text()) or {}
    by_name = {k.lower(): v for k, v in (raw.get("by_name") or {}).items()}
    never = tuple(re.compile(pat, re.I) for pat in (raw.get("never_map") or []))
    by_label = tuple(
        (re.compile(rule["match"], re.I), rule["key"], rule.get("type"))
        for rule in (raw.get("by_label") or [])
    )
    return by_name, by_label, never


def key_for(field: FormField) -> str | None:
    """Answer-bank key for this field, or None if the table does not know it."""
    by_name, by_label, never = _table()

    label_raw = normalise_label(field.label)

    # Blocklist first: these are questions that merely CONTAIN a keyword the
    # table knows, and answering them from the bank would be confidently wrong.
    for pattern in never:
        if pattern.search(label_raw):
            return None
    if len(label_raw) > MAX_LABEL_LEN:
        return None

    name = normalise_name(field.name).lower().strip("[]_ ")
    if name in by_name:
        return by_name[name]

    label = normalise_label(field.label)
    if label:
        for pattern, key, want_type in by_label:
            # An optional `type:` constraint lets one label mean two things:
            # "Cover letter" on a file input is a document, on a textarea it is
            # prose. Without this the first rule would swallow both.
            if want_type and not re.fullmatch(want_type, field.type, re.I):
                continue
            if pattern.search(label):
                return key
    return None


def derive(key: str, bank_value) -> object | None:
    """Compute a DERIVED key from the value it is derived from."""
    if key not in DERIVED:
        return None
    _, part = DERIVED[key]
    words = str(bank_value or "").split()
    if len(words) < 2:
        return None  # can't split a single token into first/last — park instead
    return words[0] if part == "first" else " ".join(words[1:])


def source_key(key: str) -> str:
    """The bank key a (possibly derived) key ultimately reads from."""
    return DERIVED[key][0] if key in DERIVED else key
