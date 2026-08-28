"""state/answers.py — the answer bank + the submit gate.

The agent SELECTS; it never composes. Every submitted field is either
sourced (you wrote it) or rendered from a template you approved.
Anything else parks the application in the review queue — never guess.

Because the runner auto-submits the moment `may_autosubmit()` returns True,
this gate is the only thing standing between the tool and a real employer.
It therefore checks four things, not one:

  1. every filled field is `sourced` or `template`;
  2. no field the form marks *required* was left unfilled — the original
     one-argument gate only inspected fields that happened to get filled, so a
     required question the adapter never recognised sailed straight through;
  3. no value is still a placeholder. `answers.yaml` ships with
     `email: TODO@gmail.com` marked `sourced: true`, so without this the very
     first run would have mailed "TODO@gmail.com" to a real company;
  4. every TEMPLATE value was actually rendered, not passed through as the
     ("TEMPLATE", path) marker tuple.
"""
from __future__ import annotations

import json, re, time
from dataclasses import dataclass
from pathlib import Path

import paths
import yaml  # pip install pyyaml

BANK = Path(__file__).parent / "answers.yaml"
REVIEW_QUEUE = paths.under("review-queue.jsonl")

# Deliberately narrow: these are the shapes the shipped template actually uses
# (TODO markers and the ₹XX–YY salary stub). A conservative pattern that misses
# an exotic placeholder is recoverable; one that flags a real answer would park
# every application forever.
PLACEHOLDER = re.compile(
    r"""
      \bTODO\b            # TODO, TODO@example.com, +00-TODO
    | \bX{2,}\b           # ₹XX–YY LPA
    | \bY{2,}\b
    | \?{2,}              # ??
    """,
    re.IGNORECASE | re.VERBOSE,
)

TEMPLATE_MARKER = "TEMPLATE"


def is_placeholder(value) -> bool:
    """True when a value is still a stub rather than a real answer.

    Only strings are inspected: `False` is a legitimate answer to
    "requires sponsorship?", and `0` a legitimate number of years.
    """
    if value is None:
        return True
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return False
    if isinstance(value, tuple):  # unrendered ("TEMPLATE", path) marker
        return True
    text = str(value).strip()
    return not text or bool(PLACEHOLDER.search(text))


@dataclass
class Filled:
    name: str
    value: object
    provenance: str  # "sourced" | "template" | "inferred"


class AnswerBank:
    def __init__(self, path: Path = BANK):
        self.path = path
        self.data: dict = yaml.safe_load(path.read_text()) if path.exists() else {}

    def lookup(self, question_key: str) -> Filled | None:
        entry = self.data.get(question_key)
        if not entry:
            return None
        if entry.get("sourced"):
            value = entry.get("value")
            if is_placeholder(value):
                return None  # a stub is not an answer — escalate, don't submit
            return Filled(question_key, value, "sourced")
        if entry.get("policy") == TEMPLATE_MARKER:
            return Filled(question_key, (TEMPLATE_MARKER, entry["template"]), "template")
        return None

    def template_path(self, question_key: str) -> Path | None:
        """Resolve a TEMPLATE entry's path relative to this bank's directory."""
        entry = self.data.get(question_key) or {}
        if entry.get("policy") != TEMPLATE_MARKER:
            return None
        return (self.path.parent / entry["template"]).resolve()

    def select_alt(self, question_key: str):
        """A canonical alternate for CONSTRAINED controls.

        Applies to dropdowns, radio groups and number inputs — the name is
        historical, the use is broader. A number input silently rejects
        "₹14 LPA (negotiable)"; `select_as: "14"` gives it the bare figure.

        "90 days (negotiable to 60)" is the right answer to a free-text notice
        question and matches no dropdown option, so a `select_as: "90 days"`
        lets one entry serve both without ever approximating: both strings are
        yours, and the dropdown gets the one that is actually on offer.
        """
        return (self.data.get(question_key) or {}).get("select_as")

    def write_back(self, question_key: str, value) -> None:
        """Every review-queue answer feeds the bank so it never parks again.

        Preserves sidecar keys such as `select_as`: re-answering a question
        should not silently discard the dropdown alternate set alongside it.
        """
        entry = dict(self.data.get(question_key) or {})
        entry.update({"value": value, "sourced": True})
        entry.pop("policy", None)      # an explicit value supersedes TEMPLATE
        self.data[question_key] = entry
        self.path.write_text(yaml.safe_dump(self.data, allow_unicode=True, sort_keys=True))


def gate_reasons(
    filled: dict[str, Filled],
    *,
    unresolved: list[str] | tuple[str, ...] = (),
    required_unfilled: list[str] | tuple[str, ...] = (),
) -> list[str]:
    """Why this application may NOT be auto-submitted. Empty list == cleared."""
    reasons: list[str] = []

    # Deliberately NOT blocking on `unresolved`: leaving an OPTIONAL question
    # blank is an ordinary, honest submission. The rule is never to invent an
    # answer, not to answer everything. Required fields are enforced below, and
    # unresolved ones are still reported so the bank can be improved.
    _ = unresolved
    for name in required_unfilled:
        reasons.append(f"required field not filled: {name}")

    for name, f in filled.items():
        if f.provenance not in ("sourced", "template"):
            reasons.append(f"{name}: provenance is {f.provenance!r}, not sourced/template")
        if isinstance(f.value, tuple) and f.value and f.value[0] == TEMPLATE_MARKER:
            reasons.append(f"{name}: template was never rendered")
        elif is_placeholder(f.value):
            reasons.append(f"{name}: value is still a placeholder ({f.value!r})")
    return reasons


def may_autosubmit(
    filled: dict[str, Filled],
    *,
    unresolved: list[str] | tuple[str, ...] = (),
    required_unfilled: list[str] | tuple[str, ...] = (),
) -> bool:
    return not gate_reasons(
        filled, unresolved=unresolved, required_unfilled=required_unfilled
    )


def park_for_review(app_id: str, url: str, unresolved: list[str]) -> None:
    REVIEW_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_QUEUE.open("a") as fh:
        fh.write(json.dumps({
            "app_id": app_id, "url": url, "unresolved": unresolved,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }) + "\n")
