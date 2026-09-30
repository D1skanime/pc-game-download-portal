---
phase: 20-media-management-and-owned-soundtrack-uploads
plan: "10"
subsystem: database
tags: [alembic, sqlalchemy, owned-media, migration, v2]
requires:
  - phase: 20-media-management-and-owned-soundtrack-uploads
    provides: typed parent-owned media candidates, placements, roles, and safe labels
provides:
  - portable idempotent legacy owned-media catalog backfill
  - ordered overview placement migration for persisted legacy screenshots
  - tombstone-preserving migrated media visibility regressions
affects: [20-08, media-api, game-details-v2, migration-validation]
tech-stack:
  added: []
  patterns:
    [database-only legacy identity backfill, marker-bounded migration downgrade]
key-files:
  created:
    - backend/alembic/versions/0129_backfill_legacy_rom_owned_media.py
    - backend/tests/models/test_rom_owned_media_migration.py
  modified:
    - backend/tests/handler/database/test_rom_media.py
    - frontend/src/v2/components/GameDetails/ScreenshotsSubtab.test.ts
key-decisions:
  - "Legacy paths are accepted only as bounded RomM resource-relative image identifiers and never opened as filesystem paths."
  - "The migration identifies records with a role-bound SHA-256 digest and its own provenance marker, so reruns and downgrades are bounded."
patterns-established:
  - "Preserve existing tombstone and placement state before adding legacy catalog state."
  - "Backfill overview positions from persisted screenshot order only when no existing overview curation exists."
requirements-completed:
  [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07]
duration: 22min
completed: 2026-09-28
---

# Phase 20 Plan 10: Legacy Owned-Media Backfill Summary

**A portable database-only migration turns persisted RomM screenshot and cover resources into deterministic, tombstone-aware owned-media candidates with legacy overview order retained.**

## Performance

- **Duration:** 22 min
- **Completed:** 2026-09-28
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Added revision 0129, which accepts only safe `roms/` relative image resource identifiers, creates role-bound provider candidates, and does not access the filesystem, source library, or a metadata provider.
- Backfilled screenshot overview placements in persisted order, while preserving existing tombstones and operator-curated placements.
- Added simulation and UI/contract regressions for a 28-item screenshot gallery, idempotent reruns, marker-bounded downgrade, and catalog-first v2 rendering.

## Task Commits

1. **Task 1: Write idempotent portable legacy owned-media backfill migration** - `372cbd42b` (test), `0b3f4cfb5` (feat)
2. **Task 2: Prove catalog visibility for migrated legacy media and record UAT recheck** - `05dd4877b` (test)

## Files Created/Modified

- `backend/alembic/versions/0129_backfill_legacy_rom_owned_media.py` - Database-only legacy candidate and overview-placement backfill.
- `backend/tests/models/test_rom_owned_media_migration.py` - SQLite migration simulation plus safe identity/path regression coverage.
- `backend/tests/handler/database/test_rom_media.py` - Detailed-ROM catalog hydration contract regression.
- `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.test.ts` - Catalog-first provider screenshot rendering regression.

## Decisions Made

- Legacy candidate identity is `legacy-` plus a SHA-256 digest of a versioned domain, role, and owned resource identifier. It is deterministic without using a source path or bytes.
- Revision 0129 uses a dedicated `romm-legacy-owned-v1` provenance marker so downgrade removes only catalog rows created by this backfill and never resource bytes.
- Plan 20-08 already contains the exact ROM 13 migrated-media browser recheck, so no redundant UAT-plan edit was necessary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Preserved tombstones before creating overview placements.**

- **Found during:** Task 1
- **Issue:** A pre-existing tombstoned candidate could otherwise receive a new overview placement during migration.
- **Fix:** The migration skips placement creation for an existing tombstoned candidate and preserves its state and null owned path.
- **Files modified:** `backend/alembic/versions/0129_backfill_legacy_rom_owned_media.py`, `backend/tests/models/test_rom_owned_media_migration.py`
- **Verification:** SQLite simulation exercises a tombstoned first screenshot, 27 ordered remaining placements, repeat upgrade, and downgrade.
- **Committed in:** `0b3f4cfb5`

**Total deviations:** 1 auto-fixed bug correction.

## Issues Encountered

- The requested pytest suites cannot establish their MariaDB test fixture because `127.0.0.1:3306` is unavailable. The actual test run collected the migration module then failed before assertions. The independent SQLite migration simulation, focused Trunk check, and `ScreenshotsSubtab` Vitest suite passed.
- Task 2's new regressions passed immediately because Plan 20-09 already supplied the catalog-first response and v2 component behavior. This is recorded as pre-existing implementation rather than a skipped verification.

## Known Stubs

None.

## Next Phase Readiness

- Plan 20-08 can execute the MariaDB/PostgreSQL migration cycles and its existing ROM 13 browser UAT recheck when the test databases are available.

## TDD Gate Compliance

- Task 1 recorded a RED test commit before its implementation commit.
- Task 2 adds regression coverage for behavior already delivered by the completed Plan 20-09 contract, so its checks were green on first execution.

## Self-Check: PASSED

- Created migration and migration regression files exist.
- Task commits `372cbd42b`, `0b3f4cfb5`, and `05dd4877b` exist in Git history.

_Phase: 20-media-management-and-owned-soundtrack-uploads_
_Completed: 2026-09-28_
