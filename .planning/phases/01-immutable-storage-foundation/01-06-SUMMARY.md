---
phase: 01-immutable-storage-foundation
plan: 06
subsystem: database
tags: [sqlalchemy, postgresql, mariadb, row-locking, integrity-errors]
requires:
  - phase: 01-immutable-storage-foundation
    provides: Immutable storage schema and deterministic mapping persistence
provides:
  - PostgreSQL-valid entity-qualified mapping locks with separate root loading
  - Named-only duplicate mapping classification and bounded identity failures
  - Order-independent model fixtures and isolated handler behavior verification
affects: [phase-02-storage-policy, mapping-administration, storage-persistence]
tech-stack:
  added: []
  patterns:
    [
      selectin relationship loading,
      entity-qualified FOR UPDATE,
      named constraint classification,
    ]
key-files:
  created: []
  modified:
    - backend/handler/database/storage_handler.py
    - backend/exceptions/storage_exceptions.py
    - backend/tests/handler/database/test_storage_handler.py
    - backend/tests/models/test_storage.py
    - backend/tools/verify_storage_migrations.py
key-decisions:
  - "Lock mapping rows without an outer join and load their storage roots separately."
  - "Translate only the two explicit mapping unique constraints into duplicate-domain errors."
requirements-completed: [ROOT-01, ROOT-04, TEST-01]
duration: 10min
completed: 2026-08-05
---

# Phase 1 Plan 6: PostgreSQL-safe Persistence Gap Closure Summary

**Portable mapping persistence with entity-qualified locks, deterministic two-session serialization, and bounded constraint-specific errors**

## Performance

- **Duration:** 10 min
- **Completed:** 2026-08-05
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Replaced the PostgreSQL-invalid outer-joined locking query with `selectinload` and `FOR UPDATE OF platform_storage_mappings` while preserving ascending active-root locks and the current-read recheck.
- Added same-transaction platform validation and bounded missing-platform and unrelated-persistence errors.
- Restricted duplicate translation to `uq_platform_storage_mappings_platform_id` and `uq_platform_storage_mappings_root_relative_path` across structured PostgreSQL and named vendor diagnostics.
- Removed model-fixture table drops and proved model tests can run before handler behavior tests on isolated MariaDB and PostgreSQL databases.
- Extended the ephemeral verifier with handler behavior execution, dynamic ports, unique containers, and unconditional cleanup. MySQL retains its established minimal 0107 migration-only baseline.

## Task Commits

1. **Task 1: Specify PostgreSQL locking and bounded failures** - `1cea72b13` (test)
2. **Task 2: Implement portable locks and precise classification** - `cccb4aabf` (fix)

## Verification Evidence

- Isolated MariaDB: 22 model-first and handler tests passed, including coordinated two-session serialization.
- Isolated PostgreSQL: 22 model-first and handler tests passed, including entity-qualified lock SQL and coordinated two-session serialization.
- MariaDB 10.11, MySQL 8.4, and PostgreSQL 15 each passed upgrade, downgrade to 0107, and re-upgrade.
- Scoped Trunk format and check passed for all five plan-owned files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bypassed pytest.ini database overrides in ephemeral handler verification**

- **Found during:** Task 2 PostgreSQL verification
- **Issue:** Repository pytest configuration forced loopback MariaDB values over the verifier's isolated database environment.
- **Fix:** Handler verification uses an empty pytest config while supplying the complete isolated database environment explicitly.
- **Files modified:** `backend/tools/verify_storage_migrations.py`
- **Commit:** `cccb4aabf`

**2. [Rule 3 - Blocking] Preserved MySQL's minimal 0107 verification boundary**

- **Found during:** Task 2 all-dialect verification
- **Issue:** The established MySQL baseline intentionally contains only the 0107 platform boundary, so the full application cleanup fixture cannot run there.
- **Fix:** Kept MySQL as an independent migration-cycle authority and ran behavior/concurrency evidence on full-schema MariaDB and PostgreSQL containers.
- **Files modified:** `backend/tools/verify_storage_migrations.py`
- **Commit:** `cccb4aabf`

## Known Stubs

None.

## Threat Flags

None. No endpoint, filesystem consumer, schema, NAS, or service surface was added.

## Self-Check: PASSED

- All five modified files exist.
- Task commits `1cea72b13` and `cccb4aabf` exist.
- Isolated behavior, concurrency, migration, and scoped static gates pass.

---

_Phase: 01-immutable-storage-foundation_
_Completed: 2026-08-05_
