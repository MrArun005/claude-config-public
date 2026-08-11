---
name: feedback_no_coauthor_commit
description: "Never add Co-Authored-By / \"generated with Claude\" trailer to git commits"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3f45f70e-86b4-4e53-a2a5-39bf513253b7
---

Do NOT add the `Co-Authored-By: Claude ...` trailer (or any "Generated with Claude" line) to git commit messages or PR bodies for this user.

**Why:** Explicit user preference — overrides the default Claude Code commit convention.
**How to apply:** When committing, write the message with no Co-Authored-By trailer at all.
