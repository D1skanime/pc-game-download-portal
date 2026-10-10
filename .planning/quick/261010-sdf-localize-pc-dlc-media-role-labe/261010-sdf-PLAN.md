# Quick Task Plan

**Task:** 261010-sdf

**Goal:** Replace raw PC DLC media role enum values in the role dropdown with localized UI labels while preserving the enum values used for filtering and uploads.

**Scope:** Update only the PC DLC media role selector and its focused regression coverage. Reuse the existing `rom.pc-media-role-*` translations and `RSelect` item-title/item-value pattern. Do not change the backend media contract, role values, filtering semantics, upload payloads, or unrelated media labels.

## Findings

- `frontend/src/v2/components/GameDetails/PcDlcMediaTab.vue` currently passes `roles` as a `RomComponentOwnedMediaRole[]` directly to `RSelect`.
- The current model is `role`, and both `filteredMedia` and `upload()` use that value as the backend enum, so the selected value must remain one of `cover`, `gallery`, `screenshot`, or `artwork`.
- `RSelect` supports object items with `item-title` and `item-value`; this is the established way to separate a display label from the selected value.
- Existing locale keys already cover all four roles: `rom.pc-media-role-cover`, `rom.pc-media-role-gallery`, `rom.pc-media-role-screenshot`, and `rom.pc-media-role-artwork`. No new locale keys are required.
- Existing `PcDlcMediaTab.test.ts` already guards localized card role labels; it needs an additional selector-specific regression guard.

## Tasks

1. **Provide localized selector items without changing role values.** In `frontend/src/v2/components/GameDetails/PcDlcMediaTab.vue`, retain the typed enum list as the source of truth and derive an item list whose `title` is `t(\`rom.pc-media-role-${value}\`)`and whose`value`is the original enum. Bind`RSelect`with`:items`, `item-title="title"`, and `item-value="value"`. Keep `v-model="role"`, the screenshot default, `filteredMedia`, and the upload `role` form field unchanged.

   **Verify:** Confirm the dropdown displays localized labels while `role.value` remains the enum used by filtering and upload. Check that all four roles are represented and no raw role enum is used as the display title.

2. **Add focused regression coverage.** Extend `frontend/src/v2/components/GameDetails/PcDlcMediaTab.test.ts` with source-level assertions for the localized role-item mapping and the `RSelect` `item-title`/`item-value` bindings. Assert that the existing enum model remains connected to filtering and upload, and that the existing `rom.pc-media-role-*` translation path is used. Keep tests narrow to this dropdown behavior.

   **Verify:** Run the focused `PcDlcMediaTab.test.ts` suite and the frontend typecheck. If the component test harness supports mounting the selector, additionally verify the rendered titles and emitted enum value; otherwise retain the repository's established source-regression style.

## Files expected to change

- `frontend/src/v2/components/GameDetails/PcDlcMediaTab.vue`
- `frontend/src/v2/components/GameDetails/PcDlcMediaTab.test.ts`

## Acceptance criteria

- The PC DLC media role dropdown shows localized UI labels for Cover, Gallery image/Galeriebild, Screenshot, and Artwork.
- No raw enum values are presented as dropdown labels.
- Selecting a displayed role still sets `role` to its original enum value and filters the corresponding media.
- Upload requests still send the original enum in the `role` form field.
- Existing screenshot default, media loading, deletion, placement, permission, and refresh behavior remain unchanged.
- Focused regression tests and frontend typecheck pass.
- No source files outside the two scoped frontend files are changed, and no commit or deployment is performed as part of planning.
