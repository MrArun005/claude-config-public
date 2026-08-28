"""state/review.py — drain the review queue back into the answer bank.

`AnswerBank.write_back()` carries the promise "Every review-queue answer feeds
the bank so it never parks again", but nothing called it, so a parked
application parked again on every subsequent run. This closes that loop.

    python -m state.review              # walk the queue, answer, write back
    python -m state.review --list       # just show what is parked
    python -m state.review --clear      # drop entries already dealt with

Answers you type here are recorded `sourced: true` — they are your words, which
is exactly the provenance the submit gate demands.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .answers import BANK, REVIEW_QUEUE, AnswerBank, is_placeholder


def _entries() -> list[dict]:
    if not REVIEW_QUEUE.exists():
        return []
    out = []
    for line in REVIEW_QUEUE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a torn last line beats losing the whole queue
    return out


def show(entries: list[dict]) -> None:
    if not entries:
        print("review queue is empty.")
        return
    for i, e in enumerate(entries, 1):
        print(f"\n[{i}] {e.get('app_id','?')}  {e.get('ts','')}")
        print(f"    {e.get('url','')}")
        for reason in e.get("unresolved", []):
            print(f"    - {reason}")


def fill_gaps(bank: AnswerBank) -> int:
    """Prompt for every bank key that is missing or still a placeholder."""
    stubs = [k for k, v in sorted(bank.data.items())
             if (v or {}).get("sourced") and is_placeholder((v or {}).get("value"))]
    if not stubs:
        print("no placeholder values left in the answer bank.")
        return 0

    print(f"{len(stubs)} answer(s) are still placeholders. These are what block "
          f"auto-submit.\nPress Enter to skip any one of them.\n")
    written = 0
    for key in stubs:
        current = bank.data[key].get("value")
        try:
            answer = input(f"  {key}  (currently {current!r})\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nstopped.")
            break
        if not answer:
            continue
        if is_placeholder(answer):
            print("    still looks like a placeholder — not saved.")
            continue
        bank.write_back(key, answer)
        written += 1
        print("    saved.")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m state.review",
        description="Answer parked questions and write them back to the bank.")
    ap.add_argument("--list", action="store_true", help="show the queue and exit")
    ap.add_argument("--clear", action="store_true", help="empty the queue and exit")
    ap.add_argument("--bank", type=Path, default=BANK, help="answer bank path")
    args = ap.parse_args(argv)

    paths.init_console()
    entries = _entries()

    if args.clear:
        if REVIEW_QUEUE.exists():
            REVIEW_QUEUE.unlink()
        print(f"cleared {len(entries)} queue entr{'y' if len(entries)==1 else 'ies'}.")
        return 0

    show(entries)
    if args.list:
        return 0

    if not args.bank.exists():
        print(f"\nno answer bank at {args.bank} — copy the example first:\n"
              f"  cp state/answers.example.yaml state/answers.yaml", file=sys.stderr)
        return 2

    print()
    written = fill_gaps(AnswerBank(args.bank))
    if written:
        print(f"\n{written} answer(s) written to {args.bank}. "
              f"Re-run the application and it will not park on these again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
