---
phase: 16-cross-platform-desktop-client
plan: 04
subsystem: desktop-core
tags: [rust, sha256, fsync, atomic-finalization, recovery, windows]
requires:
  - phase: 16-cross-platform-desktop-client
    provides: "Validated local paths, exact recovery records, strict direct transfer, and bounded scheduling"
provides:
  - "SHA-256-gated, fsynced sibling-part publication without default overwrite"
  - "Platform-aware explicit replacement, including Windows ReplaceFileW"
  - "Conservative free-space preflight and persisted recoverable local failure states"
affects: [16-05, 16-06, desktop-client]
tech-stack:
  added: []
  patterns:
    - "Verify, fsync, and publish only an exact sibling part through a narrow platform trait"
    - "Map local finalization failures to bounded persisted recovery states while retaining the part"
key-files:
  created:
    - desktop/crates/romm-download-core/src/hash.rs
    - desktop/crates/romm-download-core/src/finalize.rs
    - desktop/crates/romm-download-core/src/engine.rs
    - desktop/crates/romm-download-core/tests/finalization.rs
    - desktop/crates/romm-download-core/tests/recovery_failures.rs
  modified:
    - desktop/crates/romm-download-core/src/lib.rs
key-decisions:
  - "Normal publication uses a no-replace hard-link publication after part fsync, while explicit replacement is a separate operation."
  - "Windows production replacement calls ReplaceFileW rather than relying on Unix rename behavior."
  - "Free-space preflight subtracts only partials that do not exceed their expected member size and retains a 2 to 5 percent margin."
patterns-established:
  - "Local finalization injects platform operations so Linux and Windows semantics can be exercised without external storage."
requirements-completed: [CLNT-02, CLNT-03, CLNT-05]
duration: 12min
completed: 2026-09-17
---

# Phase 16 Plan 04: Integrity-gated finalization and recovery summary

**The desktop download core now verifies and fsyncs exact SHA-256 sibling parts before no-replace publication, and retains bounded recovery state for every local failure.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-17T07:49:00Z
- **Completed:** 2026-09-17T08:01:00Z
- **Tasks:** 1/1
- **Files modified:** 6

## Accomplishments

- Verified parts by expected size and SHA-256 before fsync and final publication.
- Kept normal completion no-replace, with a distinct explicit replacement path and native Windows `ReplaceFileW` implementation.
- Added a stateful integrity coordinator that atomically stores `COMPLETED` only after publication and stores bounded recovery state while retaining a usable part after failure.
- Covered foreign-final preservation, Linux and Windows compatibility replacement paths, checksum rejection, conservative u64 preflight, and injected disk-full recovery.

## Task Commits

1. **Integrity-gated local finalization and recovery orchestration, RED** - `34f8989e5` (test)
2. **Integrity-gated local finalization and recovery orchestration, GREEN** - `8053193eb` (feat)

## Files Created/Modified

- `desktop/crates/romm-download-core/src/hash.rs` - exact file-size and SHA-256 verification.
- `desktop/crates/romm-download-core/src/finalize.rs` - fsync, no-replace publication, explicit platform replacement, preflight, and failure classification.
- `desktop/crates/romm-download-core/src/engine.rs` - persisted completion and recoverable failure coordinator.
- `desktop/crates/romm-download-core/src/lib.rs` - narrow public core exports.
- `desktop/crates/romm-download-core/tests/finalization.rs` - deterministic publication, conflict, replacement, and checksum tests.
- `desktop/crates/romm-download-core/tests/recovery_failures.rs` - deterministic preflight and fault-injected job-state tests.

## Decisions Made

- Use a same-directory hard link for normal no-replace publication after fsync, so an existing final remains untouched.
- Keep Windows replacement distinct with `ReplaceFileW`; Linux compatibility tests do not claim Unix rename behavior for Windows production builds.
- Treat post-preflight local conditions as recoverable states because a free-space calculation cannot reserve capacity against other processes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Build correctness] Corrected the valid-part preflight dereference**

- **Found during:** Task 1, GREEN compilation.
- **Issue:** The first implementation dereferenced the `Option::filter` value twice, preventing the Rust crate from compiling.
- **Fix:** Used the single `u64` reference supplied by `Option::filter`.
- **Files modified:** `desktop/crates/romm-download-core/src/finalize.rs`.
- **Verification:** focused finalization and recovery tests, formatter, and warnings-denied Clippy passed.
- **Committed in:** `8053193eb`.

---

**Total deviations:** 1 auto-fixed (Rule 1).
**Impact on plan:** Required for build correctness with no scope expansion.

## Issues Encountered

- The host lacks Cargo. All Rust gates ran in disposable official `rust:1.90` Docker containers with `CARGO_TARGET_DIR=/tmp/romm-target`, so no workspace `desktop/target` or root-owned build output was created. Rustfmt and Clippy were installed only inside those disposable containers.
- The broader `cargo test -p romm-download-core` run exposed a pre-existing race in `tests/transfer_protocol.rs`: multiple tests share a PID-only temporary root and one cleanup can remove it while another test reads it. The task-owned focused suites and all required formatter and Clippy gates passed. The unrelated test was not modified.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plans 16-05 and 16-06 can invoke the integrity coordinator with opaque root handles and existing job storage. Final files remain protected from unverified data and non-explicit conflicts.

## Self-Check: PASSED

- All six plan-owned source and test artifacts exist.
- Both TDD commits, `34f8989e5` and `8053193eb`, exist in Git history.
- Focused tests, `cargo fmt --check`, and warnings-denied Clippy passed in the official Rust container.

---

_Phase: 16-cross-platform-desktop-client_
_Completed: 2026-09-17_
