---
phase: 01-immutable-storage-foundation
plan: 04
subsystem: database
tags: [sqlalchemy, mariadb, row-locking, immutable-storage, concurrency]
requires:
  - phase: 01-immutable-storage-foundation
    provides: Storage schema, bounded errors, and canonical resolver from plans 01-01 through 01-03
provides:
  - Existing-root-only immutable storage registration
  - Atomic canonical non-overlapping platform mapping persistence
  - Deterministic active-root serialization for initially empty concurrent inserts
affects: [01-05, mapping-administration, storage-policy, platform-mapping]
tech-stack:
  added: []
  patterns: [ordered active-root row locks, locking current-read recheck, bounded collision translation]
key-files:
  created:
    - backend/handler/database/storage_handler.py
    - backend/tests/handler/database/test_storage_handler.py
  modified:
    - backend/handler/database/__init__.py
    - backend/exceptions/storage_exceptions.py
key-decisions:
  - "Serialize mapping persistence by locking every active StorageRoot in ascending ID order before canonical comparison."
  - "Use a locking mapping read after the root lock so transactions begun before the winner committed observe the winning insert under repeatable-read isolation."
patterns-established:
  - "Root registration forces external_read_only and persists only after non-mutating health inspection succeeds."
  - "Canonical equality and either-direction ancestry are rejected across all active mappings regardless of root identity."
requirements-completed: [ROOT-01]
duration: 10min
completed: 2026-08-04
---

# Phase 1 Plan 4: Atomic Root Registration and Mapping Persistence Summary

**Health-gated immutable root registration and deterministic cross-root mapping serialization with a current-read race recheck**

## Performance

- **Duration:** 10 min
- **Started:** 2026-08-04T21:13:47Z
- **Completed:** 2026-08-04T21:23:22Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Registers only existing absolute directories after metadata-only health inspection, while forcing the immutable storage mode.
- Locks all active roots in ascending identity order before resolving and comparing every active mapping's canonical target.
- Rejects equal, ancestor, and descendant targets within one root and across distinct or nested roots without confusing textual prefixes.
- Proves with two coordinated MariaDB sessions that initially empty conflicting first inserts yield exactly one commit and one bounded overlap failure.

## Task Commits

1. **Task 1: Storage persistence and race specifications** - `037c915e7` (test)
2. **Task 2: Immutable registration and serialized mapping persistence** - `c92de0cba` (feat)

## Files Created/Modified

- `backend/handler/database/storage_handler.py` - Health-gated registration and atomic mapping persistence.
- `backend/tests/handler/database/test_storage_handler.py` - Registration, overlap, rollback, lock-order, uniqueness, and concurrency evidence.
- `backend/handler/database/__init__.py` - Storage handler singleton registration.
- `backend/exceptions/storage_exceptions.py` - Bounded overlap and duplicate mapping errors.

## Decisions Made

- All active root rows form the portable shared serialization set, locked in ascending ID order.
- Mapping reads use `FOR UPDATE` after the root lock to obtain a current read under MariaDB repeatable-read isolation.
- Database uniqueness constraints remain race backstops and are translated to bounded storage-domain errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Forced a current mapping read after root-lock acquisition**
- **Found during:** Task 2 concurrent first-insert verification
- **Issue:** A transaction begun before the winning commit retained an empty consistent-read snapshot and could commit a conflicting mapping after waiting for root locks.
- **Fix:** Made the post-lock mapping load a locking current read and retained the immediate pre-flush recheck.
- **Files modified:** `backend/handler/database/storage_handler.py`
- **Verification:** Coordinated two-session test produces exactly one commit and one bounded overlap result.
- **Committed in:** `c92de0cba`

**2. [Rule 2 - Missing Critical] Added bounded persistence collision errors**
- **Found during:** Task 2 integrity backstop implementation
- **Issue:** Raw database integrity failures would leak through the storage persistence boundary.
- **Fix:** Added bounded overlap and duplicate mapping domain errors and translated flush-time integrity collisions.
- **Files modified:** `backend/exceptions/storage_exceptions.py`, `backend/handler/database/storage_handler.py`
- **Verification:** Handler uniqueness and overlap tests pass.
- **Committed in:** `c92de0cba`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both changes are required to satisfy the locked fail-closed concurrency and bounded-error contract.

## Issues Encountered

- The development container's pytest configuration points at loopback, so verification temporarily targeted the isolated `romm_test` database by container DNS and restored the configuration immediately afterward.
- The storage model suite intentionally drops its module-scoped storage tables, so handler/resolver verification ran before the model suite against a freshly recreated isolated test database.
- Trunk and repository Ruff were unavailable. Ruff was run ephemerally with `uvx` inside the existing development container, without restarting any service.

## User Setup Required

None. No external service configuration is required.

## Known Stubs

None.

## Threat Flags

None. The handler adds no API endpoint, consumer cutover, external write path, or schema trust boundary beyond the plan's threat model.

## Next Phase Readiness

- Plan 01-05 can exercise the persistence and resolver matrix across supported database dialects.
- No scanner, watcher, download, API, frontend, or real NAS workflow has been activated.

## Self-Check: PASSED

- All four created or modified implementation files exist.
- Task commits `037c915e7` and `c92de0cba` exist.
- Handler plus resolver verification passes 55 tests; storage model verification passes 8 tests.
- Ruff formatting and static checks pass for all changed Python files.

---
*Phase: 01-immutable-storage-foundation*
*Completed: 2026-08-04*

