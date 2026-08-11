---
name: stay-responsive
description: "Controller must always be ready to reply to Arun — never get blocked in long autonomous agent chains. After each agent completes, surface status promptly and wait for direction unless Arun has explicitly said \"keep going / autonomous / overnight.\""
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 242f1762-a90e-4b64-8146-d40412471165
---

After each agent task completes (or any time the user pings during a chain), pause to surface a clean status update and wait for Arun's direction before dispatching the next implementer.

**Why:** Said verbatim 2026-05-24 mid-Phase 7 — "one agent aways wait for Arun and to reply to him." Arun was on second checkin in a row while I was deep in autonomous dispatch loops and slow to respond.

**How to apply:**
- After every agent return: verify → push → 1-sentence status → wait, unless the user has explicitly given an "autonomous through to X" or "keep going overnight" mandate that's still in force.
- Earlier "gogogogo" / "do" / "after this finish phase 7" still counts as standing mandate until completion — but I should still surface status between tasks so Arun can interrupt if needed, not bury him in agent output.
- If Arun's last message was a ping/check-in (like "where are we" / "working?" / "hi"), default to short text reply BEFORE dispatching the next agent, not after.
- Tool-call latency adds up — silent gaps of 10+ minutes feel unresponsive even when work is happening. Frequent terse status > occasional verbose dumps.

Related: [[feedback-verify-dont-trust-agents]] (verify is non-negotiable, but verify + push is fast — the gating step is "wait for Arun before next dispatch").
