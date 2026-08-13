---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 21
subsystem: legacy-migration-lineage
tags: [alembic, sqlalchemy, mariadb, mysql, postgresql, rollback, tdd]
requires:
  - phase: 06-13
    provides: exact change-set rollback and deterministic catalog locking
  - phase: 06-20
    provides: portable 0112 predecessor lifecycle and three-dialect verifier
provides:
  - private immutable 32-hex row-incarnation tokens for Rom and RomFile
  - persisted migration-time entity and RomFile parent lineage
  - collision-resistant rollback validation across all supported databases
affects: [legacy-migration, catalog-rollback, storage-migration-verifier]
tech-stack:
  added: []
  patterns:
    - unconditional cryptographic identity assignment before ORM insert
    - deterministic recorded-parent and entity token validation under row locks
key-files:
  created:
    - backend/alembic/versions/0113_legacy_change_lineage.py
  modified:
    - backend/models/rom.py
    - backend/models/storage.py
    - backend/handler/database/legacy_migration_handler.py
    - backend/tests/models/test_safe_lifecycle.py
    - backend/tests/handler/database/test_storage_lifecycle.py
    - backend/tests/integration/test_legacy_migration.py
    - backend/tools/verify_storage_migrations.py
    - backend/tests/tools/test_verify_storage_migrations.py
key-decisions:
  - "Generate every Rom and RomFile incarnation token immediately before ORM insert, overriding caller input, and reject ORM instance and bulk updates."
  - "Invalidate all pre-0113 completed migration records because their historical entity and parent lineage cannot be reconstructed safely."
patterns-established:
  - "Rollback authority binds kind, ID, entity token, recorded parent ID/token, platform, and migration-produced missing state under deterministic locks."
requirements-completed: [MIG-01, MIG-02, MIG-04]
duration: 24m
completed: 2026-08-13
---

# Phase 6 Plan 21: Immutable Legacy Change Lineage Summary

**Private random catalog incarnation tokens and persisted migration-time parent lineage now reject reparented or substituted rollback targets across MariaDB, MySQL, and PostgreSQL.**

## Performance

- **Duration:** 24 minutes 11 seconds
- **Started:** 2026-08-13T19:31:06Z
- **Completed:** 2026-08-13T19:55:17Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added revision 0113 with bounded token backfill, collision retry, named unique indexes, non-null enforcement, lineage shape constraints, old-record invalidation, and guarded portable downgrade.
- Added unconditional fresh 32-hex tokens for every ORM-created Rom and RomFile, including supplied-token replacement and immutable instance and ORM bulk-update enforcement.
- Captured entity tokens plus RomFile parent ID/token while migration locks the catalog, then validated all persisted lineage under deterministic rollback locks before mutation.
- Proved same-platform reparenting and delete/reinsert substitutions fail atomically even when ID, parent, platform, missing state, created timestamp, and updated timestamp collide.
- Preserved exact successful restoration, unrelated and later rows, injected-failure retry, source neutrality, restart durability, and cleanup across all supported database dialects.

## TDD Evidence

- **RED:** The 79-test focused suite reached the new model contract and failed because lineage columns and incarnation tokens did not exist.
- **GREEN:** The complete focused suite passed 79 tests after schema, model, handler, collision, and verifier implementation.
- **REFACTOR:** No separate refactor commit was needed. Mandatory hooks formatted and checked the final implementation.

## Task Commits

1. **Task 1: Specify portable lineage and stale substitution behavior** - `8d794d3f3` (test)
2. **Task 2: Persist and enforce migration-time lineage under locks** - `648a7add6` (fix)
3. **Post-wave: Stabilize rollback expiry fixture** - `975e021e3` (test)
4. **Post-wave: Remove stale migration import** - `e65930edf` (fix)

## Files Created/Modified

- `backend/alembic/versions/0113_legacy_change_lineage.py` - Backfills unique tokens, invalidates unknowable lineage, installs named constraints, and guards downgrade.
- `backend/models/rom.py` - Defines private token columns and ORM insert/update enforcement.
- `backend/models/storage.py` - Defines bounded entity and parent lineage with an exact shape constraint.
- `backend/handler/database/legacy_migration_handler.py` - Persists migration-time lineage and validates it under ordered locks.
- `backend/tests/models/test_safe_lifecycle.py` - Locks schema shape, uniqueness, privacy, and relationship-free lineage.
- `backend/tests/handler/database/test_storage_lifecycle.py` - Covers supplied-token overwrite, token format, instance mutation, bulk mutation, and captured lineage.
- `backend/tests/integration/test_legacy_migration.py` - Covers reparenting, ROM/RomFile substitution collisions, atomic stale rejection, exact restoration, and retry.
- `backend/tools/verify_storage_migrations.py` - Proves seeded 0112 invalidation and the complete 0113 lifecycle across all dialects.
- `backend/tests/tools/test_verify_storage_migrations.py` - Locks verifier orchestration, revision identity, DDL ordering, collision evidence, and restart markers.

## Decisions Made

- Assign tokens in `before_insert` rather than constructors so every normal ORM creation path overwrites supplied identity at the final persistence boundary.
- Reject both dirty mapped attributes and ORM-enabled bulk updates to keep the token immutable through production ORM paths.
- Store RomFile parent ID and parent incarnation token without foreign keys to mutable catalog rows, preserving durable rollback evidence after deletion or substitution.
- Mark every pre-0113 completed migration failed during upgrade because even an empty prior change set cannot prove historical lineage safely.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used task-isolated root database authority for the focused suite**

- **Found during:** Task 1 RED
- **Issue:** The ordinary development database user cannot create the uniquely named `romm_test_0621` schema required by the test fixture.
- **Fix:** Supplied the existing local MariaDB root credential only to the task-owned test process, then dropped and verified the exact database after completion.
- **Files modified:** None.
- **Verification:** RED and GREEN focused runs both reached the intended test behavior; cleanup reported `CLEANUP_OK`.
- **Committed in:** Not applicable, test environment only.

**2. [Rule 1 - Verifier bug] Avoided SQLAlchemy Row attribute name collision**

- **Found during:** Task 2 authoritative MariaDB verification
- **Issue:** `rom_file.rom_id` resolved the Row helper instead of the selected `rom_id` field in the raw collision verifier.
- **Fix:** Used deterministic positional access for the selected RomFile lineage tuple.
- **Files modified:** `backend/tools/verify_storage_migrations.py`.
- **Verification:** MariaDB exact rollback and collision lifecycle passed.
- **Committed in:** `648a7add6`.

**3. [Rule 3 - Blocking] Completed the MySQL collision fixture topology**

- **Found during:** Task 2 authoritative MySQL verification
- **Issue:** The established minimal 0107 MySQL baseline omitted created and updated timestamp columns, preventing the planned exact timestamp-collision construction.
- **Fix:** Added the two normal timestamp columns to the verifier-only minimal Rom and RomFile tables.
- **Files modified:** `backend/tools/verify_storage_migrations.py`.
- **Verification:** MySQL passed exact timestamp-collision rejection and the full raw lifecycle.
- **Committed in:** `648a7add6`.

**4. [Rule 1 - Verifier fixture bug] Preserved mixed missing state in the MySQL 0113 seed**

- **Found during:** Task 2 authoritative MySQL verification
- **Issue:** The new minimal seed accidentally marked the unmatched ROM visible, contradicting the exact unrelated-row preservation assertion.
- **Fix:** Seeded the third ROM as missing, matching the MariaDB/PostgreSQL fixture and migration contract.
- **Files modified:** `backend/tools/verify_storage_migrations.py`.
- **Verification:** MySQL exact restoration and unrelated-row preservation passed.
- **Committed in:** `648a7add6`.

**5. [Rule 3 - Blocking] Stabilized the rollback expiry fixture**

- **Found during:** Cumulative Wave 2 post-merge gate
- **Issue:** The migration helper used a fixed timestamp plus a 24-hour window that expired seven minutes before the cumulative run.
- **Fix:** Seeded migration time from current UTC at database-compatible second precision while retaining the production expiry calculation and expiry assertions.
- **Files modified:** `backend/tests/integration/test_legacy_migration.py`.
- **Verification:** Both failing parameterizations passed, followed by the complete 152-test backend union.
- **Committed in:** `975e021e3`.

**6. [Rule 3 - Blocking] Removed a stale SQLAlchemy import**

- **Found during:** Cumulative Wave 2 scoped static gate
- **Issue:** `sqlalchemy.update` remained imported after the lineage handler stopped using SQL expression updates.
- **Fix:** Removed only the unused import; digest update calls remain unchanged.
- **Files modified:** `backend/handler/database/legacy_migration_handler.py`.
- **Verification:** Scoped Ruff, Black, isort, mypy, compilation, hooks, and the 152-test backend union passed.
- **Committed in:** `e65930edf`.

---

**Total deviations:** 6 auto-fixed (2 bugs, 4 blocking issues).
**Impact on plan:** All fixes were necessary to execute the exact acceptance gates and did not widen runtime authority, public contracts, or project scope.

## Issues Encountered

- Guarded downgrade checks intentionally emitted refusal tracebacks before the verifier confirmed the expected failure and continued.
- The unfiltered Trunk invocation stalled in its tool layer after formatting; the task-owned process was stopped and the scoped Ruff, Black, isort, and mypy gate passed across all modified files.
- The focused suite retained two existing warnings for disabled pytest-env configuration and Alembic path separator deprecation.

## Verification

- Focused RED: 7 existing model tests passed before the intended missing lineage-column assertion failed.
- Focused GREEN: 79 passed with 2 existing warnings.
- MariaDB 10.11: pristine and seeded upgrades, token backfill, old-row invalidation, restart, collision rejection, guarded downgrade, cleanup downgrade, re-upgrade, and 59 handler/model tests passed.
- MySQL 8.4: complete raw lifecycle passed on the minimal 0107 baseline, including timestamp-colliding replacement rejection.
- PostgreSQL 15: complete lifecycle and 59 handler/model tests passed.
- Privacy: `incarnation_token` is absent from endpoint schemas and generated frontend contracts; no logging expression exposes it.
- Schema: revision lengths are 26 and 23 characters; lineage has no direct mutable-entity foreign key; named indexes and checks remain within identifier limits.
- Static checks: scoped Ruff, Black, isort, and mypy reported no issues; `git diff --check` passed.
- Commit hooks: RED and GREEN commits passed without bypass.
- Cumulative Wave 2 gate: 152 backend tests and 11 frontend authority tests passed; frontend typecheck and production build passed.
- Cleanup: `romm_test_0621`, all verifier containers, and task-owned logs were removed and confirmed absent.
- Post-wave cleanup: uniquely named database/user/build resources were removed, and normal application `SELECT 1` passed before and after.

## Known Stubs

None.

## Threat Flags

None. Catalog identity, persisted rollback lineage, database portability, and source-neutral rollback were all explicit plan threat boundaries. No public endpoint, authentication path, generated API surface, or filesystem authority was added.

## Next Phase Readiness

Legacy rollback now binds exact migration-time catalog incarnation and parent lineage, closing the remaining Phase 6 tautological-lineage gap.

## Self-Check: PASSED

- Summary artifact exists at the required phase path.
- Task and post-wave commits `8d794d3f3`, `648a7add6`, `975e021e3`, and `e65930edf` exist.
- All nine created or modified files exist, and neither task commit deleted a tracked file.
- The stub, privacy, logging, foreign-key, cleanup, and task-owned resource scans passed.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_
