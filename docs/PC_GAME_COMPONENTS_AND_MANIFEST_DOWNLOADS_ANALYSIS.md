# PC Game Components and Manifest Downloads

**Status:** Technical analysis and design proposal only  
**Analyzed upstream:** `rommapp/romm` `master` at `071e82adad6c836a3b04dcfbd89900a487fc275e`  
**Analysis date:** 2026-08-04

## 1. Decision summary

A PC game module is cleanly integrable as an additive RomM module. The existing `Rom` and `RomFile` aggregate already represents one logical game backed by one file or a recursive directory tree. The missing concept is a stable component that groups files below a PC game, carries component-level metadata, and can be selected as a download unit.

The recommended design is:

1. Keep `Rom` as the logical game and `RomFile` as the physical file record.
2. Add an optional `GameComponent` entity owned by a `Rom`.
3. Add an optional `game_component_id` foreign key to `RomFile`.
4. Introduce a PC-specific scanner policy that maps each first-level child directory to a component without changing source files.
5. Add immutable, versioned manifests and an authenticated per-file content endpoint with HTTP Range support.
6. Keep the current direct-file and ZIP download behavior unchanged for existing ROM clients.
7. Add optional ZIP streaming as a web convenience, not as the desktop client's canonical protocol.

Do not model each PC component as a separate `Rom`. That would duplicate game metadata, permissions, collections, play state, and provider identity. Do not use `RomFile.category` alone. It cannot express component identity, ordering, a component version, an explicit label, or one component containing several category-like files.

## 1.1 Non-negotiable external-library safety boundary

Existing game collections are archives owned outside RomM. An external library root is always mounted read-only and RomM must never create, overwrite, rename, move, extract, patch, or delete files or directories below it. This is a defense-in-depth contract, not a user preference:

1. The container mount for an external library must use `:ro`.
2. Every external root has the immutable mode `external_read_only`; this fork initially offers no writable-library mode.
3. A central backend storage policy allows only list, read, download, stream, stat, and hash operations for that mode. Direct API calls for mutations return `403 Forbidden`.
4. The scanner only reads the filesystem and persists discoveries, mappings, and metadata in the database. It never reorganizes the source tree.
5. Resources, assets, configuration, cache, manifests, and database state use separate writable storage. No metadata, covers, sidecars, lock files, or cache files are written beside games.
6. Removing a game from the catalog deletes only RomM-owned database and cache state. The UI and API name this operation `Remove from catalog`. Source-file deletion does not exist for external roots.
7. Downloads and hashing open source files for reading only. Temporary output and locks, if needed, live outside the library root and must not change source timestamps.
8. All existing mutation paths (`unlink`, `remove`, `rmtree`, `rename`, `replace`, `move`, `mkdir`, writable `open`, upload, archive extraction, patching, and ROM deletion) require a storage-root authorization check before filesystem access.

The intended deployment mounts one existing NAS games root, for example `/volume1/Mediathek/Games:/romm/library:ro`. Platform records then map to existing relative directories inside that root. Users must not restructure or copy their collection to satisfy a RomM-owned folder convention.

A read-only container mount prevents RomM from writing, but reads can still update filesystem access-time metadata depending on the NAS export and filesystem policy. Deployments that require metadata-level immutability should mount or export the library with `noatime` or the NAS-specific equivalent. This operational setting supplements, and does not replace, the container read-only mount and backend policy.

## 2. Scope and non-goals

This proposal prepares two additive capabilities:

- a PC game component model for an unchanged directory tree;
- manifest-driven file transfer with resume and per-file integrity verification.

It does not:

- implement production PC support;
- remove or redefine existing ROM behavior;
- move, rename, rewrite, or archive library files;
- require every existing `RomFile` to belong to a component;
- replace browser downloads or EmulatorJS flows;
- define installation or execution of PC games;
- treat untrusted filenames as paths.

## 3. Current architecture

RomM is a layered modular monolith:

| Area              | Current implementation                                                                      | Relevant paths                                                                    |
| ----------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| API               | FastAPI routers and Pydantic response models                                                | `backend/main.py`, `backend/endpoints/`, `backend/endpoints/responses/`           |
| Application logic | Scan, authorization, metadata, database and filesystem handlers                             | `backend/handler/`, `backend/tasks/`                                              |
| Database          | SQLAlchemy 2 models and Alembic, supporting MariaDB/MySQL and PostgreSQL                    | `backend/models/`, `backend/alembic/versions/`                                    |
| Scanner           | Platform discovery, top-level game discovery, recursive file enumeration, provider matching | `backend/handler/scan_handler.py`, `backend/handler/filesystem/roms_handler.py`   |
| File serving      | Starlette in development, nginx internal redirects and `mod_zip` in production              | `backend/endpoints/roms/`, `backend/utils/nginx.py`, `backend/utils/zip_cache.py` |
| Frontend          | Vue 3, generated OpenAPI types, active v2 feature tree                                      | `frontend/src/services/api/`, `frontend/src/__generated__/`, `frontend/src/v2/`   |
| Async/runtime     | Redis sessions/cache and RQ tasks                                                           | `backend/handler/redis_handler.py`, `backend/tasks/`                              |

The request path is normally endpoint to handler to database/filesystem/model. API schemas in the backend are authoritative. Frontend types are generated from OpenAPI, as stated in `CLAUDE.md` and implemented under `frontend/src/__generated__/`.

## 4. Current data model

### 4.1 Logical game

`Rom` is the logical library entry (`backend/models/rom.py:297`). Its filesystem identity is stored in `fs_name`, `fs_path`, `fs_extension`, and aggregate size fields (`backend/models/rom.py:360-365`). A unique index currently enforces one filesystem name per platform (`backend/models/rom.py:315-318`).

The relationship `Rom.files` owns a list of `RomFile` records (`backend/models/rom.py:444`). A game can therefore be backed by a single file, a nested single file, or multiple files without a separate game table.

### 4.2 Physical files

`RomFile` stores a database identity, owning `rom_id`, relative path, filename, byte size, modification time, hashes, archive-member metadata, category, and missing flag (`backend/models/rom.py:106-138`). Existing hashes are CRC, MD5, SHA-1, RetroAchievements, and CHD SHA-1. There is no SHA-256 column.

The scanner creates one `RomFile` per recursive physical file (`backend/handler/filesystem/roms_handler.py:321-390`). It calculates the category from matching path segments (`backend/handler/filesystem/roms_handler.py:262-319`).

### 4.3 Multi-file and multi-disc behavior

Top-level files and top-level directories both become games (`backend/handler/filesystem/roms_handler.py:702-743`). If a game is a directory, files are enumerated recursively (`backend/handler/filesystem/roms_handler.py:347-380`). This already preserves a tree such as:

```text
Armored Core VI/
  ARMORED.CORE.VI.FIRES.OF.RUBICON.v1.06/
  ARMORED.CORE.VI.FIRES.OF.RUBICON.Update.v1.07.2/
  ARMORED.CORE.VI.FIRES.OF.RUBICON.Update.v1.08.1/
  Extras/
```

`Rom.multi_file` and `Rom.top_level_file_count` are derived from file paths (`backend/models/rom.py:670-704`). Multi-disc behavior is file-oriented. An `.m3u` is an ordinary `RomFile`, detected by `Rom.has_m3u_file()` (`backend/models/rom.py:608-613`). The v2 player persists a selected `RomFile.id` in `frontend/src/v2/utils/playerDisc.ts`.

### 4.4 DLCs, patches, manuals, updates, and extras

`RomFileCategory` currently provides `game`, `dlc`, `hack`, `manual`, `patch`, `update`, `mod`, `demo`, `translation`, `prototype`, `cheat`, `soundtrack`, and `screenshot` (`backend/models/rom.py:71-84`). Categories are file attributes, not entities.

Consequences:

- several files can share a category but have no stable component identity;
- two updates cannot reliably carry separate component versions and labels;
- an `Extras` directory can contain manuals, soundtracks, and artwork but is not itself a managed unit;
- manual metadata on `Rom` (`backend/models/rom.py:400-412`) is separate from local manual files;
- runtime patch application under `backend/endpoints/roms/patch.py` consumes categorized files but does not create a component aggregate.

## 5. Assumptions that need extension

| Assumption                                              | Evidence                                                                          | Required extension                                                                           |
| ------------------------------------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| A top-level file or directory is one game               | `backend/handler/filesystem/roms_handler.py:702-743`                              | Keep this rule. Add PC interpretation below the game directory.                              |
| Recursive members are flat `RomFile` rows               | `backend/handler/filesystem/roms_handler.py:321-390`                              | Add optional component ownership while retaining relative paths.                             |
| Category can be inferred from any matching path segment | `backend/handler/filesystem/roms_handler.py:274-312`                              | PC policy should classify first-level component roots, then optionally retain file category. |
| Selection is by `RomFile.id`                            | `backend/endpoints/roms/__init__.py:1325-1375`, `frontend/src/utils/index.ts:117` | Add component selection and manifest endpoints. Keep file IDs for compatibility.             |
| Multiple selected files are downloaded as ZIP           | `backend/endpoints/roms/__init__.py:1397-1504`                                    | Desktop protocol must request files directly. ZIP remains optional.                          |
| Resume for multi-file content requires a cached ZIP     | `backend/endpoints/roms/__init__.py:1462-1478`, `backend/utils/zip_cache.py`      | Per-file Range requests remove the ZIP cache dependency.                                     |
| Existing integrity hashes are enough for identification | `backend/models/rom.py:125-132`                                                   | Add SHA-256 for transfer integrity, computed asynchronously and cached by file snapshot.     |
| Frontend details display categorized files              | `frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue`                    | Add a component hierarchy and component actions without removing file actions.               |

## 6. Reuse analysis

### Reuse unchanged

- `Rom` for logical game identity and metadata.
- `RomFile` for every physical file and its relative path.
- platform, collection, visibility, and `ROMS_READ` permission behavior.
- `FSHandler.validate_path` as the root path boundary (`backend/handler/filesystem/base_handler.py:155-224`).
- `FileResponse` in development and `X-Accel-Redirect` in production.
- generated OpenAPI frontend contract.
- existing file listing and v2 Files tab primitives.
- RQ for expensive hash generation and manifest preparation.

### Extend carefully

- `RomFileCategory`: map compatible values, but do not use it as the component primary key.
- scanner: add a platform capability or scanner policy rather than changing all platforms.
- file endpoint authorization: factor a shared resolved-file authorization path if needed, but preserve 404 masking.
- ZIP: reuse `mod_zip` line generation for optional component ZIP streaming.

### Do not reuse as a substitute

- sibling ROMs, because components are owned parts, not equivalent games;
- collections, because they group games, not files;
- archive members, because the requirement explicitly preserves unpacked physical files;
- manual metadata, because it is provider/display metadata rather than a managed download component;
- ROM `version` or `revision`, because several component versions can exist under one game.

## 7. Target data model

### 7.1 `game_components`

```text
game_components
  id                  bigint primary key
  rom_id              bigint not null references roms(id) on delete cascade
  type                enum/string not null
  display_name        varchar not null
  root_path           varchar not null
  version             varchar null
  sequence            integer not null default 0
  source              enum(scanner, user) not null
  classification_rule varchar null
  is_downloadable     boolean not null default true
  missing_from_fs     boolean not null default false
  created_at          timestamp not null
  updated_at          timestamp not null
  unique (rom_id, root_path)
```

Allowed initial types:

```text
base_game, update, hotfix, dlc, language_pack, fix, mod,
manual, soundtrack, artbook, bonus, other
```

Use a database-safe enum strategy consistent with current cross-dialect migrations. The API should return a stable string enum. `root_path` is relative to the owning game root, normalized to `/`, and never supplied directly to the content-serving filesystem layer.

### 7.2 `rom_files.game_component_id`

Add a nullable foreign key to `game_components.id` with `ON DELETE SET NULL` and an index. Nullable preserves all current ROMs without synthetic components. Application and database constraints must ensure the component and file have the same `rom_id`.

A stronger association table is not recommended initially. A physical file belongs to one source directory component. If future product requirements need overlapping download bundles, introduce a separate bundle concept instead of making source ownership many-to-many.

### 7.3 File snapshot and SHA-256

Add to `rom_files`:

```text
sha256_hash        varchar(64) null
sha256_size_bytes  bigint null
sha256_mtime_ns    bigint null
```

The hash is valid only if current size and high-resolution modification time match the recorded snapshot. If the filesystem exposes stable inode/file identifiers, they can be recorded later, but must not be required cross-platform.

Do not hash all PC libraries synchronously during an initial scan. Persist file metadata first, enqueue bounded hash work, and expose manifest state as `preparing` until required SHA-256 values exist.

## 8. Scanner design

### 8.1 Capability boundary

Introduce a platform or scanner policy such as `component_layout = first_level_directories`. Apply it only to explicitly configured PC platforms. Existing platform scanning continues unchanged.

For a PC game directory:

1. The top-level directory remains one `Rom`.
2. Each immediate child directory becomes one component candidate.
3. All descendant files inherit that component.
4. Files directly under the game root can belong to an implicit `base_game` component or remain unassigned, based on an explicit policy.
5. No filesystem changes are made.

### 8.2 Classification

Classification should be deterministic and explainable:

1. user override from the database;
2. exact configurable directory patterns;
3. conservative token rules for update, hotfix, DLC, language, fix, mod, manual, soundtrack, artbook, and bonus;
4. first plausible non-update directory as `base_game` only if confidence is high;
5. otherwise `other`.

Persist `source` and `classification_rule`. Never silently overwrite a user classification on rescan. Directory name changes should be reconciled by file membership and snapshot evidence where possible, then shown for user confirmation if ambiguous.

### 8.3 Scanner performance

- enumerate directory metadata once;
- avoid reading file contents during discovery;
- hash in RQ jobs with configurable concurrency and I/O rate limits;
- checkpoint by `rom_file_id`, size, and mtime;
- invalidate manifests when membership or a snapshot changes;
- never follow symlinks by default.

## 9. API proposal

All routes use the existing protected-route mechanism, `ROMS_READ`, ROM visibility checks, and 404 masking.

### 9.1 Component discovery

```http
GET /api/roms/{rom_id}/components
```

Returns component metadata, counts, total bytes, manifest readiness, and a summary of missing files. This may be included in the detailed ROM schema later, but a separate endpoint limits response growth.

```http
PATCH /api/roms/{rom_id}/components/{component_id}
```

Allows an authorized manager to change display name, type, version, and order. It never renames the source directory.

### 9.2 Manifest

```http
GET /api/roms/{rom_id}/components/{component_id}/manifest
Accept: application/vnd.romm.component-manifest+json; version=1
```

Responses:

- `200` with a complete immutable manifest;
- `202` with hash preparation status and retry guidance;
- `404` for absent, hidden, or unauthorized resources;
- `409` if the component changed while a manifest was being finalized.

An optional game-level endpoint may return a manifest containing selected components:

```http
POST /api/roms/{rom_id}/download-manifests
Content-Type: application/json

{"component_ids":[17,18,19]}
```

POST avoids large query strings and creates a concrete immutable selection. It must be idempotent for the same game snapshot and selection.

### 9.3 File content

```http
GET /api/download-manifests/{manifest_id}/files/{file_id}
Range: bytes=1048576-
If-Match: "sha256:<digest>"
```

The server resolves both opaque IDs through the database. It never joins a client path to a root. Response headers:

```http
ETag: "sha256:<digest>"
Accept-Ranges: bytes
Content-Length: ...
Content-Range: bytes start-end/total
Content-Type: application/octet-stream
Content-Disposition: attachment; filename*=UTF-8''...
Digest: sha-256=:base64-digest:
```

Use `If-Match` for resumed requests. Return `412 Precondition Failed` if the file snapshot no longer matches. Return `416 Range Not Satisfiable` for invalid ranges. Do not allow multi-range responses in the first version unless nginx and tests explicitly support them.

### 9.4 Optional ZIP

```http
GET /api/roms/{rom_id}/components/{component_id}/content.zip
```

This may use existing nginx `mod_zip` streaming. It is a browser convenience and does not guarantee resumability unless served from an immutable cached ZIP. The UI must not present it as the desktop protocol.

## 10. Manifest format version 1

```json
{
  "schema": "romm.component-manifest",
  "version": 1,
  "manifest_id": "01J...",
  "created_at": "2026-08-04T12:00:00Z",
  "expires_at": "2026-08-05T12:00:00Z",
  "game": {
    "rom_id": 42,
    "name": "Armored Core VI"
  },
  "components": [
    {
      "id": 18,
      "type": "update",
      "name": "Update v1.08.1",
      "version": "1.08.1",
      "root": "ARMORED.CORE.VI.FIRES.OF.RUBICON.Update.v1.08.1"
    }
  ],
  "files": [
    {
      "id": 9012,
      "component_id": 18,
      "path": "ARMORED.CORE.VI.FIRES.OF.RUBICON.Update.v1.08.1/data/chunk.bin",
      "size": 4294967296,
      "mtime_ns": 1785844800000000000,
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "content_url": "/api/download-manifests/01J.../files/9012"
    }
  ],
  "totals": {
    "files": 1,
    "bytes": 4294967296
  }
}
```

Rules:

- `path` uses `/`, is relative, NFC-normalized, contains no empty, `.`, or `..` segment, has no leading slash, drive prefix, NUL, or control character.
- Paths are display and reconstruction instructions only. Server file lookup uses IDs.
- Path comparison rules are declared in a future version if case-collision handling becomes necessary. Version 1 rejects manifests with case-insensitive collisions for Windows-compatible clients.
- All sizes are JSON integers within the implementation's safe typed representation. Generated TypeScript handling must avoid precision loss for values above `Number.MAX_SAFE_INTEGER` if aggregate libraries can reach that size.
- The manifest is immutable. Any filesystem change produces a new `manifest_id`.
- `content_url` is relative and requires normal session or client-token authentication. Do not embed durable bearer tokens in URLs.

## 11. Desktop download protocol

1. Request a manifest and persist it together with local download state.
2. Validate every manifest path before creating local directories.
3. Compare existing local files by size and SHA-256.
4. For a missing file, download to a sibling temporary file such as `.romm-part-<id>`.
5. For a partial file, send `Range: bytes=<local-size>-` and `If-Match` with the manifest ETag.
6. Persist progress after bounded byte intervals and on clean shutdown.
7. Hash the completed temporary file with SHA-256.
8. Atomically replace the destination only after the digest matches.
9. On mismatch, delete or quarantine only the temporary file and retry according to policy.
10. After restart, reload state and repeat validation. Already verified files are skipped.

The client must limit concurrent files, apply backoff, reserve disk space conservatively, and surface manifest expiration separately from data corruption.

## 12. Security and consistency

### Path traversal

RomM already validates rooted filesystem paths in `backend/handler/filesystem/base_handler.py:155-224`, and the current file endpoint resolves bytes from a trusted `RomFile` record rather than from the supplied filename (`backend/endpoints/roms/files.py:84-108`). Preserve this pattern.

Additional controls:

- validate and canonicalize at scan time, manifest creation, and client reconstruction;
- select content by manifest ID and file ID only;
- reject absolute paths, drive/UNC prefixes, `..`, NUL, separators encoded in unexpected forms, and case-colliding destinations;
- set `Content-Disposition` from the trusted database filename;
- never unpack archives as part of this protocol.

### Symlinks

`validate_path` detects symlinks in the requested path and verifies the resolved target remains below the configured root (`backend/handler/filesystem/base_handler.py:202-224`). PC scanning should default to rejecting or ignoring all symlinks, even those that resolve inside the root, because a link target can be swapped after validation. If symlink support is ever enabled, open files using platform-specific no-follow semantics and verify the opened handle.

### Authorization

The existing per-file endpoint retrieves the parent ROM and applies visibility masking (`backend/endpoints/roms/files.py:47-63`, `backend/endpoints/roms/files.py:84-100`). Manifest creation and every file request must repeat the effective authorization check. A manifest is not an authorization grant. Disabling ordinary download auth must not automatically disable manifest auth.

### File mutation during transfer

Stat before opening, open the file, stat the handle, and compare size/mtime to the manifest snapshot. For resumed requests require `If-Match`. If a post-transfer server-side check detects mutation, abort the response when possible and invalidate the manifest. The client hash remains the final integrity authority.

### SHA-256 computation

- use streaming reads with fixed buffers;
- run outside request workers;
- cap concurrent hash jobs globally and per storage root;
- cache only against an exact size/mtime snapshot;
- expose pending and failed hash states;
- never substitute current CRC, MD5, or SHA-1 fields for transfer integrity.

### Very large files

- use `BigInteger` consistently, matching `RomFile.file_size_bytes` (`backend/models/rom.py:123`);
- never buffer file content or a generated ZIP in application memory;
- keep file serving in Starlette/nginx;
- test offsets above 2 GiB and 4 GiB;
- make client progress arithmetic 64-bit safe;
- enforce configurable concurrency, bandwidth, request duration, and disk-space limits.

### Current Range behavior

Direct file downloads use Starlette `FileResponse`, which honors Range in development, or nginx `X-Accel-Redirect` in production (`backend/endpoints/roms/files.py:134-153`). Multi-file downloads only become resumable through a cached ZIP when a Range header is present (`backend/endpoints/roms/__init__.py:1462-1478`). Dedicated Range integration assertions are currently a test gap.

The new per-file protocol can reuse the direct serving seam, but must add explicit tests for `206`, `Content-Range`, `Accept-Ranges`, `If-Match`, `412`, `416`, and authorization on both development and nginx deployment paths.

## 13. Web UI concept

Implement only in v2 under `frontend/src/v2/`.

The Files tab can evolve from a category-grouped list into:

- a game summary with total files and bytes;
- expandable component cards ordered by base game, updates, DLC, extras, then user order;
- type badge, display name, detected version, file count, bytes, hash readiness, and missing state;
- component actions: download with desktop client, optional ZIP, inspect files;
- per-file rows using the existing file download action;
- a management drawer for correcting component type/name/version without renaming source folders.

Progressive disclosure avoids overloading the game details screen. Hash preparation should be component-scoped and show a retryable state. Existing ROMs without components retain the current Files tab presentation.

## 14. Existing client impact

| Client/surface        | Impact                                                                              |
| --------------------- | ----------------------------------------------------------------------------------- |
| v1 web UI             | No required feature work. Keep compatibility only.                                  |
| v2 web UI             | Add component hierarchy and new API calls. Preserve current file and ROM downloads. |
| EmulatorJS            | No model change required. It continues selecting `RomFile.id`.                      |
| Existing API clients  | Additive endpoints and nullable fields only. Existing routes retain behavior.       |
| Browser ZIP downloads | Continue current routes. Add component ZIP optionally.                              |
| Future desktop client | Uses manifest version negotiation, Range, ETag, and SHA-256.                        |
| Scanner/watcher       | PC-capability branch plus manifest/hash invalidation. Existing platforms unchanged. |

## 15. Upstream merge strategy

1. Keep the fork's default branch as a clean mirror of `rommapp/romm/master`.
2. Configure `origin` as the fork and `upstream` as `https://github.com/rommapp/romm.git`.
3. Maintain the feature as a short stack of narrow branches: schema, scanner, manifest API, desktop protocol support, v2 UI.
4. Avoid edits to v1 and avoid broad moves or formatting changes.
5. Prefer new PC-specific modules and thin hooks in shared scanner/download code.
6. Rebase or merge upstream into an integration branch regularly, at least before every feature branch merge.
7. Run upstream tests unchanged first, then fork-specific tests.
8. Track intentional divergence in a fork document with owner, rationale, upstream conflict surface, and removal condition.
9. Submit generic improvements upstream when they are independently useful, especially Range tests, safe file snapshot helpers, and hash job infrastructure.
10. Disclose AI assistance in every upstream PR as required by `CONTRIBUTING.md` and `CLAUDE.md`.

Likely conflict hotspots are `backend/models/rom.py`, `backend/handler/filesystem/roms_handler.py`, `backend/handler/scan_handler.py`, `backend/endpoints/roms/`, generated OpenAPI files, and the v2 Files tab. Keep shared-file changes small and cover them with characterization tests before extension.

## 16. Phased delivery and migration order

### Phase 0: Reproducible baseline

- Pin an upstream commit and document runtime prerequisites.
- Start the unmodified Compose stack with a mock ROM library.
- Run baseline backend, frontend, scan, and download tests.
- Add characterization tests for nested directories and current Range behavior.

Exit: upstream starts locally and baseline evidence is recorded.

### Phase 1: Contract and data model

- Add `GameComponentType` and `GameComponent`.
- Add nullable `rom_files.game_component_id`.
- Add nullable SHA-256 snapshot columns.
- Add response schemas and generated frontend types, without enabling PC scanning.
- Verify Alembic upgrade/downgrade on MariaDB and PostgreSQL.

Exit: additive schema works and existing rows remain valid without backfill.

### Phase 2: PC scanner policy

- Add explicit PC component-layout configuration.
- Discover first-level components and assign descendant files.
- Add conservative classification and user override protection.
- Add watcher reconciliation and missing-state behavior.

Exit: the example layout maps deterministically without filesystem mutation.

### Phase 3: SHA-256 pipeline and immutable manifests

- Add bounded RQ hash jobs and snapshot invalidation.
- Implement component and manifest read APIs.
- Reject unsafe/colliding manifest paths.
- Add manifest lifecycle and readiness states.

Exit: a stable manifest is produced only for a complete unchanged snapshot.

### Phase 4: Per-file resumable content

- Implement manifest-scoped file serving.
- Add ETag, `If-Match`, Range, and immutable snapshot checks.
- Verify development and nginx paths with large sparse test files.
- Add audit logging and rate/concurrency controls.

Exit: interrupted transfers resume and only bad/missing files need retransmission.

### Phase 5: Desktop client reference implementation

- Persist manifests and partial-file state.
- Reconstruct safe directories.
- Verify SHA-256 and atomic completion.
- Test restart, expiration, mutation, disk-full, permission loss, and network failure.

Exit: end-to-end resumable component download works without ZIP.

### Phase 6: v2 web UI and optional ZIP

- Add component cards and scoped readiness/error states.
- Integrate desktop-client handoff.
- Add optional component ZIP through existing nginx infrastructure.
- Test both themes, responsive layouts, mouse, keyboard, touch, and gamepad.

Exit: component discovery and downloads are usable without changing legacy flows.

### Phase 7: Hardening and upstream cadence

- Fuzz manifest paths and Range headers.
- Load-test hashing and concurrent large-file transfers.
- Run security review, migration matrix, and compatibility suite.
- Rehearse upstream merge and document fork divergence.

Exit: production implementation can be considered separately.

## 17. Required test matrix

### Scanner and model

- one top-level PC directory becomes one `Rom`;
- every immediate child directory becomes one component;
- deep files retain exact relative paths;
- root files follow explicit policy;
- update versions remain separate components;
- unknown names become `other`;
- user overrides survive rescan;
- deleted/restored directories transition missing state;
- no source file is renamed, moved, or modified;
- symlinks, loops, and root escapes are rejected.

### Database and API

- component/file ownership cannot cross ROMs;
- cascade and `SET NULL` behavior is correct;
- MariaDB and PostgreSQL upgrade/downgrade succeed;
- unauthenticated, unauthorized, hidden, and visible cases behave consistently;
- old detailed-ROM and download schemas remain compatible;
- generated frontend types match OpenAPI.

### Manifest

- stable ordering and deterministic identity;
- Unicode normalization and separator handling;
- traversal, absolute, UNC, drive, NUL, control, and collision rejection;
- hash pending, failure, retry, and invalidation;
- manifest expiration and snapshot mutation;
- aggregate sizes beyond 4 GiB.

### Download

- full `200` response;
- valid open-ended and bounded `206` responses;
- invalid and unsatisfiable `416` responses;
- matching and stale `If-Match` behavior;
- restart from partial bytes;
- server mutation during transfer;
- final SHA-256 mismatch retries only one file;
- concurrent transfer limits;
- client disk full and atomic destination behavior;
- parity between Starlette development and nginx production serving.

### Regression

- single-file ROM download;
- nested single-file ROM download;
- multi-disc ROM and generated `.m3u`;
- existing ZIP and cached ZIP behavior;
- manual, soundtrack, patch, DLC, and update file actions;
- EmulatorJS disc selection;
- scan behavior for non-PC platforms.

## 18. Local startup status

The repository was cloned cleanly to `C:\Users\admin\Documents\RomM`. The official developer path is documented in `DEVELOPER_SETUP.md`: create `romm_mock`, copy `env.template` to `.env`, build with Docker Compose, and start at `http://localhost:3000`.

The current Windows environment has no `docker` command, so the unmodified stack could not be built or started during this analysis. No Team4s runtime, Docker Desktop, WSL, database, library files, or environment secrets were changed. Runtime validation remains the first Phase 0 gate.

## 19. Final modularity decision

**Decision: feasible and cleanly modular with one new aggregate layer.**

RomM already has the hardest structural prerequisite: a logical game owns many physical files with preserved relative paths. A PC module does not require replacing the ROM model. It requires explicit component grouping, a PC-only scanner policy, SHA-256 snapshot infrastructure, and additive APIs.

The design becomes unclean if component semantics are forced into filenames, `RomFile.category`, sibling ROMs, or ZIP artifacts. Keeping `GameComponent` optional and owned by `Rom`, while leaving `RomFile` as the canonical physical file, minimizes upstream conflict and protects existing ROM functions.
