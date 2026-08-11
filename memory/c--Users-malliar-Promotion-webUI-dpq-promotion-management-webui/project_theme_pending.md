---
name: project_theme_pending
description: Remaining Tecnotree-theme follow-ups on the Tecnotree_design branch (2 open, 1 done)
metadata:
  node_type: memory
  type: project
  originSessionId: 3f45f70e-86b4-4e53-a2a5-39bf513253b7
  modified: 2026-08-11T04:15:32.902Z
---

Tecnotree Figma theme work lives on branch `Tecnotree_design`. As of 2026-08-11 HEAD is `7b345fd`; branch is **23 commits ahead / 28 behind `develop`** — not merged.

**DONE — Typography (was #3).** Roboto shipped via `@fontsource/roboto` ^5.3.0 (npm, self-hosted — not the local `localFont` route originally planned). Weights 300/400/500/700 imported in `layout.tsx`; applied by `.tt body { font-family: "Roboto", ... }` in `globals.css`. Deliberately scoped to `.tt` so other themes keep Geist — Geist is still `--font-sans` and still on `<body>`.

**OPEN — Accent scale (#1), the one visibly broken thing.** 15 `accent-{shade}` usages render **no color**: `globals.css` defines only single `--color-accent` / `--color-accent-foreground`, zero `--color-accent-<number>` tokens (Tailwind v4, no config), so `bg-accent-600` / `bg-accent-50` / `border-accent-500` don't resolve. Remaining files: `bulk-lifecycle-table.tsx` (11), `multiselect.tsx` (3), `ComparatorStatusTabs.tsx` (1). Previously-listed `promotions-table.tsx` and `brand-filter.tsx` are now clean. → Fix by replacing usages with `primary`/`muted` tokens.

**OPEN by choice — Categorical colors (#5).** `calendar/utils.tsx` still uses raw Tailwind hues (violet, indigo, +12 more) for the promotion palette, plus 3 Version Comparator section icons. A deliberate exception — semantic tokens can't supply that many distinct hues. Optional: map to `chart-*`.

Related: [[feedback_reuse_existing]], [[feedback_no_coauthor_commit]].
