---
phase: 02-read-only-policy-boundary
plan: 09
subsystem: filesystem-security
tags: [docker-compose, read-only-mount, tripwire, policy-verification, pytest]
requires:
  - phase: 02-08
    provides: closed storage enforcement inventory
provides:
  - Dual-mount writable and read-only policy parity verifier
  - Deployment example with external-only read-only mount separation
  - Final D-10 HTTP, D-11 terminal workflow, and D-15 inventory regression gate
affects: [phase-03, phase-verification, deployment]
tech-stack:
  added: []
  patterns:
    [same-tree dual-mount evidence, pre-io tripwires, separate-owned-output]
key-files:
  created:
    [
      backend/docker-compose.policy-test.yml,
      backend/tools/verify_read_only_policy.py,
    ]
  modified:
    [
      examples/docker-compose.example.yml,
      backend/endpoints/heartbeat.py,
      backend/endpoints/roms/__init__.py,
      backend/tests/endpoints/test_heartbeat.py,
      backend/tests/endpoints/roms/test_rom.py,
    ]
key-decisions:
  - "Use fixed unsaved external identities in the mount verifier so policy parity is proved without health resolution."
  - "Database-only ROM deletion remains available because it does not request filesystem mutation authority."
patterns-established:
  - "One source fixture runs through writable and read-only mounts with identical typed outcomes and byte-level manifests."
requirements-completed:
  [ROOT-05, SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, SAFE-06, TEST-03]
duration: 27min
completed: 2026-08-10
---

# Phase 2 Plan 9: Dual-Mount Policy Verification Summary

**Writable and read-only mounts now produce identical bounded pre-I/O denials while owned output remains writable and deployment mounts the external library read-only**

## Performance

- **Duration:** 27 min
- **Started:** 2026-08-10T10:24:21Z
- **Completed:** 2026-08-10T10:50:48Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added a deterministic Compose verifier that mounts one archive fixture writable and read-only, runs the complete mutation and unknown-operation matrix, and compares typed outcomes and recursive manifests.
- Proved all denial tripwires remain untouched while separately mounted owned output accepts writes in both modes.
- Updated the deployment example so only the external library is mounted `:ro`, with every owned store separate.
- Closed final-gate regressions for bounded setup-bootstrap HTTP 403 translation and database-only ROM deletion.

## Task Commits

1. **Task 1 RED: Specify dual-mount policy parity** - `3b99af730`
2. **Task 1 GREEN: Prove dual-mount policy parity** - `1c1b41ed6`
3. **Task 2: Close final policy regression gate** - `43eb0c6fc`

## Files Created/Modified

- `backend/tools/verify_read_only_policy.py` - Dual-mode runner, fixed identity matrix, I/O tripwires, recursive manifests, and owned-output assertion.
- `backend/docker-compose.policy-test.yml` - Same source tree mounted writable and read-only with separate writable output.
- `examples/docker-compose.example.yml` - External library bind mount marked read-only.
- `backend/endpoints/heartbeat.py` - Converts external bootstrap policy denial to bounded HTTP 403.
- `backend/endpoints/roms/__init__.py` - Requests external delete authority only for filesystem deletion and narrows capability types.
- `backend/tests/endpoints/test_heartbeat.py` - Setup denial channel regression.
- `backend/tests/endpoints/roms/test_rom.py` - Database-only and denied filesystem deletion regressions.

## Decisions Made

- Fixed, unsaved root and mapping identities isolate pure authorization from database and health resolution behavior.
- Manifests compare metadata and content while excluding access time, which may vary by mount implementation.
- Database catalog deletion does not require external filesystem delete authority unless `delete_from_fs` is non-empty.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Translated setup bootstrap denial through the HTTP channel**

- **Found during:** Task 2 full Phase 2 regression
- **Issue:** `StoragePolicyDenied` from setup platform bootstrap was caught broadly and returned HTTP 500.
- **Fix:** Added bounded HTTP 403 translation with code, operation, storage class, and logical identity.
- **Files modified:** `backend/endpoints/heartbeat.py`, `backend/tests/endpoints/test_heartbeat.py`
- **Verification:** Heartbeat suite passes 15 tests and the full Phase 2 gate passes.
- **Committed in:** `43eb0c6fc`

**2. [Rule 1 - Bug] Kept database-only deletion outside filesystem authorization**

- **Found during:** Task 2 full Phase 2 regression
- **Issue:** The ROM delete route requested external DELETE authority when `delete_from_fs` was empty.
- **Fix:** Made authorization conditional on a filesystem deletion request and retained pre-I/O denial for actual filesystem mutation.
- **Files modified:** `backend/endpoints/roms/__init__.py`, `backend/tests/endpoints/roms/test_rom.py`
- **Verification:** ROM, HTTP denial, and inventory suites pass 107 tests; the full Phase 2 gate passes.
- **Committed in:** `43eb0c6fc`

**3. [Rule 3 - Blocking] Used the canonical repository image for backend verification**

- **Found during:** Task 2 verification
- **Issue:** The Linux host has no `uv`, and pytest expects MariaDB and Redis on loopback.
- **Fix:** Ran the exact suite in `romm-romm-dev` sharing the MariaDB namespace with a temporary Redis sidecar.
- **Files modified:** None
- **Verification:** 858 passed, 8 skipped, with one existing Alembic warning.
- **Committed in:** Not applicable, environment-only deviation.

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking issue). **Impact:** The final gate closed channel and authorization-scope regressions without expanding product scope.

## Issues Encountered

- Repository-wide `trunk check` includes the preserved unrelated untracked `.codex/` tree and reports its existing Markdown and ESLint configuration issues. Trunk formatting and all checks pass for every file changed by this plan, and commit hooks pass without bypass.
- The first container invocation used the image entrypoint instead of pytest; overriding the entrypoint produced the authoritative result.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. The verifier and deployment separation mitigate mount reliance, destination confusion, fallback success, and inventory-gap threats without adding runtime trust boundaries.

## Verification

- Exact Phase 2 suite: 858 passed, 8 skipped, 1 existing Alembic warning.
- Dual-mount verifier: PASS for identical typed denials, absent I/O calls, unchanged manifests, and writable owned output.
- Dedicated D-10/D-15 regression set: 122 passed.
- Final inventory rerun: 6 passed.
- Trunk checks on all seven changed files: no issues.
- Repository commit hooks passed without bypass.
- `git diff --check`: passed.

## Next Phase Readiness

- Phase 2 is complete and ready for conversational verification.
- Phase 3 can build mapping administration contracts on the closed read-only policy boundary.

## Self-Check: PASSED

- Both created files and all five modified key files exist.
- Task commits `3b99af730`, `1c1b41ed6`, and `43eb0c6fc` exist on `codex/pc-module-analysis`.
- TDD RED precedes GREEN, the exact regression suite passes, and no tracked files were deleted.
- Preserved unrelated untracked files remain untouched.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-10_
