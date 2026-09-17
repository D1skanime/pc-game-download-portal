---
phase: 16-cross-platform-desktop-client
plan: 02
subsystem: desktop-core
tags: [rust, filesystem-security, recovery, sha256, unicode]
requires:
  - phase: 16-cross-platform-desktop-client
    provides: "Validated opaque manifest and member records"
provides:
  - "Canonical opaque destination-root handles that prevent later raw-path authority"
  - "Atomic, exact per-member recovery records and safe final/part classification"
  - "Portable path, collision, and symlink protections for local downloader output"
affects: [16-03, 16-04, desktop-client]
tech-stack:
  added: [sha2]
  patterns:
    - "Register a native-selected path once, then pass only a live opaque handle through core APIs"
    - "Resume parts only when every persisted identity field and local byte count matches"
key-files:
  created:
    - desktop/crates/romm-download-core/src/path.rs
    - desktop/crates/romm-download-core/src/job_store.rs
    - desktop/crates/romm-download-core/src/recovery.rs
    - desktop/crates/romm-download-core/tests/path_security.rs
    - desktop/crates/romm-download-core/tests/job_recovery.rs
  modified:
    - desktop/crates/romm-download-core/src/lib.rs
    - desktop/crates/romm-download-core/src/model.rs
key-decisions:
  - "Destination paths enter the core only at native registration and are represented thereafter by opaque expirable handles."
  - "Final files are SHA-256 verified, while parts require all persisted identity fields plus exact byte count before resumption."
patterns-established:
  - "Re-prove canonical root containment and reject symlinks immediately before local candidate inspection."
requirements-completed: [CLNT-02, CLNT-04, CLNT-05]
duration: 4min
completed: 2026-09-17
---

# Phase 16 Plan 02: Safe local recovery boundary summary

**Canonical destination-root handles, portable path rejection, atomic job records, and SHA-256-backed final/part recovery classification protect every local downloader write.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-09-17T07:40:00Z
- **Completed:** 2026-09-17T07:43:44Z
- **Tasks:** 1/1
- **Files modified:** 10

## Accomplishments

- Rejected cross-platform unsafe destination forms, portable case and Unicode collisions, and symlink escapes before candidate files can be used.
- Added an opaque destination-root registry that canonicalizes the native selection once and rejects expired handles before I/O.
- Persisted exact per-member recovery identity atomically and classified matching finals, conflicts, valid parts, mismatched parts, and oversized parts safely.

## Task Commits

1. **Canonical local path, persisted identity, and recovery classification, RED** - `b832f6e1e` (test)
2. **Canonical local path, persisted identity, and recovery classification, GREEN** - `1c76a0b43` (feat)

## Files Created/Modified

- `desktop/crates/romm-download-core/src/path.rs` - canonical root registry and portable safe target preparation.
- `desktop/crates/romm-download-core/src/job_store.rs` - atomic client-private persisted member state.
- `desktop/crates/romm-download-core/src/recovery.rs` - SHA-256 final verification and exact part recovery classification.
- `desktop/crates/romm-download-core/tests/path_security.rs` - hostile path, Unicode collision, opaque-handle, and symlink regressions.
- `desktop/crates/romm-download-core/tests/job_recovery.rs` - atomic state and final/part recovery regressions.

## Decisions Made

- Core-owned destination handles have no path serialization and expire explicitly, so queue and recovery APIs cannot be given arbitrary local paths.
- A same-name final is only complete after its digest matches. A smaller part is only resumable when its manifest ID, member ID, size, hash, snapshot, destination, and byte count all match the persisted record.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added audited SHA-256 verification and reproducible lockfile**

- **Found during:** Task 1, final-candidate classification.
- **Issue:** The existing crate did not include a cryptographic SHA-256 implementation, so a same-name final could not be safely classified as complete.
- **Fix:** Audited and pinned `sha2` 0.10.9, enabled UUID v4 handles, and committed the generated workspace lockfile.
- **Files modified:** `desktop/crates/romm-download-core/Cargo.toml`, `desktop/Cargo.lock`, `desktop/DEPENDENCY-AUDIT.md`, `desktop/crates/romm-download-core/src/recovery.rs`.
- **Verification:** Full core test suite, `cargo fmt --check`, and Clippy with warnings denied passed in the official Rust 1.90 container.
- **Committed in:** `1c76a0b43`.

---

**Total deviations:** 1 auto-fixed (Rule 2).
**Impact on plan:** The audited dependency is required to meet the mandatory matching-final integrity condition without introducing a custom cryptographic implementation.

## Issues Encountered

- The host has no Cargo or Rust tooling. All Rust checks ran in the official `rust:1.90` Docker image; Rustfmt and Clippy components were installed only inside each disposable verification container.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Later transfer and finalization plans can accept only registry-issued destination handles and exact persisted local recovery state. No backend, NAS, Team4s, Tauri, or source-root integration was added.

## Self-Check: PASSED

- All five planned local-boundary source and regression-test artifacts exist.
- Both TDD commits, `b832f6e1e` and `1c76a0b43`, exist in Git history.

---

_Phase: 16-cross-platform-desktop-client_
_Completed: 2026-09-17_
