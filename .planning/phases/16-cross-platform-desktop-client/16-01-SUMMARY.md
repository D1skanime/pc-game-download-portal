---
phase: 16-cross-platform-desktop-client
plan: 01
subsystem: desktop-core
tags: [rust, cargo, serde, manifest-validation, unicode]
requires:
  - phase: 15-direct-resumable-transfer
    provides: "Version-1 manifest response and opaque member delivery routes"
provides:
  - "Isolated Rust workspace with a strict Phase-14 manifest boundary"
  - "Typed opaque manifest/member IDs and u64 immutable transfer contracts"
  - "Portable destination collision rejection before local persistence"
affects: [16-02, 16-03, desktop-client]
tech-stack:
  added: [serde, serde_json, uuid, unicode-normalization, unicode-casefold]
  patterns:
    - "Deserialize untrusted manifests into private raw structs, then expose only validated immutable records"
    - "Reject exact, Unicode case-folded, NFC, and NFD destination collisions before job creation"
key-files:
  created:
    - desktop/Cargo.toml
    - desktop/DEPENDENCY-AUDIT.md
    - desktop/crates/romm-download-core/src/model.rs
    - desktop/crates/romm-download-core/src/manifest.rs
    - desktop/crates/romm-download-core/tests/manifest_contract.rs
  modified: []
key-decisions:
  - "Manifest URLs must byte-match the manifest/member-specific Phase-15 relative route."
  - "Full Unicode case folding complements exact, NFC, and NFD collision checks."
patterns-established:
  - "Public desktop-core errors are bounded categories and never include paths or raw server data."
requirements-completed: [CLNT-01, CLNT-04]
duration: 28min
completed: 2026-09-17
---

# Phase 16 Plan 01: Strict desktop manifest contract summary

**A standalone Rust core now accepts only typed, immutable Phase-14 manifests with exact opaque delivery routes and portable destination-collision protection.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-09-17T07:05:00Z
- **Completed:** 2026-09-17T07:32:53Z
- **Tasks:** 1/1
- **Files modified:** 8

## Accomplishments

- Created the isolated desktop Cargo workspace and romm-download-core library.
- Validated version, UUIDs, u64 sizes, lower-case SHA-256, strong quoted snapshots, and exact relative member routes.
- Rejected unsafe destinations and exact, Unicode case-folded, NFC, and NFD collisions before a manifest can reach job persistence.

## Task Commits

1. **Workspace and strict immutable-manifest boundary, RED** - c50138b11 (test)
2. **Workspace and strict immutable-manifest boundary, GREEN** - 92e506066 (feat)

## Files Created/Modified

- desktop/DEPENDENCY-AUDIT.md - exact dependency provenance, licensing, advisory review, and purpose.
- desktop/crates/romm-download-core/src/model.rs - opaque IDs, closed download states, and immutable validated records.
- desktop/crates/romm-download-core/src/manifest.rs - closed wire schema and validation boundary.
- desktop/crates/romm-download-core/src/error.rs - bounded public validation error categories.
- desktop/crates/romm-download-core/tests/manifest_contract.rs - contract coverage for valid, malformed, colliding, and path-bearing input.

## Decisions Made

- Accept a member URL only when it exactly equals the opaque Phase-15 route derived from the validated manifest and member IDs. This prevents server input from changing origin, authority, path, query, or fragment.
- Use full Unicode case folding in addition to exact, NFC, and NFD comparisons so local jobs remain portable across case-insensitive and normalization-sensitive filesystems.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added full Unicode case folding**

- **Found during:** Task 1, manifest collision validation.
- **Issue:** Rust standard lowercasing does not provide full Unicode case folding, for example ß and SS.
- **Fix:** Audited and added unicode-casefold 0.2.0, then tested the portable collision pair.
- **Files modified:** desktop/DEPENDENCY-AUDIT.md, desktop/crates/romm-download-core/Cargo.toml, desktop/crates/romm-download-core/src/manifest.rs, desktop/crates/romm-download-core/tests/manifest_contract.rs.
- **Verification:** focused contract suite, cargo fmt --check, and Clippy passed.
- **Committed in:** 92e506066.

---

**Total deviations:** 1 auto-fixed (Rule 2).
**Impact on plan:** Necessary to meet the stated full case-fold collision requirement without broadening the core boundary.

## Issues Encountered

- The host has no Rust toolchain or Cargo. Verification ran in an official Rust 1.90 Docker container with the workspace mounted read-only for test and lint output isolation.
- The host does not provide cargo audit; the pre-install RustSec review is recorded in desktop/DEPENDENCY-AUDIT.md.

## Known Stubs

None.

## User Setup Required

None.

## Next Phase Readiness

The next desktop-core plans can consume only ValidatedManifest and ValidatedMember records. No NAS, backend, source-root, Tauri, or Team4s integration was added.

## Self-Check: PASSED

- All eight planned desktop artifacts exist.
- Both TDD commits exist and the focused test, formatter, and Clippy gates pass.

---

_Phase: 16-cross-platform-desktop-client_
_Completed: 2026-09-17_
