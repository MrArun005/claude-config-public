---
name: project-test-tooling
description: dpm test stack is pinned to old versions because of Node 20.18 on this machine
metadata: 
  node_type: memory
  type: project
  originSessionId: de7ab325-bfc0-4796-b5e3-919ea1930a28
---

The `dpm/` app uses **Vitest + React Testing Library** for UI tests (set up July 2026). The stack is deliberately pinned to OLD versions: `vitest@0.34.6`, `vite@4.5.14`, `@vitejs/plugin-react@4.7.0`, `jsdom@22.1.0` (testing-library packages are latest). Config: `dpm/vitest.config.ts` (jsdom env, `@/*` alias, `css.postcss.plugins: []` workaround), `dpm/vitest.setup.ts`. Scripts: `pnpm test` / `pnpm test:watch`. Tests colocate as `*.test.ts(x)`.

**Why:** the machine runs **Node 20.18.0** (no version manager). Modern vitest 3/4, vite 7/8, and jsdom 29 are ESM-only and need Node ≥20.19 — on 20.18 they crash with `ERR_REQUIRE_ESM` or a require-module recursion bug. A `"vite": "^4.5.14"` pnpm override in `dpm/package.json` forces the CJS-capable vite tree-wide (safe: the app uses Next's bundler, not vite).

**How to apply:** If upgrading Node to ≥20.19 (ideally 22 LTS), you can drop the pins, the `vite` override, and the `css.postcss` workaround and move to latest vitest/vite/jsdom. Until then, don't bump these. First test suite (Layers 0-2) is schema `.safeParse` + pure-util tests only — no React rendering — see [[project_ui_test_suite]].
