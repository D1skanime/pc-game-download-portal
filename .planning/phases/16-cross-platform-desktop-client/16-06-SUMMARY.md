---
phase: 16-cross-platform-desktop-client
plan: 06
subsystem: desktop-ui-and-uat
tags:
  [tauri, typescript, vite, vitest, rust, streaming, resumable-transfer, uat]
requires:
  - phase: 16-cross-platform-desktop-client
    provides: "Typed Tauri command boundary, opaque destination handles, strict transfer and finalization core"
provides:
  - "Isolated state-driven desktop UI with explicit conflict recovery"
  - "Chunked HTTP transfer API with incremental sinks and durable progress callbacks"
  - "Ignored executable local-loopback 30 GiB resume/finalization UAT and platform evidence template"
affects: [desktop-client, phase-17]
tech-stack:
  added: [vite, typescript, vitest, jsdom]
  patterns:
    - "Standalone desktop UI invokes only typed command names and renders redacted state snapshots"
    - "Streaming transfer reports u64 progress after each successfully written chunk"
    - "Large-file UAT uses a uniquely owned temporary root and loopback-only HTTP server"
key-files:
  created:
    - desktop/ui/package.json
    - desktop/ui/package-lock.json
    - desktop/ui/tsconfig.json
    - desktop/ui/vite.config.ts
    - desktop/ui/src/app.ts
    - desktop/ui/src/main.ts
    - desktop/ui/src/styles.css
    - desktop/ui/src/app.test.ts
    - desktop/crates/romm-download-core/tests/sparse_30gib_uat.rs
    - .planning/phases/16-cross-platform-desktop-client/16-UAT.md
  modified:
    - desktop/DEPENDENCY-AUDIT.md
    - desktop/README.md
    - desktop/crates/romm-download-core/src/http.rs
    - desktop/crates/romm-download-core/src/transfer.rs
    - desktop/crates/romm-download-core/src/lib.rs
key-decisions:
  - "Use a standalone Vite/Vitest desktop UI outside frontend/ so Phase 17 browser handoff remains separate."
  - "Extend the core transport with bounded streaming chunks and durable progress callbacks rather than weakening the real 30 GiB UAT."
  - "Missing authorized Windows, Linux, and Bazzite runners leave Task 3 and Phase 16 blocked."
requirements-completed: []
duration: 45min
completed: 2026-09-17
---

# Phase 16 Plan 06: Desktop UI and real large-file UAT summary

**An isolated state-driven desktop shell and streaming resumable core are ready, with real three-platform evidence explicitly deferred until authorized runners exist.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-17T09:01:00Z
- **Completed:** 2026-09-17
- **Tasks:** 2/3 complete, Task 3 blocked
- **Files modified:** 15

## Accomplishments

- Added a standalone desktop UI with server configuration, pairing status, opaque manifest and destination handles, original-file progress, queue controls, and every bounded recovery state.
- Added UI regression tests proving the three explicit `LOCAL_CONFLICT` actions and absence of tokens, raw paths, Range headers, ZIP, or installation language.
- Added streaming transfer support and an ignored local-loopback UAT that writes a real sparse 30 GiB destination, persists progress, resumes with exact range/snapshot, verifies SHA-256, finalizes, and cleans up.

## Task Commits

1. **Task 1 RED: desktop recovery UI tests** - `d4f4b08cf`
2. **Task 1 GREEN: state-driven desktop UI** - `5f9bdba09`
3. **Task 2 RED: sparse 30 GiB engine UAT gate** - `eccc72b98`
4. **Task 2 GREEN/fix: streamed transfer and UAT transport** - `319a5471d`, `9fff594f2`
5. **Task 2 docs: cross-platform UAT evidence template** - `05d4aecd5`

Task 3 has no commit because required platform evidence is unavailable.

## Verification

- `cd desktop/ui && npm test -- --run` passed, 9 tests.
- `cd desktop/ui && npm run build` passed.
- Official `rust:1.90` Docker with temporary `CARGO_TARGET_DIR` passed the complete core suite serially.
- `cargo fmt --check` passed.
- `cargo clippy -p romm-download-core --all-targets -- -D warnings` passed.
- The ignored 30 GiB test compiled successfully but was not executed because the authorized 30 GiB volume and platform evidence runners are unavailable.

## Deviations from Plan

### Architectural changes

**1. [Rule 4 - Approved architectural change] Added streaming transfer and durable progress API**

- **Found during:** Task 2, real UAT design.
- **Issue:** The existing core only returned complete response bodies as `Vec<u8>`, so it could not exercise a real 30 GiB transfer or restart-safe incremental writes.
- **Fix:** Added `HttpStreamResponse`, `HttpTransport::execute_stream`, `DownloadEngine::transfer_member_stream`, chunk-level `FileSink` writes, lifecycle/origin validation, and progress callbacks used to persist `PersistedJob` records.
- **Files modified:** `desktop/crates/romm-download-core/src/http.rs`, `transfer.rs`, `lib.rs`, `tests/sparse_30gib_uat.rs`.
- **Verification:** Full core suite, formatter, and warnings-denied Clippy passed.
- **Committed in:** `319a5471d`, `9fff594f2`.

### Other deviations

- [Rule 3 - Package install gate] `@types/jsdom@26.0.0` was unavailable. Human verification approved updating to `@types/jsdom@30.0.0`, after which installation and tests succeeded.

## Issues Encountered

- A parallel full-test run exposed an existing temporary-root collision in `transfer_protocol`; serial execution passed all core tests. The test helper uses a process-wide temporary path and is outside this plan's files.
- Windows, standard Linux, and Bazzite bundle/start/core evidence cannot be produced in this VM. `16-UAT.md` records each as `BLOCKED` with the required follow-up checklist.

## Known Stubs

- `16-UAT.md` contains intentional `BLOCKED` evidence placeholders until authorized platform runners and the real isolated 30 GiB volume are available. These placeholders prevent Phase 16 completion and are not presented as passing results.

## Next Phase Readiness

The desktop UI and streaming core are ready for authorized UAT execution. Phase 16 remains incomplete until Windows, standard Linux, Bazzite, and the real 30 GiB UAT each provide recorded bundle/start/core, hash, finalization, and cleanup evidence.

## Self-Check: PASSED

- All created files exist.
- All five Task 1/2 commits are present in Git history.
- Platform evidence is explicitly blocked and no unsupported result is claimed.

---

_Phase: 16-cross-platform-desktop-client_
_Plan: 06_
_Status: blocked pending human verification_
