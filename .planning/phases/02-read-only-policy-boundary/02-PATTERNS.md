# Phase 2: Read-only Policy Boundary - Pattern Map

**Mapped:** 2026-08-09
**Files analyzed:** 11 ownership areas
**Analogs found:** 10 / 11

## Scope

Phase 2 adds a deny-by-default domain boundary for external storage. It does not add mapping APIs, cut scanners over to mappings, change catalog semantics, or activate a NAS. This map complements `02-RESEARCH.md` and uses `02-CONTEXT.md`, Phase 1 implementation and verification, and the live backend call graph.

## File Classification

| New/Modified File                                                    | Role                | Data Flow                     | Closest Analog                             | Match              |
| -------------------------------------------------------------------- | ------------------- | ----------------------------- | ------------------------------------------ | ------------------ |
| `backend/exceptions/storage_exceptions.py`                           | domain error        | request-response/event-driven | same file:1-18                             | exact extension    |
| `backend/handler/filesystem/storage_policy.py` (name discretionary)  | policy/service      | transform                     | `storage_resolver.py`:27-50,91-171         | exact architecture |
| `backend/handler/filesystem/external_access.py` (name discretionary) | capability/provider | file-I/O                      | `storage_resolver.py`:91-171               | role match         |
| `backend/handler/filesystem/__init__.py`                             | provider/config     | request-response              | same file:1-29                             | exact modification |
| `backend/tests/handler/filesystem/test_storage_policy.py`            | security unit test  | transform                     | `test_storage_resolver.py`:34-161          | exact              |
| `backend/tests/handler/filesystem/test_external_access.py`           | integration test    | file-I/O                      | `test_storage_resolver.py`:114-161,182-256 | exact              |
| `backend/tests/endpoints/roms/test_*`                                | API tests           | request-response              | `test_upload.py`:13-65,143-160             | role match         |
| `backend/tests/tasks/test_*`                                         | job tests           | event-driven                  | `test_scan_library.py`:21-79               | exact role         |
| `examples/docker-compose.example.yml`                                | deployment config   | file-I/O                      | same file:22-27                            | exact modification |
| `backend/docker-compose.test.yml` or dedicated fixture               | integration config  | file-I/O                      | same file:1-34                             | partial            |
| mutation inventory test data                                         | test/documentation  | batch                         | none                                       | no analog          |

Keep policy and external capability separate from legacy `FSHandler` subclasses. Importing or constructing external access must never invoke `FSHandler.__init__`.

## Pattern Assignments

### Typed policy denial

**Analog:** `backend/exceptions/storage_exceptions.py:1-18`

```python
class StorageResolutionError(Exception):
    code = "storage_resolution_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class InvalidRelativePathError(StorageResolutionError):
    code = "invalid_relative_path"
```

Extend this bounded domain-error convention with one policy denial type carrying only enum operation, trusted storage class, and logical root/mapping identity. Never include raw paths or OS errors. Do not copy `endpoint_exceptions.py:6-20`, which raises `HTTPException` inside an exception constructor and cannot serve jobs/internal callers.

### Closed operation model

**Analogs:** `storage_resolver.py:27-50`; enum style `scan_handler.py:64-87`.

Define every operation explicitly. The external allowlist is `LIST`, `STAT`, `READ`, `SCAN`, `HASH`, `STREAM`, `DOWNLOAD`, plus the narrowly named safe-resolution operation. Every mutation and unknown value denies. Avoid boolean `read_only`, broad READ/WRITE buckets, prefix matching, and caller path classification. Policy input is trusted `StorageRoot.mode` (`models/storage.py:27-56`), never path text. Authorize source and destination separately.

### Operation-bound external capability

**Analog:** `storage_resolver.py:91-171`

```python
def resolve_directory(storage_root: StorageRoot, raw_relative_path: str) -> Path:
    relative_path = normalize_relative_path(raw_relative_path)
    root = resolve_storage_root(storage_root)
    target = _reject_component_symlinks(root, relative_path)
    resolved_target = _strict_resolve_target(target)
    resolved_target.relative_to(root)
    ...
    return resolved_target
```

Reuse normalization, trusted root identity, component `lstat`, strict containment, bounded errors, and non-writable-root checks. At the Phase 2 public boundary replace raw `Path` returns with capabilities exposing only the approved operation. LIST must not expose open/read; READ/HASH must not expose mutation or reusable absolute paths.

Phase 1 verification explicitly deferred path-swap protection to Phase 2. Do not authorize a `Path` then reopen by name. Bind access to authorization with scoped descriptor-relative/no-follow operations where supported.

### `FSHandler` is a negative analog

`base_handler.py:153-159` resolves then creates its base directory in the constructor. Never instantiate it for an external root. Module singletons at `handler/filesystem/__init__.py:9-13` make import-time mutation a risk.

| Legacy surface        | Source                                    | Phase 2 treatment                                                 |
| --------------------- | ----------------------------------------- | ----------------------------------------------------------------- |
| mkdir                 | `base_handler.py:293-313`                 | deny before `exists`/`mkdir`                                      |
| recursive delete      | `base_handler.py:342-362`                 | deny before `is_dir`/`rmtree`                                     |
| write/overwrite       | `base_handler.py:364-447`                 | external destination impossible                                   |
| copy/link             | `base_handler.py:504-546`                 | source READ plus separate owned WRITE; never external destination |
| move/rename           | `base_handler.py:548-580`                 | deny external source/destination mutation                         |
| delete                | `base_handler.py:582-604`                 | deny before `exists`/`unlink`                                     |
| list/read/stream/stat | `base_handler.py:315-340,449-502,606-679` | operation-specific capability                                     |

Do not add an optional policy argument whose omission preserves raw external access.

### API translation and auth

**Analog:** `decorators/auth.py:72-122`.

Keep `@protected_route(..., [Scope.*])` for auth/scopes. Storage policy is an independent domain authorization after trusted identity lookup. Translate direct denials to HTTP 403 with a stable code in typed JSON. Preserve 404 masking for hidden ROM bytes before policy/resource disclosure, as in `endpoints/roms/files.py:84-100`.

### Mixed transformations

**Analog:** `endpoints/roms/patch.py:118-194`.

The positive shape is external bytes as input and `tempfile.mkdtemp` output streamed then cleaned by `BackgroundTask`. Replace `fs_rom_handler.validate_path` with READ capability and explicitly classify temp output as RomM-owned. Preserve generic external errors at lines 157-171. Never patch in place or infer destination safety from being outside the external root.

### Download/stream

**Analog:** `endpoints/roms/files.py:67-153`.

Retain `ROMS_READ`, parent visibility, DB-derived media type/disposition, and `nosniff`. Replace `validate_path(file.full_path)` and synthesized `/library/...` nginx paths with DOWNLOAD/STREAM capability handoff. Authorization must precede `FileResponse` or nginx filesystem observation; a reusable absolute path is not an acceptable capability.

### Background jobs

**Analogs:** `tasks/scheduled/scan_library.py:37-73`; `tests/tasks/test_scan_library.py:31-79`.

Patch dependencies at the consumer namespace, await real `run`, and assert exact/absent calls. On denial assert the typed error escapes immediately, no later scan/persist/success log occurs, and no success result is reported. Do not copy the `return None` fallback in `tasks/tasks.py:164-180` for policy denial.

### Docker defense in depth

**Analog:** `examples/docker-compose.example.yml:22-27`.

Make `/path/to/library:/romm/library:ro`; keep resources, Redis, assets, and config separate/writable. Add a test-only read-only mount so the identical denial matrix runs on writable and container-mounted read-only fixtures. App denial must be identical in both.

## Shared Patterns

### Trusted classification

Use `StorageRoot.id`, `StorageRoot.mode`, and mapping identity from `models/storage.py:27-95`. Never classify via `/romm/library` prefix, containment outside a root, or observed writability.

### Pre-access tripwires

**Analog:** `tests/handler/filesystem/test_storage_resolver.py:114-161`.

```python
def _manifest(path: Path) -> tuple[tuple[object, ...], ...]: ...

def forbidden(*args: object, **kwargs: object) -> None:
    raise AssertionError("storage observation attempted a mutation")

for owner, name in [(Path, "mkdir"), (Path, "unlink"), ...]:
    monkeypatch.setattr(owner, name, forbidden)
```

For each denied operation patch `lstat/stat`, `open`, enumeration, and its mutation primitive so any target contact fails. Assert policy denial first. Cover every mutation plus unknown operation on writable and read-only fixtures, with before/after manifests.

### Test conventions

Use parameterized named matrices (`test_storage_resolver.py:34-101`), `tmp_path` plus real files, endpoint `TestClient` and bearer headers (`test_upload.py:42-65`), and `AsyncMock` plus `assert_not_called` (`test_scan_library.py:64-79`).

## Mutation and Read Inventory

### Govern if source or target can be external

- Upload/final replacement: `endpoints/roms/upload.py:116-145,206-229,294-328`.
- ROM file deletion: `endpoints/roms/files.py:156-204`.
- Whole-ROM rename/delete and folder conversion: `endpoints/roms/__init__.py` (locate exact call sites during implementation).
- Manual, soundtrack, screenshot create/delete: `endpoints/roms/manual.py`, `soundtrack.py`, `screenshot.py`.
- Patch source: `endpoints/roms/patch.py:118-153,198-238`.
- Platform bootstrap: `filesystem/platforms_handler.py:29-33,79-119`.
- Scan enumeration/hash and cover extraction: `filesystem/roms_handler.py`, `scan_handler.py:150-180`, `endpoints/sockets/scan.py`.
- Extraction: `utils/archives.py`; destination must be owned.
- ZIP cache: `utils/zip_cache.py:133-150,231`; owned destination only.
- Exporters: `utils/gamelist_exporter.py`, `utils/pegasus_exporter.py`; never external targets.

### Prove structurally RomM-owned

`ROM_UPLOAD_TMP_BASE`, resources, assets, ZIP/cache, patch temp, scheduled cleanup targets, sync staging, and SSH keys. Each needs a typed owned-storage handle that cannot represent an external root, not merely a path-absence assertion.

## Ownership Boundaries

- Policy owns operation enum, closed matrix, trusted classification, and denial.
- External provider owns descriptor-bound containment and actual reads.
- Endpoint/task/scan owners translate errors but do not duplicate policy tables.
- Owned handlers retain writes only through explicit owned classification.
- Docker owns `:ro` defense in depth, not authorization.
- Phase 2 tests own the complete mutation inventory and dual-fixture matrix. Later phases own mapping APIs, scanner mapping cutover, catalog lifecycle, UI, and migration.

## Anti-patterns

- Returning `Path`, absolute strings, or generic read/write handles.
- Trusting `RomFile.full_path`, route params, or caller paths for storage class.
- Authorizing generic read then implicitly permitting list/hash/stream/download.
- Treating “outside external root” as writable-owned.
- Relying on `EROFS` after access.
- Catching denial broadly, skipping, falling back, redirecting, or reporting success.
- Endpoint-only enforcement while sockets/RQ retain raw paths.
- Leaking relative/absolute filesystem paths in denial responses.

## No Analog Found

| Concern                              | Reason                                                                                                                  |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Complete mutation inventory contract | Existing tests are per-handler. Add explicit parameterized inventory data whose missing classification fails the suite. |

## Metadata

**Search scope:** backend filesystem/scan handlers, ROM/socket endpoints, tasks, utils, tests, Docker examples, Phase 1 artifacts
**Primary analog files read:** 18
**Date:** 2026-08-09
