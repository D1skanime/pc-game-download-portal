---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 11
subsystem: frontend-catalog-lifecycle
tags: [vue, typescript, vitest, catalog-removal, accessibility]
dependency_graph:
  requires: [06-02, 06-10, 06-12]
  provides:
    - catalog-only v2 ROM removal dialog
    - IDs-only shared catalog-removal client
    - partial-result and source-safety component regression coverage
  affects: [06-16, 06-17, catalog-removal, frontend-i18n]
tech_stack:
  added: []
  patterns:
    - native dialog order for future-scan exclusion and catalog confirmation
    - exact rom_ids-only request-body regression assertion
key_files:
  created:
    - frontend/src/v2/components/Dialogs/DeleteRomDialog.test.ts
  modified:
    - frontend/src/v2/components/Dialogs/DeleteRomDialog.vue
    - frontend/src/services/api/rom.ts
    - frontend/src/components/common/Game/Dialog/DeleteRom.vue
key_decisions:
  - The active v2 removal flow exposes only catalog removal and optional future-scan exclusion.
  - The shared client accepts only ROM identities and serializes only rom_ids.
requirements_completed: [CAT-01, CAT-04]
metrics:
  duration: 45m
  completed: 2026-08-13
---

# Phase 6 Plan 11: Catalog-only V2 ROM Removal Summary

The active v2 dialog now removes catalog entries through an IDs-only client while explicitly preserving original source files and retained user value.

## Performance

- **Duration:** 45 minutes
- **Started:** 2026-08-13T08:55:12Z
- **Completed:** 2026-08-13T09:40:45Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments

- Removed per-ROM and select-all source deletion controls, filesystem warnings, destructive disk icons, and filesystem-specific success handling from the active v2 dialog.
- Added explicit catalog-only, source-unchanged, retained-value, and future-scan exclusion key contracts for Plans 16 and 17 to translate.
- Narrowed the shared client to accept only ROM identities and post only the generated `rom_ids` request field.
- Preserved native dialog control order, cancel/loading behavior, optional future-scan exclusions, and mixed-result reconciliation.
- Added component coverage for forbidden-control absence, exact request shape, partial success, exclusion behavior, and rejected requests.

## Task Commits

1. **Task 1 RED: Specify catalog-only ROM removal dialog** - `e3357b784` (test)
2. **Task 1 GREEN: Make ROM removal catalog-only** - `032fe28c1` (feat)

## Files Created/Modified

- `frontend/src/v2/components/Dialogs/DeleteRomDialog.test.ts` - Proves catalog-only copy keys, forbidden-control absence, exact Axios payload, native order, partial outcomes, and error retention.
- `frontend/src/v2/components/Dialogs/DeleteRomDialog.vue` - Removes all source-delete state, controls, branches, and styles while preserving the catalog flow.
- `frontend/src/services/api/rom.ts` - Accepts only `{ roms: SimpleRom[] }` and serializes only `rom_ids`.
- `frontend/src/components/common/Game/Dialog/DeleteRom.vue` - User-authorized one-line compatibility adjustment to the existing frozen-v1 service call.

## Decisions Made

- Future-scan exclusion remains optional and follows the game list in native DOM order before Cancel and Remove from catalog.
- The component consumes dedicated catalog-removal locale keys without editing locale JSON; Plans 16 and 17 own source text and translations.
- Failed bulk items remain in local stores and selections because only IDs absent from `failed_ids` are reconciled as removed.

## TDD Gate Compliance

- RED commit `e3357b784`: all three tests failed against the legacy source-delete UI and missing catalog-only contract.
- GREEN commit `032fe28c1`: all three tests pass with exact `{ rom_ids: [1, 2] }` request-body evidence.
- RED precedes GREEN in git history.

## Deviations from Plan

### User-authorized Compatibility Adjustment

**1. Minimal frozen-v1 call-site update**

- **Found during:** Full frontend typecheck after the shared client became IDs-only.
- **Issue:** The existing frozen-v1 caller still passed `deleteFromFs`, which the required narrowed signature correctly rejected.
- **Authorization:** The user selected checkpoint option 1 and authorized editing only this existing call site.
- **Fix:** Removed the `deleteFromFs` argument without changing v1 UI, behavior, or any other v1 file.
- **Files modified:** `frontend/src/components/common/Game/Dialog/DeleteRom.vue`
- **Verification:** Full `vue-tsc --noEmit` passed.
- **Committed in:** `032fe28c1`

### Auto-fixed Issues

**2. [Rule 3 - Blocking] Removed a stale unused generated type import**

- **Found during:** Scoped ESLint verification.
- **Issue:** `BulkOperationResponse` was unused in the plan-owned shared service and blocked the scoped lint gate.
- **Fix:** Removed the unused type import.
- **Files modified:** `frontend/src/services/api/rom.ts`
- **Verification:** Scoped ESLint completed with zero errors.
- **Committed in:** `032fe28c1`

---

**Total deviations:** 2 (1 user-authorized compatibility adjustment, 1 blocking static-check fix).
**Impact on plan:** Both changes were narrowly required by the IDs-only client contract. No v1 refactor, locale edit, deployment, service restart, or source mutation was performed.

## Issues Encountered

- The Linux host has no host-level npm. Verification ran in disposable Node 24 containers with a task-owned node_modules volume.
- Scoped ESLint reported one pre-existing non-blocking self-closing `img` warning in the v2 component; commit hooks passed all four modified files.
- Locale keys are intentionally supplied by Plans 16 and 17. Repository locale parity and sorting remained green because this plan owns no locale JSON changes.

## Verification

- Genuine RED: 3 tests collected, 3 failed for the intended missing catalog-only behavior.
- Focused GREEN Vitest: 3 passed.
- Full frontend typecheck: passed with `NODE_OPTIONS=--max-old-space-size=6144`.
- Scoped Prettier: all four files conform.
- Scoped ESLint: zero errors, one pre-existing non-blocking warning.
- Locale parity: all 17 peer locales complete against en_US.
- Locale sorting: all locale files sorted.
- `git diff --check`: passed.
- Commit hooks: four modified files checked with no issues.
- Forbidden v2/service symbols are absent: source-delete state, controls, copy keys, warning branch, disk icon, and `deleteFromFs`.
- No tracked files were deleted.

## Known Stubs

None. The component key contract is deliberate and Plans 16 and 17 provide all locale values before final closure.

## Threat Flags

None. The dialog event, request boundary, and partial-result data flow were explicitly covered by the plan threat model.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- Plans 16 and 17 can add the exact catalog-only locale key set without changing the component or service contract.
- No blocker remains for Plan 15 final contract closure.

## Self-Check: PASSED

- All four key files exist in the canonical Linux checkout.
- RED commit `e3357b784` and GREEN commit `032fe28c1` exist in git history.
- Focused tests, full typecheck, formatting, lint, locale parity, locale sorting, and commit hooks passed.
- CAT-01 and CAT-04 are represented in the plan and this summary.
- No source mutation authority or filesystem deletion request field remains in the active v2 flow.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_
