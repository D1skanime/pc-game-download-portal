---
phase: 08-bounded-v1-removal
plan: 02
subsystem: frontend
tags: [vue, router, preferences, v2]
requires: [08-01]
provides: [v2-only-boot, ui-version-cleanup]
affects: [08-03, 08-04]
tech-stack:
  added: []
  patterns: [single-default-router-view, unconditional-v2-token-scope]
key-files:
  created:
    - frontend/src/v2/views/NotFound.vue
  modified:
    - frontend/src/RomM.vue
    - frontend/src/plugins/router.ts
    - frontend/src/v2/views/Settings/UserInterface.vue
key-decisions:
  - The root, auth, application, and settings layouts use only the default router view.
  - The obsolete local UI-version key is removed during startup and no longer generated or synced.
requirements-completed: [V2-01, V2-03]
duration: 7 min
completed: 2026-08-27
---

# Phase 8 Plan 2: V2-only Boot and Preference Cleanup Summary

The application now boots through one v2 shell with default router views, permanent v2 token scope, no UI selector, and silent cleanup of the old stored preference.

## Verification

- `npx vitest run src/v2/router/routeInventory.test.ts`: 3 tests passed.
- `NODE_OPTIONS=--max-old-space-size=8192 npm run typecheck`: passed.
- `git diff --check`: passed.

## Deviations from Plan

The frozen v1 switch components still require an in-memory compile-only `useUiVersion` export. Plan 08-03 deletes those consumers and the export together; it does not participate in boot or persistence.

## Self-Check: PASSED

Ready for 08-03.
