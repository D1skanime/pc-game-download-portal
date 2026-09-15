# Cross-platform PC Downloader Design

## Goal

Provide a Tauri/Rust desktop client for Windows and Linux/Bazzite that downloads
whole PC games or selected components directly into a user-selected destination,
including 100-GB-class files, without changing the NAS library.

## Product Boundary

- The v2 web UI retains the current whole-game or component selection model.
- The desktop client downloads original files directly. It does not receive,
  create, split, unpack, or reassemble ZIP archives.
- The client does not install software, launch games, extract archives, or alter
  the source library.
- The NAS and every RomM source root remain read-only.

## Architecture

RomM turns an authorized selection into an immutable download manifest. Each
member has an opaque server identity, safe relative destination path, byte size,
SHA-256 integrity digest, and a separate strong per-file snapshot validator. The
snapshot identifies one source version, while SHA-256 proves its final content.
The validator is always a strong ETag, never a `W/` weak ETag.
The server resolves `file_id` to the trusted source root and file internally;
neither manifests nor client state contain a NAS path.

The Tauri shell calls a testable Rust library, `romm-download-core`, containing
`ManifestValidator`, `PathResolver`, `JobStore`, `DownloadScheduler`,
`FileDownloader`, `HashVerifier`, and `RecoveryManager`. Each incomplete original
file is written to a sibling `.romm-part-<manifest_member_id>` file. The client
resumes with an authenticated HTTP Range request and `If-Match` for that member's
snapshot validator. It verifies SHA-256 after the last byte, fsyncs the temporary
file, then atomically renames only that verified sibling to a nonexistent final
path. A separately tested cross-platform replace operation is required when an
explicit user overwrite replaces an existing final file.

The client accepts only safe manifest paths and creates them only below the
chosen destination root. It rejects traversal, POSIX/Windows absolute and UNC
paths, drive-relative paths, reserved Windows names, control characters,
normalization/case collisions, and symlink escapes. It uses `u64` for all size and
offset accounting, two to four sequential per-file transfers by default, and a
conservative remaining-bytes plus safety-margin free-space preflight.

## Manifest Member Contract

```json
{
  "file_id": "opaque-file-id",
  "destination": "Game/Binaries/game.pak",
  "size": 87345678901,
  "sha256": "...",
  "snapshot": "\"romm-abc123...\"",
  "download": "/api/download-manifests/.../files/..."
}
```

`snapshot` is the strong validator used with `If-Match`; it is deliberately not
the SHA-256 field. A resume request uses `Range: bytes=<valid_partial_size>-` and
`If-Match: <snapshot>`. A changed source returns `412 Precondition Failed`; the
client requests a new manifest rather than accepting bytes from another version.
The server rechecks authentication and manifest authorization for every member
request. A historical download URL is never a durable authorization grant.

## Protocol

1. The web UI or client submits a whole-game or selected-component request.
2. RomM returns an immutable manifest, or a bounded preparing/changed/error state.
3. The client validates manifest paths and saves job state. A resumable part is
   accepted only when its stored state exactly matches manifest ID, member ID,
   expected size, SHA-256, and strong snapshot; a coincidentally named part file is
   never resumed blindly.
4. It classifies a final matching SHA-256 file as complete, a differing final file
   as `LOCAL_CONFLICT`, a smaller valid part as resumable, and an oversized part as
   corrupt local state. It never overwrites a foreign final file automatically.
5. It resumes partial files from their local byte count using Range and If-Match,
   accepting `206` only when `Content-Range` begins at that exact offset and names
   the expected total size. A `200` response to a resume request is never appended.
6. A `416` response with a part exactly equal to expected size proceeds to SHA-256
   verification; an oversized part is corrupt local state. A stale manifest,
   changed source, invalid range, or authorization failure stops that file without
   combining versions.
7. A verified file is atomically completed; other files continue independently.
   Explicit overwrite downloads and verifies a new sibling part first, then uses
   the platform-tested replacement path rather than overwriting the final file.

## Delivery Phases

1. Phase 14 creates selected immutable manifests from the existing PC component
   and per-file SHA-256 evidence.
2. Phase 15 adds manifest-scoped direct Range delivery and snapshot enforcement.
3. Phase 16 builds the cross-platform Tauri/Rust local download client.
4. Phase 17 adds v2 client handoff and end-to-end hardening.

## Verification

Tests cover direct non-ZIP transfer, 4-GiB-plus offsets, resume after restart,
source changes, stale If-Match, invalid checksums, disk-full and permission
failures, Windows/Linux-safe paths, symlink escapes, and before/after
source-library evidence. Path tests include `../`, backslash traversal, POSIX and
UNC roots, drive-relative forms, reserved Windows names, trailing-space/dot names,
and Unicode normalization cases. Transfer tests use `u64` values at 5 GiB, 80 GiB,
and 120 GiB, validate every `206` response, and separately test Windows/Linux
normal completion and explicit conflict-replacement paths.

## Client States

Normal states are `QUEUED`, `PREPARING`, `READY`, `DOWNLOADING`, `PAUSED`,
`VERIFYING`, and `COMPLETED`. Recovery states are `AUTH_REQUIRED`,
`SOURCE_CHANGED`, `MANIFEST_STALE`, `LOCAL_CONFLICT`, `DISK_FULL`,
`PERMISSION_DENIED`, `NETWORK_ERROR`, and `CHECKSUM_FAILED`. A local conflict
requires an explicit user choice to overwrite, choose another destination, or skip.
Manifest states are `VALID`, `EXPIRED`, `REVOKED`, and `SOURCE_CHANGED` so that a
stale lifetime state is not confused with a changed source snapshot.
