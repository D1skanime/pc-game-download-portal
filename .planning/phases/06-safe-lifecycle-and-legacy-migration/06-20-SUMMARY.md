---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 20
subsystem: legacy-migration-integrity
tags: [alembic, sqlalchemy, mariadb, mysql, postgresql, hashing, tdd]
requires:
  - phase: 06-12
    provides: durable source fingerprints and selectable result invariants
  - phase: 06-13
    provides: portable rollback guards and cross-dialect migration verification
provides:
  - portable seeded-0111 invalidation and reversible downgrade restoration
  - aggregate-aware HASH call and return budget enforcement
  - seeded-0111 coverage in every authoritative database dialect
affects: [legacy-detection, legacy-migration, storage-migration-verifier]
tech-stack:
  added: []
  patterns:
    - reserved fingerprint refresh marker for reversible pre-constraint normalization
    - minimum of per-file and aggregate remaining bytes at the HASH boundary
key-files:
  created: []
  modified:
    - backend/alembic/versions/0112_phase6_gap_closure.py
    - backend/tools/verify_storage_migrations.py
    - backend/handler/storage/legacy_migration.py
    - backend/tests/tools/test_verify_storage_migrations.py
    - backend/tests/handler/storage/test_legacy_migration.py
key-decisions:
  - "Invalidate only fingerprintless selectable 0111 rows with the reserved fingerprint_refresh_required marker before adding selectable constraints, and restore only that exact marker during downgrade."
  - "Bound each HASH call by the lesser of its per-file allowance and aggregate remaining bytes, then reject dishonest returned byte counts before recording progress."
patterns-established:
  - "Seeded predecessor verification: exercise a representative 0111 data state through upgrade, guarded downgrade, restoration, and re-upgrade in every supported dialect."
requirements-completed: [MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
duration: 19m
completed: 2026-08-13
---

# Phase 6 Plan 20: Seeded-0111 and Hash Budget Closure Summary

**Portable seeded-0111 lifecycle repair and strict remaining-byte HASH caps now close the migration and aggregate budget gaps across MariaDB, MySQL, and PostgreSQL.**

## Performance

- **Duration:** 19 minutes 18 seconds
- **Started:** 2026-08-13T16:58:26Z
- **Completed:** 2026-08-13T17:17:44Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added a portable 0112 normalization step that invalidates fingerprintless selectable 0111 rows before constraints are installed, using a reserved marker that downgrade restores only when no durable fingerprint evidence exists.
- Extended the authoritative verifier to seed selectable and representative unselectable 0111 rows, prove exact upgrade invalidation, prove exact downgrade restoration, and prove re-upgrade invalidation.
- Replaced fixed per-file HASH allowances with the lesser of per-file allowance and aggregate remaining bytes.
- Rejected descriptor budget failures and dishonest HASH return counts against the limiting budget before counters, records, or fingerprints can advance.
- Passed the complete migration lifecycle in MariaDB 10.11, MySQL 8.4, and PostgreSQL 15.

## TDD Evidence

- **RED:** The detector suite passed 25 tests and then failed because HASH received caps `[10, 10]` instead of the required remaining aggregate caps `[5, 2]`.
- **RED:** The seeded-0111 migration verifier failed while adding the selectable fingerprint constraint to an existing fingerprintless selectable row.
- **GREEN:** The focused suite passed all 43 tests after portable row normalization, reversible downgrade ordering, and remaining-budget HASH enforcement.
- **REFACTOR:** No separate refactor commit was needed.

## Task Commits

1. **Task 1 RED: Expose seeded-0111 and HASH budget gaps** - `e132f8aef` (test)
2. **Task 2 GREEN: Bound legacy upgrades and hashing** - `172209091` (fix)

## Files Created/Modified

- `backend/alembic/versions/0112_phase6_gap_closure.py` - Invalidates seeded 0111 rows before constraints and restores the exact reserved marker during downgrade.
- `backend/tools/verify_storage_migrations.py` - Seeds, verifies, downgrades, restores, and re-upgrades representative 0111 results.
- `backend/handler/storage/legacy_migration.py` - Applies aggregate remaining-byte caps at the HASH call and return boundaries.
- `backend/tests/tools/test_verify_storage_migrations.py` - Covers seeded-0111 orchestration and portable downgrade ordering.
- `backend/tests/handler/storage/test_legacy_migration.py` - Covers STAT-to-HASH replacement, remaining caps, aggregate failure, and dishonest HASH results.

## Decisions Made

- Reserve `fingerprint_refresh_required` for upgrade-invalidated rows so downgrade can distinguish reversible 0111 normalization from later manual-mapping states.
- Drop the selectable constraint before restoring the reserved marker, then remove the new column only after restoration, which preserves valid ordering in every supported dialect.
- Treat aggregate remaining bytes as authoritative whenever it is the limiting HASH allowance, including descriptor budget errors and returned byte overages.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Supplied isolated test authentication configuration**

- **Found during:** Task 1 RED
- **Issue:** The exact focused command disabled pytest-env, leaving the application without its required test auth secret.
- **Fix:** Supplied the repository's test-only auth value to the isolated test container.
- **Files modified:** None.
- **Verification:** The focused suite collected normally and reached the intended RED assertion.
- **Committed in:** Not applicable, environment-only test preparation.

**2. [Rule 3 - Blocking] Ran the verifier from the verified Linux host**

- **Found during:** Task 1 RED
- **Issue:** The planned `docker exec` form launched the verifier inside `romm-dev`, but that runner does not contain a Docker CLI and failed with `FileNotFoundError: docker`.
- **Fix:** Ran the same standard-library verifier from `/home/d1sk/romm/backend` on the verified Linux host while retaining `romm-dev` as its configured Alembic runner.
- **Files modified:** None.
- **Verification:** The final three-dialect verifier exited zero and exercised every planned lifecycle gate.
- **Committed in:** Not applicable, environment-only verifier invocation.

**3. [Rule 3 - Blocking] Replaced an expired fixed preview timestamp**

- **Found during:** Task 2 GREEN
- **Issue:** An existing fixed test preview timestamp had expired by the execution date and blocked the focused endpoint test before the planned assertions.
- **Fix:** Seeded the preview at current UTC second precision, matching MariaDB timestamp precision.
- **Files modified:** `backend/tests/handler/storage/test_legacy_migration.py`.
- **Verification:** The full focused suite passed 43 tests.
- **Committed in:** `172209091`.

**4. [Rule 1 - Bug] Reordered downgrade restoration around the selectable constraint**

- **Found during:** Task 2 authoritative migration verification
- **Issue:** Restoring `selectable = TRUE` while the new fingerprint constraint still existed failed on MariaDB.
- **Fix:** Split downgrade operations so the selectable constraint is dropped before exact-marker restoration, then added a regression test for the required ordering.
- **Files modified:** `backend/alembic/versions/0112_phase6_gap_closure.py`, `backend/tests/tools/test_verify_storage_migrations.py`.
- **Verification:** MariaDB, MySQL, and PostgreSQL all passed seeded-0111 upgrade, downgrade restoration, and re-upgrade.
- **Committed in:** `172209091`.

**5. [Rule 3 - Blocking] Completed metadata commit with the verified host identity**

- **Found during:** Plan closeout
- **Issue:** The disposable Node GSD handler updated and staged the exact tracking set but could not commit because its container had no Git author identity.
- **Fix:** Committed the exact staged summary, STATE, ROADMAP, and REQUIREMENTS files from the verified Linux checkout with mandatory hooks.
- **Files modified:** None beyond the planned summary and tracking files.
- **Verification:** The metadata commit contains exactly four planned files, hooks passed, and no tracked file was deleted.
- **Committed in:** Final metadata commit.

---

**Total deviations:** 5 auto-fixed (1 bug, 4 blocking issues).
**Impact on plan:** The fixes restored isolated execution and portable lifecycle correctness without changing project services, acceptance criteria, or authority boundaries.

## Issues Encountered

- The authoritative guarded-downgrade checks intentionally emitted refusal tracebacks before the verifier confirmed the expected failure and continued.
- Two existing warnings remained in the focused suite: disabled pytest-env configuration and Alembic path-separator deprecation.

## Verification

- Focused RED: 25 tests passed before the expected HASH cap failure; seeded-0111 upgrade also failed on the missing fingerprint normalization.
- Focused GREEN: 43 passed with 2 existing warnings.
- MariaDB 10.11: pristine upgrade, seeded-0110, seeded-0111 invalidation and restoration, restart, guarded downgrade, cleanup downgrade, and re-upgrade passed; 54 handler tests passed.
- MySQL 8.4: full migration lifecycle including seeded-0111 invalidation and restoration passed; handler tests were intentionally skipped on the established minimal 0107 baseline.
- PostgreSQL 15: full migration lifecycle including seeded-0111 invalidation and restoration passed; 54 handler tests passed.
- Commit hooks: passed for all five modified files across both task commits.
- Cleanup: `romm_test_0620` was dropped and confirmed absent; no `romm-storage-migration-*` container remained.
- TDD commit sequence: `e132f8aef` precedes `172209091`.
- Migration identity: revision identifier length is 23 characters and remains within Alembic's portable identifier budget.

## Known Stubs

None.

## Threat Flags

None. The schema normalization and descriptor HASH boundaries were explicitly covered by the plan threat model; no new network endpoint, authentication path, file access authority, or external trust boundary was added.

## Next Phase Readiness

The seeded predecessor lifecycle and final aggregate HASH budget gaps are closed across all supported database dialects, ready for the remaining Phase 6 gap-closure plans.

## Self-Check: PASSED

- Summary artifact exists at the required phase path.
- Task commits `e132f8aef` and `172209091` exist.
- All five declared modified files exist.
- No task commit deleted tracked files.
- Stub scan found no TODO, FIXME, placeholder, coming-soon, or unavailable markers.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_
