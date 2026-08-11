---
name: feedback_list_files_to_push
description: "When leaving changes for Arun to commit/push himself, always list the exact file paths involved — he pushed a partial change once because files weren't enumerated"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 04917321-b465-40af-a005-d7a683c2c5f6
  modified: 2026-07-28T08:22:00.602Z
---

Whenever changes are left in the working tree for Arun to commit/push himself, **end the summary with an explicit "files to commit" list** (exact repo-relative paths, one per line), and repeat it if the change set grows during the conversation.

**Why:** on 2026-07-28 a two-file change (Discount price-type validation: `create-promotion-form.tsx` + `create/form-schema.ts`) was described by flow ("create and edit") but not by file; Arun committed only the create file, leaving develop inconsistent until the second file was pushed later.

**How to apply:** after any working-tree change I don't commit myself, print a short block like:
```
Files to commit:
- dpm/src/components/promotions/create-promotion-form.tsx
- dpm/src/components/promotions/create/form-schema.ts
```
Also applies when several logical changes coexist — group the file list per logical commit. Related: [[feedback_create_and_edit_both]].
