---
name: feedback_create_and_edit_both
description: "Any promotion-flow change must be applied to BOTH create and edit flows — Arun expects this by default, without asking"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 04917321-b465-40af-a005-d7a683c2c5f6
  modified: 2026-07-28T08:11:51.672Z
---

When Arun asks for a behavior/validation/UI change in the promotion flows, apply it to **both the create flow and the edit flow** in the same pass — never just one.

**Why:** DPM duplicates most logic between `create-promotion-form.tsx` and the `edit-promotion-*-sheet.tsx` files (validation runs in schemas AND in runtime submit handlers in both flows). Fixing one side leaves the other inconsistent, and Arun has had to ask twice (2026-07-28, Discount price-type duration rule).

**How to apply:** for every such change, sweep all enforcement points: `create/form-schema.ts` (create + edit schemas), `create-promotion-form.tsx` runtime checks, `edit-promotion-details-sheet.tsx` (+ other edit sheets) runtime checks. Grep for the error message text to find every copy. State explicitly in the summary which create/edit sites were touched.
