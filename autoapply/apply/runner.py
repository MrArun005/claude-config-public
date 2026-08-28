"""apply/runner.py — the ladder, wired.

Everything P0–P2 built was a primitive with no caller: `register`,
`set_status`, `may_autosubmit`, `park_for_review`, `dispatch`,
`cache_resolution`, `open_context` and `ensure_session` all had zero callers,
and the only runnable entry point was p0_test.py. This is the orchestrator that
apply/adapter.py's docstring describes but nothing implemented.

    python -m apply.runner <job-url> --company Acme --role "Senior Frontend"

Ladder (apply/adapter.py §4):

  rung 1  deterministic adapter, first matches() wins
  rung 2  adapter raises UnknownField -> Resolver names the answer key, the
          result is cached by (platform, field_signature) so the next run is
          rung 1 again
  rung 3  no adapter matched -> park (the LLM engine is the deferred P3-gate
          decision; parking beats guessing)
  rung 4  anything unexpected -> headed handoff, park, never a blind retry

Submission: this runner auto-submits as soon as state.answers.may_autosubmit()
clears, which makes that gate the last line of defence. See its docstring for
the four conditions. `--dry-run` fills and stops without clicking.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
import time
from pathlib import Path
from typing import Protocol

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

import paths
from identity import browser, session
from state import ledger
from state.answers import AnswerBank, Filled, gate_reasons, park_for_review
from state.checkpoint import Checkpoint

from .adapter import UnknownField, cache_resolution, dispatch
from .adapters.generic_form import GenericFormAdapter
from .fields import platform_of

# A submit click waits this long for a navigation, then proceeds regardless.
SUBMIT_TIMEOUT_MS = 15_000

# A field cannot bounce through rung 2 forever; each pass must make progress.
MAX_RESOLUTION_PASSES = 8

# Statuses that mean "this application is finished, do not touch it again".
TERMINAL = frozenset({"submitted"})


# --------------------------------------------------------------------------
# rung 2: naming the answer key for a field the alias table does not know
# --------------------------------------------------------------------------
class Resolver(Protocol):
    def resolve(self, platform: str, unknown: UnknownField,
                bank: AnswerBank) -> str | None: ...


class NullResolver:
    """Declines every field, so an unknown question parks instead of guessing.

    This is the default, and it is the honest one until the LLM engine is
    chosen at the P3 gate (apply/adapter.py names that as a later decision).
    """

    def resolve(self, platform, unknown, bank) -> str | None:
        return None


class MappingResolver:
    """Resolves from an explicit mapping supplied by a human.

    Keyed by field signature or by the exact label. This is how a one-off
    mapping gets injected without editing state/field-aliases.yaml, and how the
    signature cache is seeded. An LLM resolver drops in behind the same
    protocol.
    """

    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def resolve(self, platform, unknown, bank) -> str | None:
        return self.mapping.get(unknown.field_signature) or self.mapping.get(unknown.label)


# --------------------------------------------------------------------------
def app_id_for(job_url: str) -> str:
    """Deterministic, so a resumed run addresses the same checkpoint."""
    return hashlib.sha1(job_url.encode("utf-8")).hexdigest()[:12]


def _known_platform(host: str):
    """A session.Platform whose name matches this host, if one is registered.

    Most application forms are public and need no login; only registered
    platforms get a session check.
    """
    for plat in session.PLATFORMS.values():
        if plat.name.lower() in host.lower():
            return plat
    return None


async def _find_submit(page):
    for sel in ('button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Submit application")', 'button:has-text("Submit")'):
        loc = page.locator(sel).first
        if await loc.count():
            return loc
    return None


async def run(job_url: str, *, company: str | None = None, role: str | None = None,
              headless: bool = True, dry_run: bool = False,
              plan_only: bool = False,
              resolver: Resolver | None = None,
              bank: AnswerBank | None = None) -> dict:
    """Apply to one job. Returns a result dict; never raises for flow control."""
    started = time.time()
    resolver = resolver or NullResolver()
    bank = bank or AnswerBank()
    app_id = app_id_for(job_url)
    platform = platform_of(job_url)

    con = ledger.connect()
    try:
        return await _run_with_ledger(con, job_url, app_id, platform, company,
                                      role, headless, dry_run, plan_only,
                                      resolver, bank, started)
    finally:
        # Closed here, not in the inner finally: the duplicate-skip path returns
        # before the browser is ever opened, and used to leak the connection.
        con.close()


async def _run_with_ledger(con, job_url, app_id, platform, company, role,
                           headless, dry_run, plan_only, resolver, bank,
                           started) -> dict:
    fresh = ledger.register(con, app_id, job_url, platform)
    if not fresh:
        row = ledger.lookup(con, job_url) or {}
        if row.get("status") in TERMINAL:
            return {"status": "skipped_duplicate", "app_id": app_id,
                    "reason": f"already {row.get('status')} on {row.get('updated_at')}"}
        # Not terminal: a previous run crashed or parked. Resume it.
        ledger.set_status(con, app_id, "started",
                          attempts=(row.get("attempts") or 0) + 1)
    else:
        ledger.set_status(con, app_id, "started", attempts=1)

    ckpt = Checkpoint.load(app_id) or Checkpoint(app_id=app_id, url=job_url)
    ckpt.url = job_url

    template_context = {k: v for k, v in
                        (("company", company), ("role", role)) if v is not None}
    adapters = [GenericFormAdapter(bank=bank, template_context=template_context)]

    pw = ctx = None
    rung = 1
    try:
        pw, ctx = await browser.open_context(headless=headless)

        plat = _known_platform(platform)
        if plat is not None:
            login_as = bank.lookup("email")
            if login_as is None:
                return _park(con, app_id, job_url, rung,
                             ["email in the answer bank is a placeholder, so an "
                              "automated re-login is impossible"], started)
            await session.ensure_session(ctx, plat, str(login_as.value))

        page = await ctx.new_page()
        await page.goto(job_url, wait_until="domcontentloaded")

        adapter = dispatch(adapters, job_url, await page.content())
        if adapter is None:
            rung = 3
            return _park(con, app_id, job_url, rung,
                         ["no adapter matched this page (rung 3: LLM engine is "
                          "the deferred P3-gate decision)"], started)

        if plan_only:
            rows = await adapter.plan(page, {"platform": platform})
            return {"status": "plan", "app_id": app_id, "rung": 1, "plan": rows}

        # --- rungs 1 and 2 ------------------------------------------------
        result = None
        for _ in range(MAX_RESOLUTION_PASSES):
            try:
                result = await adapter.apply(page, {"platform": platform}, ckpt)
                break
            except UnknownField as unknown:
                rung = 2
                key = resolver.resolve(platform, unknown, bank)
                if not key:
                    return _park(con, app_id, job_url, rung,
                                 [f"unknown field, no resolution: {unknown.label}"],
                                 started)
                # Cached so the next run recognises it at rung 1.
                cache_resolution(platform, unknown.field_signature, key)
        if result is None:
            return _park(con, app_id, job_url, rung,
                         [f"still unresolved after {MAX_RESOLUTION_PASSES} passes"],
                         started)

        res = result["_result"]

        # --- the gate -----------------------------------------------------
        reasons = gate_reasons(res.filled, unresolved=res.unresolved,
                               required_unfilled=res.required_unfilled)
        if reasons:
            return _park(con, app_id, job_url, rung, reasons, started,
                         filled=len(res.filled))

        if dry_run:
            ledger.set_status(con, app_id, "checkpointed", rung=rung)
            return {"status": "dry_run", "app_id": app_id, "rung": rung,
                    "filled": len(res.filled), "gate": "passed"}

        submit = await _find_submit(page)
        if submit is None:
            return _park(con, app_id, job_url, rung,
                         ["gate passed but no submit control found on the page"],
                         started, filled=len(res.filled))

        # Bounded waits. `click()` auto-waits for a scheduled navigation, and
        # plenty of ATSs submit over XHR and never schedule one — an unbounded
        # wait there hangs the run rather than finishing it.
        was_at = page.url
        try:
            await submit.click(timeout=SUBMIT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            pass
        try:
            await page.wait_for_load_state("networkidle",
                                           timeout=SUBMIT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            pass

        # There is no generic ATS success signal to verify, so say which of the
        # two observable things happened rather than asserting success.
        navigated = page.url != was_at
        gone = not await submit.count()
        confirmed = navigated or gone

        ledger.set_status(con, app_id, "submitted", rung=rung, human_secs=0)
        if confirmed:
            ckpt.done()
        return {"status": "submitted", "app_id": app_id, "rung": rung,
                "filled": len(res.filled), "landed_on": page.url,
                "confirmed": confirmed,
                "elapsed_s": round(time.time() - started, 1)}

    except Exception as exc:  # rung 4 — never a blind retry
        rung = 4
        ledger.set_status(con, app_id, "failed", rung=rung)
        park_for_review(app_id, job_url,
                        [f"rung 4 headed handoff required: {type(exc).__name__}: {exc}"])
        return {"status": "failed", "app_id": app_id, "rung": rung,
                "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if pw is not None and ctx is not None:
            await browser.close_context(pw, ctx)


def _park(con, app_id: str, job_url: str, rung: int, reasons: list[str],
          started: float, filled: int = 0) -> dict:
    park_for_review(app_id, job_url, reasons)
    ledger.set_status(con, app_id, "checkpointed", rung=rung,
                      human_secs=int(time.time() - started))
    return {"status": "parked", "app_id": app_id, "rung": rung,
            "filled": filled, "reasons": reasons}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m apply.runner",
        description="Apply to one job posting, walking the rung 1-4 ladder.")
    ap.add_argument("job_url")
    ap.add_argument("--company", help="template variable for TEMPLATE answers")
    ap.add_argument("--role", help="template variable for TEMPLATE answers")
    ap.add_argument("--headed", action="store_true",
                    help="run with a visible browser window")
    ap.add_argument("--dry-run", action="store_true",
                    help="fill and report, but never click submit")
    ap.add_argument("--plan", action="store_true",
                    help="show what WOULD be entered, filling nothing at all")
    args = ap.parse_args(argv)

    paths.init_console()
    out = asyncio.run(run(args.job_url, company=args.company, role=args.role,
                          headless=not args.headed, dry_run=args.dry_run,
                          plan_only=args.plan))

    if out.get("status") == "plan":
        rows = out["plan"]
        print(f"{len(rows)} field(s) found. Nothing was filled or submitted.\n")
        for r in rows:
            mark = {"would fill": "+", "would select": "+"}.get(r["verdict"], "!")
            print(f"  {mark} {r['label']}")
            print(f"      key      : {r['key']}")
            if r["value"] is not None:
                print(f"      value    : {r['value']!r}  ({r['provenance']})")
            print(f"      verdict  : {r['verdict']}")
        blocked = [r for r in rows if r["verdict"] not in ("would fill", "would select",
                                                           "skip — intentionally left blank")]
        print(f"\n{len(rows) - len(blocked)}/{len(rows)} ready; "
              f"{len(blocked)} would block the submit gate.")
        return 0 if not blocked else 1

    print(f"status : {out['status']}")
    for key in ("app_id", "rung", "filled", "confirmed", "landed_on", "reason",
                "error", "elapsed_s"):
        if key in out:
            print(f"{key:7}: {out[key]}")
    for reason in out.get("reasons", []):
        print(f"  - {reason}")
    if out["status"] == "parked":
        print(f"\nreview queue: {paths.under('review-queue.jsonl')}")
        print("answer the open questions with:  python -m state.review")
    return 0 if out["status"] in ("submitted", "dry_run", "skipped_duplicate") else 1


if __name__ == "__main__":
    sys.exit(main())
