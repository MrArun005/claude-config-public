"""state/questions.py — remember every question any form has ever asked.

The expensive part of applying is not filling a form, it is answering a question
for the first time. Plan §5.3 makes the point: escalations are per unique
question, not per application, so a question answered once should never be asked
again. That only holds if the questions are *recorded* — otherwise each new
posting rediscovers the same gaps and the same fields park forever.

Every run appends what it saw to $AUTOAPPLY_HOME/questions.jsonl, keyed by field
signature: the question text, whether it mapped to a bank key, whether it was
required, and which platform asked. From that you get the one report that
matters — the questions still unanswered, ordered by how often they come up.

    python -m state.questions                # unanswered, most frequent first
    python -m state.questions --all          # everything ever seen
    python -m state.questions --answer <sig> # bank an answer for one

Nothing here decides an answer. It only makes sure no question is met twice
without you having had the chance to answer it once.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import paths

LOG = "questions.jsonl"


def log_path() -> Path:
    return paths.under(LOG)


def record(entries: list[dict]) -> None:
    """Append what one pass over a form saw. Cheap, append-only, never blocks."""
    if not entries:
        return
    p = log_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    except OSError:
        pass          # a logging failure must never break an application


def load() -> list[dict]:
    p = log_path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def summarise(rows: list[dict]) -> dict:
    """Collapse the log to one entry per signature, with a seen-count."""
    by_sig: dict[str, dict] = {}
    counts: Counter = Counter()
    for r in rows:
        sig = r.get("signature") or r.get("question", "")
        counts[sig] += 1
        prev = by_sig.get(sig)
        # Keep the most informative sighting: a mapped one beats an unmapped one.
        if prev is None or (not prev.get("key") and r.get("key")):
            by_sig[sig] = dict(r)
    for sig, entry in by_sig.items():
        entry["seen"] = counts[sig]
    return by_sig


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m state.questions",
        description="Every question the forms have asked, and which are unanswered.")
    ap.add_argument("--all", action="store_true", help="include answered ones")
    ap.add_argument("--answer", metavar="SIGNATURE",
                    help="bank an answer for one question (prompts for the value)")
    ap.add_argument("--key", help="with --answer: the bank key to write")
    args = ap.parse_args(argv)

    paths.init_console()
    rows = load()
    if not rows:
        print(f"nothing recorded yet at {log_path()}")
        return 0

    entries = summarise(rows)
    print(f"{len(rows)} sighting(s) of {len(entries)} distinct question(s)\n")

    if args.answer:
        from .answers import BANK, AnswerBank
        entry = entries.get(args.answer)
        if entry is None:
            print(f"no question with signature {args.answer!r}", file=sys.stderr)
            return 2
        key = args.key or entry.get("key")
        if not key:
            print("this question has no bank key yet; pass --key to name one,\n"
                  "and add a matching rule to state/field-aliases.yaml so it maps"
                  " next time.", file=sys.stderr)
            return 2
        print(f"question: {entry.get('question','')[:200]}")
        try:
            value = input("answer  > ").strip()
        except (EOFError, KeyboardInterrupt):
            return 1
        if not value:
            print("nothing written.")
            return 0
        bank = AnswerBank(BANK)
        bank.write_back(key, value)
        print(f"wrote {key} to {BANK}")
        return 0

    shown = [e for e in entries.values() if args.all or not e.get("key")]
    shown.sort(key=lambda e: (-e.get("seen", 0), e.get("question", "")))
    if not shown:
        print("every question seen so far maps to a bank key.")
        return 0

    for e in shown:
        mark = "OK " if e.get("key") else "-- "
        req = " *" if e.get("required") else ""
        print(f"  {mark} seen {e.get('seen', 1):>2}x  {e.get('question', '')[:88]}{req}")
        print(f"        sig={e.get('signature', '')}  key={e.get('key') or '(none)'}"
              f"  platform={e.get('platform', '')}")
    print(f"\n{sum(1 for e in shown if not e.get('key'))} question(s) still have no "
          f"bank key. Add a rule to state/field-aliases.yaml, then:")
    print("  python -m state.questions --answer <sig> --key <bank_key>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
