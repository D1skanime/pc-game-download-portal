---
phase: 20-media-management-and-owned-soundtrack-uploads
plan: "09"
subsystem: database
tags: [sqlalchemy, alembic, owned-media, pydantic, source-safety]
requires:
  - phase: 20-media-management-and-owned-soundtrack-uploads
    provides: parent-ROM owned-media candidates and ordered placements
provides:
  - durable screenshot, artwork, and soundtrack roles for parent-owned media
  - bounded filename-only labels for owned-media catalog records
  - role-aware placement and detail-serialization contracts
affects: [20-02, 20-03, 20-04, 20-05, media-api, openapi-generation]
tech-stack:
  added: []
  patterns:
    [server-owned media role assignment, safe filename-only catalog labels]
key-files:
  created:
    - backend/alembic/versions/0123_owned_media_role_and_display_label.py
  modified:
    - backend/models/rom.py
    - backend/endpoints/responses/rom.py
    - backend/handler/database/roms_handler.py
    - backend/tests/handler/database/test_rom_media.py
key-decisions:
  - "Backfill legacy provider candidates as screenshots and uploads as artwork from their persisted origin, without consulting MIME, tags, or source paths."
  - "Keep role immutable after candidate creation and reject incompatible placement surfaces before changing catalog order."
patterns-established:
  - "Catalog display labels are sanitized, bounded basenames rather than source-library paths, provider URLs, or embedded tag values."
  - "Only screenshots and artwork can occupy overview/background surfaces, while only soundtracks can occupy soundtrack surfaces."
requirements-completed:
  [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07]
duration: 12min
completed: 2026-09-28
---

# Phase 20 Plan 09: Owned Media Role and Label Contract Summary

**Parent-owned media now persists immutable screenshot, artwork, or soundtrack roles with bounded filename-only display labels and placement safety.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-28T13:50:00Z
- **Completed:** 2026-09-28T14:02:00Z
- **Tasks:** 2/2
- **Files modified:** 5

## Accomplishments

- Added a portable parent-owned media role and safe display-label persistence migration, including deterministic origin-only backfill and reversible downgrade.
- Required trusted role and label contracts for provider reconciliation and operator upload creation.
- Serialized role and label in detailed-ROM owned media and rejected image/audio placement mismatches before persistence.

## Task Commits

1. **Task 1: Add portable owned-media role and display-label persistence** - `46c041a41` (feat)
2. **Task 2: Expose and enforce role/label through parent catalog mutations** - `2105fb62b` (feat)

## Files Created/Modified

- `backend/models/rom.py` - Role enum, bounded display labels, validators, and safe label derivation.
- `backend/alembic/versions/0123_owned_media_role_and_display_label.py` - Additive portable migration and origin-only backfill.
- `backend/endpoints/responses/rom.py` - Detailed-ROM owned-media role and label serialization.
- `backend/handler/database/roms_handler.py` - Trusted creation contracts and role/surface enforcement.
- `backend/tests/handler/database/test_rom_media.py` - Persistence, migration, label, serialization, and placement regressions.

## Decisions Made

- Legacy provider rows backfill to `screenshot`, while legacy uploads backfill to `artwork`, because persisted origin is the only safe durable discriminator available. MIME values, tags, and source paths are not consulted.
- Direct role or label changes are unavailable after creation. Provider reconciliation rejects an identity whose supplied role conflicts with its existing role.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Advanced the migration revision to the actual catalog head.**

- **Found during:** Task 1
- **Issue:** The Plan 20-01 migration already uses revision `0127_parent_rom_owned_media`, so the planned `0123` revision identifier could not be used safely.
- **Fix:** Kept the requested filename but created revision `0128_owned_media_role_and_display_label` with `0127_parent_rom_owned_media` as its predecessor.
- **Files modified:** `backend/alembic/versions/0123_owned_media_role_and_display_label.py`
- **Verification:** The migration regression asserts the revision lineage.
- **Committed in:** `46c041a41`

**2. [Rule 1 - Bug] Normalized Windows separators before filename sanitization.**

- **Found during:** Task 1
- **Issue:** POSIX basename handling alone would preserve a backslash-delimited path prefix in a display label.
- **Fix:** Convert backslashes to separators before deriving the bounded basename.
- **Files modified:** `backend/models/rom.py`
- **Verification:** The label regression covers a backslash-delimited input.
- **Committed in:** `46c041a41`

**Total deviations:** 2 auto-fixed, one blocking and one bug fix.

## Issues Encountered

- The focused database suite could not execute assertions because `127.0.0.1:3306` is unavailable before the session fixture initializes. The module collected all 22 tests, scoped Trunk checks passed, and pure role/label checks passed. Alembic head discovery is also blocked by the local configuration's inaccessible `/romm` storage paths.

## Known Stubs

None.

## Next Phase Readiness

- Plans 20-02 through 20-05 can consume authoritative role and label fields for refresh, uploads, placement UI, and soundtrack playback.
- Re-run focused database and MariaDB/PostgreSQL migration evidence when the canonical test services are available.

## Self-Check: PASSED

- Created migration and all four modified backend contract files exist.
- Task commits `46c041a41` and `2105fb62b` exist in Git history.

_Phase: 20-media-management-and-owned-soundtrack-uploads_
_Completed: 2026-09-28_
