---
name: Test scenarios — keep small, API-driven, fast
description: Guidance for how to add Playwright e2e test scenarios in this repo — minimize DB writes, validate via API/console, avoid bulk runs
type: feedback
originSessionId: 07359bbd-cc00-4676-8f93-0aa65b8d63c2
---
When adding Playwright e2e scenarios in the promotion-management webui:

- **Do NOT run many scenarios that each create a real promotion.** Each happy-path run writes a real row to the DB. 8+ scenarios per run = junk data piling up and slow feedback loops. Keep the scenario list small (≤3 happy-path scenarios at any time).
- **Validate via the network/console**, not by re-running the UI flow with slight variations. Inspect the POST request payload and the response in `page.on('request')` / `page.on('response')`, or `page.context().on('request')`. This proves the form sent the right data without needing more test runs.
- **Verify data correctness before expanding.** Before adding scenarios, make sure the one passing scenario is actually correct (right payload, right response shape, right DB state). Don't pile scenarios on top of an unverified baseline.
- **Speed matters for tester productivity.** If a suite takes >2 min the testers won't use it — they say they can do it manually faster. Optimize for fast feedback: fewer tests, lighter logging, production build mode, API-level assertions where possible.

**Why:** user said "i dont see anything but blabbering here" — too many similar tests with verbose step logs add noise without proving anything new. The right level of variation is 1-2 happy paths plus targeted API-based assertions on payloads, not N parameterized scalar variations.

**How to apply:** before adding any new scenario, ask: "Can I prove this variation works by inspecting the API call instead of running a whole new UI flow?" If yes, do that. Keep the happy-path suite as a small smoke + one representative create flow.
