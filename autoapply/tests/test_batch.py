"""apply.batch: per-job résumé selection, generic fallback, and dedup.

Own process (browser-launch budget). Verifies WHICH file was attached by
parsing the multipart POST server-side — the only way to prove selection
rather than assume it.

    python tests/test_batch.py     # exit 0 = pass
"""
from __future__ import annotations

import functools, glob, http.server, os, shutil, sys, tempfile, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STATE = Path(tempfile.mkdtemp(prefix="autoapply-batch-"))
os.environ["AUTOAPPLY_HOME"] = str(STATE)
if "AUTOAPPLY_CHROME_PATH" not in os.environ:
    f = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    if f:
        os.environ["AUTOAPPLY_CHROME_PATH"] = f[-1]

from apply import batch                        # noqa: E402

UPLOADS: list[str] = []
failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


class _H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        marker = b'filename="'
        at = body.find(marker)
        if at != -1:
            end = body.find(b'"', at + len(marker))
            UPLOADS.append(body[at + len(marker):end].decode())
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Application received</h1>")

    def log_message(self, *a):
        pass


def main() -> int:
    handler = functools.partial(_H, directory=str(ROOT / "tests" / "fixtures"))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    # Two distinguishable "résumés" and a bank pointing at the generic one.
    generic = STATE / "generic_cv.pdf"; generic.write_bytes(b"%PDF-1.4 generic")
    special = STATE / "frontend_cv.pdf"; special.write_bytes(b"%PDF-1.4 frontend")
    bank_path = STATE / "bank.yaml"
    bank_path.write_text(
        'email: { value: "candidate@example.com", sourced: true }\n'
        f'resume_path: {{ value: "{generic}", sourced: true }}\n')

    jobs_file = STATE / "jobs.yaml"
    jobs_file.write_text(f"""
- url: {base}/upload_form.html?a=1
  company: Alpha
  role: Senior Frontend Engineer
  resume: {special}
- url: {base}/upload_form.html?b=2
  company: Beta
  role: Staff Engineer
  resume: generic
- url: {base}/upload_form.html?c=3
  company: Gamma
  role: Frontend Engineer
""")

    try:
        print("[a] jobs file parses, résumé selection resolved up front")
        jobs = batch.load_jobs(jobs_file)
        check("three jobs parsed", len(jobs) == 3, str(len(jobs)))
        check("job 1 has its own résumé",
              jobs[0]["resume"] is not None and jobs[0]["resume"].name == "frontend_cv.pdf",
              str(jobs[0]["resume"]))
        check("'generic' resolves to None (use the bank)", jobs[1]["resume"] is None)
        check("omitted resolves to None (use the bank)", jobs[2]["resume"] is None)

        print("[b] submitting the batch attaches the right file each time")
        code = batch.main([str(jobs_file), "--bank", str(bank_path)])
        check("batch exited 0 (nothing parked or failed)", code == 0, f"exit={code}")
        check("three uploads reached the server", len(UPLOADS) == 3, str(UPLOADS))
        check("job 1 sent its own résumé",
              UPLOADS[:1] == ["frontend_cv.pdf"], str(UPLOADS))
        check("jobs 2 and 3 sent the generic one",
              UPLOADS[1:] == ["generic_cv.pdf", "generic_cv.pdf"], str(UPLOADS))

        print("[c] re-running the same file applies to nothing twice")
        before = len(UPLOADS)
        batch.main([str(jobs_file), "--bank", str(bank_path)])
        check("ledger refused all three", len(UPLOADS) == before,
              f"{len(UPLOADS) - before} extra upload(s)")

        print("[d] a missing generic résumé is caught before any browser starts")
        bad_bank = STATE / "bad.yaml"
        bad_bank.write_text(
            'email: { value: "candidate@example.com", sourced: true }\n'
            'resume_path: { value: "/nonexistent/cv.pdf", sourced: true }\n')
        code = batch.main([str(jobs_file), "--bank", str(bad_bank)])
        check("refused with exit 2", code == 2, f"exit={code}")
    finally:
        httpd.shutdown()

    total = 10
    print(f"batch: {total - len(failures)}/{total} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
