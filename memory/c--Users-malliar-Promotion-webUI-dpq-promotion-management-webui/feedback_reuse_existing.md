---
name: Reuse existing components over creating new ones
description: User prefers reusing existing skeletons/components/utilities instead of creating new files when an existing one fits
type: feedback
originSessionId: b502ce45-305a-4e31-ab53-3f4615ece305
---
When a new file is needed (e.g., a Next.js `loading.tsx`, a skeleton, a util), first check whether an existing component in the codebase can be reused via import. Prefer importing the existing one over writing a new equivalent.

**Why:** User corrected me when I created a brand-new spinner `loading.tsx` for `bulk/lifecycleupdate` instead of importing the existing `BulkPromotionDateExtensionSkeleton` from the sibling `bulk/dateextension` route. They said: "we should use existing loading not just create new file everytime." Avoiding duplicated UI components keeps the look consistent and prevents drift.

**How to apply:** Before writing any new component file — especially skeletons, loaders, layouts, common UI primitives — grep/glob for similar existing ones in the same feature area or under `src/components/`. If a near-fit exists, import it. Only create a new file when no reasonable existing component fits, and even then prefer extracting a shared component to a common location rather than duplicating.
