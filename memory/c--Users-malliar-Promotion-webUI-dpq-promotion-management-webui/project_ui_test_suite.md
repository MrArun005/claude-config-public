---
name: project-ui-test-suite
description: "First UI test suite for dpm — schema + util unit tests; what's covered and deferred"
metadata: 
  node_type: memory
  type: project
  originSessionId: de7ab325-bfc0-4796-b5e3-919ea1930a28
---

First automated test suite for `dpm/` landed July 2026 (Vitest + RTL — see [[project_test_tooling]]). Scope was **Layers 0-2**: Zod schema `.safeParse` tests + pure-util tests. **54 tests, 9 files, ~6s, no backend.**

Covered: `CreatePromotionSchema` (DPM/BRM baselines, channel, priority, name, BRM relatedParty/paymentMethod/priceRule, alias-required actions), `CouponSchema`, `EditValidForSchema` (date range + weekday windows), `EditPromotionDetailsSchema` (actionAllocation + DPM duration), `EditTranslationsSchema` (localization uniqueness), and utils in `lib/utils.ts`, `lib/localization-utils.ts`, `lib/promotion-utils.ts`. Shared fixtures: `src/test/promotion-fixtures.ts`.

**Deferred (not done):** Layer 3 = RTL component-render tests (status-badge, validfor-form-field); E2E/Playwright; server actions. The 2031-line `create-promotion-form.tsx` was intentionally NOT render-tested — its rules are covered via the schema instead.

**Finding:** `CouponSchema.couponValidity` is NOT optional — a bare `{couponCodeBehaviour:"Empty"}` fails validation because the "Empty" branch only skips pattern/price checks, not the required `couponValidity` object. Possible latent bug if the UI allows Empty coupons without validity.

Design + plan docs: `docs/superpowers/specs/2026-07-15-ui-test-suite-design.md`, `docs/superpowers/plans/2026-07-15-ui-test-suite.md`. **All test work left UNCOMMITTED per user request** (user prefers to commit themselves — see [[feedback_prefer_decisive_action]]).
