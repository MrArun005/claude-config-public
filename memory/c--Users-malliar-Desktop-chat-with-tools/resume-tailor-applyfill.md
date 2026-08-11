---
name: resume-tailor-applyfill
description: resume-tailor repo hosts the job-hunt skill + applyfill assisted-apply tool; how to run/test it
metadata: 
  node_type: memory
  type: project
  originSessionId: d005f423-54e9-4d8d-b66b-7f846d0b6f5c
---

Arun's job-application work lives in `C:\Users\malliar\Desktop\resume-tailor` (GitHub MrArun005/resume-tailor), NOT chat-with-tools. The job-hunt skill is at `.claude/skills/job-hunt/` with `scripts/applyfill.mjs` — an assisted-apply tool (built 2026-07-02, branch `feature/playwright-prefill`): opens application URLs in Chrome (persistent profile `.chrome-apply-profile`), pre-fills from `applications/answers.base.json` (+ per-job override), attaches résumé, never submits, human reviews.

- Tests: `pnpm test:workflow` (uses `vitest.workflow.mjs`; the default `vitest.config.ts` is broken on Windows — CJS require of ESM std-env — and only targets lib/**).
- Finding live jobs: query board APIs directly (`boards-api.greenhouse.io/v1/boards/<co>/jobs`, `api.lever.co/v0/postings/<co>?mode=json`) — search-engine links to postings are usually stale.
- Known limits: custom career sites (Okta upload button, Databricks/Coinbase JS-rendered forms, Lever location autocomplete) need manual completion.
- Tracker: `applications/INDEX.md` (gitignored, holds personal data). See [[claude-not-gemini]], [[one-application-per-company]].
