---
quick_id: 261010-twn
description: Make PC DLC media deletion tolerate already-missing owned files while preserving database deletion and component-version semantics.
type: tdd
---

# Plan

## Objective

Make DELETE /api/roms/{id}/pc-components/{component_id}/media/{media_id} idempotent with respect to the owned file: a missing file must not turn a successful database deletion into HTTP 500. The database row/placements must still be deleted, the DLC component updated_at version must still advance, and normal filesystem failures must retain the established cleanup-intent behavior where applicable. Do not broaden the endpoint scope, alter authorization, or change stale-version/404 semantics.

## Tasks

1. **Add the focused RED regression for an already-missing PC DLC media file.** Extend backend/tests/endpoints/roms/test_pc_component_resources.py with a deletion test that creates a DLC component-owned media row whose owned_path does not exist, captures the component version, invokes the DELETE endpoint with that exact version, and asserts the request succeeds, the media is absent from the component response/database, and the component version has advanced. Patch fs_resource_handler.remove_file to raise FileNotFoundError so the test deterministically reproduces the reported id 22 failure without touching real storage. Also assert the missing-file cleanup does not cause a second error or change the endpoint response contract. Run the focused endpoint test before implementation and confirm it fails with the current 500 behavior.

2. **Implement the smallest backend idempotency fix by following the existing parent-media deletion handling.** Update backend/endpoints/roms/pc_component_resources.py::delete_component_media so the database mutation remains first and authoritative, while FileNotFoundError from removing the already-absent owned path is treated as successful cleanup. Preserve the current 404 response when the database deletion returns None, the current authorization and expected-version checks, and the existing success payload. For other filesystem/OS failures, reuse the established parent-media cleanup-intent approach only if the existing PC-component cleanup model/API supports it; otherwise keep the change narrowly scoped to the proven missing-file case and document why. Do not catch database errors, roll back the committed row deletion, or introduce a second deletion architecture.

3. **Expand regression coverage for deletion/version semantics and run verification.** Keep or add assertions for a present-file delete, stale expected version, unknown media id, and placement cascade/absence as covered by the existing PC component resource tests. Verify the new missing-file case returns HTTP 200, removes the media from subsequent GET state, and exposes the refreshed component version expected by the client. Run:

   - cd backend && uv run pytest tests/endpoints/roms/test_pc_component_resources.py -q
   - the relevant database PC-component resource tests if the implementation touches their contract
   - the repository normal backend type/lint check for touched Python files, if configured

## Files expected to change

- backend/endpoints/roms/pc_component_resources.py
- backend/tests/endpoints/roms/test_pc_component_resources.py
- backend/tests/handler/database/test_pc_component_resources.py only if existing database/version coverage must be extended

## Acceptance criteria

- Deleting a PC DLC media record whose owned file is already absent returns success rather than HTTP 500.
- The media row is deleted, its placements do not remain, and the DLC component version is advanced exactly as for a normal deletion.
- A real existing file is still removed normally.
- Unknown media and stale expected_version behavior remain unchanged.
- No frontend, schema, storage mapping, or deployment changes are included.
- Only the requested plan artifact is created in this planning-only task; no source code or commit is produced.
