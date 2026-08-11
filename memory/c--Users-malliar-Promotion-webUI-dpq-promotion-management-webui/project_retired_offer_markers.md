---
name: project_retired_offer_markers
description: "Retired-offer marker + channel-less-offer filter work (built 2026-07-29) was DISCARDED 2026-07-30 at Arun's request — not needed now; how to rebuild if wanted later"
metadata: 
  node_type: memory
  type: project
  originSessionId: 04917321-b465-40af-a005-d7a683c2c5f6
  modified: 2026-07-30T10:47:23.827Z
---

Built 2026-07-29 for the offer-code picker, then **discarded (git stash dropped) 2026-07-30** — Arun said "not needed right now." All in `dpm/src/app/actions/rule-actions.ts` + `combo-box.tsx` + `global.d.ts` (3 files, ~51 lines).

**What it did (rebuild spec if resurrected):**
1. **Hide channel-less offers** in `getProductCodeOptions` — both the external-system branch and the plain-code branch skipped any offer with `(channel ?? []).length === 0` (they'd only fail channel validation on save). Removed the now-dead `'No Channel'` label fallbacks.
2. **Mark retired offers in the list** — on search (query present), `getProductCodeOptions` also queried the retired mirror (`getRetiredProducts` with the same q/brand/channel filters) and appended matches with a new `retired: true` flag.
3. `IRuleOption` + `ComboBoxItemType` gained an optional `retired?: boolean`.
4. `combo-box.tsx` rendered a red "Retired" badge, dimmed the row, blocked NEW selection of retired items but allowed DESELECTING an already-saved one (pairs with Clear All & Save).

Related: the "Clear All & Save" popup + `getRetiredOfferCodes` are ALREADY committed on develop (kept) — this discarded work was the picker-side complement. See [[project_price_type_discount]] context is separate. Superseded discussion 2026-07-30: a new channel-match requirement inside the externalSystem branch (externalSystem.channel.name === url channel → list; no channel → show as valid) was being discussed when this was discarded.
