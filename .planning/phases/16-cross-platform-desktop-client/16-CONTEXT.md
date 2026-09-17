# Phase 16: Cross-platform Desktop Client - Context

**Gathered:** 2026-09-17
**Status:** Ready for planning
**Source:** Approved cross-platform downloader design, user decisions, and completed
Phase 15 contract

<domain>
## Phase Boundary

Phase 16 creates a Windows and Linux/Bazzite desktop client with a Tauri shell
and a testable Rust download core. It downloads Phase-15 immutable manifest
members directly to a user-selected local destination. It does not add the v2
web-client handoff, install or launch games, extract or create archives, or
change a RomM source root. Those remain Phase 17 or outside product scope.
</domain>

<decisions>
## Locked Product and Protocol Decisions

- A whole-game selection means the Phase-14 eligible selected components only.
  It never means recursive arbitrary source-directory download.
- Every member remains its original file. A 100-GB EXE, ISO, PAK, or other
  file is never packaged, split into ZIPs, unpacked, or reassembled.
- The client supports both all selected game content and intentionally selected
  components, using the immutable Phase-14 manifest and Phase-15 member URL.
- The client is cross-platform: Windows plus Linux, including Bazzite. All
  local filename, filesystem, atomic-finalization, and path rules must be
  designed and tested for both families.

### Download core

- Tauri is a thin shell. `romm-download-core` contains manifest validation,
  safe path resolution, persistent job state, scheduling, file transfer,
  hashing, and recovery. It must be independently unit/integration testable.
- Use `u64` for every remote/local size, offset, range start, and progress
  counter. Tests cover 5 GiB, 80 GiB, and 120 GiB metadata without requiring
  huge test allocations.
- Default scheduling is bounded and conservative: two to four sequential
  file transfers, not multiple parallel ranges for one file.
- Each resume uses `Range: bytes=<offset>-` and the exact quoted strong
  `If-Match` snapshot from its manifest member. Weak ETags are invalid.
- A resume accepts only a strict `206` whose `Content-Range` starts exactly at
  the requested offset and declares the expected total size. A resume `200`
  never appends. A `412` makes the state `SOURCE_CHANGED`; it never combines
  source versions. A `416` with exact local size proceeds to SHA-256
  verification, while an oversized part is corrupt local state.

### Local state, integrity, and conflicts

- Incomplete output is a sibling part named
  `.romm-part-<manifest_member_id>`. It can resume only when persisted job
  state exactly matches manifest ID, member ID, expected size, SHA-256, and
  snapshot. A coincidentally named part file is never trusted.
- Final exists plus matching SHA-256 means complete. A differing final is a
  `LOCAL_CONFLICT`, never silently overwritten. An explicit overwrite still
  downloads and verifies a new sibling part first, then uses a separately
  tested platform-aware replace path.
- After a complete SHA-256 match, fsync the part and atomically rename it to a
  nonexistent final target on the same filesystem. The explicit replacement
  path is distinct, particularly on Windows.
- States include `QUEUED`, `PREPARING`, `READY`, `DOWNLOADING`, `PAUSED`,
  `VERIFYING`, `COMPLETED`, `AUTH_REQUIRED`, `SOURCE_CHANGED`,
  `MANIFEST_STALE`, `LOCAL_CONFLICT`, `DISK_FULL`, `PERMISSION_DENIED`,
  `NETWORK_ERROR`, and `CHECKSUM_FAILED`.

### Local path and resource safety

- The manifest contains only opaque file IDs and validated relative
  destinations, never NAS/container/source paths. The client creates files
  only beneath the canonical selected destination root.
- Reject traversal, POSIX and Windows absolute paths, UNC roots, drive-relative
  forms, reserved Windows names, control characters, trailing dot/space cases,
  Unicode normalization/case collisions, and symlink escapes. Resolve then
  prove canonical target containment before writing.
- Free-space preflight is remaining bytes after valid partials plus a
  conservative safety margin. Disk-full remains a recoverable state because
  other processes can fill a drive after preflight.
- No test may access Team4s, a NAS, or an actual external library. Use isolated
temporary roots, mocks, and sparse/synthetic large values.
</decisions>

<canonical_refs>

## Canonical References

- `docs/superpowers/specs/2026-09-15-cross-platform-pc-downloader-design.md`
- `.planning/phases/14-immutable-download-manifests/14-VERIFICATION.md`
- `.planning/phases/15-direct-resumable-transfer/15-VERIFICATION.md`
- `.planning/phases/15-direct-resumable-transfer/15-UAT.md`
- `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- `CLAUDE.md`

</canonical_refs>

<deferred>

## Deferred

- Phase 17: v2 handoff, browser-to-installed-client launch, and full live
  end-to-end hardening.
- No deployment, Team4s restart, live NAS access, or source-library mutation.

</deferred>

---

_Phase: 16-cross-platform-desktop-client_
_Context gathered: 2026-09-17 from approved downloader design_
