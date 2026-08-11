---
name: feedback-skill-discipline
description: "User wants the full subagent-driven-development discipline used on HRMS — 2-stage review per task, TDD discipline, parallel planning, never skip verification gates"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 242f1762-a90e-4b64-8146-d40412471165
---

User said on 2026-05-23 (~09:45 IST): "lets use all of our skills to make it faster, quicker and sharper"

**Why:** Earlier in the same session I'd been dispatching implementer subagents without the 2-stage review pattern (spec compliance → code quality), which led to real defects:
- Inlined `regionForLocation` duplication in attendance-compute.service.ts
- Schema field-name surprises (`defaultBalance` vs spec's `daysPerYear`, `FIXED_YEARLY` vs `ANNUAL_GRANT`)
- Service signature drift (spec said `apply(tenantId, employeeId, body)` but actual was `apply(db, email, body)`)
- Cross-commit content swaps from racing parallel agents

User pairs this with [[feedback-quality-over-speed]] — they want speed AND quality, achieved through the *proper* skill discipline, not by skipping it.

**How to apply:**

For every Phase N.M execution from here on:

1. **Plan first** (`superpowers:writing-plans`): full plan with code in every step, no placeholders, self-review before saving. Can dispatch multiple plan agents in parallel (they only write docs).

2. **Execute via `superpowers:subagent-driven-development`**, NOT loose implementer dispatch:
   - Implementer → spec-compliance reviewer → code-quality reviewer → fix loop → next task
   - Use the per-skill templates at `C:\Users\malliar\.claude\plugins\cache\superpowers-dev\superpowers\5.1.0\skills\subagent-driven-development\{implementer-prompt,spec-reviewer-prompt,code-quality-reviewer-prompt}.md`

3. **Every implementer follows `superpowers:test-driven-development`** — RED (failing test) → GREEN (minimal impl) → REFACTOR.

4. **`superpowers:dispatching-parallel-agents` rules:**
   - One agent per truly independent problem domain (different files, no shared module registration)
   - Max 2 in flight at once (per [[feedback-quality-over-speed]])
   - Never race on shared files: `app-shell.tsx`, `app.module.ts`, `seed.ts`, `package.json`, schema files

5. **`superpowers:verification-before-completion`** before each task is marked done: actual test+typecheck+lint output, not "should pass".

6. **`superpowers:requesting-code-review` at end of each phase**: final code-reviewer subagent on the entire batch before push.

7. **`superpowers:systematic-debugging`** when anything breaks: trace data flow, find root cause, never patch symptoms.

The fastest path is the disciplined path — skipping the 2-stage review feels faster but costs more in rework + commit-swap cleanups + half-broken schemas later.
