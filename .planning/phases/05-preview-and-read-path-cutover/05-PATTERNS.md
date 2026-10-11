# Phase 5: Preview and Read-path Cutover - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 22 likely new or modified files
**Analogs found:** 18 / 22

## Integration Constraint

Phase 3 has not landed in this checkout. The names `handler/storage/read_context.py`, `handler/storage/preview.py`, and `exceptions/storage_read.py` come from Phase 5 research and are provisional. The planner must first inspect the actual Phase 3 mapping repository, revision type, resolver, lifecycle states, and operation-handle API. Extend that contract rather than creating a second storage model.

## File Classification

| New/Modified File                                            | Role                         | Data Flow                          | Closest Analog                                                                                        | Match Quality                                  |
| ------------------------------------------------------------ | ---------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `backend/exceptions/storage_read.py`                         | utility/domain exceptions    | request-response, batch            | `backend/exceptions/fs_exceptions.py`                                                                 | role-match                                     |
| `backend/handler/storage/read_context.py`                    | service                      | file-I/O, request-response         | `backend/handler/filesystem/base_handler.py`                                                          | role and flow match, security semantics differ |
| `backend/handler/storage/preview.py`                         | service                      | bounded file-I/O, batch            | `backend/handler/filesystem/base_handler.py`                                                          | role-match                                     |
| `backend/handler/scan_command.py`                            | service/command              | queued batch                       | `backend/endpoints/sockets/scan.py` and `backend/tasks/scheduled/scan_library.py`                     | flow-match                                     |
| `backend/endpoints/storage/__init__.py`                      | controller/route             | request-response                   | `backend/endpoints/roms/files.py`                                                                     | role and flow match                            |
| `backend/endpoints/responses/storage.py`                     | schema                       | transform                          | existing endpoint return schemas, especially `RomFileSchema` use in `backend/endpoints/roms/files.py` | role-match                                     |
| `backend/tasks/manual/preview_mapping.py`                    | task                         | queued batch/file-I/O              | `backend/tasks/scheduled/scan_library.py`                                                             | role and queue-flow match                      |
| `backend/endpoints/sockets/scan.py`                          | socket controller/worker     | queued batch, event-driven         | existing `scan_handler` and `scan_platforms` in the same file                                         | exact modification target                      |
| `backend/tasks/scheduled/scan_library.py`                    | scheduled task               | queued batch                       | existing `ScanLibraryTask`                                                                            | exact modification target                      |
| `backend/watcher.py`                                         | watcher/coalescer            | event-driven to queued batch       | existing `process_changes`                                                                            | exact modification target                      |
| `backend/handler/filesystem/roms_handler.py`                 | filesystem service           | file-I/O, hashing                  | existing `FSRomsHandler`                                                                              | exact modification target                      |
| `backend/endpoints/roms/files.py`                            | controller                   | request-response, file-I/O         | existing `get_romfile_content`                                                                        | exact modification target                      |
| `backend/endpoints/roms/__init__.py`                         | controller                   | request-response, multi-file batch | existing `head_rom_content` and `get_rom_content`                                                     | exact modification target                      |
| `backend/endpoints/streaming.py`                             | controller/broker adapter    | request-response, streaming        | existing streaming routes in the same file                                                            | exact modification target                      |
| `backend/utils/nginx.py`                                     | response adapter             | streaming/internal redirect        | `FileRedirectResponse` and `ZipResponse`                                                              | exact modification target                      |
| `backend/utils/zip_cache.py`                                 | utility/service              | batch file-I/O                     | existing `resolve_cached_zip`                                                                         | exact modification target                      |
| `backend/tests/integration/test_mapped_scan.py`              | integration test             | queued batch/file-I/O              | scan endpoint/task tests                                                                              | partial                                        |
| `backend/tests/integration/test_scan_source_immutability.py` | adversarial integration test | batch file-I/O                     | filesystem tests using temporary roots                                                                | partial                                        |
| `backend/tests/endpoints/storage/test_mapping_preview.py`    | endpoint test                | request-response                   | `backend/tests/endpoints/roms/test_files.py`                                                          | role and flow match                            |
| `backend/tests/handler/storage/test_preview.py`              | service unit test            | bounded file-I/O                   | `backend/tests/handler/filesystem/test_roms_handler.py`                                               | role-match                                     |
| `backend/tests/tasks/test_mapping_revision_jobs.py`          | queue integration test       | queued batch                       | `backend/tests/tasks/test_scan_library.py` and `test_tasks.py`                                        | role and flow match                            |
| Existing watcher and ROM endpoint suites                     | tests                        | event-driven, request-response     | `backend/tests/test_sync_watcher.py`, `backend/tests/endpoints/roms/test_files.py`, `test_rom.py`     | exact modification targets                     |

## Pattern Assignments

### `backend/handler/storage/read_context.py` and `backend/handler/storage/preview.py`

**Analog:** `backend/handler/filesystem/base_handler.py`

**Relative-path validation pattern** (lines 187-230):

```python
def validate_path(self, path: str) -> Path:
    path_path = Path(path)
    if ".." in path_path.parts:
        raise ValueError(...)
    if path_path.is_absolute():
        raise ValueError(...)
    full_path = Path(self.base_path).resolve() / path_path
    full_path.resolve().relative_to(Path(self.base_path).resolve())
    return full_path
```

Copy the relative-input and containment shape, but consume the Phase 1/2 resolver and operation handle instead of copying `FSHandler`'s permissive symlink branch or its raw `ValueError` details. `MappingReadContext` should hold bounded logical identity (`mapping_id`, `expected_revision`), validate before access, and issue operation-specific handles. It must never accept an absolute queued path.

For preview, use the research-prescribed iterative `os.scandir` traversal. Check monotonic time and inspected-entry count both outside and inside the directory loop. Catch per-entry `OSError`, increment bounded problem categories without paths, and count only successfully observed metadata. Do not call scanner functions or mutate catalog tables.

### `backend/exceptions/storage_read.py`

**Analog:** `backend/exceptions/fs_exceptions.py` lines 7-22 and 34-40.

```python
class PlatformNotFoundException(Exception):
    def __init__(self, platform: str):
        self.message = f"Platform {platform} not found"
        super().__init__(self.message)

    def __repr__(self):
        return self.message
```

Keep typed domain exceptions in `backend/exceptions/`, but improve the contract for this phase: a shared base error with stable `code`, bounded mapping ID, expected revision, and safe state. Required subclasses cover stale mapping, unreachable storage, missing content, and denied access. Do not store or serialize absolute paths or raw `OSError` text.

### `backend/handler/scan_command.py`

**Analogs:** `backend/endpoints/sockets/scan.py` lines 837-886 and `backend/tasks/scheduled/scan_library.py` lines 25-73.

```python
async def scan_platforms(
    platform_ids: list[int],
    metadata_sources: list[str],
    scan_type: ScanType = ScanType.QUICK,
    roms_ids: list[int] | None = None,
) -> ScanStats:
    ...

class ScanLibraryTask(PeriodicTask):
    async def run(self) -> dict[str, str]:
        scan_stats = await scan_platforms(
            platform_ids=[],
            metadata_sources=metadata_sources,
            scan_type=ScanType.QUICK,
        )
        return scan_stats.to_dict()
```

Extract the common orchestration behind one frozen identity-bearing command. Recommended immutable fields are mapping ID, expected revision, trigger, scope, scan type, and bounded options. Manual, scheduled, and watcher triggers construct this same command; they differ only in trigger metadata, scope, and queue priority. Validate reachability/revision before catalog mutation and again before missing-item reconciliation and other safe boundaries.

### `backend/endpoints/storage/__init__.py`, `backend/endpoints/responses/storage.py`, and preview task

**Endpoint analog:** `backend/endpoints/roms/files.py` lines 35-64.

```python
@protected_route(
    router.get,
    "/{id}/files",
    [Scope.ROMS_READ],
    responses={status.HTTP_404_NOT_FOUND: {}},
)
async def get_romfile(request: Request, id: Annotated[int, PathVar(ge=1)]) -> RomFileSchema:
    file = db_rom_handler.get_rom_file_by_id(id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return RomFileSchema.model_validate(file)
```

Keep the route thin: enforce the appropriate admin/storage scope, start explicit preview work, and serialize a typed response. The response schema must represent `pending`, `partial`, and `complete`, observed file/directory/byte counters, budget reason, timestamp, bounded problem summary, and prior-result stale state. The task should follow the base task contract in `backend/tasks/tasks.py` lines 48-83 (`Task` metadata plus async `run`). Preserve the prior durable result when a new preview becomes pending.

### `backend/endpoints/sockets/scan.py` and `backend/tasks/scheduled/scan_library.py`

**Queue analog:** `backend/endpoints/sockets/scan.py` lines 1101-1127.

```python
return high_prio_queue.enqueue(
    scan_platforms,
    platform_ids=platform_ids,
    metadata_sources=metadata_sources,
    scan_type=scan_type,
    job_timeout=SCAN_TIMEOUT,
    result_ttl=TASK_RESULT_TTL,
    meta={"task_name": f"{scan_type.value.capitalize()} Scan", "task_type": TaskType.SCAN},
)
```

Retain queue timeout/result metadata conventions, but replace platform IDs/slugs as the source authority with serialized mapping ID plus immutable expected revision. Socket errors must translate domain errors into stable bounded payloads instead of emitting `e.message` as currently done at lines 881-885. A retry constructs a new command and job; it must not mutate the old job identity or failure history.

### `backend/watcher.py`

**Analog and replacement target:** `backend/watcher.py` lines 117-170 and 204-261.

```python
changes = [
    change for change in changes
    if change[0] in VALID_EVENTS
    and not _is_excluded(os.fsdecode(change[1]).split(LIBRARY_BASE_PATH)[-1])
]
...
tasks_scheduler.enqueue_in(
    time_delta,
    scan_platforms,
    platform_ids=[db_platform.id],
    scan_type=ScanType.QUICK,
    timeout=SCAN_TIMEOUT,
    job_result_ttl=TASK_RESULT_TTL,
)
```

Preserve filtering, delayed enqueue, timeout, TTL, and task metadata conventions. Replace global-root string splitting and slug-keyed deduplication with per-mapping event normalization through the trusted resolver. Coalesce bursts by mapping ID. While active, store at most one pending follow-up command with the revision observed when enqueued.

### `backend/handler/filesystem/roms_handler.py`

**Analog:** existing `FSRomsHandler` and `_calculate_rom_hashes`, especially lines 169-173 and 615-687.

```python
class FSRomsHandler(FSHandler):
    def __init__(self) -> None:
        super().__init__(base_path=LIBRARY_BASE_PATH)
```

Do not preserve this global base-path authority for mapped reads. Keep archive parsing and incremental hash algorithms, but accept an operation-bound descriptor/handle from `MappingReadContext`. Revalidate at safe processing boundaries and never reopen a changed source to continue the same hash or stream.

### `backend/endpoints/roms/files.py` and `backend/endpoints/streaming.py`

**Analog:** `backend/endpoints/roms/files.py` lines 67-153.

```python
@protected_route(router.get, "/{id}/files/content/{file_name}", [Scope.ROMS_READ])
async def get_romfile_content(request: Request, id: int, file_name: str):
    file = db_rom_handler.get_rom_file_by_id(id)
    rom = db_rom_handler.get_rom(file.rom_id)
    assert_rom_visible(request, rom, not_found_detail="File not found")
    if DEV_MODE:
        return FileResponse(path=fs_rom_handler.validate_path(file.full_path), ...)
    return FileRedirectResponse(download_path=Path(f"/library/{file.full_path}"), ...)
```

Preserve authentication, parent-ROM visibility masking, trusted DB-derived media type/disposition, `nosniff`, and Starlette/Nginx transport split. Replace both path constructions with a STREAM/DOWNLOAD preflight for the expected mapping revision immediately before `FileResponse`, broker URL issuance, or `FileRedirectResponse`. Translate shared domain errors to stable HTTP details without raw paths.

### `backend/endpoints/roms/__init__.py`, `backend/utils/nginx.py`, and `backend/utils/zip_cache.py`

**Multi-file analog:** `backend/endpoints/roms/__init__.py` lines 1325-1505.

```python
files.sort(key=lambda x: x.file_name)
if not files:
    raise HTTPException(status_code=404, detail=f"No files found for ROM {id}")
...
content_lines = [
    ZipContentLine(
        crc32=None,
        size_bytes=f.file_size_bytes,
        encoded_location=quote(f"/library/{f.full_path}"),
        filename=f.file_name_for_download(hidden_folder),
    )
    for f in files
]
return ZipResponse(content_lines=content_lines, filename=f"{quote(file_name)}.zip")
```

Before any response/header/body is created, preflight every selected file for identity, revision, containment, existence, regular-file type, readability, and download authorization. Build `FileResponse`, `ZipContentLine`, cached ZIP inputs, or redirect only from the complete authorized descriptor list. One failure rejects the whole transfer. HEAD must run equivalent preflight. Do not hash full content during preflight.

**Response adapter analog:** `backend/utils/nginx.py` lines 29-53 and 56-86.

```python
kwargs.setdefault("headers", {}).update({
    "Content-Disposition": ...,
    "X-Accel-Redirect": quote(str(download_path)),
})
super().__init__(media_type=media_type, **kwargs)
```

Keep Nginx adapters transport-only. Their constructors should receive an already-authorized internal location, never a catalog `full_path` or caller path. Authorization/revision checks belong immediately before adapter construction.

**RomM-owned output analog:** `backend/utils/zip_cache.py` lines 31-78 and 162-201.

```python
def _cache_dir(namespace: str) -> Path:
    return Path(ZIP_CACHE_PATH) / namespace

async def resolve_cached_zip(...):
    cache_key = get_cache_key(namespace, entries, hidden_folder)
    if get_cached_zip(namespace, cache_key):
        return get_zip_redirect_path(namespace, cache_key)
    await anyio.to_thread.run_sync(functools.partial(build_cached_zip, ...))
```

Keep generated ZIPs under `ZIP_CACHE_PATH`. Change `ZipFileEntry` to snapshot authorized mapped sources, not reusable raw `full_path` strings. Do not fall back from a failed source preflight to mod_zip; fallback is only acceptable for generated-cache construction failure after all sources are authorized.

## Test Pattern Assignments

### Endpoint tests

**Analog:** `backend/tests/endpoints/roms/test_files.py` lines 16-64 and 150-165.

```python
def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

r = client.get(url, headers=_auth(access_token))
assert r.status_code == status.HTTP_200_OK
assert r.headers["content-type"].startswith("image/png")
```

Use existing `TestClient`, database fixtures, bearer helper, and direct status/header assertions. Add preview state transitions and no-catalog-write assertions. Extend ROM tests with stable redacted error bodies, HEAD/Range parity, authorization immediately before handoff, 100-part preflight, failed final part before output, and DEV/Nginx parity.

### Filesystem, watcher, and queue tests

Use pytest temporary roots and `unittest.mock` patching, as shown in `backend/tests/test_sync_watcher.py` lines 18-40. Add shared fixtures for mapping replacement, disabled/removed/unreachable states, source-tree before/after manifests, invalidated operation handles, fakeredis/RQ failure metadata, and response capture before headers. Cover huge flat and deep trees, both budget limits, unreadable entries, Unicode, zero-byte files, symlinks, and raw `OSError` redaction.

## Shared Patterns

### Authentication and visibility

**Source:** `backend/endpoints/roms/files.py` lines 35-70 and 84-100.

Apply `@protected_route` with repository scopes, then enforce parent object visibility before resolving bytes. Preserve 404 masking for hidden or unavailable catalog objects.

### Error translation

Domain services raise stable storage-read exceptions. Endpoint, socket, and RQ boundaries translate them for their channel. Public fields are limited to error code, bounded mapping ID, expected revision, and safe state. Log only through a redacting adapter.

### Read integrity

All consumers follow: authorize catalog object, load expected mapping identity, preflight/resolve for the specific operation, then create exactly one handle or authorized redirect. Abort on mutation/unreachability; never reopen and concatenate a second version.

### Scan safety

Resolve and health-check before scan/catalog work. Revalidate at explicit safe boundaries and before missing-item reconciliation. Unreachable storage is a visible failure, never an empty archive. Generated assets, cache files, and exports must target verified RomM-owned locations.

## No Analog Found

| File/Concern                                       | Role            | Data Flow         | Reason                                                                                                                          |
| -------------------------------------------------- | --------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Phase 3 mapping/revision integration               | service/model   | CRUD and file-I/O | Phase 3 artifacts and implementation are absent; planner must inspect them after they land.                                     |
| Durable preview-result persistence model/migration | model/migration | CRUD              | Research recommends mapping-associated durable state but marks its location as assumed; use Phase 3 storage fields if provided. |
| Response-before-output capture fixture             | test fixture    | streaming         | No current fixture proves every source was preflighted before headers/body.                                                     |
| Operation handle invalidation fixture              | test fixture    | file-I/O          | No mapping-revision operation-handle implementation exists in this checkout.                                                    |

## Metadata

**Analog search scope:** `backend/handler/`, `backend/endpoints/`, `backend/tasks/`, `backend/utils/`, `backend/exceptions/`, and mirrored `backend/tests/`
**Strong analogs read:** filesystem base/ROM handlers, scan socket and scheduled task, watcher, ROM file/download endpoints, Nginx and ZIP cache adapters, filesystem exceptions, endpoint and watcher tests
**Pattern extraction date:** 2026-08-11
