# Owned OST Background Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a game use a random, operator-selected mix of local OST files and RomM-uploaded soundtrack tracks as background audio on its v2 detail route.

**Architecture:** Preserve `rom_local_background_audio` for immutable source-library files. Add an owned-media-only selection relation and protected replacement endpoint, expose its ids in `DetailedRomSchema`, then merge both selected sources into the existing `useBackgroundAudio` lifecycle. The manual owned soundtrack queue and player remain independent from background selection.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic, Vue 3, TypeScript, Pinia, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-28-local-ost-background-audio-design.md`

## Global Constraints

- Work only in `/home/d1sk/romm` and preserve unrelated worktree changes.
- Never modify a source-library file, NAS mount, Team4s, Docker Compose configuration, or legacy source-writing soundtrack route.
- Keep local and RomM-owned background-audio relations separate, with foreign-key cleanup and no polymorphic id column.
- Owned selection accepts only active, same-ROM `soundtrack` media at write time and uses the parent-ROM optimistic `expected_version` contract. A later inactive selection row may remain but is ignored for playback.
- Manual soundtrack queue, ordering, mini-player, upload, download, and deletion behavior stay separate from background selection.
- Background audio starts only on the active detail route, randomly from one combined collection of all selected valid local and active owned candidates, with equal per-candidate probability regardless of source type. It stops on cleanup or playback failure.
- Use existing `R*` primitives, `useCan`, typed API methods, translated copy, and native linear focus order.
- Generate frontend API types after backend contract changes. Do not hand-edit `frontend/src/__generated__/`.

## Review Focus

- A different-ROM owned id must be rejected without changing selection. Task 1 handler and endpoint tests cover it.
- Artwork or inactive owned candidates must not be newly written as background-selected. Inactive persisted rows must be ignored for playback. Tasks 1 and 2 cover validation and filtering.
- Physical deletion of a selected owned candidate must cascade its selection; mere deactivation need not. Task 1 covers it.
- Owned playback must use the owned content route, never a source-library route. Task 2 covers it.
- Autoplay rejection, route leave, and ROM change must clear background audio without affecting the manual player. Task 2 covers it.

---

### Task 1: Owned background-audio persistence and protected API

**Files:**

- Create: `backend/alembic/versions/0131_owned_background_audio.py`
- Modify: `backend/models/rom.py`
- Modify: `backend/handler/database/roms_handler.py`
- Modify: `backend/endpoints/responses/rom.py`
- Modify: `backend/endpoints/roms/media.py`
- Test: `backend/tests/handler/database/test_rom_media.py`
- Test: `backend/tests/endpoints/roms/test_media.py`

**Interfaces:**

- Consumes: existing local-background selection and owned-media placement optimistic-lock patterns.
- Produces: `RomOwnedBackgroundAudio`; `RomOwnedBackgroundAudioRequest(media_ids: list[int], expected_version: UTCDatetime)`; `DetailedRomSchema.owned_background_audio_media_ids: list[int]`; and `replace_owned_background_audio(rom_id: int, expected_updated_at: datetime, media_ids: list[int]) -> Rom | None`.

- [ ] **Step 1: Write failing handler tests**

```python
def test_owned_background_audio_accepts_only_active_same_rom_soundtracks(rom):
    track = make_owned_soundtrack(rom)
    selected = db_rom_handler.replace_owned_background_audio(
        rom.id, rom.updated_at, [track.id]
    )
    assert selected.owned_background_audio_media_ids == [track.id]
    assert db_rom_handler.replace_owned_background_audio(
        rom.id, selected.updated_at, [foreign_track.id]
    ) is None
    assert db_rom_handler.replace_owned_background_audio(
        rom.id, selected.updated_at, [artwork.id]
    ) is None
```

Add separate cases for duplicate ids, inactive-media write rejection, stale version, deactivation retaining the historical row, and physical candidate deletion cascading the relation.

- [ ] **Step 2: Verify the tests fail**

Run: `cd backend && uv run pytest tests/handler/database/test_rom_media.py -k owned_background_audio -q`

Expected: FAIL because the model, property, and handler method do not exist.

- [ ] **Step 3: Add the migration, ORM relation, and handler**

Create additive revision `0131_owned_background_audio` after `0130_local_background_audio`. Add `rom_owned_background_audio(rom_id, media_id)` with cascading foreign keys, a pair uniqueness constraint, and a ROM index. Add ROM and owned-media relationships and a stable id projection. Lock and preload owned candidates/selections, require same-ROM active soundtrack media for each incoming id, atomically replace rows, update `updated_at`, and return the hydrated ROM. Do not delete a historical relation merely because its candidate later becomes inactive.

- [ ] **Step 4: Add request, schema, and protected endpoint**

Use `media_ids` with the positive/unique validation used by owned placement reorder. Add `PUT /{id}/media/owned-background-audio`, applying `_visible_rom`, `Scope.ROMS_WRITE`, and `_conflict` as the local-background route does.

- [ ] **Step 5: Write endpoint tests and verify green**

```python
response = client.put(
    f"/api/roms/{rom.id}/media/owned-background-audio",
    headers={"Authorization": f"Bearer {access_token}"},
    json={"media_ids": [track.id], "expected_version": rom.updated_at.isoformat()},
)
assert response.status_code == status.HTTP_200_OK
assert response.json()["owned_background_audio_media_ids"] == [track.id]
```

Add visibility/scope and foreign-id rejection cases.

Run: `cd backend && uv run pytest tests/handler/database/test_rom_media.py tests/endpoints/roms/test_media.py -k 'owned_background_audio or local_background_audio' -q`

Expected: PASS, or record the existing host-DB blocker without altering pytest, Compose, or services.

- [ ] **Step 6: Verify migrations and commit**

Extend the established disposable migration verifier through revision 0131, requiring fresh upgrade, downgrade one, re-upgrade, and cleanup.

```bash
git add backend/alembic/versions/0131_owned_background_audio.py backend/models/rom.py backend/handler/database/roms_handler.py backend/endpoints/responses/rom.py backend/endpoints/roms/media.py backend/tests/handler/database/test_rom_media.py backend/tests/endpoints/roms/test_media.py
git commit -m "feat: select owned background audio"
```

### Task 2: Unified v2 selection and playback

**Files:**

- Modify: `frontend/src/services/api/rom.ts`
- Modify: `frontend/src/services/api/rom.test.ts`
- Modify: `frontend/src/v2/components/GameDetails/SoundtrackPanel.vue`
- Modify: `frontend/src/v2/components/GameDetails/SoundtrackPanel.test.ts`
- Modify: `frontend/src/v2/views/GameDetails.vue`
- Modify: `frontend/src/v2/views/GameDetails.test.ts`
- Modify: `frontend/src/v2/composables/useBackgroundAudio/index.test.ts`
- Regenerate: `frontend/src/__generated__/`

**Interfaces:**

- Consumes: Task 1's owned id field and endpoint.
- Produces: `romApi.replaceOwnedBackgroundAudio({ romId, mediaIds, expectedVersion })`, owned-track background toggle controls, and one `BackgroundAudioTrack[]` from local and owned selections.

- [ ] **Step 1: Write failing frontend service and view tests**

Add a service expectation for `PUT /roms/41/media/owned-background-audio` and `{ media_ids: [12, 13], expected_version: ... }`. Require the panel to use `owned_background_audio_media_ids`, `replaceOwnedBackgroundAudio`, a toggle, and selected badge. Require GameDetails to admit owned media only when selected, active, and `role === "soundtrack"`, using its owned content URL. Add a behavioral test that selected local and owned candidates are passed as one combined collection to `playRandom`, so probability is per candidate rather than split by source type.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm run test -- src/services/api/rom.test.ts src/v2/components/GameDetails/SoundtrackPanel.test.ts src/v2/views/GameDetails.test.ts --run`

Expected: FAIL because the generated field, typed service API, control, and unified selection do not yet exist.

- [ ] **Step 3: Generate API types and implement the service**

Run `cd frontend && npm run generate` against the active local backend. Import the generated request type in `services/api/rom.ts`; implement the typed PUT method. Never edit generated files manually.

- [ ] **Step 4: Implement independent owned-track background controls**

Derive `selectedOwnedTrackIds` and implement `toggleOwnedBackgroundAudio(mediaId: number)`. Replace the complete selected id set with the typed API, refresh canonical state on success, and retain existing conflict feedback. Render the same translated background action and badge for active owned tracks in both included and available lists, independent of manual queue inclusion; gate it with `canManage`.

- [ ] **Step 5: Implement unified active-route selection**

Replace the local-only GameDetails computation with one combined array of selected local and selected active owned candidates. Keep local file URLs unchanged. Owned URLs must be `/api/roms/${rom.id}/media/${media.id}/content`. Pass that single array once to `backgroundAudio.playRandom(tracks)`, never choose a source type first, and do not use `soundtrackPlayer` or `MiniPlayer`.

- [ ] **Step 6: Test green, typecheck, and commit**

Extend the audio-composable test for an owned content URL and preserve rejection cleanup. Add panel toggle-off and GameDetails cleanup tests. Add the explicit mixed-source regression test: local plus owned candidates reach one `playRandom` invocation as one array, and inactive owned candidates are absent from that array.

Run: `cd frontend && npm run test -- src/services/api/rom.test.ts src/v2/components/GameDetails/SoundtrackPanel.test.ts src/v2/views/GameDetails.test.ts src/v2/composables/useBackgroundAudio/index.test.ts --run && npm run typecheck`

Expected: PASS.

```bash
git add frontend/src/services/api/rom.ts frontend/src/services/api/rom.test.ts frontend/src/v2/components/GameDetails/SoundtrackPanel.vue frontend/src/v2/components/GameDetails/SoundtrackPanel.test.ts frontend/src/v2/views/GameDetails.vue frontend/src/v2/views/GameDetails.test.ts frontend/src/v2/composables/useBackgroundAudio/index.test.ts frontend/src/__generated__
git commit -m "feat: play owned tracks as background audio"
```

### Task 3: Regression verification and UAT record

**Files:**

- Modify: `.planning/phases/20-media-management-and-owned-soundtrack-uploads/20-UAT.md`
- Modify: `.planning/phases/20-media-management-and-owned-soundtrack-uploads/20-VALIDATION.md`

**Interfaces:**

- Consumes: the backend contract and v2 behavior from Tasks 1 and 2.
- Produces: truthful automated evidence and a UAT case distinguishing local and owned background candidates.

- [ ] **Step 1: Add the UAT scenario**

Require: upload supported audio, mark it as background without manual queue inclusion, leave and re-enter Witcher 3's active v2 detail route, and confirm it is eligible for background playback. Record autoplay policy silence separately from manual player playback. Confine testing to RomM-owned media.

- [ ] **Step 2: Run regression verification**

Run: `cd frontend && npm run test && npm run typecheck && npm run build && python3 src/locales/check_i18n_locales.py && python3 src/locales/check_i18n_sorted.py`

Expected: PASS with any unrelated failure or warning recorded exactly. Run Task 1 backend/migration checks and `trunk check` without blanket-formatting the dirty tree.

- [ ] **Step 3: Perform browser UAT and record only observed results**

Verify a selected uploaded track after a route change, an unselected upload remains silent, local selected OST tracks still work, the manual playlist is unaffected, and deletion prevents future selection. Record browser/version, pass/fail, defects, and autoplay-policy outcome.

- [ ] **Step 4: Commit evidence after results are known**

```bash
git add .planning/phases/20-media-management-and-owned-soundtrack-uploads/20-UAT.md .planning/phases/20-media-management-and-owned-soundtrack-uploads/20-VALIDATION.md
git commit -m "test: verify owned background audio"
```
