"""P3 exit-criterion runner — the execution ladder, end to end.

Plain script, no pytest, matching p0_test.py's convention (pytest is not a
dependency).

    python p3_test.py

Everything runs against REAL Chromium driving REAL forms served over HTTP on
127.0.0.1, so goto / fill / select / submit are genuinely exercised rather than
mocked. State is redirected to a throwaway $AUTOAPPLY_HOME, so a run cannot
touch the real ledger, checkpoints, profile or answer bank.

What is NOT covered here, and cannot be from this machine: the Gmail IMAP OTP
path (needs your app password — that is p0_test.py) and any real ATS form
(needs a live posting and a logged-in session).
"""
from __future__ import annotations

import asyncio
import functools
import glob
import http.server
import json
import os
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

FIXTURES = Path(__file__).parent / "tests" / "fixtures"

# Redirect all state BEFORE importing anything that resolves a path at import.
STATE_HOME = Path(tempfile.mkdtemp(prefix="autoapply-p3-"))
os.environ["AUTOAPPLY_HOME"] = str(STATE_HOME)

# This image ships a Chromium revision that pip-installed Playwright does not
# expect, and has no system Chrome, so point at the binary explicitly.
if "AUTOAPPLY_CHROME_PATH" not in os.environ:
    for pattern in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                    "/opt/pw-browsers/chromium-*/chrome-linux64/chrome"):
        found = sorted(glob.glob(pattern))
        if found:
            os.environ["AUTOAPPLY_CHROME_PATH"] = found[-1]
            break

from apply import runner                                       # noqa: E402
from state import ledger                                       # noqa: E402
from state.answers import AnswerBank                           # noqa: E402
from state.checkpoint import Checkpoint                        # noqa: E402

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((PASS if ok else FAIL, name, detail))
    print(f"  {PASS if ok else FAIL}  {name}" + (f"   — {detail}" if detail else ""))
    return ok


# --------------------------------------------------------------------------
# fixture server
# --------------------------------------------------------------------------
SUBMISSIONS: list[str] = []


class _Quiet(http.server.SimpleHTTPRequestHandler):
    """Records every request. The fixture forms submit to thanks.html, so a hit
    there is server-side proof a submit really happened — checking the browser
    for empty inputs proves nothing, since a fresh page load is always empty."""

    def do_GET(self):
        if "thanks.html" in self.path:
            SUBMISSIONS.append(self.path)
        return super().do_GET()

    def log_message(self, *args):  # keep the harness output readable
        pass


def serve(directory: Path):
    handler = functools.partial(_Quiet, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


# --------------------------------------------------------------------------
# banks (fake data only — this file is committed)
# --------------------------------------------------------------------------
COMPLETE_BANK = """
full_name:            { value: "Test Candidate",             sourced: true }
email:                { value: "candidate@example.com",      sourced: true }
phone:                { value: "+1-555-0100",                sourced: true }
location:             { value: "Bengaluru, India",           sourced: true }
notice_period:        { value: "30 days",                    sourced: true }
years_experience:     { value: 5,                            sourced: true }
years_react:          { value: 5,                            sourced: true }
requires_sponsorship: { value: false,                        sourced: true }
linkedin:             { value: "https://linkedin.com/in/test", sourced: true }
"""

STUB_BANK = COMPLETE_BANK.replace(
    '{ value: "candidate@example.com",      sourced: true }',
    '{ value: "TODO@gmail.com",             sourced: true }')

# Complete except salary_expectation, which required_gap.html demands.
GAP_BANK = COMPLETE_BANK


def write_bank(text: str, name: str) -> AnswerBank:
    path = STATE_HOME / name
    path.write_text(text)
    return AnswerBank(path)


def reset_state() -> None:
    """Fresh ledger/checkpoints/queue between scenarios that must not share."""
    for target in ("ledger.db", "checkpoints", "review-queue.jsonl",
                   "field-resolutions.json", "chrome-profile.lock"):
        p = STATE_HOME / target
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


def queue_entries() -> list[dict]:
    q = STATE_HOME / "review-queue.jsonl"
    if not q.exists():
        return []
    return [json.loads(l) for l in q.read_text().splitlines() if l.strip()]


def ledger_status(job_url: str) -> str | None:
    con = ledger.connect()
    try:
        row = ledger.lookup(con, job_url)
        return row["status"] if row else None
    finally:
        con.close()


# --------------------------------------------------------------------------
async def main() -> int:
    httpd, base = serve(FIXTURES)
    complete = write_bank(COMPLETE_BANK, "bank-complete.yaml")
    stub = write_bank(STUB_BANK, "bank-stub.yaml")

    try:
        # 1 -------------------------------------------------------------
        print("\n[1] complete bank + mappable form -> gate passes, submitted")
        reset_state()
        url1 = f"{base}/simple_form.html"
        out = await runner.run(url1, bank=complete)
        check("status is submitted", out["status"] == "submitted", str(out))
        check("ran at rung 1", out.get("rung") == 1)
        check("landed on the thank-you page",
              "thanks" in out.get("landed_on", ""), out.get("landed_on", ""))
        check("ledger says submitted", ledger_status(url1) == "submitted")
        check("nothing parked", queue_entries() == [])
        check("checkpoint cleared after success",
              Checkpoint.load(runner.app_id_for(url1)) is None)
        check("server saw exactly one submission", len(SUBMISSIONS) == 1,
              f"{len(SUBMISSIONS)} hit(s)")

        # 2 -------------------------------------------------------------
        print("\n[2] bank with a TODO stub -> gate BLOCKS, nothing submitted")
        reset_state()
        before = len(SUBMISSIONS)
        out = await runner.run(f"{base}/simple_form.html", bank=stub)
        check("status is parked", out["status"] == "parked", str(out))
        check("ledger not submitted",
              ledger_status(f"{base}/simple_form.html") == "checkpointed")
        reasons = " ".join(out.get("reasons", []))
        check("blocked because email is a stub",
              "email" in reasons.lower() or "Email" in reasons, reasons[:120])
        check("parked in the review queue", len(queue_entries()) == 1)
        check("server saw NO submission",
              len(SUBMISSIONS) == before, f"{len(SUBMISSIONS)-before} hit(s)")
        check("reason points at the review CLI", "state.review" in reasons, reasons[:80])

        # 3 -------------------------------------------------------------
        print("\n[3] unknown question + NullResolver -> rung 2, parked")
        reset_state()
        url3 = f"{base}/unknown_field.html"
        out = await runner.run(url3, bank=complete, resolver=runner.NullResolver())
        check("status is parked", out["status"] == "parked", str(out))
        check("escalated to rung 2", out.get("rung") == 2, f"rung={out.get('rung')}")
        check("names the unknown question",
              "Kubernetes" in " ".join(out.get("reasons", [])),
              " ".join(out.get("reasons", []))[:120])

        # 4 -------------------------------------------------------------
        print("\n[4] same question + MappingResolver -> resolution cached, "
              "next run is rung 1 again")
        reset_state()
        resolver = runner.MappingResolver(
            {"What is your favourite Kubernetes operator?": "__skip__"})
        out = await runner.run(url3, bank=complete, resolver=resolver)
        cache = STATE_HOME / "field-resolutions.json"
        check("resolution was cached", cache.exists())
        cached = json.loads(cache.read_text()) if cache.exists() else {}
        check("cache keyed by platform::signature",
              any(k.startswith("127.0.0.1::") for k in cached), str(cached))
        check("submitted once resolved", out["status"] == "submitted", str(out))

        # The cache must survive a *different* generated id for the same
        # question — that is what the digit-stripped signature buys.
        reset_state_keep_cache = json.loads(cache.read_text())
        reset_state()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(reset_state_keep_cache))
        out = await runner.run(url3, bank=complete, resolver=runner.NullResolver())
        check("cache hit: rung 1 with a declining resolver",
              out["status"] == "submitted" and out.get("rung") == 1, str(out))

        # 5 -------------------------------------------------------------
        print("\n[5] re-run an already-submitted URL -> never apply twice")
        out = await runner.run(url3, bank=complete)
        check("status is skipped_duplicate", out["status"] == "skipped_duplicate",
              str(out))

        # 6 -------------------------------------------------------------
        print("\n[6] crash mid-form -> resume REPLAYS completed fields")
        reset_state()
        url6 = f"{base}/simple_form.html"
        # First pass parks (stub email), leaving a checkpoint behind.
        await runner.run(url6, bank=stub)
        app_id = runner.app_id_for(url6)
        ck = Checkpoint.load(app_id)
        check("checkpoint survived the parked run", ck is not None)
        done_before = dict(ck.completed_fields) if ck else {}
        check("checkpoint recorded per-field, not per-page",
              len(done_before) >= 5, f"{len(done_before)} fields")

        # Second pass with a bank that has ONLY the email. If the other fields
        # still end up on the page, they were replayed from the checkpoint and
        # not re-derived from the bank.
        email_only = write_bank(
            'email: { value: "candidate@example.com", sourced: true }\n',
            "bank-email-only.yaml")
        out = await runner.run(url6, bank=email_only)
        check("resumed run submitted", out["status"] == "submitted", str(out))
        replayed = out.get("filled", 0)
        check("replayed the earlier fields from the checkpoint",
              replayed >= len(done_before), f"filled={replayed} was={len(done_before)}")

        # 7 -------------------------------------------------------------
        print("\n[7] page with no form -> rung 3, parked")
        reset_state()
        out = await runner.run(f"{base}/no_form.html", bank=complete)
        check("status is parked", out["status"] == "parked", str(out))
        check("rung 3", out.get("rung") == 3, f"rung={out.get('rung')}")
        check("says no adapter matched",
              "no adapter" in " ".join(out.get("reasons", [])).lower())

        # 8 -------------------------------------------------------------
        print("\n[8] required field the bank cannot answer -> gate blocks")
        reset_state()
        gap = write_bank(GAP_BANK, "bank-gap.yaml")
        url8 = f"{base}/required_gap.html"
        before = len(SUBMISSIONS)
        out = await runner.run(url8, bank=gap)
        check("status is parked", out["status"] == "parked", str(out))
        reasons = " ".join(out.get("reasons", []))
        check("blocked by the unfilled-REQUIRED rule",
              "required field not filled" in reasons, reasons[:160])
        check("nothing submitted", ledger_status(url8) != "submitted")
        check("server saw NO submission",
              len(SUBMISSIONS) == before, f"{len(SUBMISSIONS)-before} hit(s)")

    finally:
        httpd.shutdown()

    # 9 -------------------------------------------------------------
    print("\n[9] alias-table ordering (pure lookup, no browser)")
    sys.path.insert(0, str(Path(__file__).parent / "tests"))
    import test_mapping
    check("every ordering trap maps correctly", test_mapping.run() == 0)

    # 10 ------------------------------------------------------------
    print("\n[10] question catalogue is coherent and fully reachable")
    from state import seed
    qs = seed.all_questions()
    check("catalogue has 30-60 questions", 30 <= len(qs) <= 60, f"{len(qs)}")
    keys = [q["feeds"] for q in qs]
    check("no duplicate answer keys", len(keys) == len(set(keys)))
    import yaml as _yaml
    tbl = _yaml.safe_load(Path("state/field-aliases.yaml").read_text())
    reachable = set(tbl["by_name"].values()) | {r["key"] for r in tbl["by_label"]}
    from apply.aliases import DERIVED
    # assessment_willing feeds §5.5 eligibility routing, not a form field.
    orphans = set(keys) - reachable - set(DERIVED) - {"assessment_willing"}
    check("every catalogue key is reachable by the alias table",
          not orphans, str(sorted(orphans)))

    # ----------------------------------------------------------------
    failed = [r for r in results if r[0] == FAIL]
    print(f"\n{'='*66}\n{len(results)-len(failed)}/{len(results)} checks passed")
    if failed:
        print("\nFAILURES:")
        for _, name, detail in failed:
            print(f"  - {name}   {detail}")
    print(f"state dir: {STATE_HOME}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
