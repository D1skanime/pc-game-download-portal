---
phase: 01-immutable-storage-foundation
plan: 07
subsystem: database
tags: [sqlalchemy, postgresql, mariadb, mysql, integrity-errors]
requires:
  - phase: 01-immutable-storage-foundation
    provides: Portable mapping persistence with named uniqueness classification
provides:
  - PostgreSQL structured constraint classification for both approved mapping constraints
  - MariaDB/MySQL duplicate classification gated by errno 1062 and approved key names
  - Bounded persistence failures for non-1062 and unknown DBAPI diagnostic shapes
affects: [phase-02-storage-policy, mapping-administration, storage-persistence]
tech-stack:
  added: []
  patterns:
    [
      structured PostgreSQL diagnostics,
      errno-gated vendor diagnostics,
      fail-closed persistence translation,
    ]
key-files:
  created: []
  modified:
    - backend/handler/database/storage_handler.py
    - backend/tests/handler/database/test_storage_handler.py
key-decisions:
  - "Treat raw MariaDB/MySQL key names as duplicate evidence only when DBAPI errno is 1062."
patterns-established:
  - "Vendor diagnostic classification: prefer PostgreSQL constraint_name, otherwise require errno 1062 before allowlisted key matching."
requirements-completed: [ROOT-01, ROOT-04, TEST-01]
duration: 6min
completed: 2026-08-05
---

# Phase 1 Plan 7: Vendor-gated Duplicate Classification Summary

**PostgreSQL constraint diagnostics preserved with errno-1062-gated MariaDB/MySQL duplicate classification and fail-closed bounded errors**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-05T20:07:33Z
- **Completed:** 2026-08-05T20:13:06Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Preserved authoritative PostgreSQL `diag.constraint_name` matching for both approved mapping uniqueness constraints.
- Required MariaDB/MySQL DBAPI `errno == 1062` before matching either approved raw key name.
- Added positive and adversarial diagnostic coverage, including save-path assertions for exact bounded `StoragePersistenceError` output.

## Task Commits

1. **Task 1: Specify truthful vendor diagnostics** - `c1012dc3d` (test)
2. **Task 2: Gate raw key matching on errno 1062** - `8cee9f978` (fix)

## Files Created/Modified

- `backend/tests/handler/database/test_storage_handler.py` - Positive PostgreSQL and errno-1062 cases plus non-1062 and missing-errno negative save paths.
- `backend/handler/database/storage_handler.py` - Defensive errno gate before raw approved-key matching.

## Decisions Made

- Raw MariaDB/MySQL key text is insufficient duplicate evidence without DBAPI errno 1062.
- A present PostgreSQL structured constraint name remains authoritative and never falls through to raw text matching.

## Verification Evidence

- Focused RED gate failed on a non-1062 diagnostic mentioning an approved key.
- Focused GREEN gate: 14 passed, 11 deselected.
- Scoped regression suite: 79 passed across storage handler, storage models, and storage resolver tests.
- Scoped Trunk format and check passed for both plan-owned files.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The host does not expose `uv`, so verification ran inside the existing `romm-dev` development container against isolated test databases. No container or service was restarted or reconfigured.

## Known Stubs

None.

## Threat Flags

None. No network endpoint, authentication path, filesystem access, schema, service, Team4s, or NAS surface changed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The final Phase 1 failed truth is closed and ready for phase verification.
- Phase 2 can rely on bounded vendor-specific mapping persistence errors.

## Self-Check: PASSED

- Both modified files exist.
- Task commits `c1012dc3d` and `8cee9f978` exist.
- Focused tests, scoped regression tests, and scoped Trunk checks pass.

---

_Phase: 01-immutable-storage-foundation_
_Completed: 2026-08-05_
