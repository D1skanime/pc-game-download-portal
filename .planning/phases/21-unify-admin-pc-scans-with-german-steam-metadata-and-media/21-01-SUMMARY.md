---
phase: 21-unify-admin-pc-scans-with-german-steam-metadata-and-media
plan: "01"
subsystem: metadata
tags: [steam, pc-metadata, localization, provenance, pytest]
requires:
  - phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
    provides: SteamHandler German-first same-App-ID fallback and normalized Steam provenance.
provides:
  - Pure Steam PC enrichment request and patch boundary.
  - Shared reviewed-candidate Steam patch application.
affects: [scan-handler, admin-pc-scans, steam-owned-media]
tech-stack:
  added: []
  patterns: [pure normalized provider patch, explicit Steam App-ID revalidation]
key-files:
  created:
    - backend/handler/metadata/pc_steam_enrichment.py
    - backend/tests/handler/metadata/test_pc_steam_enrichment.py
  modified:
    - backend/handler/metadata/steam_merge.py
    - backend/endpoints/roms/pc_metadata.py
    - backend/tests/handler/metadata/test_steam_merge.py
    - backend/tests/endpoints/roms/test_pc_metadata.py
key-decisions:
  - "An explicit reviewed Steam App ID is rehydrated through the same pure resolver as scan enrichment."
  - "Manual developer and publisher values use the existing Steam manual-field guard."
patterns-established:
  - "Provider calls return a normalized patch or {}, never ORM mutations."
  - "A selected Steam candidate is invalid when its App ID is absent, malformed, unavailable, or mismatched."
requirements-completed: [STEAM-02, STEAM-05]
duration: 9min
completed: 2026-09-30
---

# Phase 21 Plan 01: Shared Steam PC Patch Boundary Summary

**A pure, ID-first Steam PC enrichment patch is shared by reviewed Steam metadata selection and prepared for administrator scan reuse.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-09-30T13:06:00Z
- **Completed:** 2026-09-30T13:14:55Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- Added an immutable request and pure resolver that gates Steam, resolves explicit or stored IDs first, permits one eligible-platform title lookup, and fails closed to an empty patch.
- Extended Steam merge protection to retain manually supplied developer and publisher values.
- Replaced the selection endpoint's inline Steam lookup and normalization with the shared resolver while retaining candidate validation, media selection, and optimistic locking.

## Task Commits

1. **Task 1: Define and test the shared Steam PC patch boundary**
   - `b7ff99946` `test(21-01): define Steam PC enrichment contract`
   - `1376c8223` `feat(21-01): add shared Steam PC enrichment`
2. **Task 2: Route selected Steam candidates through the same pure patch contract**
   - `5feb6c8bf` `test(21-01): cover shared Steam selection patch`
   - `da8e42e23` `feat(21-01): share Steam candidate enrichment`

## Files Created/Modified

- `backend/handler/metadata/pc_steam_enrichment.py` - Pure request-based Steam resolution and guarded patch construction.
- `backend/handler/metadata/steam_merge.py` - Manual developer and publisher provenance protection.
- `backend/endpoints/roms/pc_metadata.py` - Reviewed Steam candidate rehydration through the shared resolver.
- `backend/tests/handler/metadata/test_pc_steam_enrichment.py` - ID-first, platform-gate, malformed, ambiguous, and provider-failure coverage.
- `backend/tests/handler/metadata/test_steam_merge.py` - Manual developer and publisher regression coverage.
- `backend/tests/endpoints/roms/test_pc_metadata.py` - Shared resolver, malformed selection, and empty-patch HTTP-contract coverage.

## Decisions Made

- Reused `SteamHandler` through a pure patch boundary, so German-first same-App-ID localization stays provider-owned and no selection or scan helper obtains a session.
- Treat an empty resolver result as the existing 422 Steam-candidate rejection, preventing malformed or rate-limited provider data from persisting partial metadata.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Focused pytest commands could collect the changed modules but could not execute assertions because the configured MariaDB endpoint at `127.0.0.1:3306` is unavailable. No Docker Compose, NAS, Team4s, or external source library was accessed.
- Direct `ruff` invocation is unavailable in the local `uv` environment. The repository pre-commit check ran successfully for every task commit and reported no issues on the staged files.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The shared patch contract is ready for scan orchestration and owned-media reconciliation in subsequent Phase 21 plans.
- Re-run the focused backend pytest suite when an authorized MariaDB test endpoint is available.

## Self-Check: PASSED

- Confirmed all six plan code/test files exist in their committed revisions.
- Confirmed task commits `b7ff99946`, `1376c8223`, `5feb6c8bf`, and `da8e42e23` exist in Git history.

_Phase: 21-unify-admin-pc-scans-with-german-steam-metadata-and-media_
_Completed: 2026-09-30_
