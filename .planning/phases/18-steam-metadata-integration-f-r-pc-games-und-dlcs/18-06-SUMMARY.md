---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: 06
subsystem: api
tags: [fastapi, openapi, typescript, steam, v2]
requires:
  - phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
    provides: Nullable persisted Steam IDs and provenance fields from Plan 18-02
provides:
  - Existing ROM and PC component API responses expose persisted Steam IDs and provenance
  - Generated frontend contracts mirror the authoritative OpenAPI response schema
affects: [steam-metadata, pc-components, frontend-api-contract]
tech-stack:
  added: []
  patterns:
    [OpenAPI-generated client contracts, provenance-only metadata serialization]
key-files:
  created: []
  modified:
    - backend/endpoints/responses/rom.py
    - backend/tests/endpoints/roms/test_rom.py
    - frontend/src/__generated__/models/PcComponentMetadataSchema.ts
    - frontend/src/__generated__/models/SimpleRomSchema.ts
    - frontend/src/__generated__/models/DetailedRomSchema.ts
key-decisions:
  - "Steam identity and raw provenance use the established ROM and component response surfaces without a Steam-specific route or display field."
  - "Generated contract churn unrelated to these response fields remains unstaged and is preserved for its owning work."
patterns-established:
  - "Persisted provider provenance is observational API data and must not become synthetic display authority."
requirements-completed: [STEAM-02, STEAM-04]
duration: 10min
completed: 2026-09-25
---

# Phase 18 Plan 06: Steam API Contract Summary

**Existing ROM and PC component responses now serialize persisted Steam App IDs and provenance, with matching generated TypeScript contracts.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-09-25T09:35:00Z
- **Completed:** 2026-09-25T09:44:04Z
- **Tasks:** 2/2
- **Files modified:** 8

## Accomplishments

- Added Steam ID and provenance fields to the existing ROM response schema and completed the existing component response schema.
- Added endpoint serialization coverage that confirms Steam data is observational and no synthetic display field is exposed.
- Regenerated the API client from the running canonical backend, then updated directly affected typed v2 fixtures.

## Task Commits

1. **Task 1: Serialize Steam identity and provenance only through existing metadata surfaces** - `0e2f029cc` (test), `691159510` (feat)
2. **Task 2: Regenerate and typecheck the frontend API contract** - `c5a4dc026` (chore)

## Files Created/Modified

- `backend/endpoints/responses/rom.py` - Existing ROM and component schemas expose nullable Steam identity and provenance.
- `backend/tests/endpoints/roms/test_rom.py` - Endpoint contract coverage for parent and component serialization.
- `frontend/src/__generated__/models/PcComponentMetadataSchema.ts` - Generator-produced component Steam fields.
- `frontend/src/__generated__/models/SimpleRomSchema.ts` - Generator-produced ROM Steam fields used by list responses.
- `frontend/src/__generated__/models/DetailedRomSchema.ts` - Generator-produced detailed ROM Steam fields.
- `frontend/src/v2/components/GameDetails/PcDlcDetail.test.ts` - Typed component fixture includes nullable Steam contract values.
- `frontend/src/v2/components/GameDetails/RelatedGameCard.vue` - Typed synthetic ROM fixture includes nullable Steam contract values.

## Decisions Made

- `steam_metadata` remains observational provenance. No display-derived Steam field, endpoint, or mutation surface was introduced.
- The generator's current client names ROM list schemas `SimpleRomSchema.ts`, not the stale plan path `RomSchema.ts`; generated files were never edited manually.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated direct typed fixture consumers after generated contract expansion**

- **Found during:** Task 2
- **Issue:** Existing v2 test and synthetic-ROM fixture literals no longer satisfied generated required nullable Steam fields.
- **Fix:** Added explicit `null` values without changing any UI behavior or provenance display authority.
- **Files modified:** `frontend/src/v2/components/GameDetails/PcDlcDetail.test.ts`, `frontend/src/v2/components/GameDetails/RelatedGameCard.vue`
- **Verification:** `npm run test -- src/v2/components/GameDetails/PcDlcDetail.test.ts` passed with 8 tests.
- **Committed in:** `c5a4dc026`

### Plan Adjustments

- The plan referenced the absent `backend/tests/endpoints/test_rom.py`; coverage was added to the existing endpoint test module `backend/tests/endpoints/roms/test_rom.py`.
- The plan referenced absent generated `RomSchema.ts`; the canonical generator produces `SimpleRomSchema.ts` and `DetailedRomSchema.ts` for the existing ROM surfaces.

**Total deviations:** 1 auto-fixed blocking issue and 2 repository-layout adjustments. No scope creep.

## Issues Encountered

- The prescribed backend pytest command cannot initialize because its MariaDB test configuration points to unavailable `127.0.0.1:3306`; the same failure occurs in `romm-dev`. No assertion ran, so endpoint coverage awaits reachable test infrastructure.
- The generated API contract makes the full frontend typecheck fail on the pre-existing heartbeat default missing `STEAM_API_ENABLED`. This unrelated provider-registration gap is recorded in `deferred-items.md`.

## Known Stubs

None. Nullable fixture values model the persisted optional API contract and do not flow to a placeholder UI.

## Next Phase Readiness

- Steam scan and display work can consume the existing generated ROM and component fields.
- Restore the MariaDB test endpoint and add the heartbeat default before treating full-suite verification as green.

## Self-Check: PASSED

- Verified all eight implementation, generated-contract, test, and summary files exist.
- Verified task commits `0e2f029cc`, `691159510`, and `c5a4dc026` exist in Git history.
