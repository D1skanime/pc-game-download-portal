---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "03"
subsystem: storage-lifecycle
tags: [fastapi, sqlalchemy, mapping-removal, reconnection, openapi]

requires:
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "01"
    provides: retained catalog identity and durable lifecycle schema
  - phase: 05-preview-and-read-path-cutover
    provides: mapping-revision-bound read contexts
provides:
  - bounded administrator mapping-removal consequences and explicit confirmation
  - atomic mapping revision invalidation with visible-unreachable retained catalog
  - exact logical identity or unique complete-hash reconnection
  - safe-boundary cancellation checks for mapping-bound work
affects: [06-04, 06-07, 06-09, mapping-administration, scanning]

tech-stack:
  added: []
  patterns:
    - deterministic platform, root, mapping, ROM, and ROM-file lifecycle locking
    - preview-bound confirmation revalidated inside the removal transaction
    - exact logical identity before unique complete-hash reconnection

key-files:
  created:
    - backend/tests/handler/database/test_storage_lifecycle.py
    - frontend/src/__generated__/models/StorageMappingRemovalConfirmationSchema.ts
    - frontend/src/__generated__/models/StorageMappingRemovalConsequencesSchema.ts
  modified:
    - backend/handler/database/storage_handler.py
    - backend/handler/database/roms_handler.py
    - backend/handler/storage/read_context.py
    - backend/handler/scan_handler.py
    - backend/endpoints/storage.py
    - backend/endpoints/responses/storage.py

key-decisions:
  - "Mapping removal retains every platform ROM and ROM file while marking them unreachable in the same transaction that invalidates the mapping revision and appends audit history."
  - "Removal confirmation binds expected mapping version and expected affected catalog count, then revalidates both under locks."
  - "Reconnection accepts one exact normalized logical identity or one unique complete CRC32, MD5, and SHA1 identity, with no weaker fallback."

patterns-established:
  - "Removal consequence contract: report only bounded retention, immutability, revision, and cancellation facts."
  - "Reconnection authority: exact logical identity first, otherwise complete triple-hash uniqueness."

requirements-completed: [CAT-03, CAT-04]

duration: 26min
completed: 2026-08-12
---

# Phase 06 Plan 03: Mapping Removal and Reconnection Summary

**Atomic mapping removal with bounded administrator consequences, retained unreachable catalog state, revision cancellation, and unambiguous reconnection**

## Performance

- **Duration:** 26 min
- **Started:** 2026-08-12T21:00:36Z
- **Completed:** 2026-08-12T21:26:43Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments

- Added an administrator-only consequence preview and ordinary explicit confirmation contract that reports retained catalog count, preserved value, source immutability, revision invalidation, and safe-boundary cancellation.
- Extended mapping removal to lock and revalidate lifecycle state, deactivate and increment the mapping revision, mark retained ROM and ROM-file rows unreachable, and append audit history in one transaction.
- Preserved source manifests and all catalog rows while making old mapping-bound work fail stale at its next boundary.
- Restricted reconnection to exact normalized logical identity or unique complete CRC32, MD5, and SHA1 identity, never weaker identifiers or first-match behavior.
- Regenerated the frontend OpenAPI models and verified the shared contract remains type-safe.

## Task Commits

1. **Task 1: Specify mapping removal, cancellation and reconnection (RED)** - `788cd2ed1` (test)
2. **Task 2: Implement mapping removal, cancellation and reconnection (GREEN)** - `06e6e5f16` (feat)

## Files Created/Modified

- `backend/handler/database/storage_handler.py` - Typed consequence/result values and the locked atomic removal transaction.
- `backend/handler/database/roms_handler.py` - Exact logical and unique complete-hash missing-ROM matching.
- `backend/handler/storage/read_context.py` - Named safe boundaries before owned writes and response commitment.
- `backend/handler/scan_handler.py` - Mapping revision checks around mapped scan processing and commitment.
- `backend/endpoints/storage.py` - Administrator preview and confirmed removal routes with bounded conflicts.
- `backend/endpoints/responses/storage.py` - Strict confirmation, consequence, and changed-consequence schemas.
- `backend/endpoints/sockets/scan.py` - Supplies normalized logical identity to the canonical reconnection query.
- `backend/exceptions/storage_exceptions.py` - Bounded changed-consequence conflict.
- `backend/tests/handler/database/test_storage_lifecycle.py` - Removal retention, rollback, staleness, source equality, and reconnection acceptance evidence.
- `backend/tests/endpoints/test_storage.py` - Authorization, confirmation, bounded response, and OpenAPI evidence.
- `backend/tests/endpoints/sockets/test_scan.py` - Logical identity propagation regression evidence.
- `frontend/src/__generated__/` - Regenerated mapping-removal contract models and exports.

## Decisions Made

- Mapping deactivation remains a reversible administrative state change; only confirmed removal additionally marks the platform catalog unreachable.
- The consequence preview count includes all retained ROMs for the mapped platform, including rows already marked missing, because all remain visible catalog consequences.
- Changed consequence counts fail with a bounded 409 conflict and require a new preview rather than silently accepting drift.
- Already-open file descriptors are not claimed to be revoked. Running work stops only at explicit safe boundaries.

## TDD Gate Compliance

- RED: `788cd2ed1` failed because the removal consequence handler did not exist.
- GREEN: `06e6e5f16` implemented the transaction, API, boundaries, reconnection, and generated contract.
- Commit order was verified with `git log`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Wired logical identity through the active scan caller**

- **Found during:** Task 2
- **Issue:** The planned database matcher could not enforce exact logical reconnection unless the active scan caller supplied the observed logical path.
- **Fix:** Passed the mapping-relative ROM path from the scan socket orchestration and updated its regression expectation.
- **Files modified:** `backend/endpoints/sockets/scan.py`, `backend/tests/endpoints/sockets/test_scan.py`
- **Verification:** Adjacent storage, ROM, scan, and handler regression gate passed, 148 tests.
- **Committed in:** `06e6e5f16`

**2. [Rule 3 - Blocking] Regenerated the frontend API contract**

- **Found during:** Pre-PR verification
- **Issue:** The new request and response schemas changed OpenAPI and required generated client models.
- **Fix:** Regenerated the typed models and exports, then ran the frontend typecheck.
- **Files modified:** `frontend/src/__generated__/`
- **Verification:** `npm run typecheck` passed.
- **Committed in:** `06e6e5f16`

**3. [Rule 2 - Missing Critical] Added a bounded changed-consequence conflict**

- **Found during:** Task 2
- **Issue:** Revalidation needed a typed safe failure that disclosed neither rows nor paths when the catalog count changed after preview.
- **Fix:** Added `StorageMappingConsequencesChangedError` and mapped it to an allowlisted 409 response.
- **Files modified:** `backend/exceptions/storage_exceptions.py`, `backend/endpoints/storage.py`, `backend/endpoints/responses/storage.py`
- **Verification:** Focused endpoint and lifecycle gate passed, 55 tests.
- **Committed in:** `06e6e5f16`

---

**Total deviations:** 3 auto-fixed (2 missing critical, 1 blocking)
**Impact on plan:** Each change was required for correctness, safe disclosure, or contract consistency. No Phase 7 UI, deployment, source mutation, or fallback authority was added.

## Issues Encountered

- `pytest.ini` forces `DB_HOST=127.0.0.1`, which is invalid inside `romm-dev`. Verification used `-c /dev/null`, explicit Compose service hosts, and `asyncio_mode=auto`.
- The direct cached Trunk CLI check stalled after formatting. The mandatory commit hooks subsequently checked all 15 implementation files successfully with no issues.
- Existing untracked planning and workspace files were preserved unchanged.

## Verification

- Required focused gate: 55 passed.
- Adjacent storage handler, ROM handler, scan socket, and scan handler gate: 148 passed.
- Frontend generated-contract typecheck: passed.
- Commit hooks: all 15 implementation/generated files checked cleanly.
- Source manifest equality covers relative path, file type, mode, size, SHA-256, and symlink identity; atime is excluded.
- Stub scan found only existing filename-placeholder scan semantics, not an implementation stub.
- Threat-surface scan found no unmodeled boundary. The new endpoint, transaction, and bounded result are covered by T-06-03A through T-06-03C.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 06-04 can build legacy detection and migration confirmation on the same mapping revision and safe consequence patterns.
- No blockers remain.

## Self-Check: PASSED

- All created key files exist in the canonical Linux checkout.
- RED and GREEN task commits exist in git history in the required order.
- CAT-03 and CAT-04 implementation and verification claims are represented above.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-12_
