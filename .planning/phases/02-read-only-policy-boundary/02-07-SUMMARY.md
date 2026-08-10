---
phase: 02-read-only-policy-boundary
plan: 07
subsystem: filesystem-security
tags: [sync, watcher, cleanup, background-jobs, storage-policy]
requires:
  - phase: 02-03
    provides: trusted owned storage composition
  - phase: 02-04
    provides: composition-owned external read capabilities
provides:
  - Owned-only sync, SSH, watcher-output, platform-bootstrap, and cleanup gates
  - Terminal StoragePolicyDenied propagation across task and sync exception boundaries
  - Runnable pre-I/O denial evidence for sync and cleanup jobs
affects: [02-08, 02-09, storage-inventory]
tech-stack:
  added: []
  patterns:
    [
      authorize-before-io,
      terminal-domain-denial,
      trusted-provider-path-derivation,
    ]
key-files:
  created:
    - backend/tests/tasks/test_storage_policy.py
  modified:
    - backend/handler/filesystem/sync_handler.py
    - backend/handler/sync/ssh_handler.py
    - backend/watcher.py
    - backend/handler/filesystem/platforms_handler.py
    - backend/tasks/tasks.py
    - backend/tasks/scheduled/cleanup_orphaned_resources.py
    - backend/tasks/scheduled/cleanup_upload_tmp.py
    - backend/tasks/scheduled/cleanup_zip_cache.py
    - backend/tasks/sync_push_pull_task.py
    - backend/sync_watcher.py
key-decisions:
  - "Sync and SSH filesystem operations authorize the composition-owned SYNC descriptor before I/O."
  - "StoragePolicyDenied bypasses broad job and sync recovery handlers and remains terminal."
patterns-established:
  - "Cleanup tasks authorize their exact closed owned kind before database or filesystem work."
  - "Watcher path interpretation derives from the composition-owned external descriptor, never caller-selected storage identity."
requirements-completed: [ROOT-05, SAFE-02, SAFE-04, SAFE-06, TEST-03]
duration: 10min
completed: 2026-08-10
---

# Phase 2 Plan 7: Owned Sync and Terminal Job Denial Summary

**Sync, SSH, watcher, platform bootstrap, and cleanup flows now authorize trusted storage before I/O while policy denials escape background workflows without partial success**

## Performance

- **Duration:** 10 min
- **Started:** 2026-08-10T09:47:00Z
- **Completed:** 2026-08-10T09:57:00Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Bound sync handler reads and mutations plus SSH key/temp operations to the trusted SYNC descriptor.
- Rejected external platform bootstrap before filesystem access and based watcher path derivation on the immutable external descriptor.
- Authorized resource, upload-temp, and ZIP-cache cleanup against their exact closed owned kinds.
- Made StoragePolicyDenied terminal across job metadata, sync watcher, connection, per-file, and outer sync recovery boundaries.
- Added pre-I/O denial tests and retained focused sync fixture coverage.

## Task Commits

1. **Task 1 RED: Specify owned sync operations** - `9a33361d8`
2. **Task 1 GREEN: Bind sync outputs to owned storage** - `1d78b014b`
3. **Task 1 fixture follow-up** - `9818eab36`
4. **Task 2 RED: Specify terminal job policy denials** - `c26e7ba7c`
5. **Task 2 GREEN: Make background policy denial terminal** - `162c5c655`

## Files Created/Modified

- `backend/handler/filesystem/sync_handler.py` - Exact owned authorization for sync list, hash, directory, write, and delete operations.
- `backend/handler/sync/ssh_handler.py` - Trusted SYNC descriptor construction and owned authorization for keys and temporary downloads.
- `backend/watcher.py` - External watcher paths derived from the composition-owned descriptor.
- `backend/handler/filesystem/platforms_handler.py` - External bootstrap mutation denial before mkdir.
- `backend/tasks/scheduled/cleanup_*.py` - Closed owned-kind cleanup authorization.
- `backend/tasks/tasks.py`, `backend/tasks/sync_push_pull_task.py`, `backend/sync_watcher.py` - Terminal denial propagation.
- `backend/tests/tasks/test_storage_policy.py` - Cleanup and job denial matrix.
- `backend/tests/handler/filesystem/test_sync_handler.py`, `backend/tests/test_sync_watcher.py` - Owned descriptor fixtures and sync operation evidence.

## Decisions Made

- Used the existing closed owned descriptors rather than accepting raw destination roots or adding compatibility fallbacks.
- Preserved ordinary operational error handling while carving out StoragePolicyDenied as an immediate terminal channel.
- Kept mapping-aware watcher lookup deferred to Phase 5 while removing LIBRARY_BASE_PATH as the path-interpretation authority.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bound constructor-bypassing sync test fixtures**

- **Found during:** Task 1 GREEN verification
- **Issue:** Legacy focused fixtures used `__new__` and therefore lacked the newly required trusted storage descriptor.
- **Fix:** Injected the existing composition-owned SYNC descriptor into those fixtures.
- **Files modified:** `backend/tests/handler/filesystem/test_sync_handler.py`, `backend/tests/test_sync_watcher.py`
- **Verification:** Sync, watcher, and platform suite passes 61 tests.
- **Committed in:** `9818eab36`, `1d78b014b`

**Total deviations:** 1 auto-fixed (1 blocking issue). **Impact:** Test construction now matches the production authority contract without product scope expansion.

## Issues Encountered

- Host uv and node are unavailable. Backend verification ran in disposable containers against the canonical bind-mounted checkout and isolated MariaDB test schema.
- The existing development container cannot reach the separate test database at pytest's loopback address, so database-backed suites used a disposable test process sharing the database container network.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. The pre-existing watcher bulk-query TODO is unrelated to this plan and does not block the storage-policy contract.

## Threat Flags

None. Changes mitigate the plan's declared destination-confusion and fallback-success threats and add no new network, authentication, schema, or trust-boundary surface.

## Verification

- Task 1 plan gate: 61 passed.
- Task 2 plan gate: 41 passed.
- Combined storage-policy regression: 369 passed, 1 Alembic configuration warning.
- Python compilation passed for all modified backend modules.
- Commit hooks formatted and checked every staged task file without bypass.

## Next Phase Readiness

- Plan 02-08 can inventory the now-governed sync, watcher, cleanup, and background task seams.
- No blockers remain.

## Self-Check: PASSED

- All created and modified key files exist in the canonical Linux checkout.
- All five plan task commits exist on `codex/pc-module-analysis`.
- Both RED commits precede their corresponding GREEN commits.
- No tracked file deletions or unintended untracked files were introduced.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-10_
