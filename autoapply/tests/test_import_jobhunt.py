"""apply.import_jobhunt: translate the job-hunt skill's output into a jobs file.

Pure parsing, no browser — runs in milliseconds.

    python tests/test_import_jobhunt.py
"""
from __future__ import annotations

import shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from apply import import_jobhunt as imp   # noqa: E402

failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def build(tmp: Path) -> Path:
    """A faithful replica of the skill's applications/ layout, awkward cases included."""
    apps = tmp / "applications"
    apps.mkdir()

    # Exactly the table shape documented in skills/job-hunt/SKILL.md Step 4.
    (apps / "INDEX.md").write_text("""# Applications

| Code | Company | Role | Coverage | Apply email | Posting | Status |
|------|---------|------|----------|-------------|---------|--------|
| JOB-001 | Acme | Senior Engineer | 88% | careers@acme.com | https://boards.greenhouse.io/acme/jobs/1 | draft ready |
| JOB-002 | Beta Labs | Staff Frontend Engineer | 81% | none found | [posting](https://jobs.lever.co/beta/2) | draft ready |
| JOB-003 | Gamma | Platform Engineer | 79% | none found | none found | needs link |
| JOB-004 | Delta | AI Engineer | 84% | hr@delta.io | <https://delta.io/careers/4> | sent |
| PTL-001 | Wellfound | portal search | - | - | https://wellfound.com/jobs | portal |
| JOB-005 |  |  | 70% | - | https://eps.example/5 | draft ready |
""")

    def folder(name: str, pdfs: list[str]) -> Path:
        d = apps / name
        d.mkdir()
        (d / "job.md").write_text(f"# {name}\n\nCompany: from-job-md\n")
        for pdf in pdfs:
            (d / pdf).write_bytes(b"%PDF-1.4")
        return d

    folder("JOB-001 - Acme - Senior Engineer", ["Arun - Acme - 2026-08-27.pdf"])
    folder("JOB-002 - Beta Labs - Staff Frontend Engineer",
           ["Arun - Beta Labs - 2026-08-27.pdf"])
    folder("JOB-003 - Gamma - Platform Engineer", ["Arun - Gamma.pdf"])
    # Two PDFs: ambiguous on purpose — must NOT pick one.
    folder("JOB-004 - Delta - AI Engineer",
           ["Arun - Delta - v1.pdf", "Arun - Delta - v2.pdf"])
    folder("JOB-005 - Eps - Frontend", [])          # no PDF at all
    return apps


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="imp-"))
    try:
        apps = build(tmp)
        jobs, notes = imp.collect(apps)
        codes = [j["code"] for j in jobs]
        blob = " | ".join(notes)

        print("[a] rows the skill produced")
        check("kept the four jobs with real links",
              codes == ["JOB-001", "JOB-002", "JOB-004"], str(codes))
        check("skipped the row with no posting URL (JOB-003)",
              "JOB-003" in blob and "no posting URL" in blob, blob[:110])
        check("skipped the portal row with no folder (PTL-001)",
              "PTL-001" in blob and "no application folder" in blob, blob[:160])
        check("skipped the row missing company/role (JOB-005)",
              "JOB-005" in blob and "missing company or role" in blob, blob[:200])

        print("[b] résumé selection")
        by_code = {j["code"]: j for j in jobs}
        check("JOB-001 uses its tailored PDF",
              by_code["JOB-001"]["resume"] is not None
              and by_code["JOB-001"]["resume"].name == "Arun - Acme - 2026-08-27.pdf",
              str(by_code["JOB-001"]["resume"]))
        check("JOB-004 with two PDFs falls back to generic, does NOT pick one",
              by_code["JOB-004"]["resume"] is None and "2 PDFs" in blob,
              str(by_code["JOB-004"]["resume"]))

        print("[c] link and field extraction")
        check("markdown link unwrapped",
              by_code["JOB-002"]["url"] == "https://jobs.lever.co/beta/2",
              by_code["JOB-002"]["url"])
        check("angle-bracket link unwrapped",
              by_code["JOB-004"]["url"] == "https://delta.io/careers/4",
              by_code["JOB-004"]["url"])
        check("company with a space preserved",
              by_code["JOB-002"]["company"] == "Beta Labs",
              by_code["JOB-002"]["company"])

        print("[d] the emitted file is valid input for apply.batch")
        out = tmp / "jobs.yaml"
        out.write_text(imp.to_yaml(jobs))
        from apply.batch import load_jobs
        parsed = load_jobs(out)
        check("apply.batch accepts it", len(parsed) == 3, str(len(parsed)))
        check("tailored résumé survives the round trip",
              parsed[0]["resume"] is not None
              and parsed[0]["resume"].name.startswith("Arun - Acme"),
              str(parsed[0]["resume"]))
        check("generic stays generic", parsed[2]["resume"] is None,
              str(parsed[2]["resume"]))

        print("[e] --only-status filter")
        kept = [j for j in jobs if "draft ready" in j["status"].lower()]
        check("status column parsed", len(kept) == 2, str([j["status"] for j in jobs]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = 12
    print(f"import_jobhunt: {total - len(failures)}/{total} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
