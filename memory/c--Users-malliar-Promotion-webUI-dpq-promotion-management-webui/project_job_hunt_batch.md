---
name: project_job_hunt_batch
description: "Job-hunt batch 2026-07-22: 52 jobs (JOB-011..050 + PTL-001..012), dashboard UI on Desktop, résumé variant system"
metadata: 
  node_type: memory
  type: project
  originSessionId: 020779f4-d0fd-4176-b5ac-98af8edcef08
  modified: 2026-07-27T07:05:51.530Z
---

Batch of 2026-07-22 for Arun's remote job hunt (see [[user_profile_background]]):

- **Dashboard UI** (date-filterable, user-requested): `C:\Users\malliar\Desktop\job-hunt-dashboard\index.html` — vanilla JS, loads `jobs.js` (generated from `jobs.json`), statuses persist in localStorage.
- **Applications**: `C:\Users\malliar\Desktop\resume-tailor\applications\` — JOB-011..JOB-050 folders (job.md + content.json + PDF each), INDEX.md tracker, FORM-ANSWERS.md cheat sheet. PTL-001..012 are portal search links (no folders).
- **Résumé variants** in `applications\_variants\`: fullstack (=master resume-2026-07-02.json), frontend, backend, platform, **ai-architect** (added 2026-07-27 — architecture-track positioning, "Architecture Highlights" section). Cluster-matched per job, not per-JD tailored.
- 2026-07-27 additions: JOB-052 Deloitte Agentic AI Developer (recruiter outreach, CTC answered: current ₹12L assumed midpoint, expected ₹18L, 90d notice); JOB-053 Wissen Technology Gen AI Architect (JD-tailored, 6-10yr ask vs 4.8 actual).
- Folkgrove/HRMS fact update: **5,000+ automated tests** now (was 2,400+) — all variants updated.
- Already applied earlier (2026-07-02, skip these companies): Netomi, Okta, Rubrik, Databricks, Coinbase.
- **PDF rendering**: skill's topdf.mjs fails (no puppeteer/playwright on this machine) — use Edge headless instead: `msedge --headless=new --no-pdf-header-footer --print-to-pdf=...`.
- Best India-eligible fresh sources found: Greenhouse boards queried directly via `boards-api.greenhouse.io` (turing, gitlab, canonical, okx, sportygroup, distantjob); RemoteOK/Remotive were stale or junk.
