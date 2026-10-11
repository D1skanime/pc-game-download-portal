# Phase 20: Media management and owned soundtrack uploads - Pattern Map

**Mapped:** 2026-09-28
**Files analyzed:** 17
**Analogs found:** 17 / 17

## File Classification

| New/Modified File                                              | Role      | Data Flow                  | Closest Analog                                           | Match Quality |
| -------------------------------------------------------------- | --------- | -------------------------- | -------------------------------------------------------- | ------------- |
| `backend/models/rom.py`                                        | model     | CRUD                       | same file, `RomComponentOwnedMedia`                      | role-match    |
| `backend/alembic/versions/0xxx_parent_rom_media.py`            | migration | transform                  | `0117_component_owned_media_and_notes.py`                | exact         |
| `backend/endpoints/responses/rom.py`                           | schema    | transform                  | same file, `PcComponentOwnedMediaSchema`                 | role-match    |
| `backend/handler/database/roms_handler.py`                     | service   | CRUD                       | same file, component owned-media helpers                 | role-match    |
| `backend/handler/filesystem/resources_handler.py`              | service   | file-I/O                   | same file, component-owned resource writers              | exact         |
| `backend/endpoints/roms/media.py`                              | route     | request-response, file-I/O | `pc_component_resources.py`                              | role-match    |
| `backend/endpoints/roms/__init__.py`                           | config    | request-response           | same file, router inclusion block                        | exact         |
| `backend/tests/endpoints/roms/test_media.py`                   | test      | request-response           | `test_pc_component_resources.py`                         | role-match    |
| `backend/tests/handler/database/test_rom_media.py`             | test      | CRUD                       | `test_pc_component_resources.py`                         | role-match    |
| `frontend/src/services/api/rom.ts`                             | service   | request-response           | same file, typed ROM methods                             | exact         |
| `frontend/src/stores/roms.ts`                                  | store     | transform                  | same file, `DetailedRomSchema` alias/current ROM refresh | exact         |
| `frontend/src/stores/soundtrackPlayer.ts`                      | store     | event-driven               | same file, `PlayerTrack` and ordered playlist            | exact         |
| `frontend/src/v2/components/GameDetails/MediaTab.vue`          | component | request-response           | same file, subtab shell                                  | exact         |
| `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue` | component | CRUD, file-I/O             | same file, owned upload/delete and refresh               | role-match    |
| `frontend/src/v2/components/GameDetails/ArtworkSubtab.vue`     | component | CRUD, file-I/O             | same file, gallery plus `PcDlcMediaTab.vue`              | role-match    |
| `frontend/src/v2/components/GameDetails/SoundtrackPanel.vue`   | component | event-driven, file-I/O     | same file, `selectTrack` queue loading                   | role-match    |
| `frontend/src/v2/views/GameDetails.vue`                        | component | event-driven               | same file, resolved background setter                    | exact         |
| `frontend/src/v2/components/AppShell/BackgroundArt.vue`        | component | event-driven               | same file, two-layer cross-fade                          | exact         |
| `frontend/src/locales/*/rom.json`                              | config    | transform                  | existing `rom.json` key grouping                         | exact         |

## Pattern Assignments

### `backend/models/rom.py`, `backend/alembic/versions/0xxx_parent_rom_media.py`, and `backend/endpoints/responses/rom.py`

**Analogs:** `backend/models/rom.py:113-125,385-429`, `backend/alembic/versions/0117_component_owned_media_and_notes.py:27-115`, `backend/endpoints/responses/rom.py:343-369`.

Create parent-ROM candidate and placement tables, separate from `Rom.path_screenshots`, `RomFile`, and component media. Model a durable provider identity/tombstone on the candidate, and placement purpose plus `position` on a child placement table. Use `native_enum=False` and checks in the migration to remain portable across MariaDB, MySQL, and PostgreSQL.

```python
class RomComponentOwnedMediaRole(enum.StrEnum):
    COVER = "cover"
    BACKGROUND = "background"
    GALLERY = "gallery"
    SCREENSHOT = "screenshot"
    ARTWORK = "artwork"
    SOUNDTRACK = "soundtrack"

class RomComponentOwnedMedia(BaseModel):
    __tablename__ = "rom_component_owned_media"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="CASCADE")
    )
    mime_type: Mapped[str] = mapped_column(String(length=100))
    owned_path: Mapped[str] = mapped_column(String(length=FILE_PATH_MAX_LENGTH))
```

Copy migration timestamp helper and explicit indexes/foreign keys from `0117...:17-115`. Add response schemas beside `PcComponentOwnedMediaSchema`, use `ConfigDict(from_attributes=True)`, `extra="forbid"` on mutation requests, `UTCDatetime` for expected version, and expose the resolved catalog/placements on `DetailedRomSchema` (`responses/rom.py:764-835`).

### `backend/handler/database/roms_handler.py`

**Analog:** `backend/handler/database/roms_handler.py:2022-2226`.

Follow `@begin_session`, scoped parent lookup, expected-version check, `session.flush()`, and `None` for stale/missing writes. Unlike the component analogue, do not replace same-role candidates and do not let normal scan import mutate this catalog. Implement dedicated methods for explicit refresh reconciliation, provider tombstone delete, placement toggle, and complete-list atomic reorder. Candidate deletion removes placements; placement removal must leave candidate bytes and record intact.

```python
@begin_session
def create_pc_component_owned_media(..., expected_updated_at: datetime, ...):
    component = self._get_pc_dlc_component(
        session, rom_id, component_id, expected_updated_at, with_owned_media=True
    )
    if component is None:
        return None
    media = RomComponentOwnedMedia(...)
    session.add(media)
    component.updated_at = datetime.now(timezone.utc)
    session.flush()
    return AppliedPcComponentOwnedMedia(media, replaced_owned_paths)
```

The parent implementation should version the ROM or a dedicated catalog version consistently. Reorder receives the full placement ID list and expected version, validates exact membership/no duplicates, assigns sequential positions in one transaction, then returns the canonical order. A refresh can reactivate provider tombstones but creates no placement.

### `backend/handler/filesystem/resources_handler.py`

**Analog:** `backend/handler/filesystem/resources_handler.py:150-205`.

All Phase 20 writes use `FSResourcesHandler` under `rom.fs_resources_path`, never `fs_rom_handler`. Provider downloads require HTTPS, stream with size caps, verify decoded image bytes, map a MIME allowlist to extension, then call `write_file`. Generate server-controlled parent-ROM paths/names for uploads; never use client filename as a destination path.

```python
async with httpx_client.stream("GET", url, timeout=30) as response:
    if response.status_code != status.HTTP_200_OK or not _check_content_type(
        response, ("image/",), "PC component provider media"
    ):
        raise ValueError("Provider media response is not an image")
    # bounded aiter_bytes collection
...
with Image.open(BytesIO(response_content)) as image:
    image.verify()
await self.write_file(response_content, media_path, filename)
```

For artwork use the upload validation in `pc_component_resources.py:145-171`: decode with Pillow and derive MIME/extension from format. Add a separate audio allowlist/cap and stream/spool validation for MP3, AAC, FLAC, OGG, OPUS, M4A, and WAV. Do not add tag enrichment.

### `backend/endpoints/roms/media.py` and router registration

**Analog:** `backend/endpoints/roms/pc_component_resources.py:1-313`; register as `backend/endpoints/roms/__init__.py:126-133,240-249`.

Copy imports, `@protected_route`, `assert_rom_visible`, generated JSON response shape, multipart `Annotated[UploadFile, File()]`, and protected inline content pattern. Parent routes use `Scope.ROMS_READ` for visible reads/content and `Scope.ROMS_WRITE` for refresh, upload, placement and delete. Return 404 for invisible/missing parent ROM and 409 for stale expected versions.

```python
@protected_route(router.post, "/{id}/pc-components/{component_id}/media", [Scope.ROMS_WRITE])
async def upload_component_media(..., expected_version: Annotated[datetime, Form()], media: Annotated[UploadFile, File()]):
    content, mime_type, extension = await _validated_upload(media)
    owned_path: str | None = None
    try:
        owned_path = await fs_resource_handler.store_pc_component_upload(...)
        applied = db_rom_handler.create_pc_component_owned_media(...)
        if applied is None:
            raise ValueError("The PC component changed before media was stored")
    except ValueError as exc:
        if owned_path is not None:
            await fs_resource_handler.remove_file(owned_path)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
```

Copy the owned read descriptor rather than a ROM-file content route (`pc_component_resources.py:277-313`): `open_owned_access(storage_composition.owned[OwnedStorageKind.RESOURCES], StorageOperation.READ, media.owned_path)`, inline `StreamingResponse`, content length, and `X-Content-Type-Options: nosniff`.

Do not import, call, or expose `backend/endpoints/roms/soundtrack.py`. Its writes use the external ROM handler and violate this phase boundary.

### Backend tests

**Analogs:** `backend/tests/endpoints/roms/test_pc_component_resources.py:1-107`; `backend/tests/handler/database/test_pc_component_resources.py:1-191`.

Use existing `client`, `access_token`, `rom`, `admin_user`, `session`, and DB handlers. Retain focused scope/foreign-parent/stale-version assertions. Add endpoint tests for permission masking, owned-only content, upload MIME/size rejection, cleanup on conflict, and an explicit regression that Phase 20 routes never request `SIDECAR_WRITE` or `fs_rom_handler`. Add handler tests for tombstone persistence through normal scan, explicit refresh restoring candidate unselected, placement versus candidate deletion, full-list reorder conflict, and no source path mutation.

### `frontend/src/services/api/rom.ts` and `frontend/src/stores/roms.ts`

**Analog:** `frontend/src/services/api/rom.ts:317-327,694-702,817-834`; `frontend/src/stores/roms.ts:1-130`.

After backend OpenAPI generation, import generated parent-media schemas and add typed methods around `/roms/${romId}/media...`. Keep service calls in this file, not in a component, except the existing generic API pattern used by the DLC tab. Preserve `DetailedRom = DetailedRomSchema`; update `currentRom` from the authoritative `getRom` response after every successful media mutation, as `ScreenshotsSubtab.vue:112-121` does.

### `frontend/src/v2/components/GameDetails/MediaTab.vue`

**Analog:** `frontend/src/v2/components/GameDetails/MediaTab.vue:1-172`.

Retain URL-synchronised `subtab`, `defineAsyncComponent`, mounted `v-show` panels, and XS sidebar stacking. Remove the `rom.has_soundtrack` empty-state gate because owned tracks are not `RomFile` soundtrack state. Add proper tab button/panel ID linkage while preserving the current navigation shape.

```ts
watch(subTab, (value) => {
  if (route.query.subtab !== value) {
    router.replace({
      path: route.path,
      query: { ...route.query, subtab: value },
    });
  }
});
```

### `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue` and `ArtworkSubtab.vue`

**Analogs:** `ScreenshotsSubtab.vue:20-174,230-303`; `ArtworkSubtab.vue:1-175`; `PcDlcMediaTab.vue:1-161`.

Use component-local `loading`, pending-ID, `useSnackbar`, `useConfirm`, a `refreshRom()` that replaces both `currentRom` and store cache, `RDropzone`, `REmptyState`, `RCarousel`, and token-only scoped styling. For deletion, confirmation is danger-toned and only calls the new parent owned-media endpoint. Gate controls with `useCan` for ROM write scope; read-only users may see resolved assets.

```ts
async function refreshRom() {
  const { data } = await romApi.getRom({ romId: props.rom.id });
  romsStore.currentRom = data;
  romsStore.update(data);
}

if (!(await confirm({ title: t("common.delete"), tone: "danger" }))) return;
```

Keep source `merged_screenshots`, personal screenshots, and community screenshots visibly separate from parent owned candidates. Candidate placement actions toggle placement only. Candidate delete is irreversible from RomM storage and displays the provider refresh recovery wording. Artwork uses contained gallery previews and `RCarousel` as in `ArtworkSubtab.vue:38-97`; background ordering must be native button controls, not drag-only.

### `frontend/src/v2/components/GameDetails/SoundtrackPanel.vue` and `frontend/src/stores/soundtrackPlayer.ts`

**Analogs:** `SoundtrackPanel.vue:82-145,299-335`; `soundtrackPlayer.ts:8-216`.

Replace the `RomFile`-filtered alphabetical `tracks` computed with ordered included owned-media placements. Generalize track identity from `fileId` to a stable owned media ID, then make `currentIndex`, playlist metadata lookup, `next`, and `previous` use that identity. Filename is the display label. Build queue and rendered rows from exactly the same ordered placement array.

```ts
function selectTrack(fileId: number) {
  const playerTracks: PlayerTrack[] = tracks.value.map((t) => ({
    romId: props.rom.id,
    fileId: t.id,
    fileName: t.file_name,
    url: fileUrl(t.id, t.file_name),
  }));
  player.loadPlaylistForRom(props.rom.id, playerTracks, metas);
  player.play(
    playerTracks.find((p) => p.fileId === fileId)!,
    metas[fileId],
  );
}
```

Preserve `setError`, active-track stop-before-delete (`SoundtrackPanel.vue:319-322`), mini-player ownership, native audio decoding failure handling, and `useSnackbar`. Upload and deletion only call parent owned-media endpoints. Do not call legacy `/soundtracks` mutations, query source `RomFile` audio, or display/enrich tags.

### `frontend/src/v2/views/GameDetails.vue` and `frontend/src/v2/components/AppShell/BackgroundArt.vue`

**Analogs:** `GameDetails.vue:146-169`; `BackgroundArt.vue:1-43`; `useReducedMotion/index.ts:21-67`.

Replace component-local background selection with the ordered resolved parent placements. Preserve `useBackgroundArt()` as the only backdrop setter. In a `watchEffect`/`watch` cleanup, set the first URL immediately; only create an interval when this route is active, two or more backgrounds exist, and `useReducedMotion().enabled` is false. Clear it on route, ROM, placement, or preference changes. `BackgroundArt` already owns the A/B opacity cross-fade and needs no new animation mechanism.

```ts
const { enabled: reducedMotion } = useReducedMotion();
watchEffect((onCleanup) => {
  const urls = selectedBackgroundUrls.value;
  if (urls.length === 0) return;
  setBgArt(urls[0]);
  if (reducedMotion.value || urls.length < 2) return;
  let index = 0;
  const timer = window.setInterval(
    () => setBgArt(urls[(index = (index + 1) % urls.length)]),
    BACKGROUND_ROTATION_MS,
  );
  onCleanup(() => window.clearInterval(timer));
});
```

### Locale files and frontend tests

**Analogs:** existing `frontend/src/locales/*/rom.json`; `PcDlcMediaTab.test.ts:9-25`; `useReducedMotion/index.test.ts:66-130`.

Add all UI-SPEC strings to English source and every locale according to the locale workflow. Add focused component/store tests for candidates versus placements, confirmation/permission paths, refresh/delete/upload/reorder errors, exact playback queue order, decode error retention, and fake-timer reduced-motion cleanup. Add a source-safety test asserting no new UI calls the legacy soundtrack mutation URLs.

## Shared Patterns

### Owned-storage safety

**Sources:** `backend/endpoints/roms/pc_component_resources.py:181-212`, `backend/handler/filesystem/resources_handler.py:150-205`.

All Phase 20 writes use `fs_resource_handler` and resources-owned access. Store first, apply an optimistic DB transaction, remove only the just-stored owned path on conflict, then best-effort remove displaced owned paths. Never use `fs_rom_handler`, source-relative paths, or legacy soundtrack mutation routes.

### Protected visibility and errors

**Sources:** `pc_component_resources.py:38-51,173-235`; `ScreenshotsSubtab.vue:112-174`.

Read requests use `Scope.ROMS_READ`, mutations `Scope.ROMS_WRITE`, and every endpoint calls the parent visibility helper. Client actions retain confirmed data on error, refetch canonical media after conflict, and report bounded translated feedback through `useSnackbar`.

### Optimistic ordering

**Source:** `roms_handler.py:2037-2100`.

Use `expected_version` on every candidate or placement mutation. The server owns a complete-list reorder transaction and returns canonical positions. On 409, refetch before showing the conflict snackbar. Never retain speculative client order.

### v2 interaction and rendering

**Sources:** `PcDlcMediaTab.vue:1-161`, `ArtworkSubtab.vue:38-97`, `MediaTab.vue:101-172`.

Use only `R*` primitives, tokens, translated accessible labels, `RDropzone` for artwork/audio intake, `RCarousel` for image preview, and explicit labelled move buttons. Maintain linear DOM order, XS stacking, and 44px controls. Use `useReducedMotion` for JavaScript timers, plus existing global CSS behavior for purely visual effects.

## No Analog Found

| File/Concern                                                           | Role          | Data Flow        | Reason                                                                                                            |
| ---------------------------------------------------------------------- | ------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------- |
| Parent `RomOwnedMedia` tombstone plus reusable ordered placement model | model         | CRUD             | Existing owned media is DLC-scoped and has no durable deletion or multi-purpose placement.                        |
| Explicit provider media refresh reconciliation                         | service/route | request-response | Existing scans import component provider media, but no operator-only refresh that restores tombstones unselected. |
| Owned audio MIME validation                                            | service       | file-I/O         | Current component upload validates images only; source soundtrack routes are prohibited.                          |

## Metadata

**Analog search scope:** `backend/models`, `backend/alembic/versions`, `backend/endpoints/roms`, `backend/handler`, `backend/tests`, `frontend/src/services`, `frontend/src/stores`, `frontend/src/v2`, and locale files.

**Files scanned:** 20 primary analogs and focused supporting files.

**Pattern extraction date:** 2026-09-28
