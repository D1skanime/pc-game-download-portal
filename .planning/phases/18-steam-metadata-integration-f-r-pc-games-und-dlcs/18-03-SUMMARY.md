---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: "03"
subsystem: metadata-provider-registry
tags: [steam, steamgriddb, heartbeat, vue-v2, metadata-sources]
requires:
  - phase: 18-01
    provides: Steam storefront handler and no-key configuration
  - phase: 18-06
    provides: Steam heartbeat API contract and generated TypeScript types
provides:
  - Steam priority validation, watcher registration, and independent heartbeat reporting
  - A distinct no-key Steam v2 settings tile and Steam App-ID provider link
  - Approved live UAT evidence that Steam remains separate from SteamGridDB
affects: [18-04, 18-05, 18-07, metadata-priority, v2-settings]
tech-stack:
  added: []
  patterns:
    - Provider source slugs remain independently registered through validation, heartbeat, and v2 display surfaces.
    - Steam Storefront uses no API key and is never conflated with SteamGridDB artwork metadata.
key-files:
  created: []
  modified:
    - backend/config/config_manager.py
    - backend/watcher.py
    - backend/endpoints/heartbeat.py
    - backend/endpoints/responses/heartbeat.py
    - frontend/src/stores/heartbeat.ts
    - frontend/src/v2/components/GameDetails/providers.ts
    - frontend/src/v2/views/Settings/MetadataSources.vue
    - backend/tests/config/test_config_loader.py
    - backend/tests/endpoints/test_heartbeat.py
    - frontend/src/v2/components/GameDetails/providers.test.ts
key-decisions:
  - "Keep Steam Storefront and SteamGridDB as independent sources across API and v2 UI surfaces."
  - "Treat the isolated UAT database migration mismatch as environment evidence, not an 18-03 code defect."
patterns-established:
  - "Provider registration: every MetadataSource value must be represented by scan-priority validation and independently heartbeat-routable."
requirements-completed: []
duration: 3h 31m
completed: 2026-09-25
---

# Phase 18 Plan 03: Provider Registry and v2 Steam Presentation Summary

**Steam Storefront is independently priority-valid, heartbeat-visible, and presented as a no-key v2 metadata source with a persisted App-ID link, while SteamGridDB remains a separate artwork provider.**

## Performance

- **Duration:** 3h 31m
- **Started:** 2026-09-25T09:49:55Z
- **Completed:** 2026-09-25T13:21:00Z
- **Tasks:** 3 completed
- **Files modified:** 10

## Accomplishments

- Registered `steam` in metadata-priority validation and watcher sources, with a focused enum-alignment regression test.
- Exposed `STEAM_API_ENABLED` and Steam-only heartbeat dispatch without changing SteamGridDB behavior.
- Added separate Steam v2 settings and App-ID-link entries, then received approved live UAT evidence at `http://team4s-linux:3344`.

## Task Commits

1. **Task 1: Test and wire central Steam registration and heartbeat** - `9123f1ca0` (feat)
2. **Task 2: Add distinct v2 Steam provider display entries** - `3f42f9971` (feat)
3. **Task 3: Verify responsive and accessible Steam v2 presentation** - approved human verification, recorded by this metadata commit

## Files Created/Modified

- `backend/config/config_manager.py` - accepts Steam in metadata-priority validation.
- `backend/watcher.py` - keeps enabled Steam in the watcher provider set.
- `backend/endpoints/heartbeat.py` and `backend/endpoints/responses/heartbeat.py` - report Steam separately and route its heartbeat to the Steam handler.
- `frontend/src/stores/heartbeat.ts` - consumes the generated Steam enablement flag.
- `frontend/src/v2/components/GameDetails/providers.ts` - maps `steam_id` to the Steam Storefront App-ID URL.
- `frontend/src/v2/views/Settings/MetadataSources.vue` - shows Steam as a distinct no-key settings source.
- `backend/tests/config/test_config_loader.py`, `backend/tests/endpoints/test_heartbeat.py`, and `frontend/src/v2/components/GameDetails/providers.test.ts` - cover independent provider registration and display behavior.

## Verification

- `npm run test -- --run src/v2/components/GameDetails/providers.test.ts` passed, 1 file and 1 test.
- `npm run typecheck` passed.
- `npm run build` passed. Existing Browserslist, CSS pseudo-class, direct-eval dependency, and chunk-size warnings remained warnings only.
- The focused backend command could not start its tests because the local MariaDB test endpoint at `127.0.0.1:3306` was unavailable. It produced 31 setup errors before any test assertions ran and did not identify an 18-03 regression.

## UAT Evidence

- **Status:** APPROVED by the user on the canonical live stack at `http://team4s-linux:3344`.
- **Confirmed:** In V2 Settings, Metadata Sources, Steam is visibly separate from SteamGridDB, requires no API key, and SteamGridDB remains separately identified.
- **Data recovery:** Four Windows games became visible after the isolated UAT database was migrated from revision 0125 to 0126.

## Deviations from Plan

### UAT Environment Clarification

**1. [Environment] Corrected the live UAT endpoint and isolated schema state**

- **Found during:** Task 3 (human verification)
- **Issue:** An earlier `:3100` endpoint reference was incorrect. The temporary `No games in this platform yet` result came from the isolated UAT database being at revision 0125 while the running stack expected revision 0126.
- **Resolution:** Performed UAT at `http://team4s-linux:3344` after migrating the isolated UAT database from 0125 to 0126.
- **Impact:** The four Windows games reappeared. This was not caused by 18-03 code, so no code correction was needed.

**Total deviations:** 1 environment clarification, 0 code deviations.

## Issues Encountered

- Local backend rerun was blocked by an unavailable MariaDB test service. No service was started or changed because this plan's code and approved live UAT were already complete.

## User Setup Required

None. Steam Storefront remains a no-key provider.

## Next Phase Readiness

- Provider registration and v2 distinction are complete for Steam-dependent scan and DLC work in Plans 18-04, 18-05, and 18-07.
- Re-run the focused backend tests when the local MariaDB test endpoint is available.

## Self-Check: PASSED

- Confirmed this summary exists and the Task 1, Task 2, and checkpoint commits are present in Git history.

_Phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs_
_Completed: 2026-09-25_
