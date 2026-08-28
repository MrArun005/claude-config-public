"""apply/watch.py — catch a posting while it is still minutes old.

Applications get read roughly in arrival order, so being early is worth more
than being polished. This polls Greenhouse board APIs, spots jobs whose
`first_published` falls inside a freshness window, and hands the fresh ones to
the ladder.

    python -m apply.watch --once                    # one sweep, report only
    python -m apply.watch --max-age 60 --plan       # keep watching, plan each
    python -m apply.watch --interval 300 --apply    # keep watching, SUBMIT

Detection latency is the poll interval, so a 300s interval finds a posting a
median of ~2.5 minutes old and at worst 5, leaving the ladder's ~25s well
inside a 10-minute target.

Two safety properties, both deliberate:

  * `--max-age` (default 60 min) is an absolute filter, not merely a first-run
    guard. A board holds hundreds of old postings; without it the first sweep
    would try to apply to all of them.
  * The first sweep NEVER acts. It records a baseline and reports what it saw,
    so a mistyped filter costs nothing.

This reads Greenhouse's public JSON board API, a documented feed meant to be
consumed. It deliberately touches no site whose operator has asked agents to
stay away — check robots.txt before adding a source.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import paths

from . import sources

IST = timezone(timedelta(hours=5, minutes=30))
API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
UA = "autoapply/1.0 (personal job search)"
SEEN = "watch-seen.json"

READY_VERDICTS = ("would fill", "would select")


def _seen_path() -> Path:
    return paths.under(SEEN)


def load_seen() -> set:
    p = _seen_path()
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen(seen: set) -> None:
    p = _seen_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(seen)[-20000:]))


def fetch(board: str) -> list:
    """Normalised postings for a board written as "platform:slug".

    A bare slug means greenhouse, so older invocations keep working.
    """
    platform, _, slug = board.partition(":")
    if not slug:
        platform, slug = "greenhouse", platform
    return sources.fetch(platform, slug)


def published(job: dict):
    return job.get("published")


def age_minutes(job: dict, now):
    dt = published(job)
    return None if dt is None else (now - dt).total_seconds() / 60.0


def matches(job: dict, title_re, loc_re, drop_re=None) -> bool:
    title = job.get("title", "")
    if drop_re is not None and drop_re.search(title):
        return False
    return bool(title_re.search(title)
                and loc_re.search(job.get("location") or ""))


def sweep(boards: list, title_re, loc_re, max_age: float, seen: set,
          drop_re=None):
    """Returns (fresh matching jobs, total scanned, errors)."""
    now = datetime.now(timezone.utc)
    fresh, total, errors = [], 0, []
    for board in boards:
        try:
            jobs = fetch(board)
        except Exception as exc:
            errors.append(f"{board}: {type(exc).__name__}")
            continue
        total += len(jobs)
        for job in jobs:
            key = f"{board}|{job.get('url', '')}"
            if key in seen:
                continue
            seen.add(key)
            age = age_minutes(job, now)
            if age is None or age > max_age:
                continue
            if not matches(job, title_re, loc_re, drop_re):
                continue
            job["_board"], job["_age_min"] = board, age
            fresh.append(job)
    fresh.sort(key=lambda j: j["_age_min"])
    return fresh, total, errors


async def act(job: dict, mode: str) -> str:
    from . import runner
    out = await runner.run(
        job["url"],
        company=job["_board"].partition(":")[2] or job["_board"],
        role=job.get("title"),
        plan_only=(mode == "plan"),
        dry_run=(mode == "dry-run"),
    )
    if out["status"] == "plan":
        rows = out.get("plan", [])
        ready = [r for r in rows if r["verdict"] in READY_VERDICTS]
        return f"plan: {len(ready)}/{len(rows)} ready"
    filled = out.get("filled")
    return out["status"] + (f" ({filled} filled)" if filled else "")


def describe(job: dict) -> str:
    loc = job.get("location") or "?"
    when = published(job)
    ist = when.astimezone(IST).strftime("%H:%M IST") if when else "?"
    return (f"{job['_age_min']:6.1f}m  [{job['_board']}] {job.get('title', '?')}\n"
            f"           {loc}  |  posted {ist}\n"
            f"           {job.get('url', '')}")


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m apply.watch",
        description="Watch Greenhouse boards for freshly posted jobs.")
    ap.add_argument("--boards", default="gitlab,canonical,sportygroup,turing,okx",
                    help='comma-separated "platform:slug" (a bare slug means greenhouse)')
    ap.add_argument("--boards-file",
                    help="YAML written by apply.sources --discover -o")
    # "Senior Software Engineer" is the commonest title for this job, and the
    # old frontend-only default excluded it -- 12 matches instead of 286 across
    # the same ten boards. Breadth here, precision via --exclude.
    ap.add_argument("--title",
                    default=r"software engineer|front[- ]?end|react|next\.?js|"
                            r"full[- ]?stack|web engineer|\bsde\b|developer")
    ap.add_argument("--exclude",
                    default=r"sales|account executive|recruit|marketing|"
                            r"customer success|professional services|salesforce|"
                            r"support engineer|solutions? (architect|engineer)|"
                            r"data engineer|machine learning|\bqa\b|manager|director",
                    help="regex; titles matching this are dropped first")
    ap.add_argument("--location",
                    default=r"india|bangalore|bengaluru|hyderabad|pune|chennai|"
                            r"remote|worldwide|anywhere|global")
    ap.add_argument("--max-age", type=float, default=60.0,
                    help="only act on jobs younger than this many minutes")
    ap.add_argument("--interval", type=int, default=300,
                    help="seconds between sweeps (default 300)")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--newest", type=int, metavar="N",
                    help="report the N freshest matches regardless of age or "
                         "whether they have been seen; never acts")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true", help="SUBMIT to each fresh job")
    args = ap.parse_args(argv)

    paths.init_console()
    mode = ("apply" if args.apply else "dry-run" if args.dry_run
            else "plan" if args.plan else "report")
    boards = [b.strip() for b in args.boards.split(",") if b.strip()]
    if args.boards_file:
        import yaml
        with open(args.boards_file, encoding="utf-8") as fh:
            spec = yaml.safe_load(fh) or {}
        boards = [f"{b['platform']}:{b['slug']}" for b in spec.get("boards", [])]
    title_re, loc_re = re.compile(args.title, re.I), re.compile(args.location, re.I)
    drop_re = re.compile(args.exclude, re.I) if args.exclude else None

    if args.newest:
        # A one-shot "what is newest right now" query. Ignores the seen-set and
        # the age filter, and deliberately never acts -- this is for looking.
        now = datetime.now(timezone.utc)
        found = []
        for board in boards:
            try:
                jobs = fetch(board)
            except Exception as exc:
                print(f"  {board}: {type(exc).__name__} - skipped", file=sys.stderr)
                continue
            for job in jobs:
                if not matches(job, title_re, loc_re, drop_re):
                    continue
                age = age_minutes(job, now)
                if age is None:
                    continue
                job["_board"], job["_age_min"] = board, age
                found.append(job)
        found.sort(key=lambda j: j["_age_min"])
        print(f"\n{len(found)} matching postings across {len(boards)} board(s); "
              f"showing the {min(args.newest, len(found))} freshest\n")
        for job in found[:args.newest]:
            age = job["_age_min"]
            when = (f"{age / 60:.1f}h" if age < 2880 else f"{age / 1440:.0f}d")
            loc = job.get("location") or "?"
            stamp = published(job)
            ist = stamp.astimezone(IST).strftime("%d %b %H:%M IST") if stamp else "?"
            print(f"  {when:>6} old  {job.get('title', '?')}  [{job['_board']}]")
            print(f"              {loc}  |  posted {ist}")
            print(f"              {job.get('url', '')}\n")
        return 0

    seen = load_seen()
    first_run = not seen
    print(f"watching {len(boards)} board(s) every {args.interval}s | "
          f"fresh = under {args.max_age:.0f} min | mode={mode}")
    if first_run:
        print("first sweep: recording a baseline, acting on nothing.")
    if mode == "apply":
        print("SUBMIT MODE - anything whose gate clears goes to the employer.")

    try:
        while True:
            t0 = time.time()
            fresh, total, errors = sweep(boards, title_re, loc_re, args.max_age,
                                         seen, drop_re)
            save_seen(seen)
            stamp = datetime.now(IST).strftime("%H:%M:%S")
            print(f"\n[{stamp} IST] scanned {total} | {len(fresh)} fresh match(es)"
                  + (f" | errors: {', '.join(errors)}" if errors else ""))

            for job in fresh:
                print("  " + describe(job))
                if first_run or mode == "report":
                    continue
                print(f"           -> {asyncio.run(act(job, mode))}")

            first_run = False
            if args.once:
                return 0
            time.sleep(max(30, args.interval - (time.time() - t0)))
    except KeyboardInterrupt:
        print("\nstopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
