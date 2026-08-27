"""select_as: one answer serving both a free-text field and a dropdown.

Runs as its OWN PROCESS, invoked by p3_test.py. That is not stylistic: each
runner.run() launches a persistent Chromium, and a constrained container
exhausts somewhere past a dozen launches in one process — the symptom moves
around (a click that never returns, then a goto that times out), which is how
resource exhaustion presents rather than a logic bug. A fresh process gets a
fresh browser budget, so this scenario tests the feature instead of the limit.

    python tests/test_select_as.py     # exit 0 = pass
"""
from __future__ import annotations

import asyncio
import functools
import glob
import http.server
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

STATE = Path(tempfile.mkdtemp(prefix="autoapply-selectas-"))
os.environ["AUTOAPPLY_HOME"] = str(STATE)
if "AUTOAPPLY_CHROME_PATH" not in os.environ:
    found = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    if found:
        os.environ["AUTOAPPLY_CHROME_PATH"] = found[-1]

from apply import runner                       # noqa: E402
from state.answers import AnswerBank           # noqa: E402

BASE_BANK = """
full_name:            { value: "Test Candidate",             sourced: true }
email:                { value: "candidate@example.com",      sourced: true }
phone:                { value: "+1-555-0100",                sourced: true }
location:             { value: "Bengaluru, India",           sourced: true }
years_experience:     { value: 5,                            sourced: true }
years_react:          { value: 5,                            sourced: true }
requires_sponsorship: { value: false,                        sourced: true }
linkedin:             { value: "https://linkedin.com/in/test", sourced: true }
"""

# The fixture's notice dropdown offers "15 days / 30 days / 90 days" — none of
# which is the honest free-text answer below.
FREE_TEXT = 'notice_period: { value: "90 days (negotiable to 60)", sourced: true }\n'
WITH_ALT = ('notice_period: { value: "90 days (negotiable to 60)", '
            'select_as: "90 days", sourced: true }\n')

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _bank(extra: str, name: str) -> AnswerBank:
    p = STATE / name
    p.write_text(BASE_BANK + extra)
    return AnswerBank(p)


def _reset() -> None:
    shutil.rmtree(STATE / "chrome-profile", ignore_errors=True)
    shutil.rmtree(STATE / "checkpoints", ignore_errors=True)
    (STATE / "ledger.db").unlink(missing_ok=True)
    (STATE / "review-queue.jsonl").unlink(missing_ok=True)


async def main() -> int:
    handler = functools.partial(_Quiet, directory=str(ROOT / "tests" / "fixtures"))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        print("[a] free-text answer, no alternate -> must park, never near-miss")
        _reset()
        out = await runner.run(f"{base}/simple_form.html",
                               bank=_bank(FREE_TEXT, "free.yaml"))
        reasons = " ".join(out.get("reasons", []))
        check("parked rather than picking '90 days' unasked",
              out["status"] == "parked", str(out)[:160])
        check("names the options that were on offer",
              "no option matches" in reasons, reasons[:120])

        print("[b] same answer + select_as -> submits the canonical option")
        _reset()
        out = await runner.run(f"{base}/simple_form.html",
                               bank=_bank(WITH_ALT, "alt.yaml"))
        check("gate cleared and submitted", out["status"] == "submitted",
              str(out)[:160])
        check("dropdown got '90 days', not the sentence",
              "notice=90+days" in out.get("landed_on", ""),
              out.get("landed_on", "")[-70:])
    finally:
        httpd.shutdown()

    print(f"select_as: {4 - len(failures)}/4 checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
