---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 02
subsystem: auth
tags: [vue, vitest, storage-mapping, first-run, read-only-recovery]

# Dependency graph
requires:
  - phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
    provides: Canonical Games/pc bootstrap and read-only storage readiness contracts
provides:
  - Fresh admin setup handoff into the server-owned PC storage mapping route
  - Retry-safe setup bootstrap ownership and read-only storage root recovery
affects: [phase-33, first-run-routing, storage-admin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Setup remains the sole legacy storage bootstrap caller
    - Storage root recovery surfaces remain GET-only and read-only

key-files:
  created:
    - frontend/src/v2/views/Auth/Setup.test.ts
    - frontend/src/v2/components/Settings/StorageRootsSection.test.ts
  modified:
    - frontend/src/v2/views/Auth/Setup.vue
    - frontend/src/v2/components/Settings/StorageRootsSection.vue

key-decisions:
  - "Use the server-returned platform ID when opening the existing mapping workflow after authenticated setup."
  - "Keep retry ownership in Setup and remove legacy bootstrap mutation from StorageRootsSection."

patterns-established:
  - "Fresh setup authenticates, refreshes session state, bootstraps once, and routes to PLATFORM_STORAGE_MAPPING."
  - "Read-only storage recovery does not expose or invoke bootstrapLegacy."

requirements-completed: [PGDP-33-01]

# Metrics
duration: reconciliation only
completed: 2026-10-15
---

# Phase 33 Plan 02: First-run setup mapping handoff Summary

**Fresh admin setup now enters the server-owned PC mapping workflow while storage root recovery remains read-only**

## Performance

- **Duration:** Reconciliation of existing commits only
- **Started:** Existing implementation commits from 2026-10-15 15:24 UTC
- **Completed:** 2026-10-15
- **Tasks:** 2 implemented, reconciled from existing commits
- **Files modified:** 4 source/test files, plus this summary

## Accomplishments

- Confirmed `a327bc129` implements authenticated setup completion, the sole bootstrap call, and navigation with the returned `platform_id`.
- Confirmed `5e841a731` preserves retry ownership in Setup and removes `bootstrapLegacy` from `StorageRootsSection`.
- Confirmed focused coverage for successful handoff, missing mapping, retry without recreating the admin, and zero recovery bootstrap calls.

## Task Commits

1. **Task 1: Route successful admin setup into canonical PC mapping** - `a327bc129` (feat)
2. **Task 2: Remove legacy bootstrap callers and constrain recovery** - `5e841a731` (fix)

## Verification

- Focused Vitest passed in the verified Linux checkout using the PGDP development container:
  - `Setup.test.ts`: 3 tests passed
  - `StorageRootsSection.test.ts`: 1 test passed
  - Total: 2 test files, 4 tests passed
- `python3 frontend/src/locales/check_i18n_locales.py` passed.
- `python3 frontend/src/locales/check_i18n_sorted.py` passed.
- The previously launched full frontend Vitest run had no completion result and remained active without a final summary. It was treated as timed out/blocked and stopped. No full-suite pass is claimed.
- Frontend typecheck was not completed because reconciliation was stopped at the user's request. No implementation changes were made during this reconciliation.

## Files Created/Modified

- `frontend/src/v2/views/Auth/Setup.vue` - Authenticated bootstrap and server-owned mapping route handoff.
- `frontend/src/v2/views/Auth/Setup.test.ts` - Setup success, missing mapping, and retry coverage.
- `frontend/src/v2/components/Settings/StorageRootsSection.vue` - Read-only storage root and mapping management surface without legacy bootstrap.
- `frontend/src/v2/components/Settings/StorageRootsSection.test.ts` - Regression proof that the component never calls `bootstrapLegacy`.

## Decisions Made

- Reconciled the existing implementation commits without reimplementing or reverting code.
- Preserved the pre-existing `.planning/STATE.md` modification.

## Deviations from Plan

None in implementation. Verification was limited by the interrupted full Vitest run and the user's request to stop further checks.

## Issues Encountered

- A leftover full Vitest process was found in the frontend container, had not produced a completion summary, and was stopped before reconciliation continued.
- The prescribed `docker compose exec` service name was unavailable from the PGDP compose context, so the focused tests were run through the already-running PGDP development container with the verified repository mounted at `/app/frontend`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 33-02 implementation is present in commits `a327bc129` and `5e841a731`. The focused verification and locale checks pass. A full Vitest result and frontend typecheck remain unavailable from this interrupted reconciliation and should be run separately if required.

## Self-Check: PASSED

- Summary file created at the required phase path.
- Commits `a327bc129` and `5e841a731` exist in Git history.
- Pre-existing `.planning/STATE.md` modification was preserved.
- No implementation files were changed during reconciliation.

---
*Phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc*
*Completed: 2026-10-15*
