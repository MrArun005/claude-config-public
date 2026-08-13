---
name: reference_claude_config_backup
description: "Personal Claude Code config (CLAUDE.md, skills, all project memory) is backed up to a private GitHub repo"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 28d7d99e-946d-452c-8453-9386f0347f74
  modified: 2026-08-11T15:06:03.463Z
---

Claude Code config is backed up at **https://github.com/MrArun005/claude-config** (private, created 2026-08-11).

Local working copy: `C:\Users\malliar\claude-config` — a **separate** directory, deliberately not a git repo inside `~/.claude`, because that directory holds `.credentials.json`, `history.jsonl`, `sessions/` and full conversation transcripts that must never be committed.

Contents: `CLAUDE.md`, `skills/job-hunt/`, and `memory/<project-key>/*.md` for all 5 projects (57 files). README documents the restore procedure.

To refresh after memory changes: re-copy the three sources into `~/claude-config`, then commit and push.

Must stay **private** — the memory files include job-hunt/FAANG plans, employer-internal ticket detail, and colleagues' names. Commits use the work identity `Arun M <Arun.Mallikarjun@tecnotree.com>` (Arun confirmed this deliberately when asked).
