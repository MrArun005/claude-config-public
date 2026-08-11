---
name: feedback-quality-over-speed
description: "User prefers quality over speed on the HRMS project — fewer parallel agents, stronger verification between tasks, cleaner commit history"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 242f1762-a90e-4b64-8146-d40412471165
---

User explicitly redirected away from raw speed toward quality on 2026-05-23 after a long parallel-execution session.

**Why:** The speed-first approach caused real defects this session:
- 2 agents stream-timed-out at 2.5h wall-clock leaving schemas half-broken
- Lint-staged stash/restore swapped commit message/content TWICE between parallel agents (commits `0f6553d`/`c9af8b1` and `524bb9f`/`9ef2ff8`)
- Production-build blocker in `apps/web/src/lib/letters.ts` was a pre-existing bug not caught until late in the session
- Agents bundled each other's files into wrong commits when committing simultaneously

User said: "lets work efficiently now not to worry too much on speed but quality"

**How to apply:**
- Cap parallel agents at 1-2, not 4-5
- Never dispatch a new agent while a parallel agent is editing the same file (especially shared files like `app-shell.tsx`, `app.module.ts`, `seed.ts`, `package.json`)
- Run verification (typecheck + lint + tests) explicitly between tasks, not just at the end
- Use the full subagent-driven-development 2-stage review pattern: spec-compliance review → code-quality review → implementer fixes → next task
- Prefer doing small focused work yourself over dispatching another agent when the work is well-specified
- Don't dispatch a task whose implementation depends on an in-flight task's exports (race condition on file presence)
- Commit messages MUST match commit contents — if lint-staged stash/restore swap happens, fix via `git commit --amend -m` BEFORE the next commit lands on top
- Default to serial execution unless tasks are provably independent at the file level (not just "different services") — even seemingly independent tasks can collide on `dist/generated`, lint-staged, or shared module registration
