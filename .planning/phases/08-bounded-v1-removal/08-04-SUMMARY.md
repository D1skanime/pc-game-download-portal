---
phase: 08-bounded-v1-removal
plan: 04
subsystem: frontend
tags: [vitest, router, boot, regression]
requires: [08-03]
provides: [v2-route-regression-gate, v2-boot-regression-gate]
affects: [phase-09]
tech-stack:
  added: []
  patterns: [import-graph-fixture, deleted-tree-guard]
key-files:
  created:
    - frontend/src/v2/router/v2Boot.test.ts
  modified:
    - frontend/src/v2/router/routeInventory.test.ts
key-decisions:
  - Focused tests validate route records and required module loaders without browser or live infrastructure.
  - Deleted source trees are guarded by filesystem assertions in the boot suite.
requirements-completed: [V2-03, V2-04, V2-05]
duration: 4 min
completed: 2026-08-27
---

# Phase 8 Plan 4: Targeted V2 Regression Gate Summary

Focused regression coverage now locks route outcomes, the single v2 boot path, required shared imports, generated contracts, overlays, and physical absence of frozen source.

## Verification

- `npx vitest run src/v2/router/routeInventory.test.ts src/v2/router/v2Boot.test.ts src/v2/components/GameDetails/ManualSubtab.test.ts`: 9 tests passed.
- `trunk check frontend/src/v2/router/routeInventory.test.ts frontend/src/v2/router/v2Boot.test.ts`: passed after one automatic formatting fix.
- `python3 src/locales/check_i18n_locales.py`: passed.
- `python3 src/locales/check_i18n_sorted.py`: passed.
- `NODE_OPTIONS=--max-old-space-size=8192 npm run typecheck`: passed.
- `git diff --check`: passed.
- Browser, live NAS, deployment, and service checks were intentionally deferred to Phase 9.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

Phase complete, ready for verification and Phase 9 live validation.
