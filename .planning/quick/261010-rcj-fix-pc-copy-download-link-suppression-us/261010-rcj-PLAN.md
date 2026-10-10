# Quick Task Plan

**Task:** 261010-rcj

**Goal:** Suppress the copy-download-link action for real PC ROMs in both v2 action surfaces, while preserving the existing direct-link behavior for non-PC ROMs.

**Diagnosis:** `useGameActions` currently defines `isPcRom` as `platform_slug === "pc"`. The generated ROM shape also carries `platform_fs_slug`, and scanned PC ROMs use `platform_slug: "win"` with `platform_fs_slug: "pc"`. Because `GameActions.vue` uses `canShowCopyDownloadLink` for the header circle and `GameActionsList.vue` uses the same value for More, both surfaces incorrectly expose copy-link for real PC ROMs.

**Scope:** Make the shared PC predicate recognize the filesystem slug used by the real ROM shape, retain compatibility with the existing `platform_slug: "pc"` case, and leave the PC download-selection route and all non-PC actions unchanged. Add focused Vitest coverage at the composable and both consuming surfaces. Do not change backend contracts, generated types, translations, or product behavior outside this gate.

## Tasks

1. **Correct the shared PC classification and add regression coverage.** Update `frontend/src/v2/composables/useGameActions/index.ts` so `isPcRom` treats a ROM as PC when `platform_fs_slug === "pc"` or the existing `platform_slug === "pc"` compatibility shape is present. Keep `download()` routed to `/rom/:id?tab=pc-components` for that predicate and keep `canShowCopyDownloadLink` true for non-PC ROMs. Extend `frontend/src/v2/composables/useGameActions/index.test.ts` with focused cases for the real `{ platform_slug: "win", platform_fs_slug: "pc" }` shape, the legacy `{ platform_slug: "pc" }` shape, and a non-PC shape. Assert both copy-link visibility and PC download routing, while avoiding unrelated action tests.

   **Verify:** `cd frontend && npm run test -- --run src/v2/composables/useGameActions/index.test.ts`

2. **Prove both UI consumers hide only the PC copy-link action.** Extend `frontend/src/v2/components/GameActions/GameActionsList.test.ts` to assert the More menu omits `rom.copy-link` for the real PC shape and keeps it for a non-PC ROM. Add `frontend/src/v2/components/GameActions/GameActions.test.ts` with shallow focused coverage of the header action row, asserting the copy-link `GameActionBtn` is absent for `{ platform_slug: "win", platform_fs_slug: "pc" }` and present for a non-PC ROM. Keep the existing download button and other action controls present in both cases, and do not duplicate the composable's routing assertions in component tests.

   **Verify:** `cd frontend && npm run test -- --run src/v2/components/GameActions/GameActionsList.test.ts src/v2/components/GameActions/GameActions.test.ts`; `cd frontend && npm run typecheck`

## Files expected to change

- frontend/src/v2/composables/useGameActions/index.ts
- frontend/src/v2/composables/useGameActions/index.test.ts
- frontend/src/v2/components/GameActions/GameActionsList.test.ts
- frontend/src/v2/components/GameActions/GameActions.test.ts

## Dependency order

Task 1 precedes Task 2 because the component tests must exercise the corrected shared predicate. Task 2 only adds consumer-level regression coverage and must not introduce a second PC classification.

## Acceptance criteria

- A ROM shaped as `platform_slug: "win", platform_fs_slug: "pc"` has no copy-download-link action in the GameDetails header circle or its More menu.
- The existing `platform_slug: "pc"` shape remains treated as PC.
- Non-PC ROMs continue to expose copy-download-link in both surfaces.
- PC Download still opens the existing `pc-components` selection tab, and non-PC Download still uses the existing direct file download path.
- The focused composable and component tests pass, and frontend typecheck passes.
- No product code outside the shared action predicate and focused tests is changed; no commit is created.
