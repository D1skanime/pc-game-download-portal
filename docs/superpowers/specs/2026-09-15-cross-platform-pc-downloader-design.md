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
SHA-256 digest, and snapshot identity. A manifest becomes invalid when its source
snapshot changes.

The client saves local job state. Each incomplete original file is written to a
sibling `.romm-part` file. The client resumes with an authenticated HTTP Range
request and an `If-Match` snapshot condition. It verifies SHA-256 after the last
byte and atomically renames only a verified temporary file to its final manifest
path.

The client accepts only safe manifest paths and creates them only below the
chosen destination root. It uses 64-bit-safe size and offset accounting, bounded
parallel downloads, conservative free-space checks, and clear recovery states.

## Protocol

1. The web UI or client submits a whole-game or selected-component request.
2. RomM returns an immutable manifest, or a bounded preparing/changed/error state.
3. The client validates manifest paths and saves job state.
4. It skips completed files whose size and SHA-256 match the manifest.
5. It resumes partial files from their local byte count using Range and If-Match.
6. A stale manifest, changed source, invalid range, or authorization failure stops
   that file without combining versions.
7. A verified file is atomically completed; other files continue independently.

## Delivery Phases

1. Phase 14 creates selected immutable manifests from the existing PC component
   and per-file SHA-256 evidence.
2. Phase 15 adds manifest-scoped direct Range delivery and snapshot enforcement.
3. Phase 16 builds the cross-platform Tauri/Rust local download client.
4. Phase 17 adds v2 client handoff and end-to-end hardening.

## Verification

Tests cover direct non-ZIP transfer, 4-GiB-plus offsets, resume after restart,
source changes, stale If-Match, invalid checksums, disk-full and permission
failures, Windows/Linux-safe paths, and before/after source-library evidence.
