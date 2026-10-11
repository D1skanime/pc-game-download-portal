# Phase 17: Browser Download Manager - Pattern Map

**Mapped:** 2026-09-17
**Files analyzed:** 22 planned files or modifications
**Analogs found:** 18 / 22

## File Classification

| New/Modified File                                                    | Role                    | Data Flow                   | Closest Analog                                                          | Match Quality                     |
| -------------------------------------------------------------------- | ----------------------- | --------------------------- | ----------------------------------------------------------------------- | --------------------------------- |
| `backend/models/download_transfer.py`                                | model                   | event-driven                | `backend/models/download_manifest.py`, `backend/models/sync_session.py` | role-match                        |
| `backend/models/rom.py`                                              | model                   | CRUD                        | existing `RomComponent` relationships                                   | partial, archive-set model is new |
| `backend/handler/database/download_transfers_handler.py`             | service                 | event-driven                | `backend/handler/database/sync_sessions_handler.py`                     | role-match                        |
| `backend/handler/database/download_manifests_handler.py`             | service                 | CRUD                        | same file                                                               | exact modification                |
| `backend/endpoints/responses/download_transfer.py`                   | model/schema            | request-response            | `backend/endpoints/responses/download_manifest.py`                      | exact                             |
| `backend/endpoints/download_transfers.py`                            | route                   | request-response            | `backend/endpoints/download_manifests.py`                               | exact                             |
| `backend/main.py`, `backend/handler/database/__init__.py`            | config/registration     | request-response            | existing router and handler registrations                               | exact modification                |
| `backend/alembic/versions/XXXX_download_transfer_sessions.py`        | migration               | transform                   | `backend/alembic/versions/0119_download_manifests.py`                   | exact                             |
| `backend/tests/models/test_download_transfer.py`                     | test                    | event-driven                | `backend/tests/models/test_download_manifest.py`                        | role-match                        |
| `backend/tests/handler/database/test_download_transfers_handler.py`  | test                    | CRUD                        | `backend/tests/handler/database/test_download_manifests_handler.py`     | exact                             |
| `backend/tests/endpoints/test_download_transfers.py`                 | test                    | request-response            | `backend/tests/endpoints/test_download_manifests.py`                    | exact                             |
| `frontend/src/services/api/downloadTransfers.ts`                     | service                 | request-response            | `frontend/src/services/api/rom.ts`                                      | role-match                        |
| generated `frontend/src/__generated__/` download types               | config/generated client | transform                   | existing generated OpenAPI types                                        | exact, generated only             |
| `frontend/src/v2/components/GameDetails/PcComponents.vue`            | component               | event-driven                | same file                                                               | exact modification                |
| `frontend/src/v2/components/GameDetails/DownloadManager.vue`         | component               | event-driven                | `PcComponents.vue`, `FilesTab/FileRow.vue`                              | role-match                        |
| `frontend/src/v2/components/GameDetails/DownloadSelectionDialog.vue` | component               | request-response            | `components/shared/ConfirmDialog.vue`                                   | role-match                        |
| `frontend/src/v2/components/GameDetails/DownloadQueueItem.vue`       | component               | streaming                   | `FilesTab/FileRow.vue`                                                  | partial                           |
| `frontend/src/v2/components/GameDetails/DownloadModeSelector.vue`    | component               | request-response            | `DownloadSelectionDialog.vue`                                           | new feature composite             |
| `frontend/src/v2/composables/useBrowserDownloadQueue/index.ts`       | hook                    | streaming                   | no direct analog                                                        | none                              |
| `frontend/src/v2/utils/downloadManifestPath.ts`                      | utility                 | transform                   | no direct analog                                                        | none                              |
| `frontend/src/v2/workers/downloadHash.worker.ts`                     | utility/worker          | streaming                   | no direct analog                                                        | none                              |
| frontend component, composable, utility, API tests and locale files  | test/config             | request-response, streaming | `PcComponents.test.ts`, `rom.test.ts`                                   | role-match                        |

## Pattern Assignments

### `backend/models/download_transfer.py` and archive-set additions in `backend/models/rom.py` (models, event-driven and CRUD)

**Analogs:** `backend/models/download_manifest.py` lines 24-186 and `backend/models/sync_session.py` lines 17-53.

Copy the `StrEnum`, typed `Mapped` columns, owner FK cascade, `BaseModel` timestamps, joined owner relationship, and explicit child relationship style. The transfer session must link to the immutable manifest and game, but it must not duplicate a source path, direct URL, or delivery authority. Use `BigInteger` for all selected, expected, and observed byte counters, as the manifest member already does at `download_manifest.py:134`.

```python
class DownloadManifestStatus(enum.StrEnum):
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SOURCE_CHANGED = "source_changed"

class DownloadManifest(BaseModel):
    __tablename__ = "download_manifests"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
```

For sessions, use the scoped lookups and lifecycle counters from `SyncSession`, but do not use its device semantics:

```python
class SyncSessionStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
```

Add an explicit persisted archive-set/profile plus ordered member relation. It is a new domain model, not an inference from `relative_path` or component kind. It needs a uniqueness constraint for a set's component membership and an ordering column if UI and manifest order are contractual. Modify `DBDownloadManifestsHandler.create_manifest()` at lines 64-162 so it locks and validates an exact selected set before it captures any member evidence.

### `backend/handler/database/download_transfers_handler.py` and `backend/handler/database/download_manifests_handler.py` (services, event-driven and CRUD)

**Analogs:** `backend/handler/database/sync_sessions_handler.py` lines 14-192; `backend/handler/database/download_manifests_handler.py` lines 64-162 and 164-202.

Use `@begin_session`, owner predicates in every select/update, transaction flush on create, and narrow state-specific methods rather than a client-provided arbitrary `data` update. Lock the manifest and selected archive-set components with `with_for_update()` before creating the immutable manifest. New session event ingestion must validate the allowed transition from the persisted item state, monotonically increasing observed bytes, bounded error code, and append-only ordinal. Treat browser values as observations only.

```python
@begin_session
def get_session(self, session_id: int, user_id: int, session: Session = None):
    return session.scalar(
        select(SyncSession).filter_by(id=session_id, user_id=user_id).limit(1)
    )

@begin_session
def create_manifest(self, user_id: int, rom_id: int, component_ids: Sequence[int] | None,
                    session: Session = None) -> DownloadManifest:
    rom = session.scalar(select(Rom).where(Rom.id == rom_id).with_for_update())
```

Preserve component then member order exactly. The current authority is `RomComponent.id` followed by `RomComponentManifestMember.id` at `download_manifests_handler.py:85-120`; archive-set order must be explicit if it differs. Do not add filesystem reads, attachment delivery, or Range parsing to this handler.

### `backend/endpoints/responses/download_transfer.py` and `backend/endpoints/download_transfers.py` (schema and route, request-response)

**Analogs:** `backend/endpoints/responses/download_manifest.py` lines 1-44 and `backend/endpoints/download_manifests.py` lines 157-209.

Use Pydantic `extra="forbid"`, field bounds, typed response schemas, `@protected_route`, `Scope.ROMS_READ`, owner lookups, `assert_rom_visible`, and masked 404 responses. Create routes under `/api/download-transfer-sessions`, for example create from a manifest, get/list owner history, and append validated observation events. Do not create a file endpoint, accept a member URL, source path, arbitrary Range, checksum, or authorization token.

```python
class DownloadManifestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    component_ids: list[int] | None = Field(default=None, min_length=1, max_length=100)

@protected_route(router.get, "/download-manifests/{manifest_id}", [Scope.ROMS_READ])
async def get_download_manifest(request: Request, manifest_id: str) -> DownloadManifestResponse:
    manifest = db_download_manifest_handler.get_manifest(manifest_id, request.user.id)
    if manifest is None:
        _not_found()
    assert_rom_visible(request, manifest.rom, not_found_detail=_NOT_FOUND)
    return _serialize(_valid_or_error(manifest))
```

The direct transfer contract is read-only and must remain in `backend/endpoints/download_manifests.py:191-257`. Enhanced resumes must call that existing member URL with exact `Range` and `If-Match`, never a new endpoint. Preserve its 412, 409, and 410 distinctions.

### `backend/alembic/versions/XXXX_download_transfer_sessions.py` (migration, transform)

**Analog:** `backend/alembic/versions/0119_download_manifests.py` lines 17-129, plus the topology repair in `0121_download_manifest_member_identity_and_topology.py` lines 17-150.

Derive the revision from the live Alembic head at implementation time. Use local enum helpers, explicit `op.create_table`, `BigInteger`, named constraints, owner and manifest FK cascades, source/member FKs with `RESTRICT` where history needs referential integrity, and owner/status/time indexes. Provide an exact downgrade in reverse dependency order. Do not reuse stale revision `0121` as `down_revision` without checking the active head.

### `backend/tests/models/test_download_transfer.py`, `backend/tests/handler/database/test_download_transfers_handler.py`, and `backend/tests/endpoints/test_download_transfers.py` (tests)

**Analogs:** `backend/tests/models/test_download_manifest.py`, `backend/tests/handler/database/test_download_manifests_handler.py` lines 1-265, and `backend/tests/endpoints/test_download_manifests.py` lines 1-533.

Follow the local fixture and fake-filesystem seam. Test model constraints and user cascade; handler locking, exact archive-set acceptance/rejection, immutable copied selection evidence, event order, monotonic `BigInteger` progress, and disallowed transitions; endpoint auth and hidden-ROM masking, payload bounds, and absence of raw paths.

```python
def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}

created = client.post(
    f"/api/roms/{rom.id}/download-manifests",
    headers=_headers(access_token),
    json={"component_ids": [component.id]},
)
assert created.status_code == status.HTTP_201_CREATED
```

Keep Phase 15 transfer tests authoritative for headers and source behavior. Their critical protocol assertions are at `test_download_manifests.py:184-351`: full attachment is 200, resume is 206 only with exact snapshot, invalid Range is 416 before opening a source, stale validators are 412, and source changes produce no source bytes.

### `frontend/src/services/api/downloadTransfers.ts` and generated types (service, request-response)

**Analog:** `frontend/src/services/api/rom.ts` lines 1-30, 330-430, and 740-834.

Create a focused typed service using canonical `api`, imported generated response/request types, named object arguments, and one method per server route. Keep manifest creation and member URLs typed from OpenAPI. Do not put Fetch streaming or File System Access calls in this service.

```typescript
async function selectPcComponentMetadataCandidate({
  romId,
  componentId,
  selection,
}: {
  romId: number;
  componentId: number;
  selection: PcMetadataSelectionRequest;
}) {
  return api.post<PcComponentMetadataSelectionResponse>(
    `/roms/${romId}/pc-components/${componentId}/metadata-selection`,
    selection,
  );
}
```

Backend response changes require `npm run generate`; do not hand-maintain `frontend/src/__generated__/` files.

### `frontend/src/v2/components/GameDetails/PcComponents.vue`, `DownloadManager.vue`, `DownloadSelectionDialog.vue`, `DownloadQueueItem.vue`, and `DownloadModeSelector.vue` (feature components, event-driven and request-response)

**Analogs:** `PcComponents.vue` lines 1-181, `GameDetails.vue` lines 348-366, `FilesTab/FileRow.vue` lines 1-220, and `components/shared/ConfirmDialog.vue` lines 1-160.

Put the download entry point in `PcComponents`, never the Files tab. Use a feature composite with typed props, `defineEmits`, aliases, R primitives, `useI18n`, `formatBytes`, semantic sections/lists, and `RDialog` with `fullscreenOnMobile`. Keep archive choices first, component and member detail collapsed, and use manifest-safe destination labels only.

```vue
<PcComponents
  :rom-id="currentRom.id"
  :components="currentRom.components ?? []"
  @applied="refreshPcDetails"
/>
```

The queue item should copy `FileRow`'s controlled component contract: props carry data/state; emitted actions let `DownloadManager` own queue transitions. Use native DOM order, `RCheckbox`, `RBtn`, `RProgressLinear`, `RAlert`, `RBadge`, and `REmptyState`, never raw Vuetify controls. Use inline `:loading` on the manifest/session creation button. `handed_to_browser` is terminal browser handoff, not complete or verified.

Use `ConfirmDialog` through `useConfirm` for removing cancelled queue rows. It already starts focus on its cancel control at lines 37-53. Pass localized cancellation text, danger tone, and do not invent a feature-local overlay.

### `frontend/src/v2/composables/useBrowserDownloadQueue/index.ts`, `frontend/src/v2/utils/downloadManifestPath.ts`, and `frontend/src/v2/workers/downloadHash.worker.ts` (hook, utility, worker, streaming)

**No direct analog found.** These need implementation from the Phase 17 research contract, not a legacy download, desktop, Blob, or ZIP flow.

The queue composable owns bounded active-file scheduling, `AbortController` pause/cancel, the standard attachment handoff queue, and enhanced Fetch streaming only. It must feature-detect `"showDirectoryPicker" in window`; preserve the selection on picker rejection; retain only validated resume metadata; and never serialize a directory handle, source path, replacement URL, arbitrary destination, or browser permission grant. Standard mode marks each attempt `handed_to_browser` after user-initiated attachment handoff and exposes no page progress, resume, retry, or checksum claim.

`downloadManifestPath.ts` must be a pure, testable POSIX relative-destination validator. Reject empty segments, `.`, `..`, slash variants, absolute POSIX and Windows roots, drive letters, control characters, duplicate or collision-prone destinations, then revalidate before every child-handle traversal. It must never accept a typed local target path.

The worker must perform incremental SHA-256 while bytes are streamed to a new writable file handle. Never buffer a member in Blob, ArrayBuffer, or `crypto.subtle.digest()`. On resume, send exactly:

```typescript
const response = await fetch(member.download, {
  credentials: "same-origin",
  headers:
    offset > 0
      ? { Range: `bytes=${offset}-`, "If-Match": member.snapshot }
      : {},
  signal: controller.signal,
});
```

Accept resume only when status is 206 and `Content-Range` exactly agrees with the stored validated offset and manifest size. Map 412 to source changed, 409/410 to expired or revoked manifest, and never append a 200 response to partial local content. Package installation for incremental hashing remains a human-verification checkpoint from `17-RESEARCH.md`.

### Frontend tests and locales (tests and config)

**Analogs:** `frontend/src/v2/components/GameDetails/PcComponents.test.ts` lines 1-166, `frontend/src/services/api/rom.test.ts` lines 1-151, and `frontend/src/v2/composables/useSnackbar/index.ts` lines 1-62.

Use Vitest `mount`, typed fixtures with `satisfies`, mocked router/i18n/API seams, and exact rendered assertions. Test valid default archive set, named missing component warning and disabled action, optional member exclusion, standard handoff labels, feature detection and picker cancellation fallback, queue cap/order, pause/resume/cancel, 200 versus strict 206 resume, 412/409/410 mapping, verified only after mock digest equality, and no source/local path rendering. Test utilities separately for all traversal, Windows, Unicode, collision, and duplicate cases. Add all user strings to English and every locale, then run parity and sorting checks.

Use the existing snackbar channel only for significant outcomes:

```typescript
const snackbar = useSnackbar();
snackbar.success(message);
snackbar.error(message);
```

## Shared Patterns

### Manifest and transfer authority

**Source:** `backend/endpoints/download_manifests.py` lines 157-257; `backend/handler/database/download_manifests_handler.py` lines 64-162.

All browser workflows create one validated immutable manifest, then use only `member.download`. The queue cannot construct a URL, request a custom range other than strict enhanced resume, or access source data. Existing server transfer checks perform owner, visibility, lifecycle, snapshot, size, and direct streaming validation.

### Authorization and non-disclosure

**Source:** `backend/endpoints/download_manifests.py` lines 157-209.

```python
assert_rom_visible(request, rom, not_found_detail=_NOT_FOUND)
manifest = db_download_manifest_handler.get_manifest(manifest_id, request.user.id)
if manifest is None:
    _not_found()
```

Apply the same `ROMS_READ`, owner, visibility, and masked 404 convention to every transfer-session route. Session history is journal data only and must never reveal a manifest's source location or become a credential.

### Strict resume and truthful state

**Source:** `backend/endpoints/download_manifests.py` lines 211-249.

```python
if if_match is not None and if_match != persisted_member.snapshot:
    _precondition_failed()
if range_header is not None and if_match is None:
    _precondition_failed()
```

Enhanced resume requires the original manifest snapshot, 206, and exact `Content-Range`. Standard browser attachments have only `handed_to_browser`. Only local enhanced streamed digest equality can yield `verified`.

### v2 interaction, persistence, and feedback

**Sources:** `.claude/skills/frontend-v2-patterns/SKILL.md`, `.claude/skills/frontend-v2-input/SKILL.md`, `frontend/src/v2/components/shared/ConfirmDialog.vue` lines 32-108.

Keep dialog and disclosure state in local refs, Game Details tab in the existing URL query, and validated enhanced resume state browser-local only. Use `useBreakpoint`, native order for linear controls, no custom key handlers, `RDialog` overlay scope, `RProgressLinear` for determinate enhanced bytes, inline `RAlert` for recoverable item state, and `useSnackbar` only for significant outcomes. No source paths, raw local paths, or unsupported browser completion claims may render.

## No Analog Found

| File or concern                    | Role    | Data Flow | Reason                                                                                       |
| ---------------------------------- | ------- | --------- | -------------------------------------------------------------------------------------------- |
| explicit archive-set/profile model | model   | CRUD      | Current components have kinds only. Phase 14 accepts an arbitrary eligible non-empty subset. |
| `useBrowserDownloadQueue`          | hook    | streaming | No browser queue owns controlled attachments, Fetch streaming, pause, and resume.            |
| `downloadManifestPath.ts`          | utility | transform | No existing browser-side safe destination validator covers FSA child-handle traversal.       |
| `downloadHash.worker.ts`           | worker  | streaming | No incremental large-file hashing worker exists.                                             |

## Metadata

**Analog search scope:** `backend/{models,handler,database,endpoints,responses,alembic,tests}`, `frontend/src/{services,v2}`, `.claude/skills`
**Files scanned:** 31
**Pattern extraction date:** 2026-09-17
