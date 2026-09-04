---
phase: 13-pc-igdb-metadata-and-dlc-media
plan: 02
subsystem: scan-and-media-import
tags: [igdb, scan, pc, dlc, owned-media]
requires:
  - phase: 13-01
    provides: normalized PC IGDB metadata fields
provides:
  - Version-guarded parent and DLC IGDB persistence during Windows scans
  - Unambiguous-DLC-only owned cover, screenshot, and artwork imports
  - Non-fatal optional provider-media failure handling
affects: [13-03, 13-04]
tech-stack:
  added: []
  patterns:
    - Scan imports keep provider URLs transient and persist only owned paths with stable provider-media identifiers.
key-files:
  created:
    - backend/tests/handler/database/test_pc_igdb_enrichment.py
  modified:
    - backend/endpoints/sockets/scan.py
    - backend/handler/database/roms_handler.py
    - backend/handler/metadata/pc_match_handler.py
    - backend/handler/metadata/igdb_handler.py
    - backend/endpoints/roms/pc_metadata.py
key-decisions:
  - Parent artworks use the established owned screenshot collection, while DLC artworks retain their explicit component-owned role.
  - Automatic DLC enrichment requires exactly one related IGDB candidate and a current parent-contained DLC version.
duration: 45min
completed: 2026-09-04
---

# Phase 13 Plan 02: Scan-Time PC IGDB Enrichment Summary

**Windows scans now retain normalized parent metadata and import parent/DLC IGDB media into RomM-owned storage, with DLC writes gated by one trusted relationship.**

## Accomplishments

- Added version-guarded parent enrichment and contained DLC metadata/media persistence helpers.
- Hydrated exactly one related IGDB DLC candidate before persisting metadata or downloading provider media.
- Imported DLC cover, screenshots, and artwork through the validated component-owned resource writer, storing deterministic provider-media identifiers rather than URLs.
- Made optional DLC provider-media failures log and continue without undoing valid metadata or scan visibility.
- Added IGDB artwork normalization. Parent artwork joins the established owned screenshot collection, while the candidate contract preserves artwork identity for DLC-owned records.

## Task Commits

1. **Task 1: Add authoritative PC enrichment persistence helpers**
   - `29544ad67` test(13-02): cover contained PC IGDB enrichment
   - `3e6bb006f` feat(13-02): persist contained PC IGDB enrichment
2. **Task 2: Orchestrate scan-time parent and unambiguous DLC import**
   - `e15c27278` test(13-02): cover IGDB artwork normalization
   - `bd1f683d9` feat(13-02): expose normalized IGDB artwork URLs
   - `4da02e0fb` test(13-02): cover scan-time DLC IGDB imports
   - `5610faa8d` feat(13-02): enrich scanned DLCs with owned IGDB media
   - `eefba5856` fix(13-02): remove unused scan test import
   - `511b61f7b` test(13-02): require owned parent artwork import
   - `38887e535` feat(13-02): persist parent IGDB artwork as owned media

## Verification

- `cd backend && uv run pytest tests/handler/metadata/test_igdb_handler.py tests/handler/metadata/test_pc_match_handler.py tests/endpoints/roms/test_pc_metadata.py tests/endpoints/sockets/test_scan.py tests/handler/database/test_pc_igdb_enrichment.py -q` passed, 145 tests.
- Scoped `trunk check --no-fix` passed for all eight changed backend files.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 2 - Missing critical functionality] Made IGDB artwork durable for parent scans**
   - **Found during:** Task 2
   - **Issue:** IGDB requested artwork URLs, but the parent scan only had the established owned cover/screenshot persistence route.
   - **Fix:** Normalized artwork URLs and included them in the owned parent screenshot collection. DLC candidates retain an explicit artwork role and component-owned record.
   - **Files modified:** `backend/handler/metadata/igdb_handler.py`, `backend/handler/metadata/pc_match_handler.py`, `backend/endpoints/roms/pc_metadata.py`
   - **Commits:** `511b61f7b`, `38887e535`

2. **[Rule 1 - Bug] Corrected metadata-handler import location**
   - **Found during:** Task 2 test collection
   - **Issue:** The singleton matcher is not exported from `handler.metadata`.
   - **Fix:** Imported it from `handler.metadata.pc_match_handler`.
   - **Files modified:** `backend/endpoints/sockets/scan.py`
   - **Commit:** `5610faa8d`

## Self-Check: PASSED

- Confirmed all listed implementation and test files exist.
- Confirmed all task commits exist in Git history.
