---
name: feedback_prefer_decisive_action
description: Prefer decisive action over clarifying questions when intent is reasonably clear
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3f45f70e-86b4-4e53-a2a5-39bf513253b7
---

This user prefers decisive action. When the intent is reasonably inferable, just do it (state the assumption briefly) instead of asking clarifying questions or using AskUserQuestion.

**Why:** They've repeatedly pushed for momentum ("go", "do it", "do bro") and rejected a clarifying-question prompt mid-task.
**How to apply:** Infer the most sensible interpretation, act, and note what you assumed. Reserve questions for genuinely ambiguous, high-stakes/irreversible forks — not for choices with an obvious default.
