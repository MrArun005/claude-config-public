"""apply/tabs.py — one Chrome window, one tab per application, left open.

Whether a click actually submitted is genuinely hard to know from inside: forms
that submit over XHR leave the URL unchanged, so a successful send and a silent
validation failure look identical. Rather than keep guessing, this leaves the
evidence on screen — every application gets its own tab, filled and submitted,
and the browser stays open afterwards so a human can scroll through the tabs and
see what each form says.

    python -m apply.tabs jobs.yaml            # apply + submit, leave tabs open
    python -m apply.tabs jobs.yaml --dry-run  # fill every tab, submit nothing

Chrome is launched as a separate process with remote debugging, and Playwright
CONNECTS to it rather than owning it. That is the whole trick: a Playwright-owned
browser dies when this script exits, so the tabs would vanish exactly when you
wanted to read them. Connected this way, Chrome outlives the script.

The profile is the dedicated one from identity/browser.py, never the real Chrome
profile (plan §3.1 — and Chrome >=136 refuses remote debugging on the default
user-data-dir anyway). Close the window yourself when you are done reviewing;
the next run reuses the same profile and its logins.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import paths
from identity import browser as identity_browser
from state.answers import BANK, AnswerBank

from . import runner
from .batch import JobsFileError, load_jobs

DEBUG_PORT = 9222
CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/opt/google/chrome/chrome",
)


def find_chrome() -> str | None:
    if exe := os.environ.get("AUTOAPPLY_CHROME_PATH"):
        return exe if Path(exe).exists() else None
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    return shutil.which("google-chrome") or shutil.which("chromium")


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def launch_chrome(port: int) -> subprocess.Popen | None:
    """Start Chrome with remote debugging on the dedicated profile."""
    exe = find_chrome()
    if exe is None:
        print("no Chrome or Edge found; set AUTOAPPLY_CHROME_PATH", file=sys.stderr)
        return None
    profile = identity_browser.PROFILE
    profile.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [exe, f"--remote-debugging-port={port}",
         f"--user-data-dir={profile}",
         "--no-first-run", "--no-default-browser-check",
         "--disable-blink-features=AutomationControlled",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if port_open(port):
            return proc
        time.sleep(0.25)
    print(f"Chrome did not open the debugging port {port}", file=sys.stderr)
    return None


async def drive(jobs: list, bank: AnswerBank, dry_run: bool, port: int) -> list:
    from playwright.async_api import async_playwright

    results = []
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        ctx = b.contexts[0] if b.contexts else await b.new_context()

        for i, job in enumerate(jobs, 1):
            label = f"[{i}/{len(jobs)}] {job['company']} - {job['role']}"
            print(f"\n{label}\n    {job['url']}")
            out = await runner.run(
                job["url"], company=job["company"], role=job["role"],
                dry_run=dry_run, bank=bank, ctx=ctx)
            out["_job"] = job
            results.append(out)

            line = out["status"]
            if out.get("filled"):
                line += f"  ({out['filled']} fields)"
            if "confirmed" in out:
                line += f"  confirmed={out['confirmed']}"
            if out.get("evidence"):
                line += f"  evidence={out['evidence']!r}"
            print(f"    {line}")
            for reason in out.get("reasons", [])[:3]:
                print(f"      - {reason[:120]}")

        # Deliberately NOT closing: the tabs are the deliverable.
    return results


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m apply.tabs",
        description="Apply to every job in a jobs file, one tab each, "
                    "leaving the browser open for review.")
    ap.add_argument("jobs_file", type=Path)
    ap.add_argument("--bank", type=Path, default=BANK)
    ap.add_argument("--dry-run", action="store_true",
                    help="fill every tab but never click submit")
    ap.add_argument("--port", type=int, default=DEBUG_PORT)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)

    paths.init_console()
    try:
        jobs = load_jobs(args.jobs_file)
    except JobsFileError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.limit:
        jobs = jobs[:args.limit]
    if not args.bank.exists():
        print(f"no answer bank at {args.bank}", file=sys.stderr)
        return 2

    already = port_open(args.port)
    if already:
        print(f"attaching to the Chrome already listening on {args.port}")
        proc = None
    else:
        proc = launch_chrome(args.port)
        if proc is None:
            return 2
        print(f"Chrome opened on the dedicated profile "
              f"({identity_browser.PROFILE})")

    print(f"{len(jobs)} job(s), one tab each, "
          f"{'FILL ONLY' if args.dry_run else 'SUBMITTING'}")

    results = asyncio.run(drive(jobs, AnswerBank(args.bank), args.dry_run,
                                args.port))

    print("\n" + "=" * 70)
    for r in results:
        job = r["_job"]
        extra = ""
        if r["status"] == "submitted":
            extra = f"confirmed={r.get('confirmed')} evidence={r.get('evidence')}"
        elif r["status"] == "parked":
            extra = (r.get("reasons") or [""])[0][:60]
        print(f"  {r['status']:18} {job['company'][:20]:22} {extra}")
    counts: dict = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\n  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"\n  Chrome is STILL OPEN with {len(results)} tab(s). Scroll through them")
    print(f"  and confirm each one yourself, then close the window.")
    print(f"  Screenshots + page text: {paths.under('applications')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
