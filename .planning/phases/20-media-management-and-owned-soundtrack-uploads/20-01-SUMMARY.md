---
phase: 20-media-management-and-owned-soundtrack-uploads
plan: "01"
subsystem: database
tags: [sqlalchemy, alembic, owned-media, cleanup, optimistic-locking]
requires:
  - phase: 01-immutable-storage-foundation
    provides: owned-resource storage boundary
provides:
  - parent-ROM owned-media candidates, tombstones, and ordered placements
  - durable owned-resource cleanup intents
affects: [20-02, media-api, v2-media-management]
tech-stack:
  added: []
  patterns:
    [locked parent-ROM media mutations, complete-list placement replacement]
key-files:
  created:
    - backend/models/owned_media_cleanup.py
    - backend/alembic/versions/0122_parent_rom_owned_media.py
  modified:
    - backend/models/rom.py
    - backend/handler/database/roms_handler.py
    - backend/endpoints/responses/rom.py
key-decisions:
  - "Use revision 0127_parent_rom_owned_media because 0126 is the current Alembic head, while retaining the planned filename."
  - "Provider deletions tombstone the candidate and clear its owned path; uploads are removed after committed path handoff."
patterns-established:
  - "Only exact generated relative owned-resource paths enter cleanup intents."
  - "Reorder accepts the full existing membership only and replaces all positions atomically."
requirements-completed:
  [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07]
duration: 10min
completed: 2026-09-28
---

# Phase 20 Plan 01: Parent-ROM Owned Media Catalog Summary

**Parent-ROM owned-media candidates, provider tombstones, ordered placements, and bounded cleanup intents with no external-library path representation.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-09-28T13:40:00Z
- **Completed:** 2026-09-28T13:48:00Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- Added portable SQLAlchemy and Alembic contracts for provider/upload candidates and independent overview, background, and soundtrack placements.
- Added locked expected-version catalog mutations, provider tombstones, complete-list reorder validation, and durable cleanup intent lifecycle helpers.
- Added focused persistence tests for candidate-placement separation, path-only cleanup intents, tombstone reactivation, and incomplete reorder rejection.

## Task Commits

1. **Task 1: Define portable parent-ROM media and placement contracts** - `e257db39c` (feat)
2. **Task 2: Implement locked catalog mutation and ordering invariants** - `8a401cc46` (feat)

## Files Created/Modified

- `backend/models/rom.py` - Parent-ROM candidate and placement models.
- `backend/models/owned_media_cleanup.py` - Bounded resource cleanup intents.
- `backend/alembic/versions/0122_parent_rom_owned_media.py` - Reversible portable schema migration.
- `backend/endpoints/responses/rom.py` - Detail and mutation response contracts.
- `backend/handler/database/roms_handler.py` - Transactional catalog mutations and cleanup transitions.
- `backend/tests/handler/database/test_rom_media.py` - Focused contract tests.

## Decisions Made

- The planned migration filename remains `0122_parent_rom_owned_media.py`, but its Alembic revision is `0127_parent_rom_owned_media` because the repository already has a distinct 0122 revision and current head is 0126.
- Only a generated relative owned path is accepted by catalog and cleanup methods. Absolute paths and traversal markers are rejected before persistence.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Advanced the Alembic revision identifier to the actual repository head.**

- **Found during:** Task 1
- **Issue:** `0122_download_archive_sets` already owns the 0122 revision identifier and current head is 0126.
- **Fix:** Created the planned filename with revision `0127_parent_rom_owned_media` and `down_revision = 0126_add_steam_metadata`.
- **Verification:** `alembic heads` resolves the new revision as the single head.
- **Committed in:** `e257db39c`

**Total deviations:** 1 auto-fixed (Rule 3)

## Issues Encountered

- The configured MariaDB test server at `127.0.0.1:3306` is unreachable, so the focused pytest suite and migration upgrade/downgrade cycle could not run. The suite collects all four tests before database setup, and static imports, `alembic heads`, `trunk fmt`, and scoped `trunk check` pass.

## Known Stubs

None.

## Next Phase Readiness

Plan 20-02 can add discovery, upload, protected routes, and the scheduled cleanup consumer against these contracts. Re-run the focused database suite and migration cycle when the MariaDB verifier is available.

## Self-Check: PASSED

- All six implementation/test files exist.
- Task commits `e257db39c` and `8a401cc46` exist.
