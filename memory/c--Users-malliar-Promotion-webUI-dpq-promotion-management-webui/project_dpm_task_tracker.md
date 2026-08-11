---
name: project_dpm_task_tracker
description: "Active DPM task list with completion % — tests, Tecnotree design, block-day/back-dates, mass offer-code removal, discount non-mandatory fields"
metadata: 
  node_type: memory
  type: project
  originSessionId: a39ce85d-431c-44ad-93f0-0d97a3ebda81
---

DPM work queue (set 2026-07-23). Overall progress: **~56%**.

1. **Writing unit test cases (incl. edge cases)** — ~40%
   54 Vitest tests (schemas + lib utils, Layers 0–2) done & on branch `tests/ui-suite`. Pending: server-action tests, criteria-parse transform, component tests, E2E, deeper edge cases. See [[project_ui_test_suite]] and the phased plan `docs/superpowers/plans/2026-07-22-test-coverage-expansion.md`.

2. **Design change for Tecnotree** — ~85%
   Done & pushed to `Tecnotree_design`: tt theme + Roboto, table layout pattern (fixed toolbar / scroll body / sticky header / footer+pagination bar), unified search pill, icon-button pagination + rows-per-page pill, toggle radius, blue active status tabs, Cancel→link, Back→secondary, today-date highlight, sort moved between search & filter. Remaining: footer content finalization, exact color/spacing polish. See [[project_theme_pending]].

3. **Block-day + back-dates review from develop** — ~85%
   Back-dates (date extension via `promotionMasterData.dateExtension`) on `develop` (`4cb7384`). Block-day (weekday enable/disable) now ALSO on `develop` (`d824ef7`), pushed block-day-only via worktree (0 design leaked): form-schema `enabled` flag + conditional time validation, WeekdayRow UI, create-form defaults enabled, edit-sheet buildWeekDayDefaults. Remaining: functional review/QA on develop.

4. **Mass offer-code removal when lifecycle status = Retired, in Edit Criteria page** — ~60% (uncommitted, type-clean)
   In `edit-promotion-criteria-sheet.tsx`: the EXISTING save-time "Invalid Offers" popup (fed by `validateAllPartNumbers`, which validates offer codes too and fires FIRST) now has **Clear All & Save** (`handleClearInvalidOffers`) that strips ALL flagged invalid codes via form.setValue + re-submits. `validateAllPartNumbers` returns structured `invalidEntries {path,code,type}`. Retired ones are relabeled `"X" is Retired` via backend `getRetiredOfferCodes` in `rule-actions.ts` (opposite query `lifecycleStatus=Retired`); non-retired keep channel/not-found message. Popup is height-capped + scrollable.
   OPEN BUG: for part numbers, the `=Retired` `q=<code>` search isn't returning the product (still shows "not found" instead of "is Retired"). Added `[retired-check]` server log in getRetiredOfferCodes to diagnose `retiredResults`/`matched`; likely need to query by external-system id / code field instead of free-text `q=`. Also pending: empty-criteria-node edge case after clear.

5. **Discount price-type: make 3 fields non-mandatory in UI** — ~10% (analysis done, BLOCKED on confirmation)
   For price type = Discount: time period, Unit, effective-from should NOT be required.
   FINDINGS: mandatory-ness is masterData-config-driven via `enableTimePeriodBasedOnPriceType` (array of price types). SAME array controls BOTH show and required:
   - show: `action-form-field.tsx:404` `shouldShowPriceTerm = enableTimePeriodBasedOnPriceType.includes(priceType)`
   - required: `create-promotion-form.tsx:1018` requires duration.value + duration.unit when priceType is in that array.
   Note: current required-check only enforces Time Period + Unit (NOT effective-from — verify where/if effective-from is validated).
   Removing "Discount" from the config (Option A) HIDES the fields (show+required coupled) — not wanted. Need to DECOUPLE:
   - B1 (recommended, config-driven): keep `enableTimePeriodBasedOnPriceType` for show; add new masterData key e.g. `mandatoryTimePeriodBasedOnPriceType` for required; Discount in show-not-required. Needs backend to return new key (default to existing array).
   - B2 (quick, hardcoded): skip required-check when priceType === "Discount".
   User leaning B; **awaiting confirmation before implementing.**

**How to apply:** update the per-task % and overall as items land. Recompute overall as the mean of the five task %s.
