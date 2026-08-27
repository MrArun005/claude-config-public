"""apply/import_jobhunt.py — turn the job-hunt skill's output into a jobs file.

The job-hunt skill already does discovery and per-job tailoring, and its output
happens to carry exactly what apply.batch needs:

    applications/INDEX.md                       Company, Role, Posting link
    applications/JOB-001 - <Company> - <Role>/  the tailored résumé PDF

So the tailored résumé for each posting becomes that job's `resume:` entry, and
nothing has to be re-entered by hand.

    python -m apply.import_jobhunt "C:\\...\\applications" -o jobs.yaml
    python -m apply.import_jobhunt ./applications --skip-applied

This is a pure translation. It reads INDEX.md (falling back to each folder's
job.md), copies the values across, and reports anything it will not guess at:

  * a row with no posting URL is skipped and named — the skill writes "none
    found" when it could not find one
  * a folder with several PDFs falls back to the generic résumé and lists what
    it saw, because choosing between them is your call
  * PTL-style rows (portal search links with no folder) are skipped

Review the file it writes before running a batch with it.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s<>()\[\]|]+")
CODE_RE = re.compile(r"^([A-Z]{2,5}-\d{2,4})\b")

# "JOB-001 - Acme - Senior Engineer"
FOLDER_RE = re.compile(r"^(?P<code>[A-Z]{2,5}-\d{2,4})\s*-\s*(?P<rest>.+)$")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_index(path: Path) -> list[dict]:
    """Rows from the skill's INDEX.md table, by column name."""
    rows: list[dict] = []
    header: list[str] | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = _cells(line)
        if header is None:
            lowered = [c.lower() for c in cells]
            if "code" in lowered and "company" in lowered:
                header = lowered
            continue
        if set("".join(cells)) <= set("-: "):      # the separator row
            continue
        row = dict(zip(header, cells))
        if row.get("code"):
            rows.append(row)
    return rows


def parse_job_md(path: Path) -> dict:
    """Fallback: the per-folder job.md. Free-form, so read it conservatively."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict = {}
    for line in text.splitlines():
        low = line.lower()
        for key, names in (("company", ("company",)), ("role", ("role", "title")),
                           ("code", ("code",))):
            for name in names:
                if low.lstrip("*#- ").startswith(name):
                    _, _, value = line.partition(":")
                    if value.strip():
                        out.setdefault(key, value.strip().strip("*_`"))
    if m := URL_RE.search(text):
        out.setdefault("posting", m.group(0))
    return out


def find_resume(folder: Path) -> tuple[Path | None, str]:
    """The tailored résumé in this folder, or a reason for not choosing one."""
    pdfs = sorted(p for p in folder.glob("*.pdf") if p.is_file())
    if not pdfs:
        return None, "no PDF in the folder — will use the generic résumé"
    if len(pdfs) > 1:
        names = ", ".join(p.name for p in pdfs)
        return None, f"{len(pdfs)} PDFs ({names}) — will use the generic résumé"
    return pdfs[0], ""


def collect(applications: Path) -> tuple[list[dict], list[str]]:
    notes: list[str] = []
    jobs: list[dict] = []

    folders = {}
    for child in sorted(applications.iterdir()):
        if child.is_dir() and (m := FOLDER_RE.match(child.name)):
            folders[m.group("code")] = child

    index = applications / "INDEX.md"
    rows: list[dict] = parse_index(index) if index.exists() else []
    if not rows:
        notes.append(f"no usable table in {index}; falling back to job.md files")
        for code, folder in folders.items():
            jm = folder / "job.md"
            if jm.exists():
                data = parse_job_md(jm)
                data["code"] = code
                rows.append({"code": code, "company": data.get("company", ""),
                             "role": data.get("role", ""),
                             "posting": data.get("posting", "")})

    for row in rows:
        code = (row.get("code") or "").strip()
        folder = folders.get(code)
        posting = ""
        for cell in (row.get("posting"), row.get("link"), row.get("url")):
            if cell and (m := URL_RE.search(str(cell))):
                posting = m.group(0)
                break

        if not posting:
            notes.append(f"{code}: no posting URL — skipped")
            continue
        if folder is None:
            notes.append(f"{code}: no application folder (portal link?) — skipped")
            continue

        company = (row.get("company") or "").strip()
        role = (row.get("role") or "").strip()
        if not company or not role:
            notes.append(f"{code}: missing company or role in INDEX.md — skipped "
                         f"(a 'why this company' field would park)")
            continue

        resume, why = find_resume(folder)
        if why:
            notes.append(f"{code}: {why}")

        jobs.append({"code": code, "url": posting, "company": company,
                     "role": role, "resume": resume,
                     "status": (row.get("status") or "").strip()})
    return jobs, notes


def already_applied(url: str) -> str | None:
    from state import ledger
    con = ledger.connect()
    try:
        row = ledger.lookup(con, url) or {}
        return row.get("status") or None
    finally:
        con.close()


def to_yaml(jobs: list[dict]) -> str:
    lines = ["# Generated by apply.import_jobhunt from the job-hunt skill's output.",
             "# Review before running a batch. `resume: generic` uses the answer",
             "# bank's resume_path; a path is that job's tailored résumé.", ""]
    for job in jobs:
        lines.append(f"# {job['code']}"
                     + (f"  ({job['status']})" if job["status"] else ""))
        lines.append(f"- url: {job['url']}")
        lines.append(f"  company: {_q(job['company'])}")
        lines.append(f"  role: {_q(job['role'])}")
        lines.append(f"  resume: {_q(str(job['resume'])) if job['resume'] else 'generic'}")
        lines.append("")
    return "\n".join(lines)


def _q(text: str) -> str:
    """Quote only when YAML would otherwise misread it."""
    if text and (text[0] in "'\"[{&*#?|->%@`" or ": " in text
                 or text.strip() != text or text.endswith(":")):
        return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m apply.import_jobhunt",
        description="Build a jobs file from the job-hunt skill's applications/ folder.")
    ap.add_argument("applications", type=Path,
                    help="the skill's applications/ directory")
    ap.add_argument("-o", "--out", type=Path, default=Path("jobs.yaml"))
    ap.add_argument("--skip-applied", action="store_true",
                    help="leave out URLs the ledger has already submitted")
    ap.add_argument("--only-status", metavar="TEXT",
                    help="keep only INDEX.md rows whose Status contains TEXT")
    args = ap.parse_args(argv)

    if not args.applications.is_dir():
        print(f"not a directory: {args.applications}", file=sys.stderr)
        return 2

    jobs, notes = collect(args.applications)

    if args.only_status:
        want = args.only_status.lower()
        before = len(jobs)
        jobs = [j for j in jobs if want in j["status"].lower()]
        notes.append(f"--only-status {args.only_status!r}: kept {len(jobs)}/{before}")

    if args.skip_applied:
        kept = []
        for job in jobs:
            status = already_applied(job["url"])
            if status == "submitted":
                notes.append(f"{job['code']}: already submitted — left out")
            else:
                kept.append(job)
        jobs = kept

    for note in notes:
        print(f"  note: {note}")

    if not jobs:
        print("\nnothing to write.", file=sys.stderr)
        return 1

    args.out.write_text(to_yaml(jobs), encoding="utf-8")
    tailored = sum(1 for j in jobs if j["resume"])
    print(f"\nwrote {args.out} — {len(jobs)} job(s), "
          f"{tailored} with a tailored résumé, {len(jobs) - tailored} generic")
    print(f"\nreview it, then:  python -m apply.batch {args.out} --plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
