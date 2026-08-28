"""apply/batch.py — run a list of jobs through the ladder, one at a time.

    python -m apply.batch jobs.yaml --plan      # inspect the whole list first
    python -m apply.batch jobs.yaml --dry-run   # fill everything, submit nothing
    python -m apply.batch jobs.yaml             # submit

The jobs file carries what the runner cannot infer. A bare list of URLs is not
enough: `company` and `role` feed the TEMPLATE answers, and a form asking "why
this company" parks without them rather than rendering a blank clause.

    # jobs.yaml
    - url: https://boards.greenhouse.io/acme/jobs/123
      company: Acme
      role: Senior Frontend Engineer
      resume: variants/frontend.pdf      # this job gets its own résumé
    - url: https://jobs.lever.co/beta/456
      company: Beta
      role: Staff Engineer
      resume: generic                    # explicitly the generic one
    - url: https://jobs.example.com/789
      company: Example
      role: Frontend Engineer            # omitted -> also the generic one

Résumé selection: name a file for the jobs that need their own, and either say
`generic` or leave it out for the rest. `generic` means `resume_path` from the
answer bank. Relative paths resolve against the jobs file's own directory.
Nothing is inferred — a résumé is never matched to a posting by keyword.

Execution is strictly serial, and not as a policy choice: the browser profile
is single-writer (identity/browser.py holds a lockfile), so two applications
cannot share it. That happens to be what plan §7 wants anyway.

Rate discipline (§7 — per-platform daily caps, randomised human-pace delays) is
NOT implemented. `--delay` is offered as a blunt stand-in; the register's
account-suspension risk is real once more than a couple of applications go out
together.
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from pathlib import Path

import yaml

import paths
from state.answers import BANK, AnswerBank, is_placeholder

from . import runner
from .fields import platform_of

GENERIC = {"generic", "default", "master", "base"}


class JobsFileError(Exception):
    """The jobs file is unusable. Raised before any browser is launched."""


def load_jobs(path: Path) -> list[dict]:
    """Parse and fully validate the jobs file. Fails fast, on everything."""
    if not path.exists():
        raise JobsFileError(f"no such jobs file: {path}")
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise JobsFileError(f"{path} is not valid YAML: {exc}") from exc

    if isinstance(raw, dict):
        raw = raw.get("jobs")
    if not isinstance(raw, list) or not raw:
        raise JobsFileError(
            f"{path} must be a list of jobs (or a mapping with a `jobs:` list)")

    problems: list[str] = []
    jobs: list[dict] = []
    seen: set[str] = set()

    for i, entry in enumerate(raw, 1):
        if not isinstance(entry, dict):
            problems.append(f"job {i}: expected a mapping, got {type(entry).__name__}")
            continue
        url = str(entry.get("url") or "").strip()
        if not url:
            problems.append(f"job {i}: no `url`")
            continue
        if url in seen:
            problems.append(f"job {i}: `url` repeated in this file ({url})")
            continue
        seen.add(url)

        for field in ("company", "role"):
            if not str(entry.get(field) or "").strip():
                problems.append(
                    f"job {i} ({url}): no `{field}` — a form asking "
                    f"'why this company' will park without it")

        resume = entry.get("resume")
        resolved: Path | None = None
        if resume is not None and str(resume).strip().lower() not in GENERIC:
            resolved = Path(str(resume)).expanduser()
            if not resolved.is_absolute():
                resolved = (path.parent / resolved).resolve()
            if not resolved.is_file():
                problems.append(f"job {i} ({url}): résumé not found: {resolved}")

        jobs.append({
            "url": url,
            "company": str(entry.get("company") or "").strip() or None,
            "role": str(entry.get("role") or "").strip() or None,
            "resume": resolved,
        })

    if problems:
        raise JobsFileError(
            f"{len(problems)} problem(s) in {path}:\n  - "
            + "\n  - ".join(problems))
    return jobs


def check_generic_resume(bank: AnswerBank) -> str | None:
    """The generic résumé must exist too, or every job that omits one parks."""
    entry = bank.data.get("resume_path") or {}
    value = entry.get("value")
    if not value or is_placeholder(value):
        return "answer bank has no usable `resume_path` (the generic résumé)"
    if not Path(str(value)).expanduser().is_file():
        return f"generic résumé does not exist: {value}"
    return None


def _bank_for(base_path: Path, resume: Path | None) -> AnswerBank:
    """A bank view for one job, with resume_path swapped when overridden.

    Re-read per job rather than mutating a shared instance, so one job's
    override cannot leak into the next. Note the clone still points at the real
    file, so nothing here may call write_back().
    """
    bank = AnswerBank(base_path)
    if resume is not None:
        bank.data = {**bank.data,
                     "resume_path": {"value": str(resume), "sourced": True}}
    return bank


async def run_batch(jobs: list[dict], *, bank_path: Path, mode: str,
                    delay: float, headless: bool) -> list[dict]:
    results: list[dict] = []
    for i, job in enumerate(jobs, 1):
        label = f"[{i}/{len(jobs)}] {job['company'] or '?'} — {job['role'] or '?'}"
        print(f"\n{label}\n    {job['url']}")
        if job["resume"] is not None:
            print(f"    résumé: {job['resume'].name}")

        out = await runner.run(
            job["url"],
            company=job["company"], role=job["role"],
            headless=headless,
            dry_run=(mode == "dry-run"),
            plan_only=(mode == "plan"),
            bank=_bank_for(bank_path, job["resume"]),
        )
        out["_job"] = job
        results.append(out)

        if mode == "plan":
            rows = out.get("plan", [])
            blocked = [r for r in rows
                       if r["verdict"] not in ("would fill", "would select",
                                               "skip — intentionally left blank")]
            print(f"    {len(rows)} field(s), {len(blocked)} would block:")
            for r in blocked:
                print(f"      ! {r['label']}  ->  {r['verdict']}")
        else:
            print(f"    {out['status']}"
                  + (f"  ({out.get('filled')} fields)" if out.get("filled") else ""))
            for reason in out.get("reasons", [])[:4]:
                print(f"      - {reason[:140]}")

        # Serial by necessity (single-writer profile); the pause is optional.
        if delay and i < len(jobs):
            jitter = delay * random.uniform(0.7, 1.3)
            print(f"    pausing {jitter:.0f}s")
            await asyncio.sleep(jitter)
    return results


def summarise(results: list[dict], mode: str) -> int:
    print("\n" + "=" * 70)
    buckets: dict[str, list[dict]] = {}
    for r in results:
        buckets.setdefault(r["status"], []).append(r)

    width = max((len(r["_job"]["company"] or "?") for r in results), default=8) + 2
    for r in results:
        job = r["_job"]
        note = ""
        if r["status"] == "parked":
            note = (r.get("reasons") or [""])[0][:70]
        elif r["status"] == "skipped_duplicate":
            note = r.get("reason", "")[:70]
        elif r["status"] == "failed":
            note = r.get("error", "")[:70]
        print(f"  {r['status']:18} {(job['company'] or '?'):<{width}} {note}")

    print("\n  " + "  ".join(f"{k}={len(v)}" for k, v in sorted(buckets.items())))
    by_platform: dict[str, int] = {}
    for r in results:
        by_platform[platform_of(r["_job"]["url"])] = \
            by_platform.get(platform_of(r["_job"]["url"]), 0) + 1
    if len(by_platform) > 1 or mode != "plan":
        print("  per platform: "
              + ", ".join(f"{k}={v}" for k, v in sorted(by_platform.items())))

    parked = buckets.get("parked", [])
    if parked:
        print(f"\n  {len(parked)} parked. Answer them and they stop parking:")
        print("    python -m state.review")
    return 0 if not (buckets.get("parked") or buckets.get("failed")) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m apply.batch",
        description="Apply to every job in a jobs file, one at a time.")
    ap.add_argument("jobs_file", type=Path)
    ap.add_argument("--bank", type=Path, default=BANK, help="answer bank path")
    ap.add_argument("--plan", action="store_true",
                    help="show what WOULD be entered for every job; fill nothing")
    ap.add_argument("--dry-run", action="store_true",
                    help="fill every form but never click submit")
    ap.add_argument("--headed", action="store_true", help="visible browser")
    ap.add_argument("--delay", type=float, default=0.0, metavar="SECONDS",
                    help="pause between jobs, randomised ±30%% (a blunt stand-in "
                         "for the rate discipline of plan §7)")
    ap.add_argument("--limit", type=int, help="stop after this many jobs")
    args = ap.parse_args(argv)

    paths.init_console()
    mode = "plan" if args.plan else ("dry-run" if args.dry_run else "submit")

    try:
        jobs = load_jobs(args.jobs_file)
    except JobsFileError as exc:
        print(f"{exc}", file=sys.stderr)
        return 2

    if not args.bank.exists():
        print(f"no answer bank at {args.bank}", file=sys.stderr)
        return 2
    bank = AnswerBank(args.bank)

    # Only matters if some job relies on the generic résumé.
    if any(j["resume"] is None for j in jobs):
        problem = check_generic_resume(bank)
        if problem:
            print(f"{problem}\n"
                  f"Either fix resume_path, or name a `resume:` for every job.",
                  file=sys.stderr)
            return 2

    if args.limit:
        jobs = jobs[:args.limit]

    print(f"{len(jobs)} job(s), mode={mode}, serial (single-writer profile)")
    if mode == "submit":
        print("SUBMITTING — every job whose gate clears goes to the employer.")
    started = time.time()
    results = asyncio.run(run_batch(jobs, bank_path=args.bank, mode=mode,
                                    delay=args.delay,
                                    headless=not args.headed))
    code = summarise(results, mode)
    print(f"  elapsed {time.time() - started:.1f}s")
    return code


if __name__ == "__main__":
    sys.exit(main())
