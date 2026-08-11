---
name: Bulk lifecycle + date-filter behaviors (May 2026)
description: Non-obvious UX rules for the date range filter and bulk lifecycle confirmation, gated by validation that automated tests must respect
type: project
originSessionId: 07359bbd-cc00-4676-8f93-0aa65b8d63c2
---
Two related behavior rules in the promotion-management webui as of mid-May 2026:

**1. Date range filter requires BOTH ends** ([filter-selects.tsx](dpm/src/components/filter-selects.tsx))
- Picking only a start OR only an end date does NOT update URL params or refetch — it stays in local state.
- URL params (`validFor.startDateTime`, `validFor.endDateTime`) update only when both ends are set, or when both are cleared.

**Why:** users reported that selecting just one date caused half-applied filters and confusing result sets. Fixed in commit `a56ba62` (Bhutite, 2026-05-19).

**How to apply:** any e2e test or new filter UI on this page must select both ends to actually trigger a filter, or clear both to reset.

**2. Bulk lifecycle confirm requires ALL target statuses chosen** ([bulk-lifecycle-table.tsx](dpm/src/components/promotions/table/bulk-lifecycle-table.tsx))
- `individual` mode: every row must have a status picked.
- grouped mode: every unique source-`lifecycleStatus` must have a target picked.
- Confirm button stays disabled until then (and on top of the existing `hasStatusPermission` check).

**Why:** users were able to submit half-configured bulk updates and got partial results. Added in commit `6423644` (Arun, 2026-05-19).

**How to apply:** any test of the bulk lifecycle wizard must populate target statuses for every selected row/group before expecting Confirm to be clickable.
