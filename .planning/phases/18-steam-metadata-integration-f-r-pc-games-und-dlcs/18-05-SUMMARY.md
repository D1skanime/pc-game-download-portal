---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: 05
subsystem: backend metadata
tags: [steam, dlc, igdb, safety]
requires:
  - phase: 18-04
    provides: shared Steam normalizer
provides:
  - IGDB-first, parent-aware Steam DLC enrichment
affects: [scan, pc-components]
tech-stack:
  added: []
  patterns: [typed parent identity, unique high-confidence Steam selection]
key-files:
  created: []
  modified:
    - backend/adapters/services/steam_types.py
    - backend/handler/metadata/pc_match_handler.py
    - backend/handler/metadata/steam_handler.py
    - backend/endpoints/sockets/scan.py
decisions:
  - Steam DLC enrichment requires one hydrated IGDB identity, a DLC Store type, and either a matching parent App ID or one high-confidence result.
metrics:
  tasks_completed: 2
---

# Phase 18 Plan 05: IGDB-authoritative Steam DLC enrichment Summary

Steam DLC data now supplements an existing IGDB-resolved DLC component only after typed product, parent, and unique-confidence validation.

## Accomplishments

- Added the typed `SteamFullGame` contract and strict positive-decimal parent App-ID parsing.
- Added parent-aware DLC type validation and unique 0.90 title-confidence selection after IGDB hydration.
- Kept IGDB component persistence first, then applied normalized Steam data only to that same existing component.
- Rejected malformed parent relations, non-DLC product types, parent mismatches, service failures, and ambiguity without a Steam write.

## Task Commits

1. `2b09285c2` test(18-05): specify safe Steam DLC validation
2. `19569bfb3` feat(18-05): enrich validated IGDB DLCs from Steam

## Verification

- `trunk fmt` and `trunk check` passed for all seven changed backend files.
- Focused pytest was attempted, but all collection setup is blocked by `mariadb.OperationalError: Can't connect to server on '127.0.0.1' (115)`, the pre-existing host test-DB configuration issue documented in STATE.md.

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 2 - Critical functionality] Preserved the Storefront product type and parent payload in normalized Steam details.

- **Found during:** Task 2
- **Issue:** The narrow matcher could not safely distinguish a DLC from a base game or inspect the typed parent after App-ID resolution.
- **Fix:** Retained only `type` and `fullgame` provenance required for the validation gate.
- **Files modified:** `backend/handler/metadata/steam_handler.py`
- **Commit:** `19569bfb3`

## Known Stubs

None.

## Self-Check: PASSED

- All planned code and test files exist.
- Both task commits exist in Git history.
