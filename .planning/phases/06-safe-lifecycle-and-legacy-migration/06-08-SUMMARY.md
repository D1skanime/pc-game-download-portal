---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "08"
subsystem: legacy-migration-rollback
tags:
  [fastapi, sqlalchemy, rollback, concurrency, mariadb, mysql, postgresql, tdd]
requires:
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "06"
    provides: atomic migration records and owned-state rollback metadata
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "07"
    provides: durable productive first-use CAS
provides:
  - bounded administrator rollback eligibility and mutation API
  - migration-first locked rollback CAS with mapping revision invalidation
  - restart-durable rollback evidence across MariaDB, MySQL, and PostgreSQL
affects: [06-09, phase-07, legacy-migration, storage-lifecycle, openapi]
tech-stack:
  added: []
  patterns:
    - migration-then-mapping rollback lock ordering shared with first-use CAS
    - typed bounded rollback errors without source paths or stored snapshots
    - disposable three-dialect restart and round-trip verification
key-files:
  created:
    - frontend/src/__generated__/models/LegacyRollbackErrorCode.ts
    - frontend/src/__generated__/models/LegacyRollbackErrorDetail.ts
    - frontend/src/__generated__/models/LegacyRollbackErrorResponse.ts
    - frontend/src/__generated__/models/LegacyRollbackRequestSchema.ts
    - frontend/src/__generated__/models/LegacyRollbackStatusSchema.ts
  modified:
    - backend/handler/database/legacy_migration_handler.py
    - backend/endpoints/responses/storage.py
    - backend/endpoints/storage.py
    - backend/tests/endpoints/test_storage.py
    - backend/tests/integration/test_legacy_migration.py
    - backend/tools/verify_storage_migrations.py
    - backend/tests/tools/test_verify_storage_migrations.py
    - frontend/src/__generated__/index.ts
key-decisions:
  - "Rollback and productive first use serialize by locking the migration row before the mapping row."
  - "Rollback invalidates the created mapping revision, restores only exact prior owned mapping state when still valid, and marks catalog rows unreachable without source access."
  - "Rollback status and errors expose bounded IDs, versions, eligibility, expiry, and operation vocabulary only."
patterns-established:
  - "Rollback CAS: validate migration identity/version/expiry/use state, lock mapping lineage in ID order, apply owned changes, audit, and mark rolled back in one transaction."
  - "Verifier cleanup: restore seeded mapping baseline before downgrade and re-upgrade assertions."
requirements-completed: [MIG-02, MIG-04, MIG-05]
duration: 31min
completed: 2026-08-13
---

# Phase 6 Plan 8: Typed Rollback API and Durable Persistence Summary

**Unused legacy migrations can now be rolled back through a bounded administrator API, with first-use serialization, atomic owned-state restoration, and three-dialect restart evidence**

## Performance

- **Duration:** 31 min
- **Started:** 2026-08-12T23:39:00Z
- **Completed:** 2026-08-13T00:10:00Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Added typed administrator-only rollback status and mutation routes requiring migration identity, platform binding, and expected version.
- Implemented migration-first row locking shared with productive first use, atomic mapping invalidation, bounded prior mapping restoration, catalog reachability reversal, audit, and durable rolled-back state.
- Proved stable failure for used, stale, replayed, expired, missing, and cross-platform identities without exposing source paths or snapshots.
- Extended the disposable verifier to prove rollback and mapping revision persistence across MariaDB, MySQL, and PostgreSQL restarts and round trips.
- Regenerated the OpenAPI TypeScript contract and passed frontend typechecking.

## Task Commits

1. **Task 1: Specify rollback API and persistence** - `8ad3f1aa2` (test)
2. **Task 2: Implement rollback and three-dialect durability** - `115aa163c` (feat)

## Files Created/Modified

- `backend/handler/database/legacy_migration_handler.py` - Bounded rollback status, exact identity checks, ordered locks, atomic rollback, and durable errors.
- `backend/endpoints/responses/storage.py` - Typed rollback request, status, and error schemas.
- `backend/endpoints/storage.py` - Administrator-only rollback status and mutation routes with safe error translation.
- `backend/tests/endpoints/test_storage.py` - Authorization, bounded serialization, stable 409, and OpenAPI contract evidence.
- `backend/tests/integration/test_legacy_migration.py` - Source-neutral success, rejection, flush-failure retry, restart, and rollback/first-use race evidence.
- `backend/tools/verify_storage_migrations.py` - Three-dialect rollback restart persistence and exact seeded-state cleanup.
- `backend/tests/tools/test_verify_storage_migrations.py` - Verifier restart and cleanup regression coverage.
- `frontend/src/__generated__/` - Generated rollback API models and exports.

## Decisions Made

- Rollback locks the migration row first, then locks created and prior mapping rows in ID order. This matches first-use ordering and gives one deterministic race winner.
- A successful rollback deactivates and revises the migration-created mapping, marks reconnected platform catalog rows unreachable, appends bounded audits, and marks the migration rolled back in the same transaction.
- A prior mapping is restored only when the migration recorded it as active and its exact durable ID, platform, version, and inactive state still match.
- Status remains observational and bounded. It reports eligibility, first-use state, expiry, IDs, and versions, never relative paths, container paths, raw snapshots, or source capabilities.

## TDD Gate Compliance

- RED: `8ad3f1aa2` was committed after a valid isolated MariaDB run passed 52 existing tests and failed with 404 only because rollback routes were absent.
- GREEN: `115aa163c` implements the rollback transaction, typed routes, generated contract, verifier durability, and race/failure behavior.
- Commit order was verified with git history.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Regenerated the typed frontend contract**

- **Found during:** Task 2 API implementation
- **Issue:** New response schemas and routes change the backend-owned OpenAPI contract.
- **Fix:** Regenerated TypeScript models and exports, then ran frontend typechecking with a 4 GB Node heap.
- **Files modified:** `frontend/src/__generated__/`
- **Verification:** `npm run typecheck` passed.
- **Committed in:** `115aa163c`

**2. [Rule 1 - Bug] Restored the verifier's seeded mapping baseline**

- **Found during:** Task 2 real-dialect verification
- **Issue:** The new restart proof correctly advanced the seeded mapping to revision 5, but the verifier did not restore revision 4 before its later downgrade and re-upgrade assertion.
- **Fix:** Reset the verifier-owned seeded mapping to active revision 4 during exact lifecycle cleanup and added a cleanup-order regression test.
- **Files modified:** `backend/tools/verify_storage_migrations.py`, `backend/tests/tools/test_verify_storage_migrations.py`
- **Verification:** The complete MariaDB, MySQL, and PostgreSQL verifier passed.
- **Committed in:** `115aa163c`

**3. [Rule 3 - Blocking] Verified the actual split runner bind**

- **Found during:** Task 2 runner preflight
- **Issue:** The plan's literal `/app` bind assertion did not match the verified Compose topology, which binds this checkout's backend at `/app/backend`.
- **Fix:** Verified `/home/d1sk/romm/backend:/app/backend` exactly before running the backend-only verifier.
- **Files modified:** None.
- **Verification:** All verifier commands executed against the canonical backend bind.
- **Committed in:** Not applicable.

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All deviations were required for contract consistency, correct verifier cleanup, and fail-closed execution against the canonical checkout. No source mutation, deployment, v1, UI, or Team4s scope was added.

## Issues Encountered

- The initial frontend typecheck exhausted Node's default heap. Re-running with `NODE_OPTIONS=--max-old-space-size=4096` passed.
- The real-dialect verifier intentionally prints expected downgrade-preflight tracebacks while confirming unsafe downgrades fail before DDL. Its final result passed all three dialects.
- The isolated MariaDB database used for focused tests was verified by exact name and dropped after final verification. All disposable verifier containers cleaned themselves up.

## Validation Evidence

- Valid RED selector: 52 existing tests passed, then the absent rollback route failed with HTTP 404.
- Final focused endpoint, integration, and verifier suite: 87 passed.
- MariaDB handler gate: 47 passed.
- PostgreSQL handler gate: 47 passed.
- MariaDB, MySQL, and PostgreSQL pristine plus seeded-0110 upgrade, downgrade, re-upgrade, restart, rollback-state, and mapping-revision proofs passed.
- Frontend generated-contract typecheck passed with a 4 GB Node heap.
- Commit hook checked and formatted all 13 GREEN files with no issues.
- `git diff --check` passed.
- Source manifests remained identical across rollback success, rejection, injected crash, race, and retry.

## Known Stubs

None.

## Threat Review

No unmodeled trust boundary was introduced. The new routes and transaction are the surfaces covered by T-06-08A through T-06-08C: admin authorization and bound CAS identity, owned-state-only rollback, and bounded status disclosure.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 06-09 can consume the typed rollback contract and three-dialect durability evidence for final lifecycle and immutability closure.
- No blockers remain.

## Self-Check: PASSED

- All 13 implementation and generated-contract artifacts exist in the canonical Linux checkout.
- RED commit `8ad3f1aa2` and GREEN commit `115aa163c` exist in git history in required order.
- MIG-02, MIG-04, and MIG-05 implementation and verification claims are represented above.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_
