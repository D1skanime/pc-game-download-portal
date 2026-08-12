---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "07"
subsystem: legacy-migration-first-use
tags: [migration, storage, lifecycle, concurrency, tdd]
requires:
  - phase: 06-06
    provides: atomic legacy migration and durable mapping lineage
provides:
  - productive-use marker committed before legacy source access
  - bounded provenance and exact-revision revalidation
  - idempotent concurrent first-use CAS
affects: [06-08, 06-09, legacy-retirement]
tech-stack:
  added: []
  patterns: [lock-backed first-use CAS, validate-mark-revalidate-open]
key-files:
  created:
    - backend/tests/integration/__init__.py
    - backend/tests/integration/test_legacy_migration.py
  modified:
    - backend/handler/database/legacy_migration_handler.py
    - backend/handler/storage/read_context.py
    - backend/handler/scan_handler.py
    - backend/endpoints/roms/__init__.py
    - backend/endpoints/roms/files.py
key-decisions:
  - Productive operations persist only scan, hash, stream, play, or download.
  - First use is marked under row locks before descriptor creation and source access.
  - The exact active mapping revision is revalidated after marking.
requirements-completed: [MIG-04]
duration: 17min
completed: 2026-08-12
---

# Phase 6 Plan 7: Productive First-Use CAS Summary

Productive legacy-backed reads durably mark bounded first-use provenance before source access, with exact-revision revalidation and concurrent idempotence.

## Performance

- **Duration:** 17 min
- **Started:** 2026-08-12T23:13:01Z
- **Completed:** 2026-08-12T23:30:04Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Covered scan, hash, stream, play, download, and multifile member access at the shared mapped-read boundary.
- Implemented immutable, lock-backed first-use marking that is safe under concurrent callers.
- Enforced validate, mark, exact-revision revalidate, then open ordering.
- Preserved source immutability across productive operations.

## Task Commits

1. **Task 1: Specify productive first-use behavior with failing integration tests** - `6d57b2df2` (test)
2. **Task 2: Implement productive first-use CAS** - `3b4dfa9be` (feat)
3. **Task 2 deviation: Isolate integration test collection** - `9d2de1f52` (fix)

## Files Created/Modified

- `backend/tests/integration/test_legacy_migration.py` - Ordering, provenance, concurrency, stale revision, and immutability contract.
- `backend/tests/integration/__init__.py` - Unique package-qualified integration test namespace.
- `backend/handler/database/legacy_migration_handler.py` - Lock-backed marker and revision guard.
- `backend/handler/storage/read_context.py` - Shared productive-use ordering and operation normalization.
- `backend/handler/scan_handler.py` - Explicit scan provenance.
- `backend/endpoints/roms/__init__.py` - Play and multifile download provenance.
- `backend/endpoints/roms/files.py` - Download preflight provenance.

## Decisions Made

- Persist only the bounded vocabulary: scan, hash, stream, play, and download.
- Mark before descriptor creation and source open, then revalidate the active mapping revision.
- Preserve the original marker and increment lifecycle version only once.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Isolated the integration test namespace**

- **Found during:** Task 2 combined verification
- **Issue:** The new integration test and an existing handler test had the same top-level module basename, causing pytest collection mismatch.
- **Fix:** Added `backend/tests/integration/__init__.py`.
- **Files modified:** `backend/tests/integration/__init__.py`
- **Commit:** `9d2de1f52`

## Issues Encountered

Initial commands with invalid database grants or incomplete explicit environment were corrected and were not counted as RED evidence. The valid isolated MariaDB RED run failed because `first_used_at` remained null at the source-open seam.

## Verification

- Valid TDD RED observed before implementation.
- Focused integration suite: 10 passed.
- Final affected backend suite: 169 passed, 7 skipped.
- Git diff whitespace check passed.
- RED commit precedes GREEN commit.

## Known Stubs

None.

## Threat Review

No unmodeled security surface was introduced. Plan threats cover lifecycle CAS integrity, bounded provenance, exact-revision validation, and source immutability.

## Self-Check: PASSED

All seven files and task commits `6d57b2df2`, `3b4dfa9be`, and `9d2de1f52` exist, and the final affected suite passed.
