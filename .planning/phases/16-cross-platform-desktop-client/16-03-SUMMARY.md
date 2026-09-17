---
phase: 16-cross-platform-desktop-client
plan: 03
subsystem: desktop-core
tags: [rust, http, range-requests, resumable-transfer, scheduler, security]
requires:
  - phase: 16-cross-platform-desktop-client
    provides: "Validated immutable manifests and opaque destination-root handles"
provides:
  - "Origin-bound bearer-authenticated immutable manifest retrieval"
  - "Strict fresh and resume transfer response validation with u64 accounting"
  - "Cancellation-safe bounded whole-file transfer permits"
affects: [16-04, desktop-client]
tech-stack:
  added: []
  patterns:
    - "Use transport and file-sink traits so protocol behavior is verified without a live server or NAS."
    - "Retain the configured origin in the core engine and reject cross-origin final redirect URLs before response acceptance."
key-files:
  created:
    - desktop/crates/romm-download-core/src/http.rs
    - desktop/crates/romm-download-core/src/transfer.rs
    - desktop/crates/romm-download-core/src/scheduler.rs
    - desktop/crates/romm-download-core/tests/transfer_protocol.rs
    - desktop/crates/romm-download-core/tests/scheduler.rs
  modified:
    - desktop/crates/romm-download-core/src/lib.rs
    - desktop/crates/romm-download-core/src/model.rs
key-decisions:
  - "The protocol engine receives only a validated configured origin, opaque manifest ID, and destination-root handle."
  - "A fresh response must be an exact 200 stream, while a resumed response must be an exact 206 range response with the manifest snapshot."
  - "Scheduler permits use RAII release so cancellation and every error exit cannot consume capacity permanently."
patterns-established:
  - "No manifest raw JSON, cookie state, CSRF state, origin replacement, or token-bearing URL enters the shell-facing core API."
requirements-completed: [CLNT-01, CLNT-02]
duration: 5min
completed: 2026-09-17
---

# Phase 16 Plan 03: Direct transfer protocol and scheduler summary

**A mock-verified Rust transfer core now fetches immutable manifests from a configured origin, strictly validates byte-safe 200/206 resume responses, and caps concurrent whole-file streams.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-09-17T07:46:30Z
- **Completed:** 2026-09-17T07:51:55Z
- **Tasks:** 1/1
- **Files modified:** 7

## Accomplishments

- Added an origin-bound authenticated manifest client which accepts only HTTP(S), adds bearer authorization to each request, and rejects cross-origin redirect results before parsing data.
- Added strict direct-transfer validation for exact fresh 200 bodies, resumed Range and If-Match requests, exact 206 Content-Range and Content-Length values, lifecycle/auth failures, and safe 416 verification candidates.
- Added a conservative 2 through 4 whole-file permit scheduler that releases capacity through RAII on all normal, error, pause, and cancellation exits.
- Added mock protocol tests for invalid manifests, lifecycle/auth states, root handles, redirects, u64 5/80/120 GiB metadata, and scheduler bounds.

## Task Commits

1. **Strict direct transfer and bounded scheduling, RED** - `431b75437` (test)
2. **Failed manifest queueing regression coverage, RED** - `08b353f7a` (test)
3. **Strict direct transfer and bounded scheduling, GREEN** - `1529b5a81` (feat)
4. **Scheduler test formatting** - `4d2a35a0d` (style)

## Files Created/Modified

- `desktop/crates/romm-download-core/src/http.rs` - origin validator and mockable credentialed transport boundary.
- `desktop/crates/romm-download-core/src/transfer.rs` - manifest queueing and strict fresh/resume protocol engine.
- `desktop/crates/romm-download-core/src/scheduler.rs` - bounded RAII permit scheduler for whole-file streams.
- `desktop/crates/romm-download-core/src/lib.rs` - public core API exports.
- `desktop/crates/romm-download-core/src/model.rs` - opaque manifest-ID parsing for configured core requests.
- `desktop/crates/romm-download-core/tests/transfer_protocol.rs` - mock origin, status, redirect, range, and large-u64 protocol coverage.
- `desktop/crates/romm-download-core/tests/scheduler.rs` - configured-limit and capacity-release coverage.

## Decisions Made

- The transfer engine retains the origin used to retrieve the validated manifest, so member routes stay relative and cannot replace the authority.
- The mock transport reports its final URL. The core rejects a redirect result outside the configured origin before it accepts response bytes or parses a manifest.
- No real HTTP adapter was added in this plan because the protocol layer is complete and testable through transport traits without introducing a network library or live service dependency.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Build correctness] Replaced unit trait errors with bounded explicit error markers**

- **Found during:** Task 1, required Clippy verification.
- **Issue:** Clippy with warnings denied rejected the initial transport and file-sink `Result<_, ()>` signatures.
- **Fix:** Added bounded `HttpTransportError` and `FileSinkError` marker types, then re-ran the focused tests, formatter, and Clippy gates.
- **Files modified:** `desktop/crates/romm-download-core/src/http.rs`, `desktop/crates/romm-download-core/src/transfer.rs`, `desktop/crates/romm-download-core/src/lib.rs`, `desktop/crates/romm-download-core/tests/transfer_protocol.rs`.
- **Verification:** 7 focused tests, `cargo fmt --check`, and Clippy with warnings denied passed.
- **Committed in:** `1529b5a81`.

---

**Total deviations:** 1 auto-fixed (Rule 1).
**Impact on plan:** Required to satisfy the specified warnings-denied quality gate, without changing protocol behavior or scope.

## Issues Encountered

- The host lacks Cargo. All Rust test, formatter, and Clippy checks ran in the official disposable `rust:1.90` Docker container. The image required installing the Rustfmt and Clippy components within that disposable container.
- Clippy initially rejected unit error types on the new traits. Replaced them with bounded explicit error marker types and re-ran every required gate.

## Known Stubs

None. The plan intentionally exposes a transport trait rather than a live adapter, so tests require neither a server nor a NAS.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Later desktop plans can use the opaque queued manifest and root handle, strict transfer outcomes, and bounded scheduler permits without accepting raw manifest JSON or arbitrary local paths.

## Self-Check: PASSED

- All seven plan-owned source and test artifacts exist.
- TDD RED and GREEN commits, `431b75437` and `1529b5a81`, exist in Git history.
- The focused test suite passed 7 tests, followed by `cargo fmt --check` and Clippy with warnings denied in the official Rust container.

---

_Phase: 16-cross-platform-desktop-client_
_Completed: 2026-09-17_
