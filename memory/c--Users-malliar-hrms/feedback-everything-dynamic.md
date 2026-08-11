---
name: feedback-everything-dynamic
description: "STRICT RULE — all business rules (tax rates, holidays, countries, regions, statutory percentages) must be DB-resident and operator-editable, NOT hardcoded in TypeScript"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 242f1762-a90e-4b64-8146-d40412471165
---

User issued on 2026-05-23 (~10:30 IST): "we should make everything dynamic — make this strict rule — all rules tax rules holidays country whatever we can do dynamically we have to do it"

**Why:** This is a multi-tenant SaaS HRMS. Each tenant could be in a different jurisdiction with different rates. Statutory rates change annually (TDS slabs, SS wage base, SUI rates per state). Hardcoding ANY of this in TypeScript means a code deploy is required to update — unacceptable for production. Customers must be able to update their own rates without engineering involvement.

**How to apply:**

### What MUST be DB-resident (not hardcoded constants)

1. **Tax slabs / brackets** — `TaxSlab` model with `country`, `regime`, `fiscalYear`, `lowerBound`, `upperBound`, `rate` rows. NEVER as a TypeScript `const SLABS = [...]`.
2. **Statutory rates** — `StatutoryRate` model with `country`, `kind` (PF/ESI/FICA/SUI/etc.), `region` (state where applicable), `effectiveFrom`, `effectiveTo`, `employeeRate`, `employerRate`, `wageBase`, `wageCap` rows. Versioned, so historical recompute is correct.
3. **Holidays** — already DB-driven via `Holiday` model. The `IN_GAZETTE_HOLIDAYS_2026_2030` TypeScript constant is ONLY for seeding the acme demo tenant; production tenants get an empty table they populate themselves (or import from gazette JSON).
4. **Leave policies** — already DB-driven via `LeavePolicy` model with `region` column. Each tenant can have any combination of regions + policies.
5. **Countries** — `Country` model (`code`, `name`, `currency`, `defaultLocale`, `payrollFrequencies`). NOT a TypeScript union type.
6. **Regions / states** — `Region` model (`code`, `countryCode`, `name`). The location → region mapping should also be DB-driven (or at least overridable via tenant settings) rather than the hardcoded `regionForLocation` switch.
7. **Salary structure formulas** — DSL/JSON in `SalaryComponent.formulaKey` resolved via DB lookup, not switch statements.
8. **Workflow definitions** — already DB-driven via Phase 0.8 `WorkflowService`.
9. **Approval routing** — `Employee.managerId` already drives manager chain; admins should be able to override via DB.
10. **Email templates, letter templates, notification rules** — already DB-driven.

### What's allowed to stay in code

- Type definitions (interfaces, enums for compile-time safety like `LeavePolicyKind`)
- Pure algorithms (day-count helpers, payroll math, NACHA file format builders)
- Infrastructure scaffolding (Cerbos policy structure, audit field shapes)
- Bootstrapping SEED data for the demo `acme` tenant — but only as a one-time seed, not as runtime defaults

### The acid test

For any business rule or data point: "Can a tenant admin in the production UI change this without an engineer touching code?" If the answer is no, it should be DB-resident.

### Implications for current/future work

- **Phase 2.3 (in progress)**: LeavePolicy + Holiday models are already DB-driven; the TypeScript packs (`INDIA_POLICY_PACK`, `IN_GAZETTE_HOLIDAYS_2026_2030`) are SEED data only. Compliant. Continue.
- **Phase 3 (Payroll, planned but not yet executed)**: VIOLATES this rule heavily — the plan has `pf.ts`, `esi.ts`, `tds-slabs.json` constants. **Must be replanned**: TaxSlab + StatutoryRate models, admin UI for editing, services read from DB.
- **Existing `regionForLocation` heuristic** in `payroll/region.ts` (planned): replace with `LocationMapping` DB model.
- **Future country additions**: should be adding rows to `Country` + `StatutoryRate` + `TaxSlab` tables, not new TypeScript files.

### Migration path

Don't retroactively rewrite already-shipped Phase 2.1/2.2 code (LeavePolicy + Holiday + ShiftTemplate are already DB-driven). For Phase 3 onwards, design DB-first.

[[feedback-quality-over-speed]] and [[feedback-skill-discipline]] still apply — the new constraint just shapes what "quality" means structurally.
