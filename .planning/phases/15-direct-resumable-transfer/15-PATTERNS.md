# Phase 15: Direct Resumable Transfer - Pattern Map

**Mapped:** 2026-09-16
**Files analyzed:** 7 anticipated new or modified files
**Analogs found:** 7 / 7

## File Classification

| New/Modified File                                                                                      | Role                 | Data Flow                   | Closest Analog                                                                  | Match Quality                                     |
| ------------------------------------------------------------------------------------------------------ | -------------------- | --------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------- |
| `backend/endpoints/download_manifests.py`                                                              | route/controller     | request-response, streaming | `backend/endpoints/roms/files.py`                                               | role and flow match, identifier model differs     |
| `backend/handler/database/download_manifests_handler.py`                                               | service              | CRUD, request-response      | same file, `get_manifest`                                                       | exact aggregate/ownership match                   |
| `backend/handler/filesystem/roms_handler.py`                                                           | service              | file-I/O, streaming         | same file, manifest capture plus `backend/handler/filesystem/storage_access.py` | exact trusted-member/HASH match                   |
| `backend/config/__init__.py`                                                                           | config               | transform                   | same file, patcher concurrency settings                                         | exact config match                                |
| `backend/endpoints/roms/files.py` or a new manifest-transfer helper module                             | utility/route helper | transform, streaming        | `backend/endpoints/roms/files.py`                                               | exact single-range and descriptor streaming match |
| `backend/tests/endpoints/test_download_manifests.py`                                                   | test                 | request-response, streaming | same file plus `backend/tests/endpoints/roms/test_files.py`                     | exact Phase-14 fixture and endpoint-test match    |
| `backend/tests/handler/filesystem/test_roms_handler.py` and `backend/tests/utils/test_rate_limiter.py` | test                 | file-I/O, event-driven      | same files                                                                      | exact isolated filesystem and limiter match       |

No database schema, migration, response JSON schema, frontend, Tauri, UI, or NAS/Team4s file belongs to this phase. The Phase-14 member already persists the public ID, selected/source component topology, expected size, SHA-256, and quoted snapshot.

## Pattern Assignments

### `backend/endpoints/download_manifests.py` (route/controller, request-response + streaming)

**Primary analog:** `backend/endpoints/download_manifests.py` lines 18-32, 68-74, 100-108.

Extend this already registered `/api` router, retaining its opaque not-found mask and its closed lifecycle envelope:

```python
_NOT_FOUND = "Download manifest not found"

def _not_found() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)

def _valid_or_error(manifest: DownloadManifest | None) -> DownloadManifest:
    if manifest is None:
        _not_found()
    if manifest.status is not DownloadManifestStatus.VALID:
        status_code, code = _STATE_ERRORS[manifest.status]
        raise HTTPException(status_code=status_code, detail={"code": code})
    return manifest
```

**Authorization and visibility pattern:** `backend/endpoints/download_manifests.py` lines 100-108.

```python
@protected_route(router.get, "/download-manifests/{manifest_id}", [Scope.ROMS_READ])
async def get_download_manifest(request: Request, manifest_id: str):
    manifest = db_download_manifest_handler.get_manifest(manifest_id, request.user.id)
    if manifest is None:
        _not_found()
    assert_rom_visible(request, manifest.rom, not_found_detail=_NOT_FOUND)
    return _serialize(_valid_or_error(manifest))
```

The transfer route must use the same `@protected_route(..., [Scope.ROMS_READ])`, owner-scoped DB lookup, `assert_rom_visible`, and 404 masking on every request. Apply them before testing `If-Match`, HASHing, acquiring/opening a transfer handle, or yielding bytes. Do not add the legacy `DISABLE_DOWNLOAD_ENDPOINT_AUTH` exception.

**Direct streaming and Range mechanics:** `backend/endpoints/roms/files.py` lines 113-155 and 274-306.

```python
def _range_bounds(value: str | None, size: int) -> tuple[int, int] | None:
    if not value:
        return None
    invalid = HTTPException(
        status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
        headers={"Content-Range": f"bytes */{size}"},
    )
    if not value.startswith("bytes=") or "," in value:
        raise invalid
    start_text, separator, end_text = value[6:].partition("-")
    if not separator:
        raise invalid
    try:
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else size - 1
        else:
            suffix = int(end_text)
            if suffix <= 0:
                raise ValueError
            start = max(size - suffix, 0)
            end = size - 1
    except ValueError:
        raise invalid from None
    if start < 0 or start >= size or end < start:
        raise invalid
    return start, min(end, size - 1)
```

```python
response_headers = {
    "Accept-Ranges": "bytes",
    "Content-Length": str(content_length),
}
response_status = status.HTTP_200_OK
if bounds is not None:
    response_status = status.HTTP_206_PARTIAL_CONTENT
    response_headers["Content-Range"] = f"bytes {start}-{end}/{size}"

return MappedContentResponse(
    _mapped_chunks(context, access, start, content_length),
    status_code=response_status,
    media_type="application/octet-stream",
    headers=response_headers,
)
```

Copy the bounded single-range shape, but explicitly validate decimal values as `u64` before converting or seeking. Preserve `416` plus `Content-Range: bytes */total` for malformed, multi-range, and unsatisfiable input. Add strict `If-Match` handling: accept only the one stored quoted strong snapshot, reject missing or `W/` validators for a Range resume, and return `412` without opening/yielding source bytes. No-RANGE remains `200` with the exact full length.

**Error convention:** follow `backend/endpoints/download_manifests.py` lines 68-74 for manifest state codes and `backend/endpoints/roms/files.py` lines 106-110 and 264-279 for bounded storage failures and descriptor cleanup. Map a fresh full-verification mismatch to `412 {"detail": {"code": "source_changed"}}` (or the phase-selected equivalent bounded code), never a filesystem error/path. Ensure a failed range parse closes a pre-opened access handle, as lines 274-279 do.

### `backend/handler/database/download_manifests_handler.py` (service, CRUD + request-response)

**Analog:** `backend/handler/database/download_manifests_handler.py` lines 164-202.

```python
@begin_session
def get_manifest(self, manifest_id: str, user_id: int, session: Session = None):
    manifest = session.scalar(
        select(DownloadManifest)
        .options(
            selectinload(DownloadManifest.rom),
            selectinload(DownloadManifest.components)
            .joinedload(DownloadManifestComponent.component)
            .joinedload(RomComponent.rom),
            selectinload(DownloadManifest.components)
            .selectinload(DownloadManifestComponent.members)
            .joinedload(DownloadManifestMember.manifest_member),
        )
        .where(
            DownloadManifest.id == manifest_id,
            DownloadManifest.user_id == user_id,
        )
    )
    # expiry and light lifecycle validation follows
```

Add an owner-scoped transfer resolver modeled on this eager load. It must select exactly one `DownloadManifestMember.public_id` beneath the requested aggregate, retaining the durable selected-component/source-member paired-FK authority from Phase 14. Return no row for a wrong member ID, wrong owner, or member from another manifest. Do not resolve a `RomFile.id`, `file_name`, `fs_path`, client path, component-relative route segment, or directory.

**Lifecycle boundary:** ordinary `get_manifest` deliberately does STAT-only revalidation at lines 187-202. The transfer path must not treat that as a proof. It needs a separate filesystem full-HASH verification immediately before opening the delivery stream, under the same bounded transfer slot.

### `backend/handler/filesystem/roms_handler.py` (service, file-I/O + streaming)

**Trusted member path analog:** `backend/handler/filesystem/roms_handler.py` lines 310-316.

```python
@staticmethod
def pc_component_member_path(rom: Rom, member: RomComponentManifestMember) -> str:
    """Return a manifest-bound source path without accepting browser paths."""
    relative_path = PurePosixPath(member.relative_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("PC component manifest path is invalid")
    return f"{rom.fs_path}/{rom.fs_name}/{relative_path.as_posix()}"
```

This is the only source locator to reuse. It is constructed from trusted persisted ROM/component-member relations, not caller text.

**Strong HASH verification analog:** `backend/handler/filesystem/roms_handler.py` lines 318-351, particularly lines 325-340 and 345-347.

```python
with self.open_rom_hash(source_path) as source:
    before = os.fstat(source.fileno())
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("PC component manifest source is unavailable")
    sha256 = source.hash("sha256").lower()
    after = os.fstat(source.fileno())

if indicators != (after.st_size, after.st_mtime_ns, after.st_dev, after.st_ino):
    raise ValueError("PC component manifest source changed")
if before.st_size != member.size_bytes or sha256 != member.sha256.lower():
    raise ValueError("PC component manifest source changed")
```

Recompute `_download_manifest_snapshot(public_id, destination, size, sha256)` using lines 247-260, then require exact equality with the stored member snapshot. The delivery helper must perform this complete verification, including regular-file and before/after indicators, through a `HASH` capability. It may subsequently open a separately authorized direct-read/download descriptor for streaming only after verification passes. No writes, temp files, ZIP access, extraction, or directory recursion.

**Descriptor access and streaming analog:** `backend/handler/filesystem/storage_access.py` lines 212-244, 247-281.

```python
class HashCapability(_DescriptorCapability):
    def hash(self, algorithm: str = "sha256") -> str:
        descriptor = self._require_descriptor()
        os.lseek(descriptor, 0, os.SEEK_SET)
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        return digest.hexdigest()

class DownloadCapability(_DescriptorCapability):
    def download(self, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        descriptor = self._require_descriptor()
        os.lseek(descriptor, 0, os.SEEK_SET)
        while chunk := os.read(descriptor, chunk_size):
            yield chunk
```

Use an operation-bound descriptor and `os.lseek` plus bounded `os.read`, retaining close-in-`finally` behavior from `backend/endpoints/roms/files.py` lines 142-155. `StorageOperation.HASH` and `StorageOperation.DOWNLOAD` are already allowed external read operations in `backend/handler/filesystem/storage_policy.py` lines 49-60.

### `backend/config/__init__.py` (config, transform)

**Analog:** `backend/config/__init__.py` lines 55-57 and 62-71.

```python
DOWNLOAD_MANIFEST_TTL_SECONDS: Final[int] = safe_int(
    _get_env("DOWNLOAD_MANIFEST_TTL_SECONDS"), 24 * 60 * 60
)

ROM_PATCHER_MAX_CONCURRENCY: Final[int] = max(
    1, safe_int(_get_env("ROM_PATCHER_MAX_CONCURRENCY"), 2)
)
```

Add the documented transfer per-process concurrency environment setting beside `DOWNLOAD_MANIFEST_TTL_SECONDS`, using `safe_int` and `max(1, ...)`. It must bound both expensive verification and the response lifetime, not just HASH setup. Avoid a byte-size cap copied from `ROM_PATCHER_MAX_FILE_SIZE_BYTES`, because 100-GB-class direct source files are in scope.

### Bounded-concurrency helper (utility, event-driven)

**Analog:** `backend/utils/rate_limiter.py` lines 46-120 and `backend/adapters/services/screenscraper.py` lines 52-57, 376-390.

```python
_concurrency_limiter = ConcurrencyLimiter(SS_DEFAULT_MAX_THREADS)

@asynccontextmanager
async def media_download_slot(url: str) -> AsyncIterator[int]:
    async with _concurrency_limiter:
        await _rate_limiter.acquire()
        yield media_download_timeout()
```

For direct transfers, use a process-local `ConcurrencyLimiter` and a dedicated `asynccontextmanager` or equivalent that holds its slot from pre-transfer full HASH verification through iterator completion/disconnect cleanup. The limiter's `__aexit__` release guarantee at `backend/utils/rate_limiter.py` lines 115-120 is required. Do not reuse ScreenScraper's limiter instance, account-derived max thread logic, rate pacing, or remote-media timeout policy.

### `backend/tests/endpoints/test_download_manifests.py` (test, request-response + streaming)

**Fixture analog:** lines 15-32, 35-72.

```python
def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}

class _ManifestFilesystem:
    def capture_download_manifest_member(self, rom, member, public_id):
        return DownloadManifestMemberEvidence(...)

@pytest.fixture(autouse=True)
def _isolated_manifest_filesystem(monkeypatch):
    monkeypatch.setattr(
        db_download_manifest_handler, "_filesystem_handler", _ManifestFilesystem()
    )
```

Extend this Phase-14-owned test surface with an isolated transfer fake that models exact member IDs, snapshots, `u64` sizes, full verification result, and descriptor chunks. Keep its autouse manifest cleanup at lines 35-39. Endpoint tests must assert exact headers and zero yielded bytes/stream opens on invalid `If-Match`, state, owner, visibility, and source-change failures.

**HTTP header assertion analog:** `backend/tests/integration/test_legacy_migration.py` lines 791-804.

```python
assert response.status_code == status.HTTP_206_PARTIAL_CONTENT
assert response.headers["accept-ranges"] == "bytes"
assert response.headers["content-length"] == "4"
assert response.headers["content-range"] == "bytes 2-5/14"
```

Test no-range `200`, exact closed/open/suffix ranges, single-range-only rejection, malformed and `u64` overflow rejection, and `416 bytes */total`. Use synthetic values `5 * 1024**3`, `80 * 1024**3`, and `120 * 1024**3` in request/response metadata without allocating files. Assert a resume cannot become a 200 response and never changes its requested start or verified total.

### `backend/tests/handler/filesystem/test_roms_handler.py` and `backend/tests/utils/test_rate_limiter.py` (tests, file-I/O + event-driven)

**Filesystem fixture analog:** `backend/tests/handler/filesystem/test_roms_handler.py` lines 1876-1951.

```python
handler = FSRomsHandler(_create_external_descriptor(1, tmp_path, mapping_id=1))
rom = Rom(id=7, fs_name="Unicode Game", fs_path="roms/win")
member = RomComponentManifestMember(
    id=42,
    relative_path="base/nested/Gruesse-ü.bin",
    size_bytes=len(content),
    sha256=hashlib.sha256(content).hexdigest(),
)
```

Copy this temporary external-root fixture for direct-member verification. Its existing regressions already prove unsafe relative paths, changed bytes, missing source, descriptor HASH use, and exact snapshot construction. Add only non-writing stream/descriptor checks and sparse or mocked `u64` stat values, never a real NAS or an allocated 5/80/120-GB file.

**Limiter test analog:** `backend/tests/utils/test_rate_limiter.py` lines 87-162.

```python
limiter = ConcurrencyLimiter(max_concurrency=1)
await limiter.acquire()
waiter = asyncio.ensure_future(limiter.acquire())
await asyncio.sleep(0)
assert not waiter.done()
limiter.release()
await asyncio.wait_for(waiter, timeout=1)
```

Reuse this deterministic blocked-waiter and release-on-error coverage. Add transfer-specific proof that a transfer retains the slot through stream generator cleanup and that a failed HASH or client disconnect releases it.

## Shared Patterns

### Protected route, ownership, and ROM visibility

**Sources:** `backend/endpoints/download_manifests.py` lines 77-108; `backend/handler/auth/dependencies.py` lines 104-123.

```python
if request.user.is_authenticated and not get_permissions(request).can_see_rom(
    rom.id, rom.platform_id
):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)
```

Apply `ROMS_READ`, owner-scoped manifest query, then `assert_rom_visible(..., not_found_detail="Download manifest not found")` on every transfer request. Hidden, foreign, missing member, and missing manifest must all be indistinguishable `404`s.

### Immutable identity and strong snapshot

**Sources:** `backend/models/download_manifest.py` lines 99-178; `backend/handler/filesystem/roms_handler.py` lines 247-260, 318-351.

`DownloadManifestMember.public_id`, `destination`, `size_bytes`, `sha256`, and quoted `snapshot` are the durable contract. Recompute the domain-separated `romm-manifest-v1` snapshot from precisely those trusted values after a fresh HASH. Do not use weak ETags, bare SHA-256 as ETag, `mtime` as a content proof, or a request path as identity.

### Read-only capability boundary and bounded errors

**Sources:** `backend/handler/filesystem/storage_policy.py` lines 12-60; `backend/handler/filesystem/storage_access.py` lines 259-281; `backend/endpoints/roms/files.py` lines 106-110.

Read and HASH only through `StorageOperation` capabilities. Keep path/storage details out of HTTP responses. Use bounded `HTTPException` detail objects for lifecycle/storage outcomes, close descriptors on every pre-header failure, and close iterator handles in `finally`.

### Configured per-process concurrency

**Sources:** `backend/config/__init__.py` lines 62-71; `backend/utils/rate_limiter.py` lines 46-120.

Use a minimum-one environment-backed maximum and `ConcurrencyLimiter`, held for the complete transfer work. It is intentionally per process, not a global cluster coordination mechanism.

## Must Not Reuse

| Existing code                                                                                                       | Why it is excluded from Phase 15                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/endpoints/roms/files.py:get_romfile_content` lines 190-306                                                 | Its route accepts legacy internal `RomFile.id` and a caller-controlled `file_name` segment, derives a mapping-relative path from legacy `RomFile.full_path`, supports HEAD and inline media disposition, and may run under `DISABLE_DOWNLOAD_ENDPOINT_AUTH`. Reuse only its Range/chunk/cleanup mechanics, never its identifier, auth bypass, path resolution, or media behavior. |
| `backend/handler/filesystem/roms_handler.py:calculate_mapped_hashes` lines 480-520                                  | Contains `.zip` special handling and archive member extraction. Direct manifest transfer must send one original member only, never ZIP content or a largest archive member.                                                                                                                                                                                                       |
| `backend/handler/filesystem/storage_access.py:StreamCapability` lines 225-230                                       | It seeks to zero and has no offset/length/cleanup ownership model for a resumable response. Use an explicit descriptor-based ranged iterator instead.                                                                                                                                                                                                                             |
| Multi-file/legacy download and ZIP cache paths (`backend/endpoints/roms/__init__.py`, `backend/utils/zip_cache.py`) | These may package files, traverse directories, or represent a whole ROM. They conflict with the one manifest-member, no-ZIP/no-directory Phase-15 contract.                                                                                                                                                                                                                       |
| `DISABLE_DOWNLOAD_ENDPOINT_AUTH` config                                                                             | Manifest transfer must always authenticate and re-authorize. A historical URL cannot become an unauthenticated durable grant.                                                                                                                                                                                                                                                     |
| Phase 16/17 client code, local `.romm-part-*` state, UI/Tauri handoff                                               | Explicitly deferred. Phase 15 serves HTTP only and does not create local parts, validate destination paths, hash local output, or touch UI.                                                                                                                                                                                                                                       |

## No Analog Found

| File/Concern                                                           | Role               | Data Flow        | Reason and planner guidance                                                                                                                                                                                |
| ---------------------------------------------------------------------- | ------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Strict `If-Match` parser for exactly one quoted strong stored snapshot | utility            | request-response | No existing server endpoint enforces a manifest-bound strong conditional request. Implement a small local helper beside the manifest transfer route; do not substitute generic weak/conditional semantics. |
| Manifest-member transfer lifetime wrapper                              | middleware/utility | streaming        | Existing `ConcurrencyLimiter` is a strong primitive but no existing response holds a transfer slot through both a full HASH and stream disconnect. Add a narrowly scoped helper with `finally` release.    |
| `u64` range parser regression matrix                                   | test               | transform        | Existing `_range_bounds` uses Python `int` but has no explicit `u64` ceiling coverage. Add explicit synthetic boundary tests.                                                                              |

## Metadata

**Analog search scope:** `backend/endpoints`, `backend/handler`, `backend/models`, `backend/config`, `backend/utils`, and matching backend tests

**Files scanned:** 22

**Pattern extraction date:** 2026-09-16
