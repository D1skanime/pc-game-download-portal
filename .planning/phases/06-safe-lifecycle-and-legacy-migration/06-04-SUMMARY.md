---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "04"
subsystem: legacy-storage-detection
tags: [fastapi, sqlalchemy, storage-policy, migration, openapi]
requires:
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "01"
    provides: durable expiring legacy detection result schema
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "03"
    provides: mapping revision invalidation and ordered lifecycle locking
provides:
  - explicit administrator-only legacy detection jobs
  - exact two-grammar fs_slug detection through LIST and STAT capabilities
  - expiring version-bound durable results with stale, replay, and cross-platform rejection
  - bounded path-free result and error contracts
affects: [06-05, 06-07, 06-09, legacy-migration, storage-administration]
tech-stack:
  added: []
  patterns:
    - exact persisted-identity candidate construction with no alias or fuzzy fallback
    - capability-bound external inspection with entry and time budgets
    - ordered context locking and save-time authority revalidation
key-files:
  created:
    - backend/handler/storage/legacy_migration.py
    - backend/handler/database/legacy_migration_handler.py
    - backend/tasks/manual/detect_legacy_storage.py
    - frontend/src/__generated__/models/LegacyDetectionResultSchema.ts
  modified:
    - backend/endpoints/storage.py
    - backend/endpoints/responses/storage.py
    - backend/handler/filesystem/storage_inventory.py
    - backend/tests/handler/storage/test_legacy_migration.py
key-decisions:
  - "Legacy detection constructs only roms/{Platform.fs_slug} and {Platform.fs_slug}/roms from the persisted platform identity."
  - "Detection reads external storage only through LIST and STAT with 10000-entry and five-second budgets."
  - "Durable results expire after 24 hours, bind observed mapping identity and version, and cannot authorize direct legacy reads."
patterns-established:
  - "Detection authority: explicit admin request enqueues integer identities only; the worker reloads persisted authority."
  - "Result authority: selectable status is necessary but never sufficient for reads and is consumed by version increment."
requirements-completed: [MIG-01, MIG-03, MIG-05]
duration: 33min
completed: 2026-08-12
---

# Phase 06 Plan 04: Exact Bounded Legacy Detection Summary

**Administrator-triggered exact legacy layout detection with capability-bound inspection, expiring durable results, and no fallback read authority**

## Performance

- **Duration:** 33 min
- **Started:** 2026-08-12T21:34:58Z
- **Completed:** 2026-08-12T22:07:49Z
- **Tasks:** 2
- **Files modified:** 18

## Accomplishments

- Added exact detection for only roms/{Platform.fs_slug} and {Platform.fs_slug}/roms, rejecting alternate case, aliases, configured names, custom layouts, and unsafe identities.
- Restricted source observation to policy-governed LIST and STAT capabilities with 10,000-entry and five-second budgets, lower-bound counts, bounded problem codes, and source-manifest equality evidence.
- Added explicit administrator POST enqueue and bounded GET result endpoints with authentication before database or storage observation.
- Persisted 24-hour results under ordered locks with platform, root path/activation, mapping identity/version, overlap, stale, expired, replay, and cross-platform checks.
- Regenerated frontend OpenAPI models and verified the generated contract with Vue TypeScript.

## Task Commits

1. **Task 1: Specify exact bounded legacy detection (RED)** - 00ee996c4 (test)
2. **Task 2: Implement exact bounded legacy detection (GREEN)** - 097211112 (feat)

## Files Created/Modified

- backend/handler/storage/legacy_migration.py - Exact candidate construction and bounded LIST/STAT traversal.
- backend/handler/database/legacy_migration_handler.py - Ordered context locks, durable result persistence, expiry, version binding, and one-use authorization.
- backend/tasks/manual/detect_legacy_storage.py - Explicit manual worker that reloads persisted root and platform authority.
- backend/endpoints/storage.py - Administrator enqueue and bounded result retrieval routes.
- backend/endpoints/responses/storage.py - Strict request, job, result, and safe error schemas.
- backend/handler/filesystem/storage_inventory.py - Closed legacy-detection capability inventory row.
- backend/handler/storage/**init**.py - Lazy compatibility export preventing storage package import cycles.
- backend/tests/handler/storage/test_legacy_migration.py - Grammar, budget, immutability, authorization, OpenAPI, expiry, stale, replay, and cross-platform evidence.
- frontend/src/**generated**/ - Regenerated bounded legacy detection contracts and exports.

## Decisions Made

- A bounded scan that reaches its entry or time limit remains selectable only when it has observed a canonical layout, and its counts are explicitly lower bounds.
- Both canonical layouts present is ambiguous and unselectable; absent, empty, unreadable, unreachable, unsafe, active-mapping, and overlap states never gain fallback authority.
- The task reloads persisted platform and root data from integer IDs and revalidates all authority-relevant fields before committing a result.
- Consuming a selectable result increments its version atomically so the same authorization cannot be replayed.

## TDD Gate Compliance

- RED: 00ee996c4 failed on the explicit absence of the exact bounded detector after isolated database setup completed.
- GREEN: 097211112 implemented the detector, worker, durable handler, API, closed inventory, tests, and generated contract.
- Commit order was verified with git log.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed a handler package import cycle**

- **Found during:** Task 2
- **Issue:** The new handler triggered an eager storage/filesystem import cycle during application startup.
- **Fix:** Preserved the compatibility export through a typed lazy module attribute and moved the detector outcome import behind TYPE_CHECKING.
- **Verification:** Focused application endpoint and detector gate passed, 61 tests.
- **Committed in:** 097211112

**2. [Rule 2 - Missing Critical] Registered the detector in the closed storage authority inventory**

- **Found during:** Task 2 threat-boundary review
- **Issue:** The manual worker required an explicit policy-governed LIST/STAT inventory row and closed-seam expectation.
- **Fix:** Added the inventory row, runnable evidence, required family, and exact descriptor-factory seam.
- **Verification:** Closed inventory suite passed, 11 tests.
- **Committed in:** 097211112

**3. [Rule 3 - Blocking] Extended test cleanup for durable legacy rows**

- **Found during:** Task 2 verification
- **Issue:** Persisted legacy rows reference platform, root, and mapping records.
- **Fix:** Deleted migration and detection result rows in foreign-key-safe order.
- **Verification:** Combined focused suite passed, 72 tests.
- **Committed in:** 097211112

**4. [Rule 3 - Blocking] Regenerated the frontend API contract**

- **Found during:** Pre-PR verification
- **Issue:** New request, job, result, and safe error schemas changed OpenAPI.
- **Fix:** Regenerated typed frontend models and exports and ran the frontend typecheck.
- **Verification:** npm run typecheck passed.
- **Committed in:** 097211112

---

**Total deviations:** 4 auto-fixed (1 missing critical, 3 blocking)
**Impact on plan:** Required for application startup, closed storage authority, test isolation, and contract consistency. No Phase 7 UI, deployment, source mutation, automatic detection, or legacy fallback was added.

## Issues Encountered

- pytest.ini forces DB_HOST=127.0.0.1, invalid inside romm-dev. Verification used -c /dev/null, explicit Compose hosts, and disposable database romm_test_0604.
- The targeted Trunk check timed out without output after formatting. Trunk formatting passed, and the mandatory commit hook checked all 18 changed files successfully.
- Existing untracked planning and workspace files were preserved unchanged.

## Verification

- Focused detector and endpoint suite: 61 passed.
- Closed storage authority inventory suite: 11 passed.
- Final combined focused suite: 72 passed.
- Frontend generated-contract typecheck: passed.
- Trunk formatting: passed.
- Commit hook: all 18 implementation and generated files checked cleanly.
- Stub scan found no TODO, FIXME, placeholder, hardcoded empty render data, or unwired data source.
- Threat-surface scan found no unmodeled boundary; T-06-04A through T-06-04C are implemented.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 06-05 can consume the version-bound detection result when creating explicit migration mappings.
- No blockers remain.

## Self-Check: PASSED

- All created key files exist in the canonical Linux checkout.
- RED and GREEN task commits exist in git history in required order.
- MIG-01, MIG-03, and MIG-05 claims are represented above.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-12_
