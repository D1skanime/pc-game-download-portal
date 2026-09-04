---
phase: 13-pc-igdb-metadata-and-dlc-media
plan: 03
subsystem: frontend
tags: [vue, openapi, igdb, pc, i18n]
requires:
  - phase: 13-01
    provides: structured parent and component PC metadata schemas
  - phase: 13-02
    provides: owned parent and DLC IGDB media
provides:
  - Typed PC metadata fields in the frontend contract
  - Target-owned parent and DLC screenshot overview galleries
  - Localized PC release and structured metadata presentation
affects: [13-04, PC metadata]
tech-stack:
  added: []
  patterns:
    - Parent screenshot overviews accept only RomM resource paths.
    - DLC screenshot overviews consume only contained owned-media screenshot records.
key-files:
  created: []
  modified:
    - frontend/src/__generated__/models/RomMetadataSchema.ts
    - frontend/src/__generated__/models/PcComponentMetadataSchema.ts
    - frontend/src/v2/components/GameDetails/OverviewTab.vue
    - frontend/src/v2/components/GameDetails/PcDlcDetail.vue
    - frontend/src/locales/*/rom.json
key-decisions:
  - Prefer pc_release_date, with first_release_date as the parent overview fallback.
  - Do not render provider URLs or cross-owner media in overview galleries.
duration: 27min
completed: 2026-09-04
---

# Phase 13 Plan 03: PC Metadata Overview Summary

**Parent and DLC v2 overviews now present localized PC metadata and show only target-owned screenshots.**

## Accomplishments

- Regenerated the frontend OpenAPI contract with normalized developer, publisher, theme, and Windows release fields.
- Added PC release fallback and separate Main developer, Publishers, and Themes groups to parent and DLC overviews.
- Restricted parent galleries to RomM-owned resource paths and DLC screenshot galleries to the selected component's owned screenshot records.
- Added translated labels in all 18 supported `rom.json` locales.

## Task Commits

1. **Task 1: Generate and adapt the typed frontend metadata contract** - `a8ebc0bd8` (chore)
2. **Task 2: Render parent and DLC PC metadata plus owned screenshot galleries** - `1584a1ac5` (test), `04305eb5e` (feat)
3. **Task 3: Localize the new PC metadata presentation** - `36ee97ae9` (feat)

## Verification

- `cd frontend && npm run test -- src/v2/components/GameDetails/OverviewTab.test.ts src/v2/components/GameDetails/PcDlcDetail.test.ts` passed, 11 tests.
- `cd frontend && npm run typecheck` passed.
- `cd frontend && python3 src/locales/check_i18n_locales.py` passed.
- `cd frontend && python3 src/locales/check_i18n_sorted.py` passed.
- Scoped `trunk check --no-fix --no-progress` passed for the modified source, test, and locale files. Generated OpenAPI models are intentionally ignored by Trunk.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 3 - Blocking contract compatibility] Updated the synthetic related-game metadata fixture**
   - **Found during:** Task 1 typecheck after OpenAPI regeneration.
   - **Issue:** `RelatedGameCard.vue` constructs a complete `RomMetadataSchema`; the generated contract made `main_developer` and `pc_release_date` required.
   - **Fix:** Added neutral `null` and empty-array values to the synthetic fixture only. This does not alter UI behavior.
   - **Files modified:** `frontend/src/v2/components/GameDetails/RelatedGameCard.vue`
   - **Committed in:** `04305eb5e`

## Known Stubs

None.

## Manual Verification

Not performed in this execution environment. Plan 13-04 UAT should inspect parent and DLC detail pages in both themes across responsive and input-modality tiers.

## Self-Check: PASSED

- Confirmed all generated contract, overview, test, and locale files exist.
- Confirmed commits `a8ebc0bd8`, `1584a1ac5`, `04305eb5e`, and `36ee97ae9` exist.
