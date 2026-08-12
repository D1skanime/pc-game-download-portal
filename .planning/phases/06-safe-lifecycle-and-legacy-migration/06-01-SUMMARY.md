---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "01"
subsystem: database
tags: [sqlalchemy, alembic, mariadb, mysql, postgresql, lifecycle]

requires:
  - phase: 03-mapping-lifecycle-and-administration
    provides: versioned storage mappings with guarded lifecycle history
  - phase: 05-preview-and-read-path-cutover
    provides: mapped read paths and durable mapping preview state
provides:
  - stable retained catalog identities for detached ROM ownership
  - typed idempotent cleanup intents with bounded retry state
  - durable legacy detection, migration, rollback, and first-use records
  - cross-dialect migration round-trip and restart-persistence verification
affects: [06-02, 06-03, 06-04, 06-05, 06-06, 06-07, 06-08, cleanup, migration]

tech-stack:
  added: []
  patterns:
    - portable named Alembic constraints with guarded destructive downgrades
    - bounded durable lifecycle state without host paths or raw snapshots

key-files:
  created:
    - backend/models/catalog_lifecycle.py
    - backend/alembic/versions/0111_safe_lifecycle_legacy_migration.py
    - backend/tests/models/test_safe_lifecycle.py
  modified:
    - backend/models/assets.py
    - backend/models/play_session.py
    - backend/models/storage.py
    - backend/tools/verify_storage_migrations.py
    - backend/tests/tools/test_verify_storage_migrations.py
    - backend/alembic/versions/0110_mapping_preview_results.py

key-decisions:
  - "Save, State, and PlaySession ownership can transfer to a retained catalog identity while screenshots remain ROM-owned."
  - "Legacy detection and migration records persist only bounded logical identifiers, counters, versions, timestamps, and safe problem codes."
  - "Downgrade refuses to discard retained ownership or lifecycle history."

patterns-established:
  - "Retained ownership: detach mutable ROM rows from durable user history through a stable catalog identity."
  - "Safe downgrade: validate destructive preconditions before issuing any DDL."
  - "Migration verification: use uniquely named disposable databases and verify state again after a real container restart."

requirements-completed: [CAT-02, MIG-02, MIG-04]

duration: 31min
completed: 2026-08-12
---

# Phase 06 Plan 01: Durable Ownership and Lifecycle Schema Summary

**Retained catalog ownership, idempotent cleanup intents, and restart-safe legacy migration records verified across MariaDB, MySQL, and PostgreSQL**

## Performance

- **Duration:** 31 min
- **Started:** 2026-08-12T19:36:18Z
- **Completed:** 2026-08-12T20:07:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added stable retained catalog identities so saves, states, and play sessions survive ROM detachment while screenshots retain cascade ownership.
- Added bounded, typed cleanup intent, legacy detection, migration, rollback, and first-use durability models.
- Added guarded Alembic upgrade/downgrade behavior and verified pristine plus seeded-0110 round trips across all three supported database dialects.
- Verified lifecycle records survive an actual disposable database-container restart.

## Task Commits

Each task was committed atomically:

1. **Task 1: Specify durable lifecycle schema (RED)** - `cf85b10fd` (test)
2. **Task 2: Implement durable lifecycle schema and verifier (GREEN)** - `d6a900e37` (feat)

## Files Created/Modified

- `backend/models/catalog_lifecycle.py` - Retained catalog ownership and typed cleanup intent models.
- `backend/models/assets.py` - Nullable ROM ownership plus retained identity attribution for saves and states.
- `backend/models/play_session.py` - Optional retained identity attribution for historical sessions.
- `backend/models/storage.py` - Durable legacy detection and migration state.
- `backend/alembic/versions/0111_safe_lifecycle_legacy_migration.py` - Portable schema upgrade and guarded downgrade.
- `backend/alembic/versions/0110_mapping_preview_results.py` - Portable mapping preview table downgrade.
- `backend/tools/verify_storage_migrations.py` - Unique disposable dialect verification with seeded state and restart checks.
- `backend/tests/models/test_safe_lifecycle.py` - ORM and ownership contract tests.
- `backend/tests/tools/test_verify_storage_migrations.py` - Verifier sequencing, downgrade, and argument tests.

## Decisions Made

- Save, State, and PlaySession records may reference a stable retained identity after their active ROM is detached; Screenshot remains non-nullable and ROM-owned.
- Lifecycle tables use relative/logical paths, bounded safe errors, scalar IDs, versions, counters, and timestamps; raw snapshots and host paths are excluded.
- Unsafe downgrades fail before DDL when lifecycle state, retained ownership, or detached assets exist.
- The Alembic revision identifier is `0111_safe_lifecycle` so it fits the repository's 32-character `alembic_version.version_num` column.

## TDD Gate Compliance

- RED: `cf85b10fd` added failing ownership, migration, persistence, and downgrade contract tests before implementation.
- GREEN: `d6a900e37` implemented the schema and made all 13 focused tests pass.
- Commit order verified with `git log`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Shortened the Alembic revision identifier**

- **Found during:** Task 2 migration verification
- **Issue:** The descriptive revision identifier exceeded the existing `VARCHAR(32)` Alembic version column on MariaDB.
- **Fix:** Kept the required migration filename while using the portable internal revision `0111_safe_lifecycle`.
- **Files modified:** `backend/alembic/versions/0111_safe_lifecycle_legacy_migration.py`
- **Verification:** MariaDB, MySQL, and PostgreSQL all upgraded to head and completed round trips.
- **Committed in:** `d6a900e37`

**2. [Rule 3 - Blocking] Made the 0110 downgrade portable on MariaDB**

- **Found during:** Task 2 seeded-0110 round-trip verification
- **Issue:** MariaDB rejects explicitly dropping an index that still backs a foreign key before the table is dropped.
- **Fix:** Removed the redundant explicit index drop; dropping `mapping_previews` removes its index and constraint atomically on every supported dialect.
- **Files modified:** `backend/alembic/versions/0110_mapping_preview_results.py`
- **Verification:** The full three-dialect 0110 ? head ? 0110 ? head seeded round trip passes.
- **Committed in:** `d6a900e37`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were required for portable migration correctness; no feature scope was added.

## Issues Encountered

- The long-running development container exposes only `/app/backend`, so verification used a short-lived runner with the canonical repository mounted at `/app` and the existing Docker socket.
- The development image entrypoint exits after startup; the disposable runner therefore used an explicit `sleep` entrypoint. Two interrupted verifier database containers and their generated empty config directory were removed before the successful matrix run.
- The expected downgrade-rejection checks emit Alembic tracebacks; the verifier catches their nonzero exits and confirms the guarded behavior.

## Verification

- `pytest -c /dev/null tests/models/test_safe_lifecycle.py tests/tools/test_verify_storage_migrations.py -q`: 13 passed.
- `trunk fmt` and `trunk check` on all nine touched Python files: clean.
- Disposable MariaDB 10.11, MySQL 8.4, and PostgreSQL 15 migration matrix: passed.
- Stub scan: no TODO, FIXME, placeholder, coming-soon, or unavailable implementation stubs.
- Threat-surface scan: all schema and file-ownership surfaces are covered by the plan threat model; no additional flags.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 06-02 onward can implement transactional delete, cleanup execution, reconnect, detection, migration, rollback, and first-use logic on these durable contracts.
- No blockers remain.

## Self-Check: PASSED

- Created files exist in the canonical Linux checkout.
- RED and GREEN task commits exist in git history.
- All plan requirements and verification claims are represented above.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-12_
