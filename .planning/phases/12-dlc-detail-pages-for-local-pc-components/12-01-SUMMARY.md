---
phase: 12-dlc-detail-pages-for-local-pc-components
plan: 01
subsystem: ui
tags: [vue, vue-router, vitest, pc-dlc]
requires:
  - phase: 12-02
    provides: Parent-owned PC DLC route validation
provides:
  - Parent ROM identity chain for local overview DLC cards
  - Canonical local DLC navigation from overview cards and PC components
affects: [12-03, 12-06]
tech-stack:
  added: []
  patterns: [named router navigation with explicit parent and component IDs]
key-files:
  created:
    - frontend/src/v2/views/GameDetails.test.ts
    - frontend/src/v2/components/GameDetails/OverviewTab.test.ts
    - frontend/src/v2/components/GameDetails/RelatedGamesGrid.test.ts
  modified:
    - frontend/src/v2/views/GameDetails.vue
    - frontend/src/v2/components/GameDetails/OverviewTab.vue
    - frontend/src/v2/components/GameDetails/RelatedGamesGrid.vue
    - frontend/src/v2/components/GameDetails/RelatedGameCard.vue
    - frontend/src/v2/components/GameDetails/PcComponents.vue
key-decisions:
  - "Local DLC navigation uses ROUTES.PC_DLC with explicit parent ROM and component IDs."
  - "Only locally matched DLC cards and DLC component rows expose detail navigation."
patterns-established:
  - "Thread parent identity explicitly through feature component props rather than deriving it from the current route."
requirements-completed: []
duration: 14min
completed: 2026-09-02
---

# Phase 12 Plan 01: Parent-owned DLC Navigation Summary

**Overview DLC cards and PC component rows now navigate by the same explicit parent-ROM and local-component route contract.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-09-02T15:40:00Z
- **Completed:** 2026-09-02T15:46:00Z
- **Tasks:** 2/2
- **Files modified:** 10

## Accomplishments

- Passed `currentRom.id` from `GameDetails` through the overview and related-game grid to local DLC cards.
- Replaced the former local DLC Files-tab navigation with the canonical named `ROUTES.PC_DLC` destination.
- Added a keyboard-accessible v2 button for DLC-only PC component rows, without changing other component kinds.
- Added focused tests for the identity chain, DLC routes, and unchanged non-local behavior.

## Task Commits

1. **Task 1: Specify the complete parent-ROM identity prop chain** - `ef99c5358` (test), `d1e793386` (test fixture correction)
2. **Task 2: Implement canonical local-DLC navigation at both parent surfaces** - `ee0ccb7ec` (feat)

## Files Created/Modified

- `frontend/src/v2/views/GameDetails.vue` - Supplies the current parent ROM ID to the overview.
- `frontend/src/v2/components/GameDetails/OverviewTab.vue` - Forwards parent identity to DLC grids.
- `frontend/src/v2/components/GameDetails/RelatedGamesGrid.vue` - Forwards parent and local component identity to cards.
- `frontend/src/v2/components/GameDetails/RelatedGameCard.vue` - Routes local DLC cards to the canonical named route.
- `frontend/src/v2/components/GameDetails/PcComponents.vue` - Adds a DLC-only accessible details action.
- `frontend/src/v2/views/GameDetails.test.ts` - Covers the top-level parent-ID binding.
- `frontend/src/v2/components/GameDetails/OverviewTab.test.ts` - Covers overview-to-grid parent identity.
- `frontend/src/v2/components/GameDetails/RelatedGamesGrid.test.ts` - Covers grid-to-card identity.
- `frontend/src/v2/components/GameDetails/RelatedGameCard.test.ts` - Covers canonical local DLC card navigation.
- `frontend/src/v2/components/GameDetails/PcComponents.test.ts` - Covers the DLC-only component-row route action.

## Decisions Made

- Navigation is emitted through `router.push({ name: ROUTES.PC_DLC, params })`, so both entry points use the route introduced by Plan 12-02.
- Non-DLC component rows, unmatched DLC cards, and external related cards retain their previous behavior.

## Deviations from Plan

None - plan executed as specified. Test fixture corrections were limited to restoring independent mock state and generated-type compatibility.

## Verification

- `npm run test -- src/v2/views/GameDetails.test.ts src/v2/components/GameDetails/OverviewTab.test.ts src/v2/components/GameDetails/RelatedGamesGrid.test.ts src/v2/components/GameDetails/RelatedGameCard.test.ts src/v2/components/GameDetails/PcComponents.test.ts` passed, 5 files and 9 tests.
- `npm run typecheck` passed.

## Known Stubs

None.

## Next Phase Readiness

Plan 12-03 can now render the canonical DLC route while both parent-detail entry points supply the required parent and component IDs.

## Self-Check: PASSED

- Verified all ten declared implementation and test files exist.
- Verified commits `ef99c5358`, `ee0ccb7ec`, and `d1e793386` exist in Git history.
