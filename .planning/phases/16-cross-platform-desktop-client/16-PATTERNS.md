# Phase 16: Cross-platform Desktop Client - Pattern Map

**Mapped:** 2026-09-17  
**Files analyzed:** 16 planned desktop files/directories  
**Analogs found:** 5 / 16 (the repository has no existing Rust, Cargo, or Tauri workspace)

## Scope and Boundary

Phase 16 adds an isolated `desktop/` workspace. It must not change `frontend/`,
the frozen v1 UI, the active v2 UI, the download-manifest backend API, source
roots, Team4s, or a NAS. Phase 17 owns v2-to-installed-client handoff.

The desktop client consumes the existing Phase 14 and 15 HTTP contract. The
core receives only an origin, a device/client token, a manifest ID, opaque
member IDs, safe relative destinations, SHA-256 values, strong snapshots, and
relative member URLs. It must never receive or persist a source/NAS path.

`desktop/` is intentionally a new top-level workspace, rather than a child of
`frontend/`: the existing `frontend/package.json` is a browser-only Vue/Vite
application with cookie/CSRF interceptors, whereas this client needs native
filesystem access and explicit bearer authentication. Reusing it would couple
the client to the later Phase-17 browser handoff.

## File Classification

| New/Modified File                                    | Role                       | Data Flow                  | Closest Analog                                       | Match Quality                             |
| ---------------------------------------------------- | -------------------------- | -------------------------- | ---------------------------------------------------- | ----------------------------------------- |
| `desktop/Cargo.toml`                                 | workspace config           | build                      | none                                                 | none, first Rust workspace                |
| `desktop/crates/romm-download-core/Cargo.toml`       | library config             | build                      | none                                                 | none                                      |
| `desktop/crates/romm-download-core/src/lib.rs`       | library facade             | request-response           | `backend/handler/filesystem/roms_handler.py`         | architecture-only                         |
| `desktop/crates/romm-download-core/src/model.rs`     | model                      | transform                  | `backend/endpoints/responses/download_manifest.py`   | contract-match                            |
| `desktop/crates/romm-download-core/src/manifest.rs`  | validator/service          | request-response           | `backend/endpoints/responses/download_manifest.py`   | contract-match                            |
| `desktop/crates/romm-download-core/src/path.rs`      | security utility           | file-I/O                   | none                                                 | none, platform-specific security boundary |
| `desktop/crates/romm-download-core/src/job_store.rs` | persistence service        | file-I/O                   | none                                                 | none                                      |
| `desktop/crates/romm-download-core/src/transfer.rs`  | HTTP/file transfer service | streaming, file-I/O        | `backend/endpoints/download_manifests.py`            | protocol-match                            |
| `desktop/crates/romm-download-core/src/hash.rs`      | integrity utility          | streaming, file-I/O        | `backend/handler/filesystem/roms_handler.py`         | role-match                                |
| `desktop/crates/romm-download-core/src/recovery.rs`  | recovery service           | file-I/O                   | none                                                 | none                                      |
| `desktop/crates/romm-download-core/src/scheduler.rs` | scheduler                  | event-driven               | `backend/handler/filesystem/roms_handler.py`         | bounded-resource match                    |
| `desktop/crates/romm-download-core/src/error.rs`     | error model                | transform                  | `backend/endpoints/download_manifests.py`            | outcome-match                             |
| `desktop/crates/romm-download-core/tests/*.rs`       | integration tests          | request-response, file-I/O | `backend/tests/endpoints/test_download_manifests.py` | behavior-match                            |
| `desktop/src-tauri/Cargo.toml` and `src/main.rs`     | native shell               | command/event              | none                                                 | none, first Tauri shell                   |
| `desktop/src-tauri/src/commands.rs`                  | command adapter            | request-response           | none                                                 | none, must remain thin                    |
| `desktop/src-tauri/tauri.conf.json` and capabilities | platform config            | config                     | none                                                 | none                                      |
| `desktop/ui/` minimal shell UI and tests             | component                  | event-driven               | `frontend/src/v2/views/Pair.vue`                     | limited, device-pair state only           |

The planner may split the core files further, but must retain the `desktop/`
boundary and keep every engine concern in `romm-download-core`, not inside a
Tauri command.

## Pattern Assignments

### `desktop/crates/romm-download-core/src/model.rs` and `manifest.rs`

**Analog:** `backend/endpoints/responses/download_manifest.py:27-44`

The API is the authority for the wire shape. Model it as a strict, versioned
Rust deserialization boundary. Reject an unknown schema version, malformed UUID
or opaque ID, non-lowercase 64-hex digest, absent/weak/unquoted snapshot, URL
outside the relative Phase-15 member route, negative/non-`u64` size, duplicate
member identity, and unsafe destination before a job or file is created.

```python
class DownloadManifestMemberSchema(BaseModel):
    file_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    destination: str
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot: str = Field(pattern=r'^".+"$')
    download: str = Field(
        pattern=r"^/api/download-manifests/[0-9a-f-]{36}/files/[0-9a-f-]{36}$"
    )
```

Do not deserialize an API-provided source path because none exists in this
contract. The core's canonical record needs at least `manifest_id`, member
`file_id`, `destination`, `size: u64`, `sha256`, `snapshot`, and `download`.
Keep snapshot identity separate from SHA-256 integrity.

### `desktop/crates/romm-download-core/src/transfer.rs`

**Analog:** `backend/endpoints/download_manifests.py:191-256`

The client must mirror, not reinterpret, the existing direct-transfer protocol:

```python
range_header = request.headers.get("range")
if_match = request.headers.get("if-match")
if if_match is not None and if_match != persisted_member.snapshot:
    _precondition_failed()
if range_header is not None and if_match is None:
    _precondition_failed()
```

```python
if bounds is not None:
    response_status = status.HTTP_206_PARTIAL_CONTENT
    headers["Content-Range"] = f"bytes {start}-{end}/{lease.size_bytes}"
```

Implementation assignments:

- Fresh member transfer: authenticated GET of the server-provided relative URL,
  no Range, accept `200` only with exact `Content-Length == size`.
- Resume: send `Range: bytes=<valid_part_len>-` and the byte-for-byte quoted,
  non-weak `If-Match: <snapshot>`. Accept only `206` whose parsed
  `Content-Range` begins at that exact offset and whose total equals `size`.
  Never append a `200` response.
- Map `412` to `SOURCE_CHANGED` when its bounded API code is
  `snapshot_mismatch` or `source_changed`; use `MANIFEST_STALE` for the
  lifecycle response and require a new manifest. Map `401`/`403` to
  `AUTH_REQUIRED`, not network failure. Treat `416` plus exact local size as
  an immediate hash-verification candidate; an oversized part is local corrupt
  state.
- The request must use `Authorization: Bearer <device-token>` on every GET.
  Do not copy the browser cookie/CSRF axios interceptor.
- Preserve the server-relative `download` field by joining it only to the
  user-configured HTTPS/HTTP origin. Never permit a manifest to replace the
  origin, or forward redirects to an unrelated origin with credentials.

### `desktop/crates/romm-download-core/src/hash.rs` and `scheduler.rs`

**Analog:** Phase 15 verified transfer, summarized in
`.planning/phases/15-direct-resumable-transfer/15-02-SUMMARY.md`.

The established resource pattern is one bounded lease retained from fresh
verification through stream cleanup. The client equivalent is a bounded
semaphore around sequential whole-file streams, with every permit released on
success, cancellation, network error, hash failure, and file error. Default to
two to four files in parallel, never many ranges for a single file. All byte
arithmetic is `u64`; test only synthetic metadata at 5, 80, and 120 GiB.

Hash bytes while writing and, after a completed stream or exact-size `416`, hash
the finished sibling part before finalization. A mismatch is
`CHECKSUM_FAILED` and leaves no promoted final file.

### `desktop/crates/romm-download-core/src/path.rs`, `job_store.rs`, and `recovery.rs`

**Analog:** none. This is the new local security boundary and must be designed
as a pure, independently testable Rust API.

Required pattern assignments:

- `PathResolver` validates manifest relative paths independently of the host
  path parser. Reject both slash styles for traversal, POSIX roots, Windows
  drive and drive-relative forms, UNC paths, control characters, reserved
  Windows names, trailing dots/spaces, normalization/case collisions, and
  symlink escapes. Resolve `destination_root + relative_destination`, then
  prove the canonical write target remains below the canonical chosen root.
- Persist a per-member sidecar job record beside or in a client-private job
  store. A `.romm-part-<manifest_member_id>` may resume only when stored
  manifest ID, member ID, expected size, SHA-256, and exact snapshot all match.
  A coincidentally named part is not state.
- Classify local candidates without overwrite: matching final is complete,
  differing final is `LOCAL_CONFLICT`, smaller matching-state part is resumable,
  oversized part is corrupt local state. Explicit overwrite still writes and
  validates a new sibling part before a platform-specific replace operation.
- Normal completion is `fsync(part)` then same-filesystem atomic rename to a
  final path which does not exist. The explicit final replacement operation is
  distinct and must have Windows and Linux tests, since replacement semantics
  differ.
- Preflight free space is remaining bytes after valid partials plus a
  conservative safety margin. Disk full later remains `DISK_FULL`, preserving
  safe restart state. Map OS permission failures to `PERMISSION_DENIED`.

### `desktop/src-tauri/*` and `desktop/ui/*`

**Analogs:** no current desktop shell exists. The closest auth state-flow is
`frontend/src/v2/views/Pair.vue:28-70`; the established authentication backend
is `backend/handler/auth/hybrid_auth.py:28-82`.

The Tauri layer is an adapter only. It may expose typed commands/events for
configuration, device authorization, manifest submission, destination choice,
queue control, and status snapshots, then delegates to `romm-download-core`.
It may not construct HTTP ranges, resolve paths, write parts, perform hash
verification, or hold job state itself.

Use the existing device authorization server contract rather than a new
password/token API. `backend/endpoints/device_auth.py:68-112` initializes a
user-approved flow and `:300-348` polls for a scoped token. The backend accepts
an `rmm_` client token as `Authorization: Bearer` in
`backend/handler/auth/hybrid_auth.py:45-82`. Store such a token only in an OS
credential store, never in the manifest, job JSON, event payload, log, URL, or
frontend code. Phase 16 can open the existing approval URL or show its code;
Phase 17, not this phase, adds the v2 selection handoff/custom-scheme flow.

The desktop UI is a new minimal shell under `desktop/ui/`, not a modification of
`frontend/src`. It should present the locked core states verbatim and make
`LOCAL_CONFLICT` choices explicit: overwrite, choose another destination, or
skip. No archive, game installation, launch, extraction, or source-management
surface belongs here.

## Shared Patterns

### Existing API contract, no server edits

**Sources:** `backend/endpoints/download_manifests.py:157-256`,
`backend/endpoints/responses/download_manifest.py:27-44`.

- Manifest creation is `POST /api/roms/{rom_id}/download-manifests` with
  `component_ids: null` for all eligible components or a non-empty explicit
  list. Phase 17 owns browser selection handoff, so Phase 16 must accept a
  prepared manifest ID/selection input through its own shell without changing
  these routes.
- Manifest retrieval is `GET /api/download-manifests/{manifest_id}`.
- Member retrieval is only the opaque relative URL supplied in the manifest.
  Each request needs current authorization and ROM visibility, therefore a
  historical URL is not an authorization credential.
- Lifecycle status is distinct: `410 manifest_expired`, `410 manifest_revoked`,
  `409 manifest_source_changed`; per-member `412` is not safe to append.

### Existing explicit-device authentication

**Sources:** `backend/endpoints/device_auth.py:68-112, 300-348`,
`backend/handler/auth/hybrid_auth.py:28-82`.

This is the only in-repository native-client authorization analog. Request only
the scope required for manifest and member reads (`ROMS_READ`), save the issued
token in the platform credential store, and honor expiry/authorization errors.
Do not rely on the browser's `/api` relative base URL, session cookie, or CSRF
cookie pattern in `frontend/src/services/api/index.ts:1-31`.

### Tests

**Analogs:** `backend/tests/endpoints/test_download_manifests.py` and
`.planning/phases/15-direct-resumable-transfer/15-VERIFICATION.md`.

Core tests use isolated temporary destination roots and a mock HTTP server or
mock transport. They must not contact Team4s, a NAS, or an external library.
Cover exact direct bytes, restart resume, 200-on-resume rejection, strict 206
`Content-Range`, 412, 416, auth/lifecycle outcomes, bad checksums, disk full,
permission denial, safe partial retention, 5/80/120 GiB metadata, all listed
Windows/POSIX/Unicode path attacks, symlink escape, and distinct normal rename
versus approved replacement paths. Tauri commands receive only thin adapter
tests; core behavior belongs in the core crate tests.

## No Analog Found

| Area                                                                    | Reason and planner direction                                                                                                                                                                   |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rust workspace, HTTP client, persistent jobs, platform filesystem logic | This is the repository's first Rust code. Create it under `desktop/` and keep it self-contained.                                                                                               |
| Tauri configuration, capabilities, command boundary                     | No Tauri application exists. Configure least privilege for the selected local destination and credential storage only, without exposing arbitrary shell or filesystem commands to the webview. |
| Cross-platform atomic replacement                                       | No existing code covers Windows replacement semantics. Keep it separately tested from normal rename.                                                                                           |
| Desktop UI design system                                                | No desktop-client UI exists. Do not import or refactor frozen v1 or alter v2. Use a small isolated UI shell driven by typed core state.                                                        |

## Metadata

**Analog search scope:** `backend/endpoints`, `backend/handler/auth`,
`backend/endpoints/responses`, `frontend/src/services/api`, `frontend/src/v2`,
phase 14/15 verification and summaries, root build configuration.  
**Files scanned:** 14 direct source/config/phase artifacts.  
**Pattern extraction date:** 2026-09-17.
