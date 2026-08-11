---
name: project_price_type_discount
description: "Arun flagged the 'Discount' price type as an active topic (2026-07-28) — duration rules + where it lives; details of the pending discussion TBD"
metadata: 
  node_type: memory
  type: project
  originSessionId: 04917321-b465-40af-a005-d7a683c2c5f6
  modified: 2026-07-28T08:18:38.045Z
---

Arun asked (2026-07-28) to remember the **price type "Discount"** topic — an ongoing discussion whose specifics he hasn't restated yet in this workspace.

Grounded code facts (verified 2026-07-28):
- `priceType` on promotion actions; known values: `Discount`, `OneTimeDiscount`, `OneTimePrice`, `Recurring`, `Flat` (options list in `action-form-field.tsx:165`; templates mostly use `OneTimeDiscount`, CHURN templates use `Discount`).
- Schema rule (`create/form-schema.ts:640-664`): for **DPM** promotions of type Shipping/ProductLevel, priceType `Discount`/`OneTimePrice`/`Recurring` **requires `priceTerm.duration.value` + `.unit`** — covered by 2 unit tests in `form-schema.edit-details.test.ts`.
- Version comparator labels `itemTotalPrice.priceType` as "Discount Type".

**Resolved 2026-07-28 — requirement: duration must NOT be mandatory for priceType "Discount" ONLY; OneTimePrice/Recurring stay mandatory.** Implemented (working tree, develop):
- `EditPromotionDetailsSchema`: duration rule list changed from [Discount, OneTimePrice, Recurring] → [OneTimePrice, Recurring] (messages updated too).
- Create flow: "Discount" filtered out of `masterData.enableTimePeriodBasedOnPriceType` before the runtime check; OneTimePrice/Recurring stay config-driven.
- DCOT+BRM duration rule (separate business rule, BE-validated too) deliberately untouched.
- The 2 edit-details unit tests on `tests/ui-suite` assert Discount-mandatory — update them to assert Discount-optional + OneTimePrice-mandatory when that branch syncs.

Related: [[project_bulk_lifecycle_date_filters]], test coverage plan Phase 2.
