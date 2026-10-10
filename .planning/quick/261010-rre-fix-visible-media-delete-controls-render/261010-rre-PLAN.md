# Quick Task Plan

**Task:** 261010-rre

**Goal:** Make the parent-ROM provider screenshot delete button and uploaded artwork delete button visibly render while retaining their existing scoped permission gates, labels, confirmations, loading behavior, click handlers, and styles.

**Scope:** Change only the delete-control template structure in `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue` and `ArtworkSubtab.vue`, plus focused assertions in their existing source-level Vitest tests. Use the existing `RTooltip activator="parent"` contract. Do not change permission logic, API calls, confirmation flows, localization keys, component styling, or unrelated tooltip-wrapped controls.

## Tasks

1. **Pin the regression contract in focused component tests.** Update `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.test.ts` and `ArtworkSubtab.test.ts` to assert that each owned-media delete control keeps its current delete icon, accessible label, handler, and permission/origin gate while placing `RTooltip activator="parent"` inside the `RBtn` activator pattern. Assert the delete `RTooltip` no longer owns the delete `RBtn` as its default slot, so the button remains in the rendered action row. Keep the tests source-level and focused, matching the existing `readFileSync` Vitest style.

   **Verify:** `cd frontend && npm run test -- --run src/v2/components/GameDetails/ScreenshotsSubtab.test.ts src/v2/components/GameDetails/ArtworkSubtab.test.ts` should fail before the template fix because the new structural assertions are absent.

2. **Repair both delete activators with the smallest template-only change.** Modify the provider screenshot delete control in `ScreenshotsSubtab.vue` and the uploaded-artwork delete control in `ArtworkSubtab.vue` so the visible `RBtn` remains the outer activator and contains a self-closing `<RTooltip activator="parent" :text="t('common.delete')" />`. Preserve the surrounding `canManage` gate, the artwork `item.origin === 'upload'` gate, `mdi-delete-outline`, existing `loading` bindings, accessible delete labels, click handlers, and all existing confirmation/API behavior. Do not alter styles or convert the other tooltip usages in either file.

   **Verify:** `cd frontend && npm run test -- --run src/v2/components/GameDetails/ScreenshotsSubtab.test.ts src/v2/components/GameDetails/ArtworkSubtab.test.ts`; then `npm run typecheck`.

## Files expected to change

- `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue`
- `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.test.ts`
- `frontend/src/v2/components/GameDetails/ArtworkSubtab.vue`
- `frontend/src/v2/components/GameDetails/ArtworkSubtab.test.ts`

## Dependency order

Task 1 precedes Task 2. The tests define the exact markup contract, and Task 2 makes the smallest implementation change needed to satisfy it. No backend, API service, store, permission map, locale, generated type, or style changes are required.

## Acceptance criteria

- Parent provider screenshot delete `RBtn` is visible in the action row for users passing the existing scoped `rom.edit` `canManage` gate.
- Uploaded artwork delete `RBtn` is visible only when the existing `canManage` and `item.origin === 'upload'` conditions pass.
- Both buttons retain `mdi-delete-outline`, the existing `common.delete` accessible label, loading state, and delete handler.
- Existing confirmation dialogs, danger tone, expected-version API calls, refreshes, snackbars, ownership/role filters, and styles remain unchanged.
- The delete tooltip text remains `common.delete`, but `RTooltip` is attached with `activator="parent"` inside the button instead of receiving the button through its default slot.
- Focused Vitest tests and frontend typecheck pass.
