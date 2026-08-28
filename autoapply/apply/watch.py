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


def fetch(board: str, timeout: int = 25) -> list:
    req = urllib.request.Request(API.format(board=board), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8")).get("jobs", [])


def published(job: dict):
    raw = job.get("first_published") or job.get("updated_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except ValueError:
        return None


def age_minutes(job: dict, now):
    dt = published(job)
    return None if dt is None else (now - dt).total_seconds() / 60.0


def matches(job: dict, title_re, loc_re) -> bool:
    return bool(title_re.search(job.get("title", ""))
                and loc_re.search((job.get("location") or {}).get("name", "")))


def sweep(boards: list, title_re, loc_re, max_age: float, seen: set):
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
            key = f"{board}:{job.get('id')}"
            if key in seen:
                continue
            seen.add(key)
            age = age_minutes(job, now)
            if age is None or age > max_age:
                continue
            if not matches(job, title_re, loc_re):
                continue
            job["_board"], job["_age_min"] = board, age
            fresh.append(job)
    fresh.sort(key=lambda j: j["_age_min"])
    return fresh, total, errors


async def act(job: dict, mode: str) -> str:
    from . import runner
    out = await runner.run(
        job["absolute_url"],
        company=job.get("company_name") or job["_board"],
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
    loc = (job.get("location") or {}).get("name", "?")
    when = published(job)
    ist = when.astimezone(IST).strftime("%H:%M IST") if when else "?"
    return (f"{job['_age_min']:6.1f}m  [{job['_board']}] {job.get('title', '?')}\n"
            f"           {loc}  |  posted {ist}\n"
            f"           {job.get('absolute_url', '')}")


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m apply.watch",
        description="Watch Greenhouse boards for freshly posted jobs.")
    ap.add_argument("--boards", default="gitlab,canonical,sportygroup,turing,okx")
    ap.add_argument("--title",
                    default=r"front[- ]?end|react|next\.?js|full[- ]?stack|web engineer")
    ap.add_argument("--location", default=r"india|remote|worldwide|anywhere|global")
    ap.add_argument("--max-age", type=float, default=60.0,
                    help="only act on jobs younger than this many minutes")
    ap.add_argument("--interval", type=int, default=300,
                    help="seconds between sweeps (default 300)")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true", help="SUBMIT to each fresh job")
    args = ap.parse_args(argv)

    paths.init_console()
    mode = ("apply" if args.apply else "dry-run" if args.dry_run
            else "plan" if args.plan else "report")
    boards = [b.strip() for b in args.boards.split(",") if b.strip()]
    title_re, loc_re = re.compile(args.title, re.I), re.compile(args.location, re.I)

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
            fresh, total, errors = sweep(boards, title_re, loc_re, args.max_age, seen)
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
