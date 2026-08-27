---
phase: 08-bounded-v1-removal
plan: 03
subsystem: frontend
tags: [vue, v1-removal, redirects, i18n]
requires: [08-02]
provides: [v1-source-removal, console-route-redirects]
affects: [08-04]
tech-stack:
  added: []
  patterns: [parameter-preserving-legacy-redirects]
key-files:
  created: []
  modified:
    - frontend/src/plugins/router.ts
    - frontend/src/RomM.vue
    - frontend/src/main.ts
key-decisions:
  - Console deep links redirect to their nearest v2 route while preserving identifiers.
  - The retired April Fools route resolves through the explicit v2 not-found component.
requirements-completed: [V2-02, V2-04]
duration: 6 min
completed: 2026-08-27
---

# Phase 8 Plan 3: Remove Frozen V1 Surface and Route Fallbacks Summary

The frozen components, views, layouts, console implementation, compatibility store, obsolete locale namespace, and v1-only tests are absent, with deliberate v2 outcomes for old links.

## Verification

- `npx vitest run src/v2/router/routeInventory.test.ts src/v2/components/GameDetails/ManualSubtab.test.ts`: 5 tests passed.
- `python3 src/locales/check_i18n_locales.py`: passed.
- `python3 src/locales/check_i18n_sorted.py`: passed.
- `NODE_OPTIONS=--max-old-space-size=8192 npm run typecheck`: passed.
- Removed-path import guard: passed, except the intentional startup removal of `settings.uiVersion`.
- `git diff --check`: passed.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

Ready for 08-04.
