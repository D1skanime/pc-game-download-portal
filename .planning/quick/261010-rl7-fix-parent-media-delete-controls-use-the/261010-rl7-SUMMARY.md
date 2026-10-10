---
name: 261010-rl7
status: complete
date: 2026-10-10
commit: 998aae57c
---

# Parent Media Delete Controls Use Scoped rom.edit

Parent-ROM provider screenshots, uploaded artwork, and owned soundtrack delete controls now reuse each component's existing scoped rom.edit management permission, matching the backend ROMS_WRITE authorization while preserving the existing owned-media actions and confirmations.

## Accomplishments

- Added focused source-contract regressions for the three parent media components.
- Removed duplicate scoped rom.delete gates and reused canManage for all six owned-media delete-control placements.
- Preserved ownership and role filters, confirmation dialogs, loading states, expected-version mutations, playlist stopping, refreshes, and snackbar behavior.

## Task Commits

1. **Task 1: Add focused permission regressions for parent media deletion** - c229f09ec
2. **Task 2: Reuse canManage for all parent owned-media delete controls** - 998aae57c

## Files Modified

- frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue
- frontend/src/v2/components/GameDetails/ScreenshotsSubtab.test.ts
- frontend/src/v2/components/GameDetails/ArtworkSubtab.vue
- frontend/src/v2/components/GameDetails/ArtworkSubtab.test.ts
- frontend/src/v2/components/GameDetails/SoundtrackPanel.vue
- frontend/src/v2/components/GameDetails/SoundtrackPanel.test.ts

## Verification

- Node v24.19.0
- Focused Vitest: 3 files passed, 14 tests passed
- Frontend typecheck: npm run typecheck passed
- The pre-fix regression run failed on the intended four new permission assertions, then passed after the gate substitution.
- No deployment performed.

## Deviations and Issues

- gsd-sdk is unavailable on team4s-linux, so quick-task SUMMARY and STATE updates were applied manually, matching the existing repository convention.
- No product-scope deviations or unrelated files were changed.

## Self-Check: PASSED

- Both task commits exist in Git history.
- All six planned source and test files are present in the commits.
- Focused tests and typecheck completed successfully.
