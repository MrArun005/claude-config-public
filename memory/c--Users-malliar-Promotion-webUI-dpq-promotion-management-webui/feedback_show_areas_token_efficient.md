---
name: feedback-show-areas-token-efficient
description: "While building, announce which new areas of the code are being touched; work token-efficiently — slow is fine if it means less token use and longer working capacity"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 95d16b0c-961a-4de7-85ce-18545dbfcffc
  modified: 2026-07-29T09:19:05.800Z
---

While building, Arun wants visibility into which **new areas of the codebase** are being worked on — brief named updates as work moves into a new page/module/component (e.g. "now touching the edit criteria page"). He also prefers **token-efficient** operation: slower execution is fine if it consumes fewer tokens, because that lets sessions work longer.

**Why:** He isn't watching every tool call; area-level updates let him follow progress cheaply. Token budget is a real constraint — longevity of the session matters more than speed.

**How to apply:** Post a one-line status note whenever work enters a distinct new area (new route, module, or component group). Avoid re-reading files unnecessarily, prefer targeted Greps/partial Reads, don't spawn agents for things doable directly, and keep summaries selective. Pairs with [[feedback-list-files-to-push]] and [[feedback-prefer-decisive-action]].
