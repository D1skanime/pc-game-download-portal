---
phase: 03-mapping-administration-contracts
plan: 05
subsystem: api
tags: [fastapi, pydantic, optimistic-concurrency, audit, authorization]
requires:
  - phase: 03-03
    provides: Transactional optimistic mapping lifecycle and immutable audit history
  - phase: 03-04
    provides: Authorized path-safe storage router and response patterns
provides:
  - Administrator-only typed mapping read, test, create, update, deactivate, remove, and reactivate routes
  - Stable path-safe HTTP 409 mapping conflicts with optimistic version details
  - Newest-first filter-bound audit history API with allowlisted snapshots
affects: [03-06, phase-5, phase-7]
tech-stack:
  added: []
  patterns:
    [
      authorize-before-handler,
      authenticated-actor-snapshot,
      typed-safe-conflicts,
    ]
key-files:
  created: []
  modified:
    - backend/endpoints/responses/storage.py
    - backend/endpoints/storage.py
    - backend/tests/endpoints/test_storage.py
key-decisions:
  - "All mapping mutations derive actor ID and display snapshot from the authenticated request and pass them directly to the transactional handler."
  - "Mapping conflicts serialize only stable codes, allowlisted identifiers, and the current version for stale writes."
requirements-completed:
  [
    MAP-01,
    MAP-02,
    MAP-03,
    MAP-04,
    MAP-05,
    MAP-06,
    API-03,
    API-04,
    AUD-01,
    AUD-02,
    TEST-02,
  ]
duration: 10min
completed: 2026-08-11
---

# Phase 3 Plan 5: Audited Mapping Administration API Summary

**Typed administrator mapping lifecycle with non-mutating tests, optimistic version preconditions, safe conflicts, immutable actor attribution, and filter-bound audit history**

## Performance

- **Duration:** 10 min
- **Completed:** 2026-08-11
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added typed administrator routes for active mapping inspection, non-mutating testing, creation, update, deactivation, removal, and explicit reactivation.
- Required positive optimistic versions for every mapping update and state transition, with actor identity captured only from authenticated request state.
- Added stable HTTP 409 responses for missing, duplicate, overlapping, and stale mappings without exception strings, host paths, or unrelated mapping paths.
- Added newest-first audit listing with platform, mapping, and action filters delegated intact to the handler's filter-bound cursor.
- Added endpoint evidence for the complete anonymous, non-admin, admin, actor, version, conflict, and audit serialization matrix.

## Task Commits

1. **Task 1: RED mapping lifecycle and audit API matrix** - `367c904f3` (test)
2. **Task 2: GREEN typed lifecycle and audit endpoints** - `9a675d33a` (feat)

## Files Created/Modified

- `backend/endpoints/responses/storage.py` - Bounded mapping request, response, conflict, snapshot, and audit page schemas.
- `backend/endpoints/storage.py` - Thin authorized mapping lifecycle, test, conflict translation, and audit routes.
- `backend/tests/endpoints/test_storage.py` - Authorization, non-mutation delegation, actor/version, safe conflict, and audit filter contracts.

## Decisions Made

- Mapping tests reuse the create-shaped candidate schema but remain a distinct route that calls only the non-persisting handler operation.
- Removal remains a soft lifecycle transition with an explicit version body and returns the resulting inactive mapping state.
- Audit response snapshots expose only root ID, relative path, version, and active state, while actor output is limited to immutable ID and bounded display snapshot.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Contract] Updated the storage OpenAPI leak assertion for intentional mapping schemas**

- **Found during:** Task 2 full endpoint verification
- **Issue:** The Phase 3 read-only test rejected the word `mapping` anywhere in storage schemas, which became invalid once the planned mapping API was added.
- **Fix:** Kept all sensitive-field assertions and removed only the obsolete generic word rejection.
- **Files modified:** `backend/tests/endpoints/test_storage.py`
- **Verification:** The full endpoint and storage-handler suites pass.
- **Committed in:** `9a675d33a`

---

**Total deviations:** 1 auto-fixed (1 test contract correction).
**Impact on plan:** The correction permits the intended public contract while preserving every path and filesystem secrecy assertion.

## Issues Encountered

- The default container test command inherits a loopback database host. Verification used the existing isolated Phase 3 database through `romm-db-dev` with explicit test-only settings and `-c /dev/null`.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

| Flag                                     | File                         | Description                                                                                                                 |
| ---------------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| threat_flag: administrator-mapping-state | backend/endpoints/storage.py | New authenticated mutation routes capture actor identity, require optimistic versions, and expose bounded conflict details. |

## Next Phase Readiness

- Plan 03-06 can add non-mutating preview and regenerate the authoritative OpenAPI client types.
- No scanner or UI coupling was introduced.
- No blockers remain.

## Self-Check: PASSED

- All three modified files exist.
- RED commit `367c904f3` precedes GREEN commit `9a675d33a`.
- Endpoint and storage-handler suites pass: 66 tests, 0 failures.
- `git diff --check` is clean and unrelated untracked files remain untouched.

---

_Phase: 03-mapping-administration-contracts_
_Completed: 2026-08-11_
