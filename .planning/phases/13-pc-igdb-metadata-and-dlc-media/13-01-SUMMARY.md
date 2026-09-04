---
phase: 13-pc-igdb-metadata-and-dlc-media
plan: 01
subsystem: database
tags: [igdb, sqlalchemy, alembic, metadata]
requires:
  - phase: 12-dlc-detail-pages-for-local-pc-components
    provides: PC component metadata and owned-media models
provides:
  - Role-aware IGDB developer, publisher, theme, and Windows release normalization
  - Equivalent parent-view and component metadata API fields
affects: [13-02, 13-03, PC metadata]
tech-stack:
  added: []
  patterns:
    [
      "PC parent metadata is projected from normalized igdb_metadata through roms_metadata",
    ]
key-files:
  created:
    [
      backend/alembic/versions/0118_pc_igdb_structured_metadata.py,
      backend/tests/models/test_pc_igdb_metadata.py,
    ]
  modified:
    [
      backend/handler/metadata/igdb_handler.py,
      backend/models/rom.py,
      backend/endpoints/responses/rom.py,
    ]
key-decisions:
  - "Use the adapter registry Windows ID, never a generic release date, for pc_release_date."
  - "Expose parent fields through the existing roms_metadata view because it is not a writable table."
patterns-established:
  - "Normalize provider names as non-empty, ordered, de-duplicated values before persistence."
requirements-completed: []
duration: 31min
completed: 2026-09-04
---

# Phase 13 Plan 01: PC IGDB Structured Metadata Summary

**IGDB now normalizes role-aware PC metadata and exposes durable developer, publisher, theme, and Windows-release fields for parent games and DLC components.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-09-04T14:30:00Z
- **Completed:** 2026-09-04T15:01:46Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- Requested IGDB involved-company roles, themes, and release-date platform data.
- Normalized the first developer, ordered de-duplicated publishers/themes, and Windows-only release timestamps without altering legacy companies or first-release metadata.
- Added matching component columns and parent view projections with detailed response-schema fields.

## Task Commits

1. **Task 1: Normalize role-aware IGDB PC metadata** - `6072fa4c4` (test), `6034da17f` (feat)
2. **Task 2: Persist and serialize equivalent parent/component fields** - `981f5940c` (test), `6ff6020b2` (feat)

## Files Created/Modified

- `backend/handler/metadata/igdb_handler.py` - IGDB field requests and safe PC metadata normalization.
- `backend/models/rom.py` - Structured fields on parent-view and component metadata models.
- `backend/endpoints/responses/rom.py` - Detailed parent and component API fields.
- `backend/alembic/versions/0118_pc_igdb_structured_metadata.py` - Portable component columns and parent view projection.
- `backend/tests/handler/metadata/test_igdb_handler.py` - Provider normalization coverage.
- `backend/tests/models/test_pc_igdb_metadata.py` - Parent/component persistence and migration contracts.

## Decisions Made

- The parent `RomMetadata` model maps the existing read-only `roms_metadata` view, so its new values are projected from durable `roms.igdb_metadata` rather than attempting to alter a view as if it were a table.
- Release-date selection uses only the Microsoft Windows platform ID from `IGDB_PLATFORM_LIST`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Migration correctness] Projected parent metadata through the existing view**

- **Found during:** Task 2
- **Issue:** `roms_metadata` is a database view on MariaDB and cannot receive columns with `ALTER TABLE`.
- **Fix:** Added component table columns and rebuilt the parent metadata view with portable JSON expressions.
- **Files modified:** `backend/alembic/versions/0118_pc_igdb_structured_metadata.py`, `backend/tests/models/test_pc_igdb_metadata.py`
- **Verification:** Focused persistence test upgrades the migration and reads the parent projection.
- **Committed in:** `6ff6020b2`

## Issues Encountered

- `tools/verify_storage_migrations.py --dialects mariadb mysql postgresql` could not start its isolated runner because the existing `romm-dev` container has no Docker gateway. Focused migration upgrade and model tests pass; the cross-dialect runner must be retried from a Docker-capable verification environment.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 13-02 can persist normalized candidates during scan-time parent and DLC enrichment.
- OpenAPI type regeneration and frontend typecheck remain required once the phase's API work is integrated.

## Self-Check: PASSED

- Confirmed all six implementation/test files exist.
- Confirmed commits `6072fa4c4`, `6034da17f`, `981f5940c`, and `6ff6020b2` exist.

---

_Phase: 13-pc-igdb-metadata-and-dlc-media_
_Completed: 2026-09-04_
