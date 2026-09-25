---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: 04
subsystem: backend metadata
tags: [steam, pc-metadata, fastapi, sqlalchemy, pytest]
requires:
  - phase: 18-01
    provides: Steam Storefront handler and App-ID lookup
  - phase: 18-02
    provides: Steam identity and provenance persistence fields
  - phase: 18-03
    provides: Steam provider registry integration
provides:
  - Non-empty, manual-safe Steam normalizer for PC main-game application
  - Revalidated Steam PC candidate selection with optimistic persistence
affects: [18-07 automatic Steam scans, PC metadata review]
tech-stack:
  added: []
  patterns: [shared provider merge policy, Steam App-ID re-resolution]
key-files:
  created: [backend/handler/metadata/steam_merge.py]
  modified:
    [
      backend/handler/metadata/pc_match_handler.py,
      backend/endpoints/roms/pc_metadata.py,
      backend/handler/database/roms_handler.py,
    ]
key-decisions:
  - "Steam display fields are applied only by normalize_steam, with manual and legacy populated values protected."
  - "Manual selection re-resolves its Steam App ID and uses existing optimistic persistence and artwork selection paths."
patterns-established:
  - "Provider provenance remains observational; only explicitly normalized fields may affect display state."
requirements-completed: [STEAM-02, STEAM-04, STEAM-05]
duration: 9min
completed: 2026-09-25
---

# Phase 18 Plan 04: Safe Steam PC Application and Refresh Summary

**A shared, non-empty Steam normalizer protects manual and legacy PC metadata while revalidated Steam candidates use existing optimistic persistence and artwork review paths.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-09-25T13:24:14Z
- **Completed:** 2026-09-25T13:33:06Z
- **Tasks:** 2/2
- **Files modified:** 9

## Accomplishments

- Added the sole `normalize_steam` policy for valid App IDs, bounded provenance, non-empty localized fields, legacy protection, and artwork candidates.
- Recorded explicit title, summary, and PC-release overrides in `manual_metadata` without discarding existing manual metadata.
- Added Steam candidate collection and server-side App-ID detail resolution before guarded PC metadata persistence.

## Task Commits

1. **Task 1: Red, green, refactor the pure Steam merge contract** - `5ebf6af12` (feat)
2. **Task 2: Connect the shared merge to Steam candidates and PC selection** - `45acc95fe` (feat)

## Files Created/Modified

- `backend/handler/metadata/steam_merge.py` - shared Steam field normalizer.
- `backend/endpoints/roms/__init__.py` - persists explicit manual field authority.
- `backend/handler/metadata/pc_match_handler.py` - exposes Steam candidates and review media.
- `backend/endpoints/roms/pc_metadata.py` - re-resolves selected Steam App IDs and normalizes details.
- `backend/handler/database/roms_handler.py` - atomically persists safe structured PC metadata updates.
- `backend/tests/handler/metadata/test_steam_merge.py` - normalizer contract coverage.
- `backend/tests/handler/metadata/test_pc_match_handler.py` - Steam candidate coverage.
- `backend/tests/endpoints/roms/test_pc_metadata.py` - server-side Steam selection coverage.
- `backend/tests/endpoints/roms/test_rom.py` - manual authority coverage.

## Decisions Made

- Steam provenance is observational and records only bounded normalized provider details plus ownership of fields previously applied by Steam.
- Existing non-empty title, summary, and release values stay protected unless the same field already has Steam provenance.
- Steam cover and screenshots remain candidate data and retain the existing explicit artwork selection flow.

## Deviations from Plan

None - plan implementation scope was followed exactly.

## Issues Encountered

- Focused Pytest suites cannot run in the host checkout because `backend/pytest.ini` forces `DB_HOST=127.0.0.1`, while the available `romm-db-dev` Compose service is network-only. Reproduce with `cd backend && uv run pytest tests/handler/metadata/test_steam_merge.py -q`; setup fails before test assertions with `mariadb.OperationalError: Can't connect to server on '127.0.0.1' (115)`.
- The running `romm-dev` container has a stale `/app` checkout and therefore cannot execute the newly added host test files. No service was restarted or changed.
- `trunk check` passed for all nine changed files. An integration-free normalizer contract check passed using the project Python environment.

## TDD Gate Compliance

The RED test was executed and failed for the expected missing-module import. The RED and GREEN changes were committed together per task, so the repository history does not contain a separate `test(18-04)` commit.

## Known Stubs

None.

## Next Phase Readiness

Plan 18-07 can route automatic PC Steam resolution through `normalize_steam` without adding a second field merge policy.

---

_Phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs_
_Completed: 2026-09-25_

## Self-Check: PASSED

- All nine planned code/test files and this summary exist.
- Task commits `5ebf6af12` and `45acc95fe` exist in Git history.
