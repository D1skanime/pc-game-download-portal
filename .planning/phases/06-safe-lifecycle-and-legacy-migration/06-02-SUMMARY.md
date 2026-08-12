---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "02"
subsystem: api
tags: [fastapi, sqlalchemy, lifecycle, cleanup-intents, openapi]
requires:
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "01"
    provides: retained catalog identity and owned cleanup intent schema
  - phase: 05-preview-and-read-path-cutover
    provides: closed external-source mutation boundary
provides:
  - IDs-only Remove from catalog API with bounded results
  - atomic retained ownership transfer for saves, states, and play sessions
  - idempotent typed cleanup of RomM-owned resources and screenshots
  - generated frontend contract without source-delete input
affects: [06-03, 06-09, phase-07, catalog, cleanup, openapi]
tech-stack:
  added: []
  patterns:
    - locked catalog detach transaction plus idempotent owned cleanup intent
    - bounded API errors that never expose source paths or raw failures
key-files:
  created:
    - backend/handler/database/catalog_lifecycle_handler.py
    - backend/tasks/manual/cleanup_catalog_assets.py
    - backend/tests/endpoints/roms/test_catalog_removal.py
    - frontend/src/__generated__/models/CatalogRemovalRequest.ts
    - frontend/src/__generated__/models/CatalogRemovalResponse.ts
  modified:
    - backend/endpoints/roms/__init__.py
    - backend/endpoints/responses/rom.py
    - backend/handler/filesystem/storage_inventory.py
    - frontend/src/services/api/rom.ts
    - frontend/src/__generated__/index.ts
key-decisions:
  - "Catalog removal locks and deletes one ROM per transaction so failures cannot partially detach user value."
  - "Saves, states, and play sessions move to one retained catalog identity before disposable catalog rows are removed."
  - "Filesystem cleanup is limited to typed RomM-owned resource and screenshot intents; the API has no external-source mutation authority."
patterns-established:
  - "Catalog detach: retain durable ownership and enqueue cleanup atomically, then process owned files idempotently."
  - "Bounded bulk result: expose stable codes, IDs, retention facts, and counts only."
requirements-completed: [CAT-01, CAT-02, CAT-04]
duration: 25min
completed: 2026-08-12
---

# Phase 06 Plan 02: Catalog-only Game Removal Summary

**IDs-only catalog removal with atomic retained ownership and retryable cleanup limited to RomM-owned resources and screenshots**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-12T20:21:23Z
- **Completed:** 2026-08-12T20:46:42Z
- **Tasks:** 2
- **Files modified:** 17

## Accomplishments

- Replaced the mixed database/source deletion endpoint with an IDs-only Remove from catalog contract.
- Preserved saves, states, and play sessions under a stable retained catalog identity while explicitly removing disposable catalog rows.
- Persisted idempotent cleanup intents in the detach transaction and added bounded retry processing for RomM-owned resources and screenshots only.
- Regenerated the OpenAPI client, removed the legacy source-delete input type, and kept the shared frontend client type-safe.
- Proved source manifest equality, rollback, retry, authorization-before-observation, concurrency, and policy inventory closure.

## Task Commits

1. **Task 1: Specify Catalog-only game removal (RED)** - 21c6ee66f (test)
2. **Task 2: Implement Catalog-only game removal (GREEN)** - 0c41fee85 (feat)
3. **Task 2 verification: Align generated API client** - 89f601e76 (fix)
4. **Task 2 verification: Close removed mutation inventory seam** - d565d23ea (fix)

## Files Created/Modified

- backend/handler/database/catalog_lifecycle_handler.py - Locked detach transaction, retained ownership transfer, cleanup intent lifecycle.
- backend/endpoints/roms/**init**.py - IDs-only route with authorization before observation and bounded results.
- backend/endpoints/responses/rom.py - Strict request and allowlisted response schemas.
- backend/tasks/manual/cleanup_catalog_assets.py - Retryable typed-owned cleanup worker.
- backend/tests/endpoints/roms/test_catalog_removal.py - Acceptance, rollback, retry, concurrency, and immutability evidence.
- backend/tests/conftest.py and backend/tests/endpoints/roms/test_rom.py - Lifecycle-aware isolation and route regression coverage.
- backend/handler/filesystem/storage_inventory.py and related tests - Retired external delete seam removed.
- frontend/src/**generated**/ and frontend/src/services/api/rom.ts - Regenerated typed contract and shared-client cutover.

## Decisions Made

- Each requested ROM uses an independent transaction, preserving bulk progress while ensuring each detach is atomic.
- A retained identity is populated from bounded logical identity and complete hashes; no host or absolute path is stored.
- Resource directories and disposable screenshots become cleanup intents. Save and state files are retained and never scheduled for cleanup.
- Missing owned cleanup targets count as idempotent success; other bounded failures persist for retry without raw error text.

## TDD Gate Compliance

- RED: 21c6ee66f failed because /api/roms/remove-from-catalog did not exist.
- GREEN: 0c41fee85 implemented the endpoint, transaction, cleanup task, and acceptance coverage.
- Commit order was verified with git log.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extended shared test cleanup for retained lifecycle rows**

- **Found during:** Task 2 verification
- **Issue:** Retained identities intentionally outlive ROM rows, so prior test cleanup left foreign-key-owned history.
- **Fix:** Delete cleanup intents and retained identities after dependent user-value rows during isolation.
- **Files modified:** backend/tests/conftest.py
- **Verification:** Combined endpoint regression gate passed, 110 tests.
- **Committed in:** 0c41fee85

**2. [Rule 3 - Blocking] Regenerated and wired the frontend API contract**

- **Found during:** Pre-PR verification
- **Issue:** Removing the old request schema made the shared TypeScript client fail typecheck.
- **Fix:** Regenerated OpenAPI models and routed the shared client through the IDs-only endpoint.
- **Files modified:** frontend/src/**generated**/, frontend/src/services/api/rom.ts
- **Verification:** npm run typecheck passed with a 6144 MB Node heap.
- **Committed in:** 89f601e76

**3. [Rule 3 - Blocking] Removed the retired route from the closed mutation inventory**

- **Found during:** Pre-PR verification
- **Issue:** The closed inventory still required the deleted external-source mutation seam.
- **Fix:** Removed only that retired entry and its boundary-only expectation.
- **Files modified:** backend/handler/filesystem/storage_inventory.py and related tests.
- **Verification:** Storage inventory suite passed, 11 tests.
- **Committed in:** d565d23ea

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** Necessary consequences of the API cutover and test isolation. No Phase 7 UI, deployment, migration, or source mutation was added.

## Issues Encountered

- pytest.ini binds DB_HOST=127.0.0.1, invalid inside the app container. Tests used -c /dev/null with explicit isolated MariaDB and Redis Compose service names.
- Frontend typecheck initially exhausted the default Node heap. It passed unchanged with NODE_OPTIONS=--max-old-space-size=6144.
- sibling_roms is a database view and cannot be deleted directly on MariaDB. Removing the underlying ROM updates it automatically.

## Verification

- Required focused gate: 34 passed.
- Combined catalog and existing ROM endpoint regression gate: 110 passed.
- Closed storage inventory: 11 passed.
- Frontend generated-contract typecheck: passed.
- Commit hooks formatted and checked all committed files with no issues.
- Source manifest evidence covers relative path, type/mode, size, SHA-256, and symlink target; atime is excluded.
- Stub scan found no implementation-blocking stubs.
- Threat surface is covered by T-06-02A through T-06-02C; no unmodeled boundary was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 06-03 can build mapping removal and reconnection on stable retained identities.
- No blockers remain.

## Self-Check: PASSED

- All created key files exist in the canonical Linux checkout.
- RED, GREEN, generated-contract, and inventory commits exist in git history.
- Requirements, tests, source-safety evidence, and deviations are represented above.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-12_
