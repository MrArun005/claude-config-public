---
name: job-hunt
description: >-
  All-in-one résumé + job-application agent. Tailor a résumé to one job, OR batch:
  find tens of jobs, tailor a truthful résumé to each, and produce a ready-to-send
  email draft per job — each tracked by a code in an applications/ folder with an
  index. Use whenever the user wants to "tailor my résumé", "apply to this job",
  "find jobs and tailor my résumé to each", "batch apply", "draft applications",
  or hands over a résumé plus job link(s) / search criteria. Everything (tailoring,
  PDF, email draft, search, batch tracking) lives in this one skill.
---

# Job Hunt — one skill: find → tailor → draft, single or batch

Take a candidate's résumé and either ONE job or TENS of jobs, and for each produce
a truthful, ATS-ready tailored résumé (HTML + PDF) and a ready-to-send email draft —
each application tracked by a code in an `applications/` folder. Tailoring never
fabricates; the user always reviews and sends.

Bundled scripts (all dependency-light, run from this skill's directory):
- `scripts/render.mjs <content.json> <template> <out.html>` — content → styled HTML
- `scripts/topdf.mjs <in.html> <out.pdf>` — HTML → PDF (Playwright/Puppeteer, SSRF-safe)
- `scripts/mkdraft.mjs --to … --subject … --body-file … --attach … --out …` — `.eml` draft

## Step 1 — Build the master profile ONCE (interview once, apply to many)

Read the résumé into the structured shape below (transcribe verbatim — don't
summarize or invent):

```json
{ "name": "", "headline": "", "contact": [],
  "sections": [ { "title": "", "blocks": [ { "heading": "", "subheading": "", "text": "", "bullets": [] } ] } ] }
```

Then run the **gap-interview once** to capture true-but-off-résumé material: skim the
target role(s), list skills/experience the résumé doesn't show, and ask the candidate
which they genuinely have (even from side projects). Record confirmed extras as a
reusable list — the **master profile** = structured résumé + confirmed extras.

This happens a single time. You then tailor every job against this profile **without
re-interviewing per job**. Never add anything the candidate didn't confirm.

## Step 2 — Get the jobs

- **Single job:** a posting URL (use the browser engine — navigate + snapshot — to
  extract title, company, JD, and any apply/recruiter email) or pasted text.
- **Batch / "find jobs":** gather criteria (role, location/remote, seniority,
  must-haves; infer from the résumé when terse). Use **web search** (`"<role>"
  "<location>" jobs`, or `site:boards.greenhouse.io <role>`, `site:jobs.lever.co`)
  and/or the browser to collect real postings. For each, capture title, company, JD,
  link, and apply email if present.

Only use postings you actually found/were given — never invent jobs, JDs, or emails.
If a board blocks fetching or hides the JD, note it and ask the user to paste that one.

## Step 3 — Per job: tailor, render, draft, track

Create the workspace once: `applications/`. For each job assign a sequential
**tracking code** `JOB-001`, `JOB-002`, … and a folder:

```
applications/JOB-001 - <Company> - <Role>/
```

Inside each folder, do:

1. **`job.md`** — the code, company, role, link, apply email (or "none found"), and the JD.
2. **Tailor** the master profile to this JD (mirror its real language where true, lead
   with the most relevant experience, fold in only confirmed extras, never fabricate).
   Write the tailored content JSON to `content.json` in the folder.
3. **Render + PDF:**
   ```bash
   node scripts/render.mjs "applications/JOB-001 - <Company> - <Role>/content.json" modern \
     "applications/JOB-001 - <Company> - <Role>/<Candidate> - <Company> - <YYYY-MM-DD>.html"
   node scripts/topdf.mjs "<...>.html" "<...>.pdf"
   ```
   Keep it 1–2 pages; if it overflows, use `compact` or trim least-relevant content.
4. **Email draft** — write the application/cold email body to `email.txt`, then:
   ```bash
   node scripts/mkdraft.mjs --to "<apply email or omit>" \
     --subject "Application — <Role> — <Candidate>" \
     --body-file "applications/JOB-001 - <Company> - <Role>/email.txt" \
     --attach "applications/JOB-001 - <Company> - <Role>/<...>.pdf" \
     --out "applications/JOB-001 - <Company> - <Role>/draft.eml"
   ```
   Omit `--to` when no address was found (inserts a placeholder to fill on review).
5. **`notes.md`** — 4–8 "what changed" notes + the ATS keyword coverage (match by
   concept, not exact wording).

**Cost discipline for big batches:** keep per-job work bounded — tailor from the
profile in one focused pass per job, don't re-derive the profile, and reuse the same
template across the batch. If the user gave a cap (e.g. "top 10"), respect it and say
what you skipped.

## Step 4 — Write the index (the tracker)

Maintain `applications/INDEX.md` — one row per job, so the codes are the tracker:

```markdown
| Code | Company | Role | Coverage | Apply email | Posting | Status |
|------|---------|------|----------|-------------|---------|--------|
| JOB-001 | Acme | Senior Engineer | 88% | careers@acme.com | <link> | draft ready |
```

## Step 5 — Deliver

Report the absolute path of `applications/` and `INDEX.md`, and a quick summary
(how many tailored, coverage range). Tell the user: open each `JOB-NNN` folder, review
the résumé PDF and `draft.eml` (double-click → opens in the mail app with the résumé
attached), fill any placeholder recipient, and **Send**.

## Guardrails

- **Truth first** — only what's in the résumé or the candidate's confirmed extras.
- **Never sends** — this skill only prepares drafts; sending is always the user's action.
- **No invented jobs/links/emails** — list only real findings.
- **One profile, many jobs** — interview once; tailor each job from that profile.
