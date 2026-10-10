---
status: complete
quick_task: 261010-rcj
subsystem: frontend-v2-game-actions
tags: [vue, vitest, pc-platform, download-actions]
requires:
  - Existing v2 useGameActions predicate and GameActions consumers
provides:
  - Filesystem-slug PC classification for shared download actions
  - Regression coverage for composable, More menu, and header action row
affects: [GameDetails action header, More menus, PC downloads]
tech-stack:
  added: []
  patterns:
    - Shared PC classification accepts platform_fs_slug with legacy platform_slug compatibility
key-files:
  created:
    - frontend/src/v2/components/GameActions/GameActions.test.ts
  modified:
    - frontend/src/v2/composables/useGameActions/index.ts
    - frontend/src/v2/composables/useGameActions/index.test.ts
    - frontend/src/v2/components/GameActions/GameActionsList.test.ts
key-decisions:
  - "Classify PC ROMs from platform_fs_slug, retaining platform_slug=pc compatibility."
  - "Keep the existing PC component route and non-PC direct download path unchanged."
metrics:
  tests_passed: 22
  completed: 2026-10-10
---

# Quick Task 261010-rcj: Suppress copy-link for filesystem PC ROMs

The shared v2 action predicate now recognizes real PC ROMs by their filesystem platform slug, hiding copy-download-link in both action surfaces while preserving legacy PC and non-PC behavior.

## Accomplishments

- Updated useGameActions to treat platform_fs_slug == pc or platform_slug == pc as PC.
- Kept PC Download routed to the existing pc-components tab.
- Added focused composable coverage for filesystem PC, legacy PC, and non-PC direct downloads.
- Added More-menu and GameDetails header coverage for copy-link visibility and retained actions.

## Verification

- Passed with Node 24.19.0: cd frontend && npm run test -- --run src/v2/composables/useGameActions/index.test.ts src/v2/components/GameActions/GameActionsList.test.ts src/v2/components/GameActions/GameActions.test.ts
- Result: 3 test files, 22 tests passed.
- Passed with Node 24.19.0: cd frontend && npm run typecheck
- No deployment performed.

## Task Commit

Atomic code, tests, and quick-task metadata commit: 67763beb9.

## Deviations from Plan

### Auto-fixed Issues

**1. Rule 3 - Test harness import**

- Found during: Task 1 focused regression setup
- Issue: The existing test mocked getDownloadPath without importing the symbol needed for the direct-download assertion.
- Fix: Added the focused test import only.
- Files modified: frontend/src/v2/composables/useGameActions/index.test.ts

**2. Rule 3 - Remote patch tooling**

- Found during: Task 1 test setup
- Issue: The verified Linux checkout did not provide the apply_patch command.
- Fix: Used a narrowly scoped Python text-edit fallback on the verified Linux checkout.
- Files modified: The four plan-listed frontend files

## Known Stubs

None.

## Self-Check: PASSED

- The four frontend implementation/test files exist.
- The quick SUMMARY and STATE row exist.
- Commit 67763beb9 contains the implementation, tests, and quick metadata.
