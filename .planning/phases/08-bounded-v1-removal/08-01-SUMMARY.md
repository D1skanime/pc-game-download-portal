---
phase: 08-bounded-v1-removal
plan: 01
subsystem: frontend
tags: [vue, router, emulatorjs, v2]
requires: []
provides: [route-inventory, v2-owned-runtime-dependencies]
affects: [08-02, 08-03, 08-04]
tech-stack:
  added: []
  patterns: [explicit-route-outcomes, neutral-shared-types]
key-files:
  created:
    - frontend/src/v2/router/routeInventory.ts
    - frontend/src/v2/router/routeInventory.test.ts
    - frontend/src/v2/utils/emulatorjs.ts
    - frontend/src/v2/views/Player/EmulatorJSPlayer.vue
  modified:
    - frontend/src/stores/galleryView.ts
    - frontend/src/composables/useGameAnimation.ts
    - frontend/src/v2/views/PairDispatcher.vue
    - frontend/src/v2/views/Player/EmulatorJS.vue
key-decisions:
  - Every public route has an explicit v2 view, redirect, or removed outcome.
  - EmulatorJS runtime integration is v2-owned before frozen source deletion.
requirements-completed: [V2-02, V2-03]
duration: 8 min
completed: 2026-08-27
---

# Phase 8 Plan 1: Inventory and Shared Dependency Extraction Summary

Explicit route classification and v2-owned EmulatorJS, pairing, gallery type, and animation dependencies remove the remaining runtime coupling to frozen frontend paths.

## Verification

- `npx vitest run src/v2/router/routeInventory.test.ts`: 3 tests passed.
- `NODE_OPTIONS=--max-old-space-size=8192 npm run typecheck`: passed.
- `git diff --check`: passed.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

Ready for 08-02.
