# Phase 7: V2 Storage Administration Experience - Research

## Existing Integration Surface

- `backend/endpoints/storage.py` and `backend/endpoints/responses/storage.py` expose the authoritative root, browse, mapping, test, and preview contracts produced by Phases 3-6.
- `frontend/src/__generated__/` remains the only source for browser-side API shapes; generated code must not be edited.
- `frontend/src/v2/components/Settings/` provides the Settings shell and existing v2 administration conventions.
- `frontend/src/v2/components/Settings/FolderMappingsSection.vue` is a legacy folder-mapping UI pattern, not the Phase 7 storage workflow. Phase 7 must not extend it into a competing draft model.
- `frontend/src/v2/lib/structural/RList/`, `RListItem/`, and state/action primitives support the required compact root list and drill-down browser.

## Planning Constraints

1. Use the canonical `platform-storage-mapping` route and converge Settings and platform entry points there.
2. Keep active mapping and editable draft separate. Every browse/test failure preserves the draft; a replacement only activates after explicit tested save.
3. Render only friendly root identity and authorized relative breadcrumbs. Never derive or display absolute paths.
4. Preview is a post-save status. Pending, partial, stale, and failure states must update locally while the page shell and navigation remain stable.
5. Compose existing universal-input mechanisms; do not introduce a new focus system.
6. Mapping removal requires a confirmation and must state that original files remain unchanged.

## Recommended Plan Shape

- Wave 1: typed v2 storage API/composable and route/entry convergence.
- Wave 2: root overview plus folder-browser and mapping draft workflow.
- Wave 3: safety-test, save/conflict, preview/recovery states, accessibility, and focused tests.

## Verification Approach

Keep Phase 7 implementation checks focused on the changed components, typecheck, and user-flow tests. Defer the expensive final live NAS/operational proof to Phase 9 as agreed.
