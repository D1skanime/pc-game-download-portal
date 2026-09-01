---
phase: 10-pc-integration-model
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, metadata, pc, launchbox]
requires:
  - phase: 10-01
    provides: Read-only PC component manifests and existing ROM persistence seams.
provides:
  - Review-only metadata candidates from configured PC providers.
  - Authenticated candidate review and explicit, atomic metadata selection.
  - A RiotPixels no-enable provider evaluation record.
affects: [10-03-pc-review-ui, metadata, roms]
tech-stack:
  added: []
  patterns: [review-first metadata selection, optimistic metadata apply]
key-files:
  created:
    - backend/handler/metadata/pc_match_handler.py
    - backend/endpoints/roms/pc_metadata.py
    - docs/providers/riotpixels-evaluation.md
  modified:
    - backend/handler/database/roms_handler.py
    - backend/endpoints/responses/rom.py
key-decisions:
  - "Candidate discovery remains non-persistent and attributes failures to a provider."
  - "Candidate application compares expected ROM version and writes in one database transaction."
  - "Provider media remains read-only candidate data and is not persisted by selection."
patterns-established:
  - "PC metadata flows collect candidates first, then apply only an explicitly selected candidate ID."
requirements-completed:
  [PCMETA-01, PCMETA-02, PCLB-01, PCLB-02, PCRP-01, PCSAFE-01, PCTEST-01]
duration: 36min
completed: 2026-09-01
---

# Phase 10 Plan 02: PC Metadata Review API Summary

**Review-only PC metadata candidates, explicit optimistic selection, and a disabled RiotPixels evaluation boundary.**

## Performance

- **Duration:** 36 min
- **Started:** 2026-09-01T08:20:00Z
- **Completed:** 2026-09-01T08:56:00Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Normalized IGDB, MobyGames, SteamGridDB, and LaunchBox lookup output into provider-attributed PC metadata candidates.
- Added protected candidate-review and selected-candidate endpoints with ROM visibility masking and atomic stale-version protection.
- Recorded RiotPixels as not enabled until official API, rights, rate-limit, attribution, and credential evidence exists.

## Task Commits

1. **Task 1: Normalize PC metadata candidates without applying them** - `a94c1d378` (feat)
2. **Task 2: Expose review and explicit apply endpoints** - `7c1ca4003` (feat)
3. **Task 3: Document and fence RiotPixels** - `fb9a6ac9e` (docs)
4. **Security correction: Keep provider media out of candidate writes** - `7b9cd78fe` (fix)

## Files Created/Modified

- `backend/handler/metadata/pc_match_handler.py` - Collects non-persistent provider candidates and eligible media descriptors.
- `backend/endpoints/roms/pc_metadata.py` - Provides authenticated candidate review and selection routes.
- `backend/handler/database/roms_handler.py` - Applies a reviewed candidate with an atomic expected-version comparison.
- `backend/endpoints/responses/rom.py` - Defines PC metadata request and response schemas.
- `backend/tests/handler/metadata/test_pc_match_handler.py` - Covers provider attribution, unavailable providers, and LaunchBox media eligibility.
- `backend/tests/endpoints/roms/test_pc_metadata.py` - Covers read-only review, validation, explicit selection, stale versions, and visibility masking.
- `docs/providers/riotpixels-evaluation.md` - Documents RiotPixels as evaluation-only.

## Decisions Made

- Candidate IDs are deterministic opaque hashes of provider identity and display data, so selection can be revalidated without persisting a pre-selection record.
- The database handler performs compare-and-swap selection because endpoint-side version checks could race with another metadata update.
- External provider media is exposed only as review descriptors. The selection write never persists an external media URL.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Kept provider media outside the metadata write payload**

- **Found during:** Task 2
- **Issue:** Persisting candidate-provided media URLs would bypass the established provider-media validation path.
- **Fix:** Restricted selection fields to provider metadata and identifiers; media remains review-only.
- **Files modified:** `backend/handler/metadata/pc_match_handler.py`, `backend/tests/handler/metadata/test_pc_match_handler.py`
- **Verification:** Targeted Trunk check passed.
- **Committed in:** `7b9cd78fe`

**2. [Rule 3 - Blocking] Mounted the planned PC metadata router from the ROM router**

- **Found during:** Task 2
- **Issue:** A new ROM sub-router is unreachable unless its parent includes it.
- **Fix:** Added the one import and `include_router` call in `backend/endpoints/roms/__init__.py`.
- **Files modified:** `backend/endpoints/roms/__init__.py`
- **Verification:** Targeted Trunk check passed.
- **Committed in:** `7c1ca4003`

**Total deviations:** 2 auto-fixed (1 security, 1 blocking).

## Issues Encountered

- The host test process cannot reach the Docker-network-only MariaDB service. The focused suites were subsequently run in the local development container and passed: `9 passed`.
- The selection test initially supplied the fixture object's timestamp directly and received `409` because it did not reflect the database's serialized timestamp precision. The test now performs the actual review-then-apply flow and uses the review response's `expected_version` value.
- OpenAPI generation could not be run because no local backend service was available. The new response schemas passed targeted Trunk validation.

## Known Stubs

None.

## User Setup Required

None - no external service configuration was added.

## Next Phase Readiness

Phase 10-03 can consume the candidate-review API and display provider availability, candidate metadata, and eligible local LaunchBox media. Database-backed endpoint verification passed in the local isolated development container.

## Self-Check: PASSED

- Summary file exists.
- Task commits `a94c1d378`, `7c1ca4003`, `fb9a6ac9e`, and `7b9cd78fe` exist.
