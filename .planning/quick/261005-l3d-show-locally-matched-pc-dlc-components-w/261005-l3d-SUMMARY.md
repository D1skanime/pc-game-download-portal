---
quick_id: 261005-l3d
subsystem: pc-components-ui
tags: [pc-components, dlc, expansions, vue, filesystem]
requires:
  - PC component metadata and owned/local component media
provides:
  - Exact expansion directory aliases classified as DLC components
  - Covered local DLC and expansion overview cards with local detail routes
affects: [PC scans, GameDetails overview, component metadata]
tech-stack:
  added: []
  patterns:
    - Local component candidates enrich remote IGDB cards by IGDB ID
key-files:
  modified:
    - backend/handler/filesystem/roms_handler.py
    - frontend/src/v2/views/GameDetails.vue
    - frontend/src/v2/components/GameDetails/RelatedGamesGrid.vue
key-decisions:
  - "Only exact top-level expansion and expansions directories alias to DLC."
  - "Matching remote entries keep their IGDB identity while using local cover and route data."
duration: 6min
completed: 2026-10-05
---

# Quick Task 261005-l3d Summary

**Local PC DLC and expansion components with covered media now appear as deduplicated overview cards that open their component detail pages.**

## Accomplishments

- Classified only `expansion` and `expansions` top-level component roots as the existing DLC kind.
- Derived eligible local candidates from DLC components with a positive IGDB ID, usable metadata name, and stored cover.
- Kept remote-only IGDB suggestions unchanged, merged duplicate IDs into one remote-identity card, and routed all local cards to `ROUTES.PC_DLC`.
- Added regression coverage for aliases, local-only cards, deduplication, stored covers, owned state, and local routes.

## Task Commits

1. `e468012b7` `test(261005-l3d): add DLC overview regressions`
2. `887e35cea` `feat(261005-l3d): show matched local PC DLC cards`

## Verification

- Passed: `cd frontend && npm run test -- OverviewTab RelatedGamesGrid RelatedGameCard`
- Passed: `cd frontend && npm run typecheck`
- Blocked by local infrastructure: `cd backend && uv run pytest tests/handler/filesystem/test_roms_handler.py -k 'pc_component or component_paths'` cannot connect to MariaDB at `127.0.0.1:3306` before executing the selected tests.
- Isolated UAT passed: a targeted QUICK rescan reclassified the existing `expansion/Hearts of Stone` component as `dlc`, alongside the Witcher base ISO, so it is eligible for the same metadata, cover, and overview-card flow.

## Decisions Made

- Expansion folder names are aliases to the existing DLC component kind, with no API or enum change.
- Only `kind === "dlc"` components qualify, preventing unresolved and extra directories from surfacing.
- A local matching cover takes precedence only when a matching local component exists; remote cards retain their original text and identity.

## Deviations from Plan

None - plan implementation followed the specified scope. Backend integration verification is pending local MariaDB availability.

## Known Stubs

None.

## Next Phase Readiness

Ready for review. Re-run the targeted backend pytest command when the local MariaDB test service is available.
