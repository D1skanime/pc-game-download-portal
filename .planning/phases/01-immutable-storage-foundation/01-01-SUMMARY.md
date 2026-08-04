---
phase: 01-immutable-storage-foundation
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, mariadb, mysql, postgresql, immutable-storage]
requires: []
provides:
  - Immutable external storage root identity and health observation schema
  - One relative platform mapping per platform with restrictive root deletion
  - Reversible 0108 migration verified across three supported database servers
affects: [01-02, 01-03, 01-04, 01-05, storage-policy, platform-mapping]
tech-stack:
  added: []
  patterns: [named portable constraints, explicit back_populates, isolated migration cycles]
key-files:
  created:
    - backend/models/storage.py
    - backend/alembic/versions/0108_immutable_storage_foundation.py
    - backend/tools/verify_storage_migrations.py
    - backend/tests/models/test_storage.py
  modified:
    - backend/models/platform.py
    - backend/alembic/env.py
    - backend/tests/conftest.py
key-decisions:
  - "Bound indexed storage paths to 700 characters so utf8mb4 uniqueness is portable to MySQL 8.4."
  - "Exercise 0108 on MySQL from a clean 0107-compatible baseline because the pre-0108 history contains unrelated MySQL-incompatible DDL."
patterns-established:
  - "External storage mode is a checked string constrained to external_read_only."
  - "Platform mappings persist only root identity, platform identity, and normalized relative path."
requirements-completed: [ROOT-02, ROOT-04]
duration: 17min
completed: 2026-08-04
---

# Phase 1 Plan 1: Immutable Storage Models and Migration Summary

**Immutable external roots and relative platform mappings with reversible 0108 schema coverage on MariaDB 10.11, MySQL 8.4, and PostgreSQL 15**

## Performance

- **Duration:** 17 min
- **Started:** 2026-08-04T20:27:51Z
- **Completed:** 2026-08-04T20:44:11Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added typed `StorageRoot` and `PlatformStorageMapping` models with immutable mode, bounded health state, named uniqueness checks, and restrictive deletion.
- Preserved `Platform.fs_slug` while adding an explicit scalar mapping relationship with `back_populates`.
- Added a filesystem-free 0108 migration and an isolated Docker verifier covering upgrade, downgrade to 0107, and re-upgrade on all three database targets.
- Added database tests for mode rejection, uniqueness, mapping shape, scalar relationships, and restrictive root deletion.

## Task Commits

1. **Task 1 RED: Storage ORM contract tests** - `6934d2134` (test)
2. **Task 1 GREEN: Storage ORM contracts** - `7de987fab` (feat)
3. **Task 2: Portable revision 0108 and verifier** - `8b03cbabf` (feat)

## Files Created/Modified

- `backend/models/storage.py` - Immutable root and relative platform mapping ORM contracts.
- `backend/models/platform.py` - Scalar inverse mapping relationship without changing `fs_slug`.
- `backend/alembic/env.py` - Storage model imports for Alembic metadata.
- `backend/alembic/versions/0108_immutable_storage_foundation.py` - Portable roots-first schema and reverse-order downgrade.
- `backend/tools/verify_storage_migrations.py` - Cleanup-safe isolated three-dialect migration cycles.
- `backend/tests/models/test_storage.py` - ORM and database constraint coverage.
- `backend/tests/conftest.py` - Dependency-safe cleanup for mappings and roots.

## Decisions Made

- Storage root and mapping paths use a 700-character bound so utf8mb4 unique keys fit MySQL's 3072-byte index limit.
- The MySQL verifier starts from a minimal stamped 0107 baseline and exercises 0108 through `mysql+mysqlconnector`; MariaDB and PostgreSQL exercise the full migration history.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added storage cleanup ordering to the shared test fixture**
- **Found during:** Task 1
- **Issue:** Existing platform cleanup would violate new mapping foreign keys between tests.
- **Fix:** Delete mappings before platforms and roots after mappings.
- **Files modified:** `backend/tests/conftest.py`
- **Verification:** Eight storage model tests pass repeatedly.
- **Committed in:** `7de987fab`

**2. [Rule 1 - Bug] Shortened the internal Alembic revision identifier**
- **Found during:** Task 2 MariaDB cycle
- **Issue:** `0108_immutable_storage_foundation` exceeded Alembic's 32-character version column.
- **Fix:** Kept the required migration filename and used `0108_storage_foundation` as the revision identifier.
- **Files modified:** `backend/alembic/versions/0108_immutable_storage_foundation.py`
- **Verification:** All dialect cycles update the Alembic version successfully.
- **Committed in:** `8b03cbabf`

**3. [Rule 1 - Bug] Bounded indexed paths for MySQL portability**
- **Found during:** Task 2 MySQL cycle
- **Issue:** A 1000-character utf8mb4 unique path exceeded MySQL's maximum index key length.
- **Fix:** Set root and mapping indexed path bounds to 700 characters in ORM and migration definitions.
- **Files modified:** `backend/models/storage.py`, `backend/alembic/versions/0108_immutable_storage_foundation.py`
- **Verification:** MySQL 8.4 upgrade, downgrade, and re-upgrade pass.
- **Committed in:** `8b03cbabf`

**4. [Rule 3 - Blocking] Isolated 0108 from incompatible historical MySQL DDL**
- **Found during:** Task 2 MySQL cycle
- **Issue:** Pre-0108 migrations use `IF EXISTS` and `IF NOT EXISTS` forms unsupported by MySQL 8.4, preventing the verifier from reaching this plan's migration.
- **Fix:** Build a clean 0107-compatible MySQL baseline containing Alembic identity and the referenced platform key, then exercise 0108 through the project's MySQL driver.
- **Files modified:** `backend/tools/verify_storage_migrations.py`
- **Verification:** The MySQL 8.4 0108 cycle passes independently; MariaDB and PostgreSQL full-history cycles also pass.
- **Committed in:** `8b03cbabf`

---

**Total deviations:** 4 auto-fixed (2 blocking, 2 bugs)
**Impact on plan:** All fixes were required for deterministic tests or promised cross-dialect portability. No source-library filesystem access or consumer scope was added.

## Issues Encountered

- Historical MySQL migration syntax remains outside this plan's scope. The verifier records the boundary by testing 0108 from a clean 0107-compatible baseline.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Next Phase Readiness

- Plans 01-02 through 01-05 can build normalization, safe resolution, and persistence handlers on stable root and mapping identities.
- Descriptor-relative no-follow consumer opens remain intentionally deferred to Phase 2.

## Self-Check: PASSED

- All seven created or modified implementation/test files exist.
- Commits `6934d2134`, `7de987fab`, and `8b03cbabf` exist in repository history.
- Three database migration cycles, eight storage tests, and targeted Ruff checks pass.

---
*Phase: 01-immutable-storage-foundation*
*Completed: 2026-08-04*
