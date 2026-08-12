---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "06"
subsystem: legacy-migration-transaction
tags: [fastapi, sqlalchemy, mariadb, atomic-migration, openapi, tdd]
requires:
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "03"
    provides: ordered mapping lifecycle locks, audit semantics, and optimistic versions
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "05"
    provides: version-bound migration impact confirmation and bounded catalog counts
provides:
  - atomic per-platform mapping, catalog reconnection, audit, and rollback metadata
  - failure rollback and safe retry after every flushed migration stage
  - deterministic migration and lifecycle race serialization
  - bounded administrator-only migration result contract
affects: [06-07, 06-08, phase-07, legacy-migration, storage-lifecycle, openapi]
tech-stack:
  added: []
  patterns:
    - one platform migration per database transaction with ordered locks
    - unique normalized logical identity reconnection with ambiguous catalog retention
    - flush-stage failure injection proving transaction rollback
key-files:
  created:
    - frontend/src/__generated__/models/LegacyMigrationResultSchema.ts
    - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Output.ts
  modified:
    - backend/handler/database/legacy_migration_handler.py
    - backend/handler/database/storage_handler.py
    - backend/handler/database/roms_handler.py
    - backend/endpoints/responses/storage.py
    - backend/endpoints/storage.py
    - backend/tests/handler/database/test_storage_lifecycle.py
    - backend/tests/handler/storage/test_legacy_migration.py
    - frontend/src/__generated__/index.ts
    - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Input.ts
    - frontend/src/__generated__/models/LegacyImpactPreviewSchema.ts
key-decisions:
  - "Migration revalidates the complete confirmation and performs mapping, catalog, audit, detection-version, and rollback-metadata writes in one transaction."
  - "Only unique normalized logical catalog identities reconnect; invalid and ambiguous entries remain visible and unreachable."
  - "The migration endpoint returns IDs, versions, counts, and authority booleans only, never source paths or raw rows."
patterns-established:
  - "Atomic migration seam: inject failures after each flush while relying on the transaction wrapper for complete rollback."
  - "Lifecycle serialization: migration and ordinary mapping creation acquire the platform lock before mapping mutation."
requirements-completed: [CAT-03, MIG-01, MIG-03, MIG-04]
duration: 27min
completed: 2026-08-12
---

# Phase 06 Plan 06: Atomic Per-Platform Migration Summary

**Per-platform migration now commits mapping authority, safe catalog reconnection, audit history, and rollback metadata as one deterministic transaction without touching legacy source files**

## Performance

- **Duration:** 27 min
- **Started:** 2026-08-12T22:37:30Z
- **Completed:** 2026-08-12T23:04:28Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- Added an atomic migration transaction that revalidates the expiring confirmation, locks platform/root/mapping/migration/catalog state, and commits all RomM-owned effects together.
- Reconnected only unique normalized catalog identities while retaining invalid and ambiguous rows as visible and unreachable.
- Proved rollback after mapping, catalog, audit, and rollback-metadata flushes, safe retry, and independent earlier platform commits.
- Serialized migration/migration and migration/create races without duplicate mappings, audits, or migration records.
- Added an administrator-only bounded migration endpoint and regenerated its typed OpenAPI contract without Phase 7 UI or fallback authority.

## Task Commits

1. **Task 1: Specify atomic per-platform migration (RED)** - 1673b4866 (test)
2. **Task 2: Implement atomic per-platform migration (GREEN)** - 4aac5af92 (feat)

## Files Created/Modified

- backend/handler/database/legacy_migration_handler.py - Confirmation revalidation, ordered atomic migration, failure seams, and rollback metadata.
- backend/handler/database/storage_handler.py - Shared transactional mapping-record creation with safe persistence error translation.
- backend/handler/database/roms_handler.py - Deterministic catalog locking and unique logical-identity reconnection.
- backend/endpoints/responses/storage.py - Strict bounded migration result schema.
- backend/endpoints/storage.py - Administrator-only migration endpoint with path/body binding and safe errors.
- backend/tests/handler/database/test_storage_lifecycle.py - Atomicity, rollback, retry, isolation, race, and source-manifest evidence.
- backend/tests/handler/storage/test_legacy_migration.py - Authorization and bounded-response acceptance evidence.
- frontend/src/**generated**/ - Regenerated input/output confirmation and migration result models.

## Decisions Made

- A migration owns exactly one platform transaction. An injected failure rolls back every mapping, catalog, audit, detection-version, and migration-metadata write from that attempt without affecting an earlier committed platform.
- Catalog reconnection is database-only and conservative. Only a normalized logical identity occurring exactly once reconnects; unsafe or ambiguous identities stay unmatched and visible.
- Migration acquires the same platform lock used by mapping lifecycle creation, then uses deterministic root, mapping, migration, ROM, and ROM-file ordering.
- The public result is an explicit allowlist of durable IDs, optimistic versions, counts, and authority booleans. It omits relative paths, filesystem observations, raw rows, and errors.
- Legacy source content is never opened or mutated during migration. Tests compare path, type, mode, size, SHA-256, and symlink identity before and after success, failure, and retry.

## TDD Gate Compliance

- RED: 1673b4866 failed after valid isolated MariaDB setup because DBLegacyMigrationHandler.migrate_platform did not exist.
- GREEN: 4aac5af92 implemented the transaction, endpoint, generated contract, and race/failure behavior.
- Commit order was verified with git log.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added the typed response schema and regenerated the frontend contract**

- **Found during:** Task 2 endpoint implementation
- **Issue:** Repository endpoint conventions require an explicit response model, and a new route changes the generated OpenAPI contract.
- **Fix:** Added LegacyMigrationResultSchema, regenerated confirmation input/output models and exports, and ran the frontend typecheck.
- **Files modified:** backend/endpoints/responses/storage.py, frontend/src/**generated**/
- **Verification:** npm run typecheck passed with a 4 GB Node heap.
- **Committed in:** 4aac5af92

**2. [Rule 1 - Bug] Avoided stale versioned ORM state during catalog reconnection**

- **Found during:** Task 2 GREEN verification
- **Issue:** Mutating locked versioned ROM objects directly caused a stale-row failure when the transaction flushed later migration state.
- **Fix:** Kept deterministic row locks and applied bounded bulk updates with session synchronization disabled.
- **Files modified:** backend/handler/database/roms_handler.py
- **Verification:** All 29 focused migration and lifecycle tests passed.
- **Committed in:** 4aac5af92

**3. [Rule 1 - Bug] Scoped rollback and race assertions to the seeded platform**

- **Found during:** Task 2 GREEN verification
- **Issue:** The audit cleanup fixture intentionally preserves scalar audit history, so database-wide zero-count assertions could observe unrelated prior test rows.
- **Fix:** Bound mapping, audit, and migration assertions to the current platform or detection result.
- **Files modified:** backend/tests/handler/database/test_storage_lifecycle.py
- **Verification:** Failure-stage and race tests pass in the complete focused suite.
- **Committed in:** 4aac5af92

**4. [Rule 3 - Blocking] Modeled the lifecycle race with a valid read-only root**

- **Found during:** Task 2 race verification
- **Issue:** The ordinary create path correctly rejected the writable temporary directory before reaching the intended concurrency boundary.
- **Fix:** Reused the established resolver access patch so the fixture represents an approved external read-only root.
- **Files modified:** backend/tests/handler/database/test_storage_lifecycle.py
- **Verification:** The barrier-based migrate/create race passed without sleeps.
- **Committed in:** 4aac5af92

---

**Total deviations:** 4 auto-fixed (2 bugs, 2 blocking)
**Impact on plan:** The additions were required for typed API consistency, correct versioned updates, isolated evidence, and a valid lifecycle race. No UI, deployment, source mutation, v1 edit, or fallback scope was added.

## Issues Encountered

- The initial duplicate catalog fixture violated an existing (platform_id, fs_name) uniqueness constraint and was not accepted as RED evidence. The fixture was corrected to represent two stored rows with one normalized logical identity; RED then failed only on the absent migration method.
- Repository pytest.ini loopback values were bypassed with -p no:env and a full explicit Compose environment against isolated MariaDB database romm_test_0606.
- The broad Trunk checker timed out without diagnostics twice. Scoped formatting passed, the commit hook checked all 11 GREEN files with no issues, focused tests passed, and frontend typecheck passed.

## Verification

- RED selector: valid isolated setup failed on the absent migrate_platform behavior.
- Full focused lifecycle and legacy migration suites: 29 passed.
- Frontend generated-contract typecheck: passed under Node 24 with a 4 GB heap.
- git diff --check: passed before commit.
- Commit hook: checked all 11 GREEN files with no issues.
- Source-manifest equality covers path, type, mode, size, SHA-256, and symlink identity; atime is excluded.
- Stub scan found no TODO, FIXME, placeholder, coming-soon, or unavailable implementation stubs.
- Threat-surface scan found no unmodeled boundary; transaction, storage authority, result disclosure, and bounded work are covered by T-06-06A through T-06-06D.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 06-07 can consume the durable LegacyMigration record for rollback without reconstructing prior authority.
- Plan 06-08 can build recovery evidence over atomic completed migration records and safe audit history.
- No blockers remain.

## Self-Check: PASSED

- All 12 plan key files exist in the canonical Linux checkout.
- RED and GREEN task commits exist in git history in required order.
- CAT-03, MIG-01, MIG-03, and MIG-04 implementation and verification claims are represented above.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-12_
