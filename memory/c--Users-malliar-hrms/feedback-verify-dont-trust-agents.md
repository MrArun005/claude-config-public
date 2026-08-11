---
name: feedback-verify-dont-trust-agents
description: "STRICT RULE — verify agent reports with own commands before claiming work done. Don't just say \"✅\" because an agent's report said so."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 242f1762-a90e-4b64-8146-d40412471165
---

User said on 2026-05-23 (~12:00 IST): "we should work clean and not just say yess when i check"

**Why:** I'd been reporting "✅ Task X done — agent reports tests pass, commit landed" without independently verifying. Risk: agent reports can be wrong or partial; tests may not actually run; seed counts may not match claimed values; API may fail to start. The user, when they check, would find the discrepancy and lose trust.

This compounds with [[feedback-quality-over-speed]] and [[feedback-skill-discipline]]: speed-first agent dispatch + trusting agent reports = false confidence.

**How to apply:**

After every claimed completion of a task by an agent, **before marking it done in todos or reporting "✅" to the user**, the controller (me) MUST independently run AT LEAST ONE of these verification commands:

1. **For service/spec tasks**: run the test command myself with my own Bash call:
   ```
   pnpm --filter @hrms/api test --run <pattern>
   ```
   Confirm the actual count + zero failures in MY output, not the agent's report.

2. **For schema/migration tasks**: directly query the DB with a Node one-liner:
   ```
   node -e "const {createControlClient} = require('./packages/db/dist/control'); ..."
   ```
   Verify row counts + sample row shapes.

3. **For seed tasks**: query the DB AND re-run the seed to verify idempotency in MY terminal.

4. **For controller / API tasks**: restart the API + hit the endpoints with curl. If a route doesn't respond as expected, the agent's "all tests pass" claim is hollow.

5. **For web tasks**: at minimum run `pnpm typecheck` + `pnpm lint`. Production build if possible.

**Examples of what NOT to do:**
- Agent says "508/508 passing, commit `abc123`" → controller marks done. **WRONG.** Run the tests yourself; verify the commit hash; verify the test count.
- Agent says "seed inserted 65 rows" → controller marks done. **WRONG.** Query the DB.
- Agent says "API still starts cleanly" → controller marks done. **WRONG.** Restart the API.

**Honest reporting format**: when telling the user a task is done, include the verification command + my own observed output, not the agent's claim.

Example good report:
> "Task 7 done — `46df9a1`. Verified myself: `pnpm test --run jurisdiction` → 141/141 in 28s; `git log --oneline -1` confirms HEAD."

Example bad report (what I've been doing):
> "Task 7 ✅ — 141 tests, agent says all green."

**Cost**: 30-60s per task for verification commands. Worth it. False completions cost 10× more in user trust + rework.
