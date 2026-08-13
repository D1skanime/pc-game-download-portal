---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 12
subsystem: legacy-migration-integrity
tags: [sqlalchemy, alembic, sha256, mariadb, mysql, postgresql, tdd]
dependency_graph:
  requires: [06-01, 06-04, 06-06, 06-10]
  provides:
    - content-complete bounded source fingerprints
    - exact catalog identity confirmation
    - durable ordered catalog change records
    - last-moment source reobservation before migration
  affects: [legacy-detection, legacy-migration, rollback, generated-contract]
tech_stack:
  added: []
  patterns:
    - descriptor-gated streaming SHA-256 with byte and monotonic deadlines
    - domain-separated length-delimited deterministic fingerprints
    - ordered row locks and exact pre-mutation confirmation
key_files:
  created:
    - backend/alembic/versions/0112_phase6_gap_closure.py
    - backend/tests/tasks/test_detect_legacy_storage.py
  modified:
    - backend/models/storage.py
    - backend/handler/filesystem/storage_access.py
    - backend/handler/storage/legacy_migration.py
    - backend/handler/database/legacy_migration_handler.py
    - backend/endpoints/responses/storage.py
    - backend/endpoints/storage.py
    - backend/tasks/manual/detect_legacy_storage.py
decisions:
  - Source fingerprints use sorted domain-separated length-delimited path, type, size, and regular-file content digest records.
  - Migration confirmation binds both the complete source fingerprint and exact scalar catalog fingerprint under ordered lifecycle locks.
  - Detection uses a 240-second observation budget beneath the inherited 300-second task timeout.
metrics:
  duration: 63m
  completed: 2026-08-13
---

# Phase 6 Plan 12: Fingerprint-Bound Legacy Migration Summary

Bounded descriptor hashing and exact catalog fingerprints now reject source or catalog drift before any migration-owned write, with portable revision 0112 evidence across MariaDB, MySQL, and PostgreSQL.

## Performance

- **Duration:** 63 minutes
- **Started:** 2026-08-13T07:06:43Z
- **Completed:** 2026-08-13T08:09:39Z
- **Tasks:** 3
- **Files modified:** 19

## Accomplishments

- Added portable SHA-256 persistence and ordered exact catalog-change rows without storing host paths, raw source contents, filenames, secrets, or JSON row snapshots.
- Implemented descriptor-gated HASH reads in fixed 1 MiB chunks with byte budgets, exact EOF checks, monotonic checks around every read, stable before/after descriptor metadata, and bounded typed failures.
- Built deterministic content-complete source and exact scalar catalog fingerprints, with incomplete observations always manual and unselectable.
- Bound impact confirmations to strict lowercase 64-hex source and catalog fingerprints and reobserved the canonical source under ordered lifecycle locks before mapping creation.
- Rejected same-metadata byte substitution, rename, disappearance, unreadability, symlink substitution, and equal-count catalog substitution before any mapping, audit, migration, or catalog write.
- Preserved 60 seconds for manual-result persistence and descriptor cleanup by applying a 240-second observation deadline beneath the inherited 300-second task timeout.
- Verified pristine and seeded lifecycle round trips across MariaDB, MySQL, and PostgreSQL and passed controlled OpenAPI regeneration with frontend typechecking.

## Task Commits

1. **Task 1: Specify portable fingerprint and exact-change persistence**
   - `c92e58c82` test(06-12): specify fingerprint persistence
2. **Task 2: Implement deterministic source and exact catalog fingerprints**
   - `c5005c1fe` test(06-12): specify bounded source fingerprints
   - `03ae969f2` feat(06-12): add bounded source fingerprints
3. **Task 3: Reobserve source and enforce exact confirmation before mutation**
   - `f412f61a1` test(06-12): specify fingerprint-bound migration
   - `d634a52ee` feat(06-12): bind migration to current fingerprints
4. **Verification fixes**
   - `8d7d9d4fc` fix(06-12): seed verifier fingerprint evidence
   - `d7a665053` fix(06-12): close scoped verification findings

## Files Created/Modified

- `backend/alembic/versions/0112_phase6_gap_closure.py` - Adds portable fingerprint constraints and exact migration-owned catalog change records.
- `backend/models/storage.py` - Persists bounded source fingerprints and delete-orphan exact change entities.
- `backend/handler/filesystem/storage_access.py`, `backend/exceptions/storage_exceptions.py` - Provide stable descriptor HASH results and bounded path-free failures.
- `backend/handler/storage/legacy_migration.py` - Produces deterministic complete source fingerprints within fixed entry, byte, and time budgets.
- `backend/handler/database/legacy_migration_handler.py` - Locks, fingerprints, reobserves, compares, and persists exact changes before migration writes.
- `backend/handler/filesystem/storage_composition.py`, `backend/handler/filesystem/storage_inventory.py` - Rebuild trusted root authority while registering only LIST, STAT, and HASH.
- `backend/endpoints/responses/storage.py`, `backend/endpoints/storage.py` - Enforce and serialize strict bounded fingerprint confirmations.
- `backend/tasks/manual/detect_legacy_storage.py` - Applies the 240-second detector budget under the inherited task timeout.
- Focused model, filesystem, handler, endpoint, task, inventory, and verifier tests prove the behavior and portability contracts.

## Decisions Made

- Source fingerprint records are binary-name ordered, domain-separated, and length-delimited so enumeration order cannot affect equality.
- Every regular-file record includes its content SHA-256; metadata equality alone never authorizes migration.
- Exact catalog fingerprints include ordered ROM and ROM-file scalar identities and missing-state values.
- Reobservation uses the same detector constants as initial observation and occurs after platform, root, mapping, result, ROM, and ROM-file locks are acquired.
- Exact change rows include only scalar entity kind, positive entity ID, and prior missing-state value for rows migration actually changes.
- Plan 15 retains ownership of the final generated OpenAPI artifact; this plan regenerated and typechecked it in a controlled disposable harness, then restored the generated scratch diff.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added bounded descriptor HASH exception types**

- **Found during:** Task 2 RED collection
- **Issue:** The planned HASH seam required typed short-read, budget, deadline, and concurrent-change failures, but no bounded exception contracts existed.
- **Fix:** Added path-free exception types and covered every failure and descriptor-close path.
- **Files modified:** `backend/exceptions/storage_exceptions.py`
- **Commit:** `03ae969f2`

**2. [Rule 2 - Missing critical functionality] Preserved the closed descriptor authority during reobservation**

- **Found during:** Task 3 GREEN implementation
- **Issue:** Rebuilding a root descriptor directly in the database handler would add an unregistered authority factory.
- **Fix:** Extended the existing trusted composition configuration with the locked external root ID and rebuilt authority only through the established composition provider.
- **Files modified:** `backend/handler/filesystem/storage_composition.py`, `backend/handler/database/legacy_migration_handler.py`
- **Commit:** `d634a52ee`

**3. [Rule 3 - Blocking] Completed endpoint confirmation translation**

- **Found during:** Task 3 GREEN implementation
- **Issue:** The response and request adapters had to carry both strict fingerprints for the internal dataclass comparison to be reachable.
- **Fix:** Added allowlisted source and catalog fingerprint serialization and parsing without expanding public error details.
- **Files modified:** `backend/endpoints/storage.py`
- **Commit:** `d634a52ee`

**4. [Rule 3 - Blocking] Updated the seeded lifecycle verifier fixture**

- **Found during:** Three-dialect verification
- **Issue:** The existing seeded-0111 selectable detection omitted the revision 0112 fingerprint and correctly failed the new selectable constraint.
- **Fix:** Seeded one bounded 64-hex fingerprint and added a regression assertion before rerunning all three dialects.
- **Files modified:** `backend/tools/verify_storage_migrations.py`, `backend/tests/tools/test_verify_storage_migrations.py`
- **Commit:** `8d7d9d4fc`

**5. [Rule 1 - Bug] Closed scoped type and lint findings**

- **Found during:** Scoped Trunk verification
- **Issue:** Error helpers were typed as returning, descriptor capabilities were not narrowed after closed-operation selection, and test captures lacked explicit types.
- **Fix:** Marked bounded raising helpers as non-returning, narrowed LIST and STAT capabilities, removed an unused import, and typed test capture state.
- **Files modified:** `backend/endpoints/responses/storage.py`, `backend/endpoints/storage.py`, `backend/handler/storage/legacy_migration.py`, focused tests
- **Commit:** `d7a665053`

## Test Results

- Task 1 genuine behavioral RED: 5 passed, 1 failed on missing fingerprint persistence.
- Task 2 genuine behavioral RED: collection failed on the missing typed descriptor HASH contract.
- Task 2 exact focused suite: 63 passed, 3 warnings.
- Task 3 genuine behavioral RED: 6 focused behavior failures.
- Task 3 planned suite: 100 passed, 2 warnings.
- Post-hook plan-wide focused suite: 146 passed, 2 warnings.
- Verifier unit suite: 9 passed, 2 warnings.
- Three-dialect verifier: MariaDB, MySQL, and PostgreSQL pristine/head, seeded lifecycle restart, guarded downgrade, cleanup, and re-upgrade passed.
- Controlled OpenAPI regeneration and frontend typecheck: passed under Node 24 with a 4 GB heap; task-owned runner and node volume cleaned.
- Scoped Trunk CI/no-cache check: 19 files checked, no issues.
- Commit hooks: scoped formatting and lint checks passed for every commit.
- `git diff --check`: passed.
- Disposable database `romm_test_0612`, migration containers, contract runner, node volume, generated scratch diff, and runtime directories were removed.

## Known Stubs

None.

## Threat Flags

None. All new file access, schema, and confirmation trust-boundary changes were explicitly covered by the plan threat model.

## Self-Check: PASSED

- Summary artifact exists at the required phase path.
- Task and verification commits `c92e58c82`, `c5005c1fe`, `03ae969f2`, `f412f61a1`, `d634a52ee`, `8d7d9d4fc`, and `d7a665053` exist.
- Revision 0112, task deadline tests, and all key implementation artifacts exist.
- No plan commit deleted tracked files.
