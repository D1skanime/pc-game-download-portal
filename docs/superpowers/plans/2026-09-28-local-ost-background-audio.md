# Local OST Background Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators mark scanned local OST tracks as a game's background music, then randomly play one when that game's detail page opens without copying source files.

**Architecture:** A dedicated relation persists selected `RomFile` soundtrack ids per ROM and is exposed in the existing detailed-ROM contract. The Media soundtrack panel manages only that relation for local tracks. A dedicated hidden background-audio composable plays one selected protected file URL from `GameDetails`, independently from the interactive owned-soundtrack player.

**Tech Stack:** Python 3.13, SQLAlchemy 2.0, Alembic, FastAPI, Vue 3, Pinia, Vitest, vue-i18n.

**Spec:** `docs/superpowers/specs/2026-09-28-local-ost-background-audio-design.md`

## Global Constraints

- Read original GOG OST files only. Never copy, upload, modify, or delete source-library audio.
- Recognize `ost`, `soundtrack`, and `soundtracks` directory segments as soundtrack categories.
- Persist only validated same-ROM `RomFile` records whose category is `soundtrack`.
- Use protected ROM-file content reads for playback and stop the hidden audio on detail-route leave.
- Do not add local-track play, pause, upload, download, sorting, or deletion controls to Media.
- Keep the existing owned-soundtrack upload and interactive player behavior unchanged.
- Add all user-visible translation keys to every locale and keep locale JSON sorted.

## Review Focus

- A file called `track.mp3` outside an OST/soundtrack directory remains unclassified and cannot be selected.
- A soundtrack file from a different ROM cannot be selected, even when its id is supplied directly.
- A rescan that drops or reclassifies a selected file removes its selection without leaving a stale playable reference.
- No selected tracks, a failed content read, or browser autoplay rejection leaves no audio playing and no visible fallback player.
- Re-entering the same ROM and moving between ROM detail pages stops the previous hidden track before selecting a new one.

---

### Task 1: Scan categorization and durable local background-audio selection

**Files:**

- Modify: `backend/handler/filesystem/roms_handler.py:category_matches`
- Modify: `backend/models/rom.py`
- Create: `backend/alembic/versions/0130_local_background_audio.py`
- Modify: `backend/handler/database/roms_handler.py`
- Modify: `backend/endpoints/responses/rom.py`
- Test: `backend/tests/handler/filesystem/test_roms_handler.py`
- Test: `backend/tests/handler/database/test_rom_media.py`

**Interfaces:**

- Consumes: `RomFileCategory.SOUNDTRACK`, `Rom.updated_at`, and `RomFile` scan lifecycle.
- Produces: `RomLocalBackgroundAudio`, `Rom.local_background_audio`, `DetailedRomSchema.local_background_audio_file_ids: list[int]`, and `DBRomsHandler.replace_local_background_audio(rom_id: int, expected_updated_at: datetime, file_ids: list[int]) -> Rom | None`.

- [ ] **Step 1: Write failing scan and database contract tests**

```python
def test_ost_directory_is_classified_as_soundtrack():
    assert category_matches("soundtrack", ["game", "ost"])

def test_local_background_audio_rejects_foreign_and_non_soundtrack_files(rom):
    assert db_rom_handler.replace_local_background_audio(
        rom.id, rom.updated_at, [foreign_file.id]
    ) is None
    assert db_rom_handler.replace_local_background_audio(
        rom.id, rom.updated_at, [game_file.id]
    ) is None
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd backend && uv run pytest tests/handler/filesystem/test_roms_handler.py tests/handler/database/test_rom_media.py -q`

Expected: FAIL because `ost` is not a soundtrack alias and the local-background-audio relation/handler does not exist.

- [ ] **Step 3: Implement scan alias, relation, migration, handler, and response contract**

Add `RomLocalBackgroundAudio` with unique `(rom_id, rom_file_id)` and cascading foreign keys. Eager-load it in `with_details`; update the scan reconciliation path so dropped `RomFile` rows cascade selections. Make `category_matches("soundtrack", ...)` accept `ost`. The handler must lock the ROM, compare `updated_at`, require every requested file to belong to the ROM and have `SOUNDTRACK` category, replace the complete selection atomically, update `rom.updated_at`, and return the hydrated ROM.

- [ ] **Step 4: Run migration and database verification**

Run: `cd backend && uv run alembic upgrade head && uv run pytest tests/handler/filesystem/test_roms_handler.py tests/handler/database/test_rom_media.py -q`

Expected: PASS, including foreign-file, category, stale-version, and cascade coverage.

- [ ] **Step 5: Commit**

```bash
git add backend/models/rom.py backend/alembic/versions/0130_local_background_audio.py backend/handler/filesystem/roms_handler.py backend/handler/database/roms_handler.py backend/endpoints/responses/rom.py backend/tests/handler/filesystem/test_roms_handler.py backend/tests/handler/database/test_rom_media.py
git commit -m "feat: persist local OST background selections"
```

### Task 2: Protected media selection API and generated client contract

**Files:**

- Modify: `backend/endpoints/roms/media.py`
- Modify: `backend/endpoints/responses/rom.py`
- Modify: `backend/tests/endpoints/roms/test_media.py`
- Regenerate: `frontend/src/__generated__/`
- Modify: `frontend/src/services/api/rom.ts`
- Test: `frontend/src/services/api/rom.test.ts`

**Interfaces:**

- Consumes: `DBRomsHandler.replace_local_background_audio` from Task 1.
- Produces: `PUT /api/roms/{id}/media/local-background-audio` accepting `{ file_ids, expected_version }` and returning `DetailedRomSchema`; `romApi.replaceLocalBackgroundAudio(...)`.

- [ ] **Step 1: Write failing endpoint and API-wrapper tests**

```python
def test_replace_local_background_audio_requires_visible_same_rom_soundtrack(client, rom):
    response = client.put(
        f"/api/roms/{rom.id}/media/local-background-audio", json=payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["local_background_audio_file_ids"] == [soundtrack.id]
```

```ts
expect(romApi.replaceLocalBackgroundAudio).toBeTypeOf("function");
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/endpoints/roms/test_media.py -q`; then `cd frontend && npm run test -- --run src/services/api/rom.test.ts`

Expected: FAIL because the protected route and typed client wrapper do not exist.

- [ ] **Step 3: Implement the route and typed wrapper**

Define a strict request schema with distinct positive `file_ids` and UTC `expected_version`. Apply `roms.write`, `_visible_rom`, and the existing conflict/re-hydration response convention. Regenerate OpenAPI types, then expose a typed service wrapper that uses the generated request type. Do not add any source-library mutation route.

- [ ] **Step 4: Run contract checks**

Run: `cd backend && uv run pytest tests/endpoints/roms/test_media.py -q && cd ../frontend && npm run typecheck && npm run test -- --run src/services/api/rom.test.ts`

Expected: PASS; hidden-ROM, cross-ROM, invalid-category, and stale-version requests are rejected.

- [ ] **Step 5: Commit**

```bash
git add backend/endpoints/roms/media.py backend/endpoints/responses/rom.py backend/tests/endpoints/roms/test_media.py frontend/src/__generated__ frontend/src/services/api/rom.ts frontend/src/services/api/rom.test.ts
git commit -m "feat: expose local OST background audio selection"
```

### Task 3: Local OST selection UI

**Files:**

- Modify: `frontend/src/v2/components/GameDetails/SoundtrackPanel.vue`
- Modify: `frontend/src/v2/components/GameDetails/SoundtrackPanel.test.ts`
- Modify: `frontend/src/locales/*/rom.json`

**Interfaces:**

- Consumes: `DetailedRomSchema.files`, `local_background_audio_file_ids`, and `romApi.replaceLocalBackgroundAudio` from Task 2.
- Produces: a read-only local-OST candidate list with one mark/unmark action and selected badge.

- [ ] **Step 1: Write failing component assertions**

```ts
expect(source).toContain('file.category === "soundtrack"');
expect(source).toContain("local_background_audio_file_ids");
expect(source).toContain("replaceLocalBackgroundAudio");
expect(source).not.toContain("/soundtracks");
```

- [ ] **Step 2: Run the component test to verify it fails**

Run: `cd frontend && npm run test -- --run src/v2/components/GameDetails/SoundtrackPanel.test.ts`

Expected: FAIL because local scanned soundtrack candidates and their selection actions are absent.

- [ ] **Step 3: Implement local OST candidate and selection rendering**

Render a separate local-OST section from `rom.files` where `category === "soundtrack"`. Use a complete replacement request so marking and unmarking preserve all other selections. Show a visible background-music badge only for selected file ids. Use `useCan`, loading state, conflict refresh, and snackbar error behavior. Do not render controls for play, pause, upload, download, sort, or delete on local rows.

- [ ] **Step 4: Add translations and run frontend verification**

Run: `cd frontend && python3 src/locales/check_i18n_locales.py && python3 src/locales/check_i18n_sorted.py && npm run test -- --run src/v2/components/GameDetails/SoundtrackPanel.test.ts && npm run typecheck`

Expected: PASS with complete sorted locales and a selected-state UI that refreshes after conflicts.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/v2/components/GameDetails/SoundtrackPanel.vue frontend/src/v2/components/GameDetails/SoundtrackPanel.test.ts frontend/src/locales/*/rom.json
git commit -m "feat: select local OST background music"
```

### Task 4: Hidden random background-audio lifecycle

**Files:**

- Create: `frontend/src/v2/composables/useBackgroundAudio/index.ts`
- Create: `frontend/src/v2/composables/useBackgroundAudio/index.test.ts`
- Modify: `frontend/src/v2/views/GameDetails.vue`
- Modify: `frontend/src/v2/views/GameDetails.test.ts`

**Interfaces:**

- Consumes: selected local `RomFile` ids from Task 2 and protected file URLs `/api/roms/{fileId}/files/content/{fileName}`.
- Produces: `useBackgroundAudio()` with `playRandom(tracks: BackgroundAudioTrack[]): void` and `stop(): void`, where `BackgroundAudioTrack` is `{ id: number; url: string }`.

- [ ] **Step 1: Write failing composable and route-lifecycle tests**

```ts
it("chooses only a supplied selected track and clears audio on stop", () => {
  const audio = useBackgroundAudio(() => 0.5);
  audio.playRandom([{ id: 2, url: "/two.mp3" }]);
  expect(createdAudio.src).toContain("/two.mp3");
  audio.stop();
  expect(createdAudio.pause).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test -- --run src/v2/composables/useBackgroundAudio/index.test.ts src/v2/views/GameDetails.test.ts`

Expected: FAIL because the hidden audio composable and route integration do not exist.

- [ ] **Step 3: Implement the dedicated hidden audio lifecycle**

Create an injectable random-source composable for deterministic tests. It owns one `HTMLAudioElement`, uses `preload="none"`, invokes `play()` without surfacing a control on rejection, and always pauses, clears `src`, and calls `load()` in `stop()`. In `GameDetails`, derive selected local soundtrack `RomFile`s, construct protected content URLs from trusted file id/name, call `playRandom` only for the active ROM detail route, and register cleanup in the existing route/background watcher.

- [ ] **Step 4: Run UI verification**

Run: `cd frontend && npm run test -- --run src/v2/composables/useBackgroundAudio/index.test.ts src/v2/views/GameDetails.test.ts src/v2/components/GameDetails/SoundtrackPanel.test.ts && npm run typecheck`

Expected: PASS; empty/failed/autoplay-blocked selections stay silent, and navigation stops the old hidden audio before a new random selection starts.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/v2/composables/useBackgroundAudio frontend/src/v2/views/GameDetails.vue frontend/src/v2/views/GameDetails.test.ts
git commit -m "feat: play selected local OST as background audio"
```

### Task 5: End-to-end migration and regression verification

**Files:**

- Test: `backend/tests/handler/database/test_rom_media.py`
- Test: `backend/tests/endpoints/roms/test_media.py`
- Test: `frontend/src/v2/components/GameDetails/SoundtrackPanel.test.ts`
- Test: `frontend/src/v2/composables/useBackgroundAudio/index.test.ts`

**Interfaces:**

- Consumes: all contracts from Tasks 1 through 4.
- Produces: verified MariaDB/PostgreSQL migration and an end-to-end safe local OST selection flow.

- [ ] **Step 1: Add migration round-trip and cross-layer regression coverage**

Add the missing assertions for migration upgrade/downgrade, selection cascade after file removal, authoritative response refresh, and route cleanup when changing games.

- [ ] **Step 2: Run backend and frontend suites**

Run: `cd backend && uv run alembic upgrade head && uv run pytest tests/handler/filesystem/test_roms_handler.py tests/handler/database/test_rom_media.py tests/endpoints/roms/test_media.py -q && cd ../frontend && npm run test -- --run src/v2/components/GameDetails/SoundtrackPanel.test.ts src/v2/composables/useBackgroundAudio/index.test.ts src/v2/views/GameDetails.test.ts && npm run typecheck`

Expected: PASS.

- [ ] **Step 3: Run formatting and static checks**

Run: `cd /home/d1sk/romm && trunk fmt && trunk check`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests frontend/src/v2 docs
git commit -m "test: cover local OST background audio flow"
```
