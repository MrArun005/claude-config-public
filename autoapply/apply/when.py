"""apply/when.py — when do these boards actually post jobs?

Being early matters, so it is worth knowing when to be watching. This reads
`first_published` across whole boards and prints the distribution in YOUR
timezone, rather than repeating folklore about Tuesday mornings.

    python -m apply.when
    python -m apply.when --boards zomato,swiggy,razorpay --tz 5.5

The answer depends entirely on which boards you sample: US and EU companies
post during their own working hours, which lands in the Indian evening. Sample
India-headquartered boards and the curve moves to IST business hours. Always
sample the boards you actually apply to.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import paths

from .watch import fetch, published

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def bar(n: int, peak: int, width: int = 34) -> str:
    return "#" * int(width * n / peak) if peak else ""


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m apply.when",
        description="Distribution of job posting times across Greenhouse boards.")
    ap.add_argument("--boards", default="gitlab,canonical,sportygroup,turing,okx")
    ap.add_argument("--tz", type=float, default=5.5,
                    help="your UTC offset in hours (default 5.5 = IST)")
    ap.add_argument("--title", default="", help="only count titles matching this regex")
    args = ap.parse_args(argv)

    paths.init_console()
    tz = timezone(timedelta(hours=args.tz))
    label = f"UTC{args.tz:+g}"

    import re
    title_re = re.compile(args.title, re.I) if args.title else None

    stamps, boards = [], [b.strip() for b in args.boards.split(",") if b.strip()]
    for board in boards:
        try:
            jobs = fetch(board)
        except Exception as exc:
            print(f"  {board}: {type(exc).__name__} - skipped", file=sys.stderr)
            continue
        for job in jobs:
            if title_re and not title_re.search(job.get("title", "")):
                continue
            dt = published(job)
            if dt:
                stamps.append(dt.astimezone(tz))

    if not stamps:
        print("no postings matched.", file=sys.stderr)
        return 1

    print(f"\n{len(stamps)} postings across {len(boards)} board(s), times in {label}\n")

    byday = Counter(d.weekday() for d in stamps)
    peak = max(byday.values())
    print("by weekday:")
    for i, name in enumerate(DAYS):
        n = byday.get(i, 0)
        print(f"  {name}  {bar(n, peak, 30):<30} {n:4}  {100 * n / len(stamps):4.1f}%")

    byhour = Counter(d.hour for d in stamps)
    peak = max(byhour.values())
    print("\nby hour:")
    for h in range(24):
        n = byhour.get(h, 0)
        mark = "  <-- peak" if n == peak else ""
        print(f"  {h:02d}:00  {bar(n, peak):<34} {n:4}{mark}")

    top = [h for h, _ in byhour.most_common(5)]
    weekday = sum(1 for d in stamps if d.weekday() < 5)
    print(f"\nbusiest hours ({label}): "
          + ", ".join(f"{h:02d}:00" for h in sorted(top)))
    print(f"weekdays account for {100 * weekday / len(stamps):.1f}% of postings")
    print(f"\nWatch that window:  python -m apply.watch --interval 300 --plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
