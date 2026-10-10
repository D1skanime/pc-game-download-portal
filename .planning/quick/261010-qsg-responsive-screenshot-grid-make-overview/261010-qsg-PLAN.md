# Quick Task Plan

**Task:** 261010-qsg

**Goal:** Fix Overview screenshot grids so wide layouts present approximately three large, space-filling columns while tablet widths reflow cleanly without tiny cards or excessive empty space.

**Scope:** Reuse the existing `ScreenshotsTab` thumbnail/lightbox behavior and Overview ownership filtering. Add only the smallest Overview-specific layout contract needed to keep Media/Screenshots subtab grids stable. Do not change screenshot data, permissions, actions, or carousel behavior.

## Tasks

1. **Pin the Overview screenshot layout contract with focused tests.** Extend `frontend/src/v2/components/GameDetails/OverviewTab.test.ts` and, if needed for the child contract, add the smallest focused test beside `ScreenshotsTab.vue`. Cover that Overview still renders only `/api/roms/` screenshots and passes the Overview layout mode to `ScreenshotsTab`; assert the responsive CSS contract uses a large card minimum and breakpoint-safe `auto-fit`/available-space behavior rather than the current `220px` minimum. Keep the existing protected URL filtering and read-only Overview behavior asserted.

   **Verify:** `cd frontend && npm run test -- --run src/v2/components/GameDetails/OverviewTab.test.ts` plus any new focused screenshot-grid test.

2. **Implement the Overview-specific responsive screenshot grid.** Update `frontend/src/v2/components/GameDetails/ScreenshotsTab.vue` to expose a narrowly scoped layout/variant prop (or equivalent existing component pattern), apply it from `OverviewTab.vue`, and style that variant with the repository’s v2 responsive rules: wide content should naturally settle near three columns with large 16:9 cards, cards should expand to fill the available row width, and tablet/smaller widths should drop columns before cards become cramped. Preserve the default grid used by `ScreenshotsSubtab.vue` and `PcDlcDetail.vue`, existing hover/touch/gamepad action visibility, lazy images, stable keys, and lightbox behavior. Use the existing `data-bp`/responsive conventions and design tokens; do not add raw media-query layout rules or a parallel screenshot component.

   **Verify:** `cd frontend && npm run test -- --run src/v2/components/GameDetails/OverviewTab.test.ts src/v2/components/GameDetails/ScreenshotsSubtab.test.ts src/v2/components/GameDetails/PcDlcDetail.test.ts`; `cd frontend && npm run typecheck`.

## Files expected to change

- `frontend/src/v2/components/GameDetails/ScreenshotsTab.vue`
- `frontend/src/v2/components/GameDetails/OverviewTab.vue`
- `frontend/src/v2/components/GameDetails/OverviewTab.test.ts`
- `frontend/src/v2/components/GameDetails/ScreenshotsTab.test.ts` if a dedicated child contract test is needed

## Dependency order

Task 1 precedes Task 2. Task 2 must preserve the existing default behavior for all non-Overview callers.

## Acceptance criteria

- Overview screenshots use approximately three columns on wide game-detail layouts, with large 16:9 cards that use the available row width.
- Tablet widths reflow to fewer columns before thumbnails become awkwardly narrow, without a large unused side gap.
- Media/Screenshots subtab and DLC screenshot grids retain their existing layout and behavior.
- Overview still excludes provider-only screenshot URLs and keeps the existing read-only/lightbox/action behavior.
- Focused Vitest tests and frontend typecheck pass.
