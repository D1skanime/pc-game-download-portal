---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 28
subsystem: database
tags: [sqlalchemy, orm, lineage, mariadb, mysql, postgresql, tdd]

requires:
  - phase: 06-safe-lifecycle-and-legacy-migration
    provides: Immutable insert tokens, instance-update rejection, and durable 0113 rollback lineage
provides:
  - Execution-boundary incarnation-token immutability for every supported ORM update form
  - Rollback-safe Rom and RomFile mutation regressions with an ordinary-update positive control
  - Real MariaDB, MySQL, and PostgreSQL guard and restart-equality evidence
affects: [phase-06-verification, legacy-rollback, catalog-lifecycle]

tech-stack:
  added: []
  patterns:
    - Documented SQLAlchemy Engine before_execute guard over statement values and parameter mappings
    - Exact mapped-table identity check that excludes Alembic ad-hoc migration tables
    - Dialect-local ORM probe before restart with token equality after restart

key-files:
  created: []
  modified:
    - backend/models/rom.py
    - backend/tests/handler/database/test_storage_lifecycle.py
    - backend/tools/verify_storage_migrations.py
    - backend/tests/tools/test_verify_storage_migrations.py

key-decisions:
  - "Enforce incarnation-token immutability at the documented Engine before_execute boundary so every supported ORM bulk path is covered before SQL."
  - "Recognize only the exact Rom and RomFile mapped tables, preserving Alembic migration updates that use independent table metadata."
  - "Run the same narrow ORM mutation matrix on every full head schema and compare seeded tokens again after database restart."

patterns-established:
  - "Execution-boundary invariants inspect compiled statement values plus single and executemany parameter mappings."
  - "Verifier failures distinguish the stable product ValueError from framework TypeError or infrastructure failure."

requirements-completed: [MIG-02, MIG-04]

duration: 30min
completed: 2026-08-20
---

# Phase 6 Plan 28: ORM Incarnation Immutability Summary

**Rom and RomFile rollback identity is now immutable across all installed SQLAlchemy ORM update forms, with identical behavior and restart persistence proven on MariaDB, MySQL, and PostgreSQL.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-08-20T11:20:33Z
- **Completed:** 2026-08-20T11:50:11Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Closed instance flush, statement values, Query.update, ORM executemany, bulk_update_mappings, and bulk_save_objects token mutation routes before SQL.
- Preserved fresh insert tokens, instance history checks, ordinary non-token bulk updates, and migration-owned ad-hoc SQL.
- Added rollback-and-reopen tests for both Rom and RomFile, including the exact bulk_update_mappings regression that proved the former bypass.
- Extended the real dialect verifier with the same ORM matrix before restart and byte-identical token checks after restart.

## Task Commits

Each task was committed atomically with mandatory hooks:

1. **Task 1 RED: Specify every supported ORM token mutation form** - 1f28a06e7 (test)
2. **Task 2 GREEN: Enforce immutable tokens at SQLAlchemy execution boundary** - 49e655ac4 (fix)

## Files Created/Modified

- backend/models/rom.py - Registers the immutable-token check at Engine.before_execute and inspects statement and parameter mappings only for exact catalog tables.
- backend/tests/handler/database/test_storage_lifecycle.py - Exercises six mutation forms for Rom and RomFile, rollback recovery, unchanged persistence, and allowed ordinary updates.
- backend/tools/verify_storage_migrations.py - Runs an exact-checkout ORM probe before restart and verifies token equality afterward for all three dialects.
- backend/tests/tools/test_verify_storage_migrations.py - Locks verifier ordering, safe markers, supported forms, and fail-closed behavior.

## Verification Evidence

- Exact RED gate: pytest exited 1 on test_catalog_incarnation_tokens_reject_bulk_update_mappings because the persisted token changed; the already-guarded instance and statement-value paths remained green.
- Focused GREEN selection: 14 passed, 34 deselected.
- Complete affected files: 48 passed.
- Verifier unit file: 17 passed.
- Real dialect verifier exited 0.
- MariaDB: ORM guard passed before restart, token equality survived restart, and 59 handler/migration checks passed.
- MySQL: ORM guard passed before restart and token equality survived restart on the intentional minimal 0107 baseline.
- PostgreSQL: ORM guard passed before restart, token equality survived restart, and 59 handler/migration checks passed.
- Scoped Trunk format and check on all four changed files: no issues.
- Python AST compilation and git diff --check passed.
- Normal application database SELECT 1 passed before cleanup.
- No token value is printed by the verifier; only bounded dialect and success markers are emitted.

## TDD Gate Compliance

- RED commit 1f28a06e7 preceded production changes and captured a genuine behavioral bypass.
- GREEN commit 49e655ac4 followed RED and made the complete matrix pass.
- No refactor commit was needed.

## Decisions Made

- Use the documented Engine.before_execute event because ORM mapper and Session events do not observe every installed bulk mutation form.
- Require exact mapped-table identity before rejecting incarnation_token parameters so migration-local table definitions retain their intended behavior.
- Load only required catalog columns with wildcard lazy loading in the narrow verifier so the intentional minimal MySQL baseline does not require unrelated eager-join tables.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provisioned the isolated test database grant**

- **Found during:** Task 1 RED
- **Issue:** The application database user could not create the exact romm_test_0628 schema required by the pytest harness.
- **Fix:** Created and granted only the task-owned database and user through the existing MariaDB container, then dropped both after verification.
- **Files modified:** None
- **Verification:** Final database and user counts were both 0.
- **Committed in:** Not applicable

**2. [Rule 3 - Blocking] Launched the verifier from the Linux host**

- **Found during:** Task 2 all-dialect verification
- **Issue:** romm-dev contains the exact checkout and Python environment but no Docker CLI, while the verifier must create disposable database containers.
- **Fix:** Ran the same checked-in Python verifier from the canonical Linux host while retaining romm-dev as its bind-mounted ORM runner.
- **Files modified:** None
- **Verification:** The verifier completed all three dialects with exit 0 against /home/d1sk/romm.
- **Committed in:** Not applicable

**3. [Rule 3 - Blocking] Made the narrow ORM probe self-contained across dialect schemas**

- **Found during:** Task 2 all-dialect verification
- **Issue:** A direct Rom import left string-named ORM relationships unregistered, and the minimal MySQL baseline lacks unrelated eager-join tables.
- **Fix:** Registered the complete application mapper set and disabled relationship eager loading for the two narrow entity reads.
- **Files modified:** backend/tools/verify_storage_migrations.py
- **Verification:** MariaDB, MySQL, and PostgreSQL all completed the ORM guard and restart probe.
- **Committed in:** 49e655ac4

---

**Total deviations:** 3 auto-fixed blocking issues.
**Impact on plan:** The fixes made the planned isolated verification deterministic without changing schema, API, service state, or product scope.

## Issues Encountered

- The verifier intentionally emits tracebacks for guarded 0109 and 0113 downgrade attempts; its final exit 0 and success markers confirm those negative checks behaved as designed.
- Pytest reported inherited unknown env-option and Alembic path-separator warnings; both were non-failing and outside this plan's scope.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. The change strengthens an existing database execution boundary and introduces no route, authentication path, schema, network client, file access path, or public token surface.

## Cleanup

- Dropped the exact romm_test_0628 database and romm_0628 user; both final counts are 0.
- Confirmed zero romm-storage-migration containers, volumes, or host temporary paths.
- Preserved all 28 baseline untracked paths.
- Performed no deployment, service restart, branch change, or unrelated edit.

## Self-Check: PASSED

- All four task files and this summary exist in the canonical Linux checkout.
- RED commit 1f28a06e7 and GREEN commit 49e655ac4 exist on codex/pc-module-analysis.
- The plan introduced no tracked-file deletion.
- The stub scan found only intentional local type initialization and embedded program strings.
- The tracked tree was clean before summary creation.
- All 28 baseline untracked paths remain preserved.
