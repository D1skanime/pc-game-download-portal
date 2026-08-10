---
phase: 03-mapping-administration-contracts
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, mariadb, mysql, postgresql, audit]
requires:
  - phase: 01-immutable-storage-foundation
    provides: Immutable storage roots and relative platform mappings
  - phase: 02-runtime-immutability-enforcement
    provides: Runtime external storage authority boundary
provides:
  - Versioned active and inactive platform mapping storage
  - Immutable scalar mapping audit snapshots
  - Fail-closed portable 0109 downgrade preflight
  - Bounded typed lifecycle, cursor, conflict, and filesystem errors
affects: [03-02, 03-03, 03-04, 03-05, 03-06, phase-5]
tech-stack:
  added: []
  patterns:
    [
      portable supporting indexes,
      scalar audit snapshots,
      pre-DDL downgrade guards,
    ]
key-files:
  created:
    - backend/alembic/versions/0109_mapping_administration_contracts.py
    - backend/tests/tools/test_verify_storage_migrations.py
  modified:
    - backend/models/storage.py
    - backend/exceptions/storage_exceptions.py
    - backend/tools/verify_storage_migrations.py
    - backend/handler/database/storage_handler.py
    - backend/tests/models/test_storage.py
key-decisions:
  - "Lifecycle uniqueness is enforced against active rows by handlers, with portable non-unique supporting indexes in the schema."
  - "0109 downgrade fails before DDL whenever audit, inactive, versioned, or duplicate lifecycle history cannot be represented by 0108."
patterns-established:
  - "Audit snapshots store bounded scalar identities and relative values without actor or mapping relationships."
  - "Migration verification proves both pristine round trips and intact fail-closed lifecycle history on every supported dialect."
requirements-completed: [MAP-02, AUD-01, AUD-02]
duration: 25min
completed: 2026-08-10
---

# Phase 3 Plan 1: Mapping Lifecycle and Audit Schema Summary

**Portable active/version mapping rows, immutable path-safe audit snapshots, and fail-closed downgrade guards across MariaDB, MySQL, and PostgreSQL**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-10T21:09:00Z
- **Completed:** 2026-08-10T21:34:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added active/version lifecycle fields and removed unconditional mapping uniqueness while retaining portable lookup indexes.
- Added append-only audit storage with immutable actor, mapping, action, and before/after scalar snapshots without host paths or destructive relationships.
- Proved pristine 0109 downgrade/re-upgrade and pre-DDL rejection of real lifecycle history on MariaDB, MySQL, and PostgreSQL.
- Added stable bounded domain errors and an explicit positive handler-test repetition option.

## Task Commits

1. **Task 1: RED model and migration lifecycle contract** - `e9eb67573` (test)
2. **Task 2: GREEN portable 0109 models and bounded exceptions** - `03548d1e2` (feat)

## Files Created/Modified

- `backend/alembic/versions/0109_mapping_administration_contracts.py` - Portable lifecycle and audit migration with guarded downgrade.
- `backend/models/storage.py` - Versioned mapping and scalar audit ORM contracts.
- `backend/exceptions/storage_exceptions.py` - Path-safe typed lifecycle and browsing failures.
- `backend/tools/verify_storage_migrations.py` - Three-dialect pristine and lifecycle-history verification.
- `backend/tests/tools/test_verify_storage_migrations.py` - Verifier CLI and lifecycle-path tests.
- `backend/tests/models/test_storage.py` - Mapping lifecycle and audit allowlist tests.
- `backend/handler/database/storage_handler.py` - Active-only conflict checks after unconditional constraints were removed.

## Decisions Made

- Supporting indexes are portable and non-unique. Active-only conflict serialization remains a handler responsibility.
- Audit attribution uses immutable scalar snapshots without foreign-key relationships, so later user or mapping lifecycle changes cannot erase history.
- Downgrade rejects any state that 0108 cannot represent before issuing destructive DDL.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added a dedicated platform foreign-key index before removing the MariaDB unique index**

- **Found during:** Task 2 migration verification
- **Issue:** MariaDB used the old unique index to support the platform foreign key and refused to drop it.
- **Fix:** Added a portable platform lookup index before constraint removal and removed it only after restoring 0108 uniqueness on downgrade.
- **Files modified:** `backend/models/storage.py`, `backend/alembic/versions/0109_mapping_administration_contracts.py`
- **Verification:** All three migration dialects passed.
- **Committed in:** `03548d1e2`

**2. [Rule 1 - Bug] Preserved active-only duplicate enforcement after removing database uniqueness**

- **Found during:** Task 2 regression verification
- **Issue:** The existing save handler accepted a second active mapping after unconditional uniqueness was removed.
- **Fix:** Added an active-only locked platform lookup after canonical root locking and filtered overlap checks to active rows.
- **Files modified:** `backend/handler/database/storage_handler.py`
- **Verification:** Model, verifier, and existing storage handler suites pass, including concurrent overlap coverage.
- **Committed in:** `03548d1e2`

**Total deviations:** 2 auto-fixed (1 blocking portability issue, 1 correctness bug)
**Impact on plan:** Both fixes preserve required Phase 3 behavior without expanding the public API or scanner scope.

## Issues Encountered

- The plan's container pytest command inherits a loopback test database host from `pytest.ini`. Verification used the existing isolated `romm_test_phase03_01` database through `romm-db-dev` with explicit test-only environment values and `-c /dev/null`.
- Expected downgrade rejection tracebacks are printed by Alembic, while the verifier confirms the nonzero exit and completes successfully.

## User Setup Required

None. No external service configuration is required.

## Known Stubs

None.

## Next Phase Readiness

- Plans 03-02 through 03-06 can rely on explicit active/version fields, immutable audit snapshots, and bounded typed failures.
- Transactional mutation and audit append behavior remains intentionally assigned to Plan 03-03.

## Self-Check: PASSED

- All created files exist.
- RED and GREEN commits exist on `codex/pc-module-analysis`.
- Focused tests and three-dialect migration verification pass.

---

_Phase: 03-mapping-administration-contracts_
_Completed: 2026-08-10_
