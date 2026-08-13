---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 13
subsystem: legacy-migration-rollback
tags: [sqlalchemy, rollback, transactions, mariadb, mysql, postgresql, tdd]
dependency_graph:
  requires: [06-06, 06-08, 06-12]
  provides:
    - exact migration-owned catalog rollback
    - stale recorded-row rejection
    - restart-persistent three-dialect restoration evidence
  affects: [legacy-migration, rollback, catalog-reachability]
tech_stack:
  added: []
  patterns:
    - ordered exact-row locking and lineage validation
    - persisted scalar before-state restoration
    - atomic stale rejection and failure retry
key_files:
  created: []
  modified:
    - backend/handler/database/legacy_migration_handler.py
    - backend/tests/handler/database/test_storage_lifecycle.py
    - backend/tests/integration/test_legacy_migration.py
    - backend/tools/verify_storage_migrations.py
    - backend/tests/tools/test_verify_storage_migrations.py
decisions:
  - Rollback locks persisted change records first, then the exact recorded ROM set plus recorded RomFile parents, then recorded RomFiles in deterministic ID order.
  - Any missing, moved, cross-platform, or externally changed recorded row makes the entire rollback fail with legacy_rollback_stale.
  - The disposable verifier retains mixed unrelated and later-created rows across a real restart and validates exact restoration before and after a second restart.
metrics:
  duration: 31m
  completed: 2026-08-13
---

# Phase 6 Plan 13: Exact Legacy Catalog Rollback Summary

Unused legacy migration rollback now restores only the persisted ROM and RomFile before-state, rejects stale catalog evidence atomically, and survives real MariaDB, MySQL, and PostgreSQL restarts.

## Performance

- **Duration:** 31 minutes
- **Started:** 2026-08-13T09:49:13Z
- **Completed:** 2026-08-13T10:20:07Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Replaced platform-wide ROM and RomFile rollback updates with restoration of only persisted migration change rows.
- Locked and validated every recorded entity, recorded RomFile parent lineage, platform ownership, and migration-produced current value before changing any catalog row.
- Preserved already-visible, unmatched-missing, ambiguous or invalid, and later-created catalog rows across writable and read-only source rollback.
- Added bounded stale rejection for changed, deleted, cross-platform, replayed, and concurrently edited rollback evidence without partial mapping, migration, audit, or catalog mutation.
- Added mapping, catalog, audit, and migration atomicity coverage through injected flush failure and retry.
- Extended the disposable database verifier with mixed exact state, durable change records, later-created rows, real restarts, guarded downgrade, cleanup, and re-upgrade across MariaDB, MySQL, and PostgreSQL.
- Preserved external source manifests and avoided descriptor construction, filesystem enumeration, host-path persistence, and raw-source persistence during rollback.

## Task Commits

1. **Task 1: Specify exact rollback over mixed and later catalog state**
   - `4cf75286e` test(06-13): specify exact catalog rollback
2. **Task 2: Capture and restore the exact validated change set**
   - `3a805900e` feat(06-13): restore exact catalog state
3. **Task 3: Prove exact rollback durability across supported databases**
   - `40829e2c7` test(06-13): specify durable exact rollback verification
   - `a25fd1822` feat(06-13): verify exact rollback on all dialects

## Files Created/Modified

- `backend/handler/database/legacy_migration_handler.py` - Locks exact durable changes and their lineage, rejects stale state, and restores only recorded prior booleans.
- `backend/tests/handler/database/test_storage_lifecycle.py` - Asserts exact migration-owned change records and uses a real bounded source fingerprint in the migration fixture.
- `backend/tests/integration/test_legacy_migration.py` - Covers mixed and later rows, stale mutation/deletion/cross-platform cases, catalog-change and first-use races, source neutrality, flush failure, retry, replay, and atomicity.
- `backend/tools/verify_storage_migrations.py` - Seeds and verifies exact catalog restoration through real restarts and upgrade/downgrade round trips on all supported dialects.
- `backend/tests/tools/test_verify_storage_migrations.py` - Requires mixed durable verifier evidence, later-row ordering, and exact restoration checks.

## Decisions Made

- Change records remain the only rollback mutation authority; rollback never enumerates a platform-wide catalog set.
- Recorded RomFile parent ROMs are locked with the exact recorded entities so lineage cannot change between validation and restoration.
- The live row must still contain the migration-produced value before restoration. Newer catalog edits win by making rollback stale.
- Change records are retained after successful rollback as durable evidence while replay is rejected by migration state and version.
- MySQL retains its established minimal 0107 verifier baseline, extended only with the catalog columns needed for exact restoration; MariaDB and PostgreSQL additionally execute the production handler/model topology.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Repaired the real migration fixture fingerprint**

- **Found during:** Task 2 full verification
- **Issue:** The existing selectable detection fixture had no source fingerprint and failed revision 0112's selectable-result constraint before the planned migration test could execute.
- **Fix:** Derived the fixture fingerprint through the trusted storage composition and detector used by production.
- **Files modified:** `backend/tests/handler/database/test_storage_lifecycle.py`
- **Commit:** `3a805900e`

**2. [Rule 2 - Missing critical functionality] Locked recorded RomFile lineage parents**

- **Found during:** Task 2 lock-order review
- **Issue:** Locking a recorded RomFile without its parent ROM left a concurrent platform-lineage change outside the rollback transaction's validation barrier.
- **Fix:** Read recorded file lineage, lock the exact union of recorded ROMs and recorded file parents in ID order, then lock and revalidate recorded RomFiles.
- **Files modified:** `backend/handler/database/legacy_migration_handler.py`
- **Commit:** `3a805900e`

## Test Results

- Task 1 genuine behavioral RED: exact rollback changed already-visible and later-created catalog rows.
- Focused exact rollback suite after GREEN: 6 passed.
- Barrier-backed catalog-change race gate: passed.
- Planned lifecycle and integration suite: 46 passed, 2 warnings.
- Verifier unit RED: missing durable exact catalog evidence.
- Verifier unit suite after GREEN: 11 passed, 2 warnings.
- Post-commit combined plan suite: 57 passed, 2 warnings.
- Real three-dialect verifier: MariaDB 10.11, MySQL 8.4, and PostgreSQL 15 passed pristine upgrade, seeded upgrade, exact rollback across restart, guarded downgrade, cleanup downgrade, and re-upgrade.
- MariaDB and PostgreSQL verifier handler/model topology: 54 passed on each dialect. MySQL retained the established minimal 0107 baseline and ran the exact raw transaction/durability verifier.
- Scoped commit hooks: all four task commits formatted and checked with no issues.
- `git diff --check`: passed.
- Task-owned migration containers, isolated database `romm_test_0613`, and verifier log were removed.

## Known Stubs

None.

## Threat Flags

None. Rollback IDs, persisted change rows, catalog concurrency, mapping lineage, external source neutrality, and database portability were all within the plan threat model.

## Self-Check: PASSED

- Summary artifact exists at the required phase path.
- Task commits `4cf75286e`, `3a805900e`, `40829e2c7`, and `a25fd1822` exist.
- All five key modified files exist.
- No plan commit deleted tracked files.
