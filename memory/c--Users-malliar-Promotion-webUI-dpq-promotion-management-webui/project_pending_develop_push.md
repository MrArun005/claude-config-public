---
name: project_pending_develop_push
description: "Standing request - two changes on design_ui_fixes are to be pushed to develop later, only when Arun asks"
metadata: 
  node_type: memory
  type: project
  originSessionId: 28d7d99e-946d-452c-8453-9386f0347f74
  modified: 2026-08-12T05:47:43.785Z
---

Arun asked (2026-08-12) that two changes eventually reach **`develop`** — **only when he explicitly asks**, never proactively. Either one at a time or both together; his choice at the time.

1. **NonCompatibility** — commit `b885736` on branch `design_ui_fixes`: adds the `NonCompatibility` category alongside `SyncToDCM` when the related party is `VISIBLE` and `PromoSync.VISIBLE.NonCompatibility === true`. Touches `lib/utils.ts` (`determineNonCompatibility`) plus the four submit paths (create form, criteria/details/org edit sheets).
2. **"statistics"** — referent unconfirmed; likely a transcription of another change on the same branch (candidates: `3a43285` sticky headers, `b0c33db` in-card search/filters, `670e7e8` compact Brand pill + scrollbar). **Ask before pushing this one.**

All six commits are already on `origin/design_ui_fixes`. Note that branch was cut from a `Tecnotree_design` that was 2 commits behind origin, so a rebase is likely needed before any merge to `develop`.

Related: [[feedback_list_files_to_push]], [[project_theme_pending]].
