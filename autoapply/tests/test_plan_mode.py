"""--plan must show everything and touch nothing.

Own process, same reason as test_select_as.py: browser launches are the scarce
resource in a constrained container.

    python tests/test_plan_mode.py    # exit 0 = pass
"""
from __future__ import annotations

import asyncio, functools, glob, http.server, os, sys, tempfile, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STATE = Path(tempfile.mkdtemp(prefix="autoapply-plan-"))
os.environ["AUTOAPPLY_HOME"] = str(STATE)
if "AUTOAPPLY_CHROME_PATH" not in os.environ:
    f = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    if f:
        os.environ["AUTOAPPLY_CHROME_PATH"] = f[-1]

from apply import runner                       # noqa: E402
from state import ledger                       # noqa: E402
from state.answers import AnswerBank           # noqa: E402

BANK = """
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

HITS: list[str] = []
failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


class _H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if "thanks.html" in self.path:
            HITS.append(self.path)
        return super().do_GET()

    def log_message(self, *a):
        pass


async def main() -> int:
    handler = functools.partial(_H, directory=str(ROOT / "tests" / "fixtures"))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    p = STATE / "bank.yaml"
    p.write_text(BANK)
    bank = AnswerBank(p)

    try:
        print("[a] plan on a fully mappable form")
        url = f"{base}/simple_form.html"
        out = await runner.run(url, bank=bank, plan_only=True)
        rows = out.get("plan", [])
        check("status is plan", out["status"] == "plan", str(out)[:120])
        check("reported every field", len(rows) == 10, f"{len(rows)} rows")
        ready = [r for r in rows if r["verdict"] in ("would fill", "would select")]
        check("all fields resolved", len(ready) == 10, f"{len(ready)}/10")
        check("shows the value each control would receive",
              all(r["value"] is not None for r in ready))
        check("NOTHING was submitted", HITS == [], str(HITS))
        con = ledger.connect()
        try:
            row = ledger.lookup(con, url) or {}
        finally:
            con.close()
        check("ledger did not mark it submitted",
              row.get("status") != "submitted", str(row.get("status")))

        print("[b] plan surfaces what would block the gate")
        out = await runner.run(f"{base}/unknown_field.html", bank=bank,
                               plan_only=True)
        rows = out.get("plan", [])
        blocked = [r for r in rows if "rung 2" in r["verdict"]]
        check("names the unmapped question", len(blocked) == 1, str(rows)[:140])
        check("still submitted nothing", HITS == [], str(HITS))
    finally:
        httpd.shutdown()

    total = 8
    print(f"plan mode: {total - len(failures)}/{total} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
