"""state/seed.py — seed the answer bank in one pass (BUILD-PLAN §5.3, P2).

The plan's P2 task is "answer all of them in one sitting (~45 min), commit".
This walks state/questions.seed.yaml so that sitting is one pass over a grouped
catalogue instead of one painful application at a time.

    python -m state.seed                    # interactive, grouped, resumable
    python -m state.seed --missing          # only what the bank still lacks
    python -m state.seed --from-json a.json # bulk load {key: value}, no typing
    python -m state.seed --list             # print the catalogue
    python -m state.seed --coverage         # which catalogue keys are answered

`--from-json` is the fast path: collect the answers however you like, drop them
in a JSON object, load them in one command.

Everything written here is recorded `sourced: true` — your words, which is the
provenance state/answers.py's submit gate demands. Values are typed per the
catalogue's `kind`, so `requires_sponsorship` lands as a real boolean and
`years_react` as a real int rather than the string "5".
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .answers import BANK, AnswerBank, is_placeholder

CATALOGUE = Path(__file__).parent / "questions.seed.yaml"

TRUTHY = {"yes", "y", "true", "1"}
FALSEY = {"no", "n", "false", "0"}


def load_catalogue() -> list[dict]:
    raw = yaml.safe_load(CATALOGUE.read_text()) or {}
    return raw.get("groups") or []


def all_questions() -> list[dict]:
    return [q for g in load_catalogue() for q in (g.get("questions") or [])]


def coerce(value: str, kind: str):
    """Type the answer per the catalogue, so the bank holds real types."""
    text = str(value).strip()
    if kind == "int":
        try:
            return int(text)
        except ValueError:
            return text            # "5+" is a legitimate thing to write
    if kind == "bool":
        low = text.lower()
        if low in TRUTHY:
            return True
        if low in FALSEY:
            return False
        return text
    return text


def unanswered(bank: AnswerBank, questions: list[dict]) -> list[dict]:
    out = []
    for q in questions:
        if q.get("kind") == "template":
            continue               # prose you write, not a value to type
        entry = bank.data.get(q["feeds"])
        if entry is None or (entry.get("sourced") and is_placeholder(entry.get("value"))):
            out.append(q)
    return out


def show_catalogue() -> None:
    n = 0
    for group in load_catalogue():
        print(f"\n\033[1m{group['name']}\033[0m")
        for q in group.get("questions") or []:
            n += 1
            freq = q.get("frequency", "")
            print(f"  {q['id']:>2}. [{freq:9}] {q['q']}")
            print(f"      → {q['feeds']} ({q.get('kind','text')})")
            if q.get("note"):
                print(f"      ! {q['note']}")
    print(f"\n{n} questions.")


def coverage(bank: AnswerBank) -> None:
    qs = [q for q in all_questions() if q.get("kind") != "template"]
    missing = unanswered(bank, qs)
    answered = len(qs) - len(missing)
    print(f"answered {answered}/{len(qs)} catalogue keys")
    if missing:
        print("\nstill needed:")
        for q in missing:
            print(f"  {q['feeds']:22} {q['q']}")


def interactive(bank: AnswerBank, only_missing: bool) -> int:
    written = 0
    for group in load_catalogue():
        questions = group.get("questions") or []
        if only_missing:
            questions = unanswered(bank, questions)
        questions = [q for q in questions if q.get("kind") != "template"]
        if not questions:
            continue

        print(f"\n\033[1m{group['name']}\033[0m")
        if group.get("note"):
            print(f"  {group['note'].strip()}")
        for q in questions:
            current = (bank.data.get(q["feeds"]) or {}).get("value")
            hint = f"  [now: {current!r}]" if current is not None else ""
            if q.get("options"):
                hint += f"  options: {', '.join(map(str, q['options']))}"
            if q.get("note"):
                print(f"\n  ! {q['note']}")
            try:
                raw = input(f"\n  {q['q']}{hint}\n  > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nstopped — answers so far are already saved.")
                return written
            if not raw:
                continue
            if is_placeholder(raw):
                print("    looks like a placeholder — not saved.")
                continue
            bank.write_back(q["feeds"], coerce(raw, q.get("kind", "text")))
            written += 1
    return written


def from_json(bank: AnswerBank, path: Path) -> int:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit("--from-json expects a JSON object of {key: value}")

    kinds = {q["feeds"]: q.get("kind", "text") for q in all_questions()}
    known = set(kinds)
    written, skipped = 0, []
    for key, value in data.items():
        if key not in known:
            skipped.append(key)
        if isinstance(value, str):
            if is_placeholder(value):
                print(f"  skipped {key}: still a placeholder ({value!r})")
                continue
            value = coerce(value, kinds.get(key, "text"))
        bank.write_back(key, value)
        written += 1
    if skipped:
        print(f"  note: not in the catalogue (written anyway): {', '.join(skipped)}")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m state.seed",
        description="Seed the answer bank from the question catalogue.")
    ap.add_argument("--list", action="store_true", help="print the catalogue and exit")
    ap.add_argument("--coverage", action="store_true",
                    help="report which catalogue keys are answered")
    ap.add_argument("--missing", action="store_true",
                    help="only ask what the bank still lacks")
    ap.add_argument("--from-json", type=Path, metavar="FILE",
                    help="bulk load a JSON object of {answer_key: value}")
    ap.add_argument("--bank", type=Path, default=BANK, help="answer bank path")
    args = ap.parse_args(argv)

    if args.list:
        show_catalogue()
        return 0

    if not args.bank.exists():
        args.bank.write_text("{}\n")
        print(f"created {args.bank}")
    bank = AnswerBank(args.bank)

    if args.coverage:
        coverage(bank)
        return 0

    if args.from_json:
        written = from_json(bank, args.from_json)
        print(f"\n{written} answer(s) written to {args.bank}")
        coverage(AnswerBank(args.bank))
        return 0

    written = interactive(bank, only_missing=args.missing)
    print(f"\n{written} answer(s) written to {args.bank}")
    coverage(AnswerBank(args.bank))
    return 0


if __name__ == "__main__":
    sys.exit(main())
