---
name: feedback_no_unasked_code_changes
description: "Never modify product/source code unless Arun explicitly asks — 'write test cases' means test files ONLY, no refactors/extractions/helpers in src/"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 04917321-b465-40af-a005-d7a683c2c5f6
  modified: 2026-07-29T10:16:05.136Z
---

Do exactly what Arun asks, nothing adjacent. "Write test cases" = create test files only. It does NOT license refactoring, extracting logic into new src/ modules, rewiring components, or any change to product code — even when that would make the code testable.

**Why:** on 2026-07-29 he asked for criteria test cases; I started extracting component logic into src/lib and rewiring the component. He stopped me twice ("don't do code changes bro"). His dev server runs from the working tree, so unasked edits also disturb his live testing.

**How to apply:** if the asked-for work genuinely requires touching src/ (e.g. logic is un-importable), STOP and present the constraint + the minimal change needed, and let him decide — do not do it preemptively. Default workspace state: only files he explicitly asked to change may be modified. Related: [[feedback_prefer_decisive_action]] (decisive within the asked scope, not beyond it), [[feedback_list_files_to_push]].
