---
name: project-testing-pattern
description: "Arun verifies the HRMS platform phase-by-phase via manual browser walkthroughs, annotating the detailed test plan files in-place. Plans live at docs/testing/PHASE-N-USER-TEST.md."
metadata: 
  node_type: memory
  type: project
  originSessionId: 242f1762-a90e-4b64-8146-d40412471165
---

Arun's testing rhythm for the HRMS platform: he walks each phase end-to-end in the browser, with the detailed test plan open in his IDE, annotating findings inline next to the test step (e.g. `--> button isnt visible`, `--- PAGE DOESNT EXIST http://...`).

**Where the plans live:** `docs/testing/PHASE-{N}-USER-TEST.md` (Phase 1, 2 done; future phases written on demand).

**How to triage his annotations:**
1. Re-read the file fully to catch every comment (the system reminders truncate)
2. Group findings into severity buckets: blockers / major / minor / UX confusion
3. Validate the URL is correct first — Arun has hit "missing page" errors that were actually wrong-port issues (he typed `localhost:8001/control/...` when the route is at `localhost:8002/jurisdiction/...`). Fix the test doc URLs, don't assume the page is missing.
4. Pick the smallest waves possible: blockers first (~30-60 min), then missing-button cluster (~60-90 min), then UX polish. Surface scope honestly before fixing.

**Why:** Said verbatim 2026-05-25 — "lets do phase 1 in details manual test please" + the followup "Please check phase 2 most of the pages doesnt even exist brotha". The phase-by-phase pattern is intentional; don't try to verify multiple phases at once.

**How to apply:**
- When Arun says "phase N" → write `docs/testing/PHASE-N-USER-TEST.md` with the same structure: pre-flight → suite-per-persona → cross-cutting → issues-found template.
- Be specific in the test steps (exact value to type, exact field to expect) — vague "click around and check" doesn't help him triage what's broken.
- Verify URLs against the actual repo's route map before writing — `find apps/web/src/app -name page.tsx` and `find apps/control-plane/src/app -name page.tsx`.
- After he annotates: pull all comments, present a clean triage matrix, propose ordered waves.

Related: [[feedback-verify-dont-trust-agents]] (his "verify before claim" rule), [[feedback-stay-responsive]] (surface findings promptly).
