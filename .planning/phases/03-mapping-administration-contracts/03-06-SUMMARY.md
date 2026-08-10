---
phase: 03-mapping-administration-contracts
plan: 06
subsystem: api
tags: [fastapi, openapi, preview, pagination, generated-types]
requires:
  - phase: 03-05
    provides: Authorized audited mapping lifecycle API
provides:
  - Bounded non-mutating active-mapping preview with opaque continuation
  - Deterministic OpenAPI safety assertions for every storage administration route
  - Generated TypeScript storage contract models
affects: [phase-4, phase-5, phase-7]
tech-stack:
  added: []
  patterns: [bounded-top-k-preview, query-bound-cursor, generated-contract]
key-files:
  created:
    - frontend/src/__generated__/models/StorageMappingPreviewSchema.ts
  modified:
    - backend/endpoints/responses/storage.py
    - backend/endpoints/storage.py
    - backend/tests/endpoints/test_storage.py
    - frontend/src/__generated__/index.ts
key-decisions:
  - "Preview enumerates one mapped directory with bounded top-k retention and never returns candidate names or paths."
  - "Preview cursors bind mapping identity, version, relative path, and the last visible binary name key."
requirements-completed:
  [MAP-03, MAP-06, API-01, API-02, API-03, API-04, AUD-02, TEST-02]
duration: 45min
completed: 2026-08-11
---

# Phase 3 Plan 6: Preview and Generated Contract Summary

**Administrator-only mapping preview with bounded deterministic enumeration, safe typed output, and generated OpenAPI client models**

## Performance

- **Duration:** 45 min
- **Completed:** 2026-08-11
- **Tasks:** 3
- **Files modified:** 24

## Accomplishments

- Added an administrator-only preview route that requires an explicit active mapping and returns a typed HTTP 409 when none exists.
- Implemented deterministic immediate-entry enumeration with O(limit) retention, a 10,000-entry hard ceiling, mapping-bound cursors, and no candidate names or paths.
- Proved preview authorization, missing-mapping behavior, pagination, hard limits, allowlisted output, and non-mutation.
- Asserted all public storage routes and response models in OpenAPI while rejecting deployment paths, raw errors, and candidate details.
- Regenerated the authoritative TypeScript contract with an isolated Uvicorn process and task-owned Node volume, then passed Node 24 typecheck.
- Passed the 144-test focused Phase 3 suite, three-dialect migration cycles, and ten handler/concurrency repetitions on both MariaDB and PostgreSQL.

## Task Commits

1. **Task 1 RED: bounded preview contract** - `a1c9fd516` (test)
2. **Task 1 GREEN: non-mutating preview** - `31395485b` (feat)
3. **Task 2: generated storage API contracts** - `9a270f7cb` (chore)
4. **Post-verification: authoritative generated-contract formatting** - `f3f51a8e2` (style)

## Files Created/Modified

- `backend/endpoints/responses/storage.py` - Fixed preview response allowlist.
- `backend/endpoints/storage.py` - Active-mapping preview, bounded enumeration, and opaque continuation.
- `backend/tests/endpoints/test_storage.py` - Preview and deterministic OpenAPI contract evidence.
- `frontend/src/__generated__/` - Generated TypeScript storage administration models.

## Decisions Made

- Preview counts only the bounded visible candidate page while reporting the number of directory entries examined to establish that page.
- Cursor replay after a mapping version or path change fails safely instead of redirecting the request.
- Scanner jobs, catalog persistence, and legacy path derivation remain outside this administration-only preview contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Environment] Isolated endpoint tests from the shared loopback database**

- **Found during:** Task 1 RED verification
- **Issue:** The container test configuration forced database host `127.0.0.1`, while the database is reachable as `romm-db-dev`; a concurrently reused database also contained partial migration state.
- **Fix:** Used a task-owned temporary pytest configuration and the isolated `romm_test_0306` database.
- **Files modified:** None.

**2. [Rule 3 - Blocking Environment] Raised Node heap only for generated-contract typecheck**

- **Found during:** Task 2 generated contract gate
- **Issue:** Vue typecheck exhausted Node's default 2 GB heap after generation.
- **Fix:** Repeated typecheck in a task-owned volume with `NODE_OPTIONS=--max-old-space-size=4096`.
- **Files modified:** None.

## Deferred Issues

- The full backend repository gate reported 2,979 passes and 10 skips, then failed with 16 failures and 124 setup errors in the pre-existing Nginx cache-header environment. No Phase 3 storage test failed.
- The official Trunk 1.25.0 `check --all` gate reported repository-wide pre-existing debt: 2,883 lint issues, 22 security issues, and 20 unformatted files. The command left the Phase 3 working tree unchanged.

## Known Stubs

None.

## Threat Flags

| Flag                                    | File                         | Description                                                                                                         |
| --------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| threat_flag: bounded-filesystem-preview | backend/endpoints/storage.py | New administrator file enumeration is mapping-bound, path-safe, bounded, non-mutating, and emits no entry identity. |

## Verification Evidence

- Preview selection: 6 passed, 0 failed.
- Focused Phase 3 suite: 144 passed, 0 failed, 0 skipped.
- OpenAPI generation: isolated Uvicorn on container loopback port 39003, exact PID cleanup confirmed.
- Frontend: Node 24 generated models and `vue-tsc --noEmit` passed.
- Migration verifier: MariaDB, MySQL, and PostgreSQL upgrade/downgrade/re-upgrade passed with lifecycle-history downgrade rejection.
- Handler verifier: 10 repetitions each on MariaDB and PostgreSQL passed.
- Source and Git safety: `git diff --check` passed; unrelated untracked files remained untouched.
- Post-verification formatting: repository-pinned Prettier 3.9.5 removed generator EOF whitespace from the 17 reported models; `git diff --check fd7f5a709..HEAD`, Node 24 typecheck, and the OpenAPI endpoint test passed.

## Self-Check: PASSED

- All modified and generated contract files exist.
- RED commit `a1c9fd516` precedes GREEN commit `31395485b`.
- Generated-contract commit `9a270f7cb` exists.
- Generated formatting commit `f3f51a8e2` exists.
- Task-owned PID files, logs, and Docker volumes were removed.
- Team4s services and host/container port 3000 were not inspected, modified, restarted, or stopped.

---

_Phase: 03-mapping-administration-contracts_
_Completed: 2026-08-11_
