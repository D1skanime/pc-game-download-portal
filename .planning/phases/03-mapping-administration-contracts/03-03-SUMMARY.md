---
phase: 03-mapping-administration-contracts
plan: 03
subsystem: database
tags:
  [sqlalchemy, transactions, optimistic-concurrency, audit, cursor-pagination]
requires:
  - phase: 03-01
    provides: Versioned active mapping rows and immutable audit schema
provides:
  - Transactional mapping create, test, update, deactivate, reactivate, and remove lifecycle
  - Active-only duplicate and canonical overlap enforcement under ordered locks
  - Atomic immutable actor and before/after audit snapshots
  - Filter-bound newest-first audit cursor pagination
affects: [03-04, 03-05, 03-06, phase-5]
tech-stack:
  added: []
  patterns:
    [
      ordered cross-dialect row locking,
      optimistic version preconditions,
      same-transaction audit append,
    ]
key-files:
  created: []
  modified:
    - backend/handler/database/storage_handler.py
    - backend/tests/handler/database/test_storage_handler.py
key-decisions:
  - "All lifecycle mutations acquire platform, active-root, and mapping locks in deterministic order before state changes."
  - "Create always inserts new history while reactivation requires an explicit inactive mapping ID and expected version."
requirements-completed:
  [MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-06, AUD-01, AUD-02]
duration: 22min
completed: 2026-08-10
---

# Phase 3 Plan 3: Transactional Mapping Lifecycle Summary

**Optimistically versioned mapping lifecycle with active-only conflicts, atomic immutable audits, and filter-bound cursor history across MariaDB and PostgreSQL**

## Performance

- **Duration:** 22 min
- **Completed:** 2026-08-10
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added separate non-mutating test and transactional create, read, update, deactivate, remove, and explicit reactivate services to `DBStorageHandler`.
- Enforced one active mapping per platform plus canonical equal and ancestor/descendant overlap rejection while inactive history releases both identities.
- Added integer expected-version checks under deterministic locks with typed stale conflicts and no retry or merge.
- Appended exactly one allowlisted audit snapshot in the mutation transaction and added newest-first, query-bound keyset pagination.
- Proved the focused 40-test handler/model suite ten times on both MariaDB and PostgreSQL through the migration verifier's real-dialect handler gate.

## Task Commits

1. **Task 1: RED lifecycle, concurrency, and atomic-audit matrix** - `da7d2f5fc` (test)
2. **Task 2: GREEN transactional lifecycle and audit query** - `09145e533` (feat)

## Files Created/Modified

- `backend/handler/database/storage_handler.py` - Ordered lifecycle locking, active-only validation, version preconditions, atomic audits, and cursor history.
- `backend/tests/handler/database/test_storage_handler.py` - Lifecycle, inactive-history, stale-version, rollback, actor snapshot, and cursor binding evidence.

## Decisions Made

- Every mutation serializes platform, active roots, and mappings in deterministic order before changing lifecycle state.
- Removal is a soft inactive transition with a distinct `remove` audit action; deactivation remains separately auditable.
- Audit cursors bind platform, mapping, and action filters to the descending `(created_at, id)` continuation key.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Correctness] Bound oversized and cross-filter audit cursors**

- **Found during:** Task 2
- **Issue:** A decoded cursor also needed a strict size ceiling and complete filter identity to remain bounded and non-replayable.
- **Fix:** Added a 2048-character ceiling plus versioned platform, mapping, and action binding.
- **Files modified:** `backend/handler/database/storage_handler.py`
- **Committed in:** `09145e533`

**2. [Rule 2 - Concurrency] Unified mutation lock order across lifecycle operations**

- **Found during:** Task 2 cross-dialect verification
- **Issue:** Locking only the addressed mapping before global roots could invert the established create order.
- **Fix:** Mutations now lock platform, ordered active roots, then ordered mapping rows before checking version or changing state.
- **Files modified:** `backend/handler/database/storage_handler.py`
- **Committed in:** `09145e533`

## Issues Encountered

- The plan's default container command inherits a loopback database host. Focused verification used isolated test databases through `romm-db-dev` and `-c /dev/null`.
- The migration verifier must run on the Linux host, not inside `romm-dev`, because it orchestrates temporary database containers through Docker.
- Expected fail-closed 0109 downgrade tracebacks are emitted during lifecycle-history verification while the verifier correctly exits successfully.

## User Setup Required

None.

## Known Stubs

None.

## Threat Flags

| Flag                                   | File                                        | Description                                                                                                                  |
| -------------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| threat_flag: transactional-admin-state | backend/handler/database/storage_handler.py | New mutation surface enforces optimistic versions, ordered locks, bounded conflicts, and same-transaction audit attribution. |

## Next Phase Readiness

- Plans 03-04 and 03-05 can expose root browsing and the complete mapping lifecycle without duplicating persistence rules.
- Plan 03-06 can reuse mapping test and active lookup for non-mutating preview and final OpenAPI evidence.

## Self-Check: PASSED

- Both modified files exist.
- RED commit `da7d2f5fc` precedes GREEN commit `09145e533`.
- Handler/model suite passes: 40 tests, 0 failures.
- MariaDB and PostgreSQL real-dialect handler gates pass ten repetitions each.
- `git diff --check` is clean and unrelated untracked files remain untouched.

---

_Phase: 03-mapping-administration-contracts_
_Completed: 2026-08-10_
