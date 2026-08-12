---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "05"
subsystem: legacy-migration-api
tags: [fastapi, sqlalchemy, migration-impact, openapi, tdd]
requires:
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "04"
    provides: exact bounded detection with expiring version-bound results
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "03"
    provides: ordered mapping lifecycle locks and overlap semantics
provides:
  - read-only per-platform legacy migration impact preview
  - bounded reconnectable and unmatched catalog counts
  - durable confirmation binding with catalog drift revalidation
  - explicit manual outcomes for active and overlapping mappings
affects: [06-06, 06-08, phase-07, legacy-migration, openapi]
tech-stack:
  added: []
  patterns:
    - database-only impact preview over normalized unique catalog identities
    - confirmation recomputation before any future migration mutation
key-files:
  created:
    - frontend/src/__generated__/models/LegacyImpactPreviewSchema.ts
    - frontend/src/__generated__/models/LegacyImpactConfirmationSchema.ts
  modified:
    - backend/handler/storage/legacy_migration.py
    - backend/handler/database/legacy_migration_handler.py
    - backend/endpoints/responses/storage.py
    - backend/endpoints/storage.py
    - backend/tests/handler/storage/test_legacy_migration.py
    - backend/tests/endpoints/test_storage.py
    - frontend/src/__generated__/index.ts
key-decisions:
  - "Impact preview counts only normalized unique catalog identities and never opens source storage."
  - "Confirmation binds detection result, result version, platform, root, relative path, observed mapping identity, catalog counts, and expiry."
  - "Active or overlapping mappings return a bounded manual-mapping outcome with zero planned effects."
patterns-established:
  - "Preview then revalidate: recompute the same read-only impact and require exact confirmation equality before mutation."
  - "Manual conflict: return safe problem codes and no confirmation rather than replacing or rewriting mappings."
requirements-completed: [MIG-01, MIG-03, MIG-05]
duration: 18min
completed: 2026-08-12
---

# Phase 06 Plan 05: Typed Legacy Migration Impact Summary

**Read-only migration impact preview with bounded catalog effects, conflict-safe manual outcomes, and restart-stable confirmation revalidation**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-12T22:14:23Z
- **Completed:** 2026-08-12T22:31:57Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments

- Added an administrator-only impact endpoint that reports the proposed mapping, reconnectable and unmatched catalog counts, bounded problems, and exact planned RomM-owned database effects.
- Bound confirmation to the durable detection result, platform, root, relative path, observed mapping identity/version, catalog counts, and expiry, then proved a fresh handler rejects catalog drift.
- Returned explicit manual-mapping outcomes with zero effects for active or overlapping mappings and retained the zero-fallback, zero-source-mutation contract.
- Regenerated the OpenAPI TypeScript models and verified the frontend contract.

## Task Commits

1. **Task 1: Specify typed impact preview and manual outcomes (RED)** - `9a57b1a6c` (test)
2. **Task 2: Implement typed impact preview and manual outcomes (GREEN)** - `87cf9d5bc` (feat)

## Files Created/Modified

- `backend/handler/storage/legacy_migration.py` - Typed impact, problem, effects, proposed mapping, and confirmation values.
- `backend/handler/database/legacy_migration_handler.py` - Ordered live-state validation, safe catalog identity counting, manual outcomes, and confirmation recomputation.
- `backend/endpoints/responses/storage.py` - Strict request, response, effect, problem, and confirmation schemas.
- `backend/endpoints/storage.py` - Administrator-only impact endpoint and allowlisted serialization.
- `backend/tests/handler/storage/test_legacy_migration.py` - RED/GREEN evidence for immutability, counts, restart, drift, and conflict behavior.
- `backend/tests/endpoints/test_storage.py` - Authorization, bounded response, and OpenAPI evidence.
- `frontend/src/__generated__/` - Regenerated typed API contract.

## Decisions Made

- Reconnectable catalog counts come from unique normalized logical identities already stored in RomM-owned catalog rows. Invalid or ambiguous identities remain unmatched and visible rather than being guessed.
- Impact preview performs no source filesystem access and creates no mapping, audit, or migration row.
- Confirmation validation recomputes current impact under ordered locks and rejects any changed catalog or live authority as `legacy_impact_stale`.
- Existing platform mappings and equal, ancestor, or descendant overlaps never produce a confirmation or planned mutation.

## TDD Gate Compliance

- RED: `9a57b1a6c` failed after valid isolated database setup because `preview_migration_impact` was absent.
- GREEN: `87cf9d5bc` implemented the handler, endpoint, schemas, tests, and generated contract.
- Commit order was verified with git log.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Regenerated the frontend API contract**

- **Found during:** Task 2 verification
- **Issue:** The new route and response schemas changed OpenAPI, so repository rules required generated TypeScript models.
- **Fix:** Regenerated the client models and exports and ran the frontend typecheck.
- **Files modified:** `frontend/src/__generated__/`
- **Verification:** `npm run typecheck` passed.
- **Committed in:** `87cf9d5bc`

**2. [Rule 3 - Blocking] Avoided an eager handler import cycle**

- **Found during:** Task 2 application import
- **Issue:** Eager storage resolver imports from the database package re-entered the filesystem package during startup.
- **Fix:** Kept impact types under `TYPE_CHECKING` and loaded runtime storage helpers only inside impact methods.
- **Files modified:** `backend/handler/database/legacy_migration_handler.py`
- **Verification:** Application test collection and all 67 focused regression tests passed.
- **Committed in:** `87cf9d5bc`

**3. [Rule 1 - Bug] Canonicalized persisted expiry timestamps**

- **Found during:** Task 2 GREEN verification
- **Issue:** MariaDB loads timezone-naive timestamps, which did not compare equal to the UTC confirmation value created before persistence.
- **Fix:** Normalize persisted expiry to UTC before binding it into the confirmation.
- **Files modified:** `backend/handler/database/legacy_migration_handler.py`
- **Verification:** Confirmation equality, expiry serialization, and fresh-handler revalidation tests passed.
- **Committed in:** `87cf9d5bc`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All changes were required for import safety, API contract consistency, and cross-database confirmation correctness. No UI, deployment, source mutation, or fallback scope was added.

## Issues Encountered

- The first test attempts were invalid setup evidence because pytest lacked an explicit authentication key and the isolated MariaDB database had not yet been granted to the test user. After creating and granting only `romm_test_0605`, unchanged RED tests failed on the absent handler as required.
- Repository `pytest.ini` loopback values were bypassed with `-p no:env` and a full explicit Compose service environment.

## Verification

- Plan selector: 10 passed, 57 deselected.
- Full legacy migration handler and storage endpoint regression gate: 67 passed.
- Frontend generated-contract typecheck: passed.
- Commit hooks formatted and checked all 13 GREEN files with no issues.
- Source manifest equality covers path, file type, mode, size, SHA-256, and symlink identity; atime is excluded.
- Stub scan found no TODO, FIXME, placeholder, coming-soon, or unavailable implementation stubs.
- Threat-surface scan found no unmodeled boundary; the new endpoint and result are covered by T-06-05A through T-06-05D.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 06-06 can consume `LegacyImpactConfirmation` and call `validate_impact_confirmation` inside the atomic migration transaction.
- No blockers remain.

## Self-Check: PASSED

- All created key files exist in the canonical Linux checkout.
- RED and GREEN task commits exist in git history in required order.
- MIG-01, MIG-03, and MIG-05 implementation and verification claims are represented above.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-12_
