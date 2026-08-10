---
phase: 03-mapping-administration-contracts
plan: 04
subsystem: api
tags: [fastapi, pydantic, authorization, openapi, filesystem]
requires:
  - phase: 03-02
    provides: Pure live root health and bounded contained directory browsing
  - phase: 03-03
    provides: Storage handler and audited mapping lifecycle foundation
provides:
  - Administrator-only root list and detail endpoints with live health
  - Bounded contained directory browse endpoint
  - Explicit path-safe storage response and error schemas
affects: [03-05, 03-06, phase-7]
tech-stack:
  added: []
  patterns:
    [
      authorize-before-observe,
      explicit response allowlists,
      bounded typed errors,
    ]
key-files:
  created:
    - backend/endpoints/responses/storage.py
    - backend/endpoints/storage.py
    - backend/tests/endpoints/test_storage.py
  modified:
    - backend/handler/database/storage_handler.py
    - backend/main.py
key-decisions:
  - "Storage administration reads require both the coarse users.read scope and an explicit administrator assertion before database or filesystem access."
  - "Root and browse responses are constructed only from explicit allowlisted schemas, and storage exceptions are translated to bounded static messages."
patterns-established:
  - "Live root health is serialized from a pure snapshot while persisted status timestamps remain separate."
  - "Storage read errors expose stable codes without using exception text or chained operating-system details."
requirements-completed: [API-01, API-02, API-04, AUD-02, TEST-02]
duration: 6min
completed: 2026-08-10
---

# Phase 3 Plan 4: Authorized Storage Read API Summary

**Administrator-only root inspection and bounded directory browsing with live health, explicit OpenAPI allowlists, and path-safe typed errors**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-10T22:04:00Z
- **Completed:** 2026-08-10T22:10:09Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added root list and detail routes that authenticate and assert administrator status before lookup or filesystem observation.
- Added contained directory browsing with hard page, path, and cursor bounds delegated to the Phase 3 resolver.
- Added explicit schemas that exclude container paths, persisted raw errors, mappings, and filesystem metadata from OpenAPI and JSON.
- Added static path-safe error translation and adversarial authorization, mutation-tripwire, sentinel, and schema tests.

## Task Commits

1. **Task 1: RED authorization and root-browser HTTP contracts** - `46f2f372a` (test)
2. **Task 2: GREEN safe root and browse endpoints** - `1461c730a` (feat)
3. **Task 2 refactor: Current FastAPI status constant** - `87654267c` (refactor)

## Files Created/Modified

- `backend/endpoints/responses/storage.py` - Explicit safe root, health, browse, cursor, and error schemas.
- `backend/endpoints/storage.py` - Administrator-only storage read router and bounded error translation.
- `backend/handler/database/storage_handler.py` - Ordered root retrieval methods used by thin endpoints.
- `backend/main.py` - Single storage router registration under `/api`.
- `backend/tests/endpoints/test_storage.py` - Authorization matrix, pure-health, minimal browse, leak, and OpenAPI evidence.

## Decisions Made

- A storage read route uses `Scope.USERS_READ` as the authentication gate and `assert_admin` as the authoritative role gate.
- Error responses use static code-specific messages and never serialize exception strings or causes.
- Root payloads expose persisted creation and update timestamps, but current health comes only from the pure live snapshot.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added handler-owned root retrieval**

- **Found during:** Task 2
- **Issue:** The endpoint contract required thin database delegation, but the storage handler did not yet expose root list or detail reads.
- **Fix:** Added ordered `get_roots` and typed `get_root` methods to `DBStorageHandler`.
- **Files modified:** `backend/handler/database/storage_handler.py`
- **Verification:** The focused endpoint, resolver, and storage-handler suites pass.
- **Committed in:** `1461c730a`

**2. [Rule 1 - Quality] Removed a new deprecated FastAPI status alias**

- **Found during:** Task 2 verification
- **Issue:** The initial implementation emitted deprecation warnings for the legacy 422 status constant.
- **Fix:** Switched to `HTTP_422_UNPROCESSABLE_CONTENT`.
- **Files modified:** `backend/endpoints/storage.py`
- **Verification:** The endpoint suite passes without that warning.
- **Committed in:** `87654267c`

---

**Total deviations:** 2 auto-fixed (1 missing critical functionality, 1 quality fix).
**Impact on plan:** Both changes preserve the planned architecture and security boundary without expanding product scope.

## Issues Encountered

- The plan's default test command inherits a loopback database host from `pytest.ini`. Verification used the existing isolated `romm_test_phase03_02` database through `romm-db-dev` with explicit test-only settings and `-c /dev/null`.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

| Flag                                              | File                         | Description                                                                                                                           |
| ------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| threat_flag: administrator-filesystem-observation | backend/endpoints/storage.py | New network routes authorize before root lookup and contained filesystem observation, then serialize allowlisted path-safe data only. |

## Next Phase Readiness

- Plan 03-05 can add the mapping lifecycle router beside the storage read contracts.
- Plan 03-06 can generate final OpenAPI client types and reuse the bounded read error envelope.
- No blockers remain.

## Self-Check: PASSED

- All five created or modified implementation and test files exist.
- RED commit `46f2f372a`, GREEN commit `1461c730a`, and refactor commit `87654267c` exist in the required order.
- Endpoint, resolver, and storage-handler suites pass: 101 tests, 0 failures.
- The storage router is registered exactly once and `git diff --check` is clean.
- Known unrelated untracked files remain untouched.

---

_Phase: 03-mapping-administration-contracts_
_Completed: 2026-08-10_
