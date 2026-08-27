# claude-config

Backup of my personal Claude Code configuration: global instructions, custom
skills, and accumulated project memory.

> **Keep this repository private.** The memory files contain personal career
> notes, employer-internal project details, and other people's names.

## Layout

```
CLAUDE.md              Global instructions applied to every project
skills/                Custom skills
  job-hunt/            Résumé tailoring + batch job application agent
memory/                Per-project memory, one directory per project
  <project-key>/
    MEMORY.md          Index loaded into context each session
    *.md               One fact per file
autoapply/             OwnCrawl v2 job-application agent (own README)
```

The `<project-key>` directory names mirror Claude Code's own encoding of the
project path (e.g. `c--Users-malliar-hrms` for `C:\Users\malliar\hrms`).

## Restoring

Copy back into `~/.claude/`:

```bash
cp CLAUDE.md ~/.claude/CLAUDE.md
cp -r skills/. ~/.claude/skills/
for d in memory/*/; do
  proj=$(basename "$d")
  mkdir -p ~/.claude/projects/"$proj"/memory
  cp "$d"*.md ~/.claude/projects/"$proj"/memory/
done
```

## autoapply

`autoapply/` is a standalone tool rather than Claude Code config, kept here so
it is backed up alongside the job-hunt skill it complements. Its own README
covers setup and the rung 1-4 execution ladder. Its answer bank
(`autoapply/state/answers.yaml`) holds personal data and is gitignored — only
`answers.example.yaml` is tracked.

## What is deliberately excluded

Nothing else from `~/.claude/` is here. In particular `.credentials.json`,
`history.jsonl`, `sessions/`, and the conversation transcripts under
`projects/` are never copied — this repo holds only instructions, skills, and
memory.
