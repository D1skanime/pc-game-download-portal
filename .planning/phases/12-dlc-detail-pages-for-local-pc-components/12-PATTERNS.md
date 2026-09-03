# Phase 12: DLC detail pages for local PC components - Pattern Map

**Mapped:** 2026-09-03  
**Files analyzed:** 26 logical file groups, including generated types and locale variants  
**Analogs found:** 26 / 26

## File Classification

| New/Modified File                                                                             | Role               | Data Flow                     | Closest Analog                                                             | Match Quality            |
| --------------------------------------------------------------------------------------------- | ------------------ | ----------------------------- | -------------------------------------------------------------------------- | ------------------------ |
| `backend/models/rom.py`                                                                       | model              | CRUD                          | `RomComponentLocalMedia`, `RomNote`                                        | exact                    |
| `backend/alembic/versions/<revision>_component_owned_media_and_notes.py`                      | migration          | CRUD                          | `0116_pc_component_local_media.py`                                         | exact                    |
| `backend/endpoints/responses/rom.py`                                                          | schema             | transform                     | `PcComponentLocalMediaSchema`, `UserNoteSchema`                            | exact                    |
| `backend/handler/database/roms_handler.py`                                                    | service            | CRUD                          | `apply_pc_component_metadata_candidate`, `get_rom_notes`                   | exact                    |
| `backend/handler/filesystem/resources_handler.py`                                             | service            | file-I/O                      | `store_pc_component_image`                                                 | role-match               |
| `backend/handler/metadata/pc_match_handler.py`                                                | service            | request-response              | `collect_candidates`, `collect_component_candidates`                       | exact                    |
| `backend/endpoints/roms/pc_metadata.py`                                                       | controller         | request-response              | parent/component candidate and selection routes                            | exact                    |
| `backend/endpoints/roms/pc_component_resources.py` (or focused additions to `pc_metadata.py`) | controller         | CRUD/file-I/O                 | `notes.py`, `pc_metadata.py`, `files.py`                                   | role-match               |
| `backend/endpoints/roms/__init__.py`                                                          | route/config       | request-response              | `pc_metadata_router` inclusion                                             | exact                    |
| `backend/tests/endpoints/roms/test_pc_metadata.py` and `test_pc_component_resources.py`       | test               | request-response/CRUD         | current PC metadata tests                                                  | exact                    |
| `frontend/src/__generated__/`                                                                 | generated types    | transform                     | OpenAPI codegen output                                                     | exact, generated only    |
| `frontend/src/services/api/rom.ts`                                                            | client service     | request-response/file-I/O     | current PC metadata and note methods                                       | exact                    |
| `frontend/src/v2/components/MatchRom/types.ts`                                                | shared type        | transform                     | `ConfirmPayload`, `SearchRom` helpers                                      | exact                    |
| `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`                                       | shared component   | request-response              | current dialog shell                                                       | exact                    |
| `frontend/src/v2/components/Dialogs/GlobalDialogs.vue`                                        | registry component | event-driven                  | current matcher registration                                               | exact                    |
| `frontend/src/v2/components/GameDetails/PcMetadataReview.vue`                                 | obsolete component | request-response              | replace/remove after matcher parity                                        | exact removal            |
| `frontend/src/v2/components/GameDetails/PcComponents.vue`                                     | feature component  | event-driven                  | current DLC navigation and metadata entry                                  | exact                    |
| `frontend/src/v2/views/GameDetails.vue`                                                       | view/controller    | request-response              | PC Components composition and refresh                                      | exact                    |
| `frontend/src/v2/views/PcDlcDetails.vue`                                                      | view/controller    | request-response              | current strict nested resolver                                             | exact                    |
| `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`                                      | feature component  | transform/event-driven        | existing DLC hero, `GameDetails.vue` tabs                                  | exact                    |
| `frontend/src/v2/components/GameDetails/PcDlcFiles.vue`                                       | feature component  | request-response              | current manifest UI, `FilesTab.vue`                                        | role-match               |
| `frontend/src/v2/components/GameDetails/PcDlcMediaTab.vue`                                    | feature component  | CRUD/file-I/O                 | `MediaTab.vue`, `PcLocalMediaReview.vue`                                   | role-match               |
| `frontend/src/v2/components/GameDetails/PcDlcNotesTab.vue`                                    | feature component  | CRUD                          | `NotesTab.vue`                                                             | exact presentation match |
| co-located `*.test.ts` files                                                                  | test               | request-response/event-driven | `PcDlcDetails.test.ts`, `PcComponents.test.ts`, `PcMetadataReview.test.ts` | exact                    |
| `frontend/src/locales/*/rom.json`                                                             | config/content     | transform                     | existing `pc-*` and detail keys                                            | exact                    |

## Pattern Assignments

### Component model, schemas, migration, and owned storage

#### `backend/models/rom.py`, `backend/endpoints/responses/rom.py`, `backend/handler/database/roms_handler.py`, and migration

**Analogs:** `backend/models/rom.py:246-334`, `backend/models/rom.py:980-1014`, `backend/endpoints/responses/rom.py:300-369`, `backend/handler/database/roms_handler.py:1748-1902`, `backend/alembic/versions/0116_pc_component_local_media.py:1-95`.

**Component relationship pattern** (`models/rom.py:246-257`):

```python
local_media: Mapped[list[RomComponentLocalMedia]] = relationship(
    lazy="raise",
    back_populates="component",
    cascade="all, delete-orphan",
    order_by="RomComponentLocalMedia.id",
)
```

Add separate `owned_media` and `notes` relationships to `RomComponent` using this lazy/cascade/order pattern. Keep `RomComponentLocalMedia` unchanged: its `source_relative_path` and `source_sha256` are mandatory source evidence (`models/rom.py:305-334`). Introduce a distinct `RomComponentOwnedMedia` with mandatory component ID, owned path, role/category, MIME type, origin and optional provider identity. It must never contain a source-library path. Introduce `RomComponentNote`, not nullable `component_id` on `RomNote`.

**Notes constraint pattern** (`models/rom.py:980-992`):

```python
__table_args__ = (
    UniqueConstraint("rom_id", "user_id", "title", name="unique_rom_user_note_title"),
    Index("idx_rom_notes_public", "is_public"),
    Index("idx_rom_notes_rom_user", "rom_id", "user_id"),
    Index("idx_rom_notes_title", "title"),
)
```

Copy it with `component_id` replacing `rom_id`, retaining independent note titles, public visibility and user ownership for each DLC. Do not weaken existing parent note constraints.

**Component-scoped optimistic update** (`roms_handler.py:1769-1816`):

```python
component = session.scalar(
    select(RomComponent).options(selectinload(RomComponent.component_metadata)).where(
        and_(RomComponent.id == component_id, RomComponent.rom_id == rom_id,
             RomComponent.kind == "dlc", RomComponent.updated_at == expected_updated_at)
    )
)
if component is None:
    return None
```

Use the same containment/kind/version predicate for component media and metadata persistence, updating `component.updated_at`. The existing `apply_pc_local_media` is not reusable for general DLC owned media: it loops all components and writes `rom.path_cover_*` (`roms_handler.py:1858-1899`).

**Migration convention** (`0116_pc_component_local_media.py:14-30`, `39-87`):

```python
def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]

op.create_table("rom_component_local_media", ...,
    sa.ForeignKeyConstraint(["component_id"], ["rom_components.id"], ondelete="CASCADE"))
```

Use portable explicit enum creation/drop, FK constraints, indexes, timestamps and symmetric downgrade. Base the revision on the actual Alembic head. Add schemas with `ConfigDict(from_attributes=True)` as in `PcComponentLocalMediaSchema`, and regenerate frontend types after OpenAPI changes rather than editing `frontend/src/__generated__/`.

#### `backend/handler/filesystem/resources_handler.py` (service, file-I/O)

**Analog:** `resources_handler.py:127-146`.

```python
async def store_pc_component_image(...):
    """Store reviewed PC media below the RomM-owned resource root only."""
    media_path = f"{rom.fs_resources_path}/pc-media"
    filename = f"{component_id}-{member_id}-{role.value}.{image_type}"
    await self.write_file(content, media_path, filename)
```

Create a separate component-owned writer rooted only below the owned resources descriptor. It receives validated bytes, not browser paths. Provider import occurs only after final selection POST, validates candidate-media membership server-side and verifies scheme/content type/size before storing. On conflict/failure remove only a newly created owned file, as `pc_metadata.py:270-283` does. Never call `fs_rom_handler.remove_file`, legacy screenshot/soundtrack write endpoints, or update parent cover columns.

### Shared matcher with a typed target adapter

#### `backend/handler/metadata/pc_match_handler.py` and `backend/endpoints/roms/pc_metadata.py`

**Analogs:** `pc_metadata.py:34-125` for DLC, `302-366` for parent, and the current `collect_candidates` / `collect_component_candidates` handler methods.

**Nested guard pattern** (`pc_metadata.py:34-60`):

```python
def _dlc_component(rom_id: int, component_id: int):
    rom = db_rom_handler.get_rom(rom_id)
    if not rom:
        raise RomNotFoundInDatabaseException(rom_id)
    component = next((item for item in rom.components if item.id == component_id), None)
    if component is None or component.kind != RomComponentKind.DLC:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return rom, component

rom, component = _dlc_component(id, component_id)
assert_rom_visible(request, rom)
```

Every component candidate, selection, media, note and download endpoint resolves this first. Parent matching resolves its `Rom` directly then calls `assert_rom_visible`. Both target types accept the same bounded explicit query (`search_term`, `search_by`) and selection repeats that same query server-side.

**Review-first selection** (`pc_metadata.py:88-125`):

```python
results = await pc_metadata_match_handler.collect_component_candidates(rom, component)
candidate = next((item for result in results.values() if result.available
                  for item in result.candidates if item.id == selection.candidate_id), None)
if candidate is None:
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=...)
updated = db_rom_handler.apply_pc_component_metadata_candidate(...)
if updated is None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=...)
```

Retain candidate recomputation and 409 optimistic conflict. Extend selection with bounded search input and selected candidate-media references, and prove each selected reference belongs to the recomputed candidate before import. GET/search, preview, filters and cancellation have no persistence side effect.

#### `frontend/src/v2/components/MatchRom/types.ts` and `MatchRomDialog.vue`

**Analogs:** `MatchRomDialog.vue:1-259`, `278-412`; `MatchRom/types.ts:1-91`.

**Current unsafe parent-only apply, to replace** (`MatchRomDialog.vue:203-258`):

```typescript
const { data } = await romApi.updateRom({ rom: rom.value });
romsStore.update(data as SimpleRom);
if (route.name === "rom") romsStore.currentRom = data;
```

Extract the shell, search state, filters, grid/list switcher and confirmation overlay behind an explicit target adapter, for example:

```typescript
type PcMatchTarget =
  | { kind: "rom"; romId: number; label: string }
  | { kind: "component"; romId: number; componentId: number; label: string };
```

The adapter owns `search`, `select`, and `refresh`, and normalizes candidates for the existing `MatchRomBodyGrid.vue` / `MatchRomBodyList.vue`. The UI never infers target type from route/name/number. A parent target calls only PC parent APIs. A component target calls only nested component APIs. Preserve the existing `RDialog`, provider chips, query controls, list/grid bodies and cover picker:

```vue
<RDialog
  v-model="show"
  scroll-content
  full-height-on-mobile
  :persistent="matching"
>
  <template #toolbar>...provider filters and search...</template>
  <template #content>
    <component :is="variantComponent" :results="filteredMatchedRoms" @confirm="onBodyConfirm" />
  </template>
</RDialog>
```

Register the one shared shell through `GlobalDialogs.vue:5-36` if it remains emitter driven. Remove `PcMetadataReview.vue` after parent and DLC entry paths launch the shared UI. It must not survive as a second simplified matcher.

#### `GameDetails.vue`, `PcComponents.vue`, and `PcDlcDetail.vue` (launcher components)

**Analogs:** `GameDetails.vue:264-355`, `PcComponents.vue:1-90`, `useGameActions/index.ts:388-396`.

```typescript
function match() {
  const rom = getRom();
  if (!rom) return;
  emitter?.emit("showMatchRomDialog", rom);
}
```

Replace `GameDetails.vue`'s PC parent `PcMetadataReview` with the new target-aware matcher launcher for `{ kind: "rom" }`. Component rows and the DLC overflow use the same launcher with `{ kind: "component" }`. Successful apply uses the existing `refreshPcDetails` fetch (`GameDetails.vue:264-272`) and only rederives the selected component.

### DLC route, tabs, menu, files, media and notes

#### `frontend/src/v2/views/PcDlcDetails.vue` (view/controller)

**Analog:** `PcDlcDetails.vue:17-84`.

```typescript
const DECIMAL_ROUTE_PARAM = /^(?:0|[1-9]\d*)$/;
function parseSafeRouteId(value: unknown): number | null {
  if (typeof value !== "string" || !DECIMAL_ROUTE_PARAM.test(value))
    return null;
  const id = Number(value);
  return Number.isSafeInteger(id) ? id : null;
}

return (
  parent.components?.find(
    (candidate) => candidate.id === componentId && candidate.kind === "dlc",
  ) ?? null
);
```

Retain this exact route boundary. Malformed, stale or non-DLC IDs must not fetch a child resource or display siblings. Keep `onBeforeRouteUpdate`; provide parent return if available and library escape otherwise.

#### `frontend/src/v2/components/GameDetails/PcDlcDetail.vue` (feature component)

**Analogs:** `PcDlcDetail.vue:31-63`, `GameDetails.vue:73-99`, `GameActionBtn.vue:328-484`.

```typescript
const cover = computed(() =>
  props.component.local_media?.find((media) => media.role === "cover"),
);
const media = computed(() =>
  (props.component.local_media ?? []).filter(
    (item) => item.role === "background" || item.role === "gallery",
  ),
);
```

Extend this with `component.owned_media` only. Never call flattened `resolveRomArtwork`, parent cover/screenshots/notes or sibling data. Copy `GameDetails.vue:73-99` URL query synchronization for exactly `overview`, `files`, `media`, `notes`; use `RTabNav`, no DLC save-data tab. Keep the back button first in DOM order. Implement the overflow using `RMenu`/`RMenuItem`, with only shared matcher, selected-artwork/media actions and exact component download, not generic parent `GameActionsList` actions.

#### `PcDlcFiles.vue` and nested component download controller

**Analogs:** `PcDlcFiles.vue:21-66`, `FilesTab.vue:435-446`, `backend/endpoints/roms/files.py:37-121`.

```vue
<li v-for="member in manifestMembers" :key="member.id">
  <dd>{{ member.relative_path }}</dd>
  <dd>{{ formatBytes(member.size_bytes) }}</dd>
  <RTag label="SHA-256" :text="member.sha256" mono />
</li>
```

Keep the component input already validated by its parent and render only `manifest_members`. New downloads resolve parent, exact component and exact member ID server-side, verify membership, open the existing authorized mapped read context and derive filename/content type from trusted data. Never create a path from browser `relative_path`, prefix-match, or use generic `downloadRom` which targets `RomFile` records. Owned artwork download is likewise scoped by an owned record ID under that component.

#### `PcDlcMediaTab.vue` and `PcDlcNotesTab.vue`

**Analogs:** `PcLocalMediaReview.vue:37-75`, `MediaTab.vue`, `NotesTab.vue:50-287`, `backend/endpoints/roms/notes.py:21-186`.

```typescript
const allNotes = computed<UserNoteSchema[]>(
  () => props.rom.all_user_notes ?? [],
);
function isOwn(note: UserNoteSchema): boolean {
  return user.value?.id != null && note.user_id === user.value.id;
}
```

Reuse the media sections and note editor/visibility/selection presentation, not parent data/API calls. Media receives only current component source-promoted and owned records. Source-evidence promotion stays explicit and component-filtered; uploads/provider imports use only new owned-component APIs. Notes use component endpoints and a component-specific note collection, preserving author-only update/delete and clearing `?note` when tabs change (`NotesTab.vue:121-132`). Use `RDialog`, `RBtn` loading, `useSnackbar` and `useConfirm` for owned-media removal. No legacy screenshot/soundtrack write route is permitted.

### Client service, i18n and tests

#### `frontend/src/services/api/rom.ts`

**Analog:** `rom.ts:312-381`, `678-731`, `742-773`.

```typescript
async function selectPcComponentMetadataCandidate({
  romId,
  componentId,
  selection,
}) {
  return api.post<PcComponentMetadataSelectionResponse>(
    `/roms/${romId}/pc-components/${componentId}/metadata-selection`,
    selection,
  );
}
async function createRomNote({ romId, noteData }) {
  return api.post<UserNoteSchema>(`/roms/${romId}/notes`, noteData);
}
```

Add fully typed nested component methods beside these and export all from the default API object. Uploads use existing form helpers/FormData, never raw `fetch` or browser source paths.

#### i18n and input

**Analogs:** locale `rom.json` existing `pc-*`/`category-dlc` keys, `MatchRomDialog.vue:278-412`, `GameActionBtn.vue:328-484`.

All copy uses `t(...)`: target-aware matcher heading/confirmation, menu items, owned media roles/errors, notes empty states, download status, unavailable return and removal confirmation. Add sorted translated keys to all 18 locale files and run both i18n validators. Use `RDialog`, `RMenu`, `RMenuItem`, `RTabNav`, `RBtn`, `RAlert`, `REmptyState`, `RImg`, `RTag`; these preserve mouse/touch/keyboard/gamepad and focus scope. Responsive layout uses `html[data-bp~="..."]`, not raw media queries or custom keyboard handlers.

#### Tests

**Analogs:** `PcMetadataReview.test.ts:1-242`, `PcComponents.test.ts:1-150`, `PcDlcDetail.test.ts:1-138`, `PcDlcDetails.test.ts:1-261`, `backend/tests/endpoints/roms/test_pc_metadata.py:1-524`.

Keep the existing Vitest mock/mount style and pytest `sync_rom_components`/`AsyncMock` endpoint style. Cover:

- Parent PC match, component row match and DLC overflow all use one matcher shell with explicit target types.
- A DLC confirm never calls generic `updateRom`; parent confirm never calls component selection.
- GET and POST use the same query; provider media imports only after explicit confirm, cancellation is read-only.
- Parent/sibling isolation for metadata, owned media, notes, hero, files and downloads; source tree remains byte-identical.
- 404 containment, 422 mismatched candidate/query, 409 optimistic conflicts, author-only note mutations and owned-file cleanup on persistence failure.
- Route parameter rejection, URL tab/note persistence, menu action emission and no custom input abstraction.

## Shared Patterns

### Authorization and source safety

Every nested route follows `_dlc_component` then `assert_rom_visible` (`pc_metadata.py:34-60`). Read uses `Scope.ROMS_READ`, metadata/media writes use `Scope.ROMS_WRITE`, and notes mirror `Scope.ROMS_USER_WRITE`. GET/review is read-only. Only server-side verified bytes may enter owned resources. No source upload, deletion, rename, extraction or remote-artwork write is in scope.

### Refresh, errors, loading

Follow `PcMetadataReview.vue:41-85` and `GameDetails.vue:264-272`: control-level `:loading`, dedicated empty states, `console.error` plus `useSnackbar`, and refetch parent detail data after mutation. Never optimistically graft a parent ROM object into a component.

## No Analog Found

There is no existing component-owned upload/provider-import or component-note persistence implementation. Combine the model/migration/resource/note patterns above. Do not approximate it using legacy parent filesystem endpoints.

## Metadata

**Analog search scope:** backend models/endpoints/responses/handlers/tests, frontend service/v2 components/views/lib/locales  
**Files scanned:** 30 focused analogs  
**Pattern extraction date:** 2026-09-03
