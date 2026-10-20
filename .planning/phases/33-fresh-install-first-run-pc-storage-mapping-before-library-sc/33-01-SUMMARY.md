---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 01
subsystem: storage
tags: [fastapi, vue, vitest, pytest, storage-mapping]

requires:
  - phase: 32-pgdp-namensumstellung-fresh-installation
    provides: Canonical PGDP naming and disposable Compose verification setup
provides:
  - Canonical Games root plus pc relative-path bootstrap representation
  - Idempotent reconciliation from the prior Games/pc plus empty-relative representation
  - Read-only server-backed storage mapping readiness helper
affects: [phase-33, first-run-routing, scan-readiness]

tech-stack:
  added: []
  patterns:
    - Server-owned storage mapping and root IDs
    - Readiness requires active, reachable, readable, non-writable root health

key-files:
  created:
    - backend/tests/endpoints/storage/test_legacy_bootstrap_paths.py
  modified:
    - backend/endpoints/storage.py
    - backend/tests/endpoints/test_storage.py
    - frontend/src/services/api/storage.ts
    - frontend/src/services/api/storage.test.ts

key-decisions:
  - "Persist the configured Games directory as the storage root and pc as the mapping relative path, producing Games/pc without storing host paths in the mapping."
  - "Treat a missing mapping as not-ready and never invoke bootstrap from the readiness helper."

patterns-established:
  - "Setup bootstrap is the sole legacy storage mutation path."
  - "Readiness is derived only from GET mapping and GET roots responses."

requirements-completed: [PGDP-33-01]

duration: 5 min
completed: 2026-10-15
---

# Phase 33 Plan 01: Canonical PC storage bootstrap and readiness Summary

**Canonical Games/pc storage bootstrap with idempotent legacy reconciliation and GET-only readiness evaluation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-15T15:10:00Z
- **Completed:** 2026-10-15T15:15:15Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Changed legacy bootstrap to register the configured Games root and persist `pc` as the relative mapping path.
- Preserved canonical Windows platform identity and reconciled the old Games/pc plus empty-relative mapping.
- Added typed frontend readiness that requires all server root health predicates and performs no POST.
- Added focused backend and frontend contract coverage.

## Task Commits

1. **Task 1: Persist the exact canonical Games/pc bootstrap pair** - `bec76a7` (test), `12c6811` (feat)
2. **Task 2: Add read-only server-backed readiness helpers** - `9b19c68` (test), `ea4514f` (feat)

## Files Created/Modified

- `backend/endpoints/storage.py` - Registers Games and maps Windows to `pc`.
- `backend/tests/endpoints/storage/test_legacy_bootstrap_paths.py` - Covers identity, exact paths, idempotency, and reconciliation.
- `backend/tests/endpoints/test_storage.py` - Confirms mutation and read route contracts.
- `frontend/src/services/api/storage.ts` - Adds `getMappingReadiness`.
- `frontend/src/services/api/storage.test.ts` - Covers ready and not-ready server states.

## Decisions Made

- Followed the plan's existing storage handler and resolver contracts without adding a table, resolver, alias map, or endpoint.
- Kept the pre-existing `.planning/STATE.md` modification untouched.

## Deviations from Plan

### Verification Environment Blocker

The prescribed backend command was run twice, but the test fixture failed before assertions because the disposable runner resolves MariaDB at `127.0.0.1:3306`, while the available `pgdp-db-dev` service is Compose-network-only. No service was restarted or changed. The generated root-owned `backend/pgdp_test/` artifact was removed.

## Issues Encountered

- Backend focused pytest: blocked during database fixture setup with `mariadb.OperationalError`, 68 setup errors in the final prescribed run.
- Frontend focused Vitest: passed, 10 tests.
- Frontend typecheck: passed with `vue-tsc --noEmit`.
- The Windows checkout was not modified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The backend and frontend contracts needed by first-run mapping routing are ready. The backend focused suite should be rerun in a runner with MariaDB reachable at the configured test endpoint.

## Self-Check: PASSED

- Summary file exists at this path.
- Task commits `bec76a7ae`, `12c68113b`, `9b19c68d0`, and `ea4514f10` exist in Git history.
- Only the planned five source/test files are present in the plan diff; pre-existing `.planning/STATE.md` remains the only unstaged change before metadata updates.

---
*Phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc*
*Completed: 2026-10-15*
