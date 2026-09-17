---
phase: 16-cross-platform-desktop-client
plan: 05
subsystem: desktop-shell
tags: [rust, tauri, device-auth, keyring, security]
requires:
  - phase: 16-cross-platform-desktop-client
    provides: "Validated manifests, opaque destination roots, and integrity-gated core transfer"
provides:
  - "Least-privilege Tauri 2 command boundary for Windows and Linux/Bazzite"
  - "Existing device authorization adapter with native OS credential storage"
affects: [16-06, desktop-client]
tech-stack:
  added: [tauri, tauri-plugin-dialog, keyring, reqwest]
  patterns:
    - "Only the native folder chooser observes a selected path before registering a core-issued opaque root handle"
    - "Device tokens remain in the OS credential store and all shell DTOs are redacted"
key-files:
  created:
    - desktop/src-tauri/src/commands.rs
    - desktop/src-tauri/src/auth.rs
    - desktop/src-tauri/src/main.rs
    - desktop/src-tauri/capabilities/default.json
    - desktop/src-tauri/tauri.conf.json
    - desktop/src-tauri/tests/command_boundary.rs
    - desktop/README.md
  modified:
    - desktop/DEPENDENCY-AUDIT.md
    - desktop/src-tauri/Cargo.toml
key-decisions:
  - "Tauri IPC carries only typed origin, manifest ID, opaque root handle, closed conflict action, and redacted state values."
  - "Device authorization joins only existing origin-bound routes, requests roms.read, and stores rmm_ tokens solely in the native keyring."
duration: 82min
completed: 2026-09-17
---

# Phase 16 Plan 05: Least-privilege desktop shell summary

**A Tauri 2 shell now exposes only typed, redacted desktop commands, delegates manifest queueing to the Rust core, and pairs through the existing scoped device authorization flow.**

## Accomplishments

- Added Windows and Linux/Bazzite Tauri bundle configuration, constrained capabilities, native-only folder selection, and an isolated `desktop/ui` input.
- Prevented webview callers from passing destination paths, bearer tokens, arbitrary manifest JSON, or shell/filesystem operations.
- Added origin-bound device init and polling with `roms.read`, interval and expiry handling, `AUTH_REQUIRED` repair state, OS credential storage, and no token-bearing DTOs.

## Task Commits

1. **Tauri command boundary, RED** - `531799d94` (test)
2. **Thin Tauri shell, GREEN** - `07b31c8c1` (feat)
3. **Device authorization adapter, RED** - `aa67b64f6` (test)
4. **Native device authorization, GREEN** - `81150a95f` (feat)
5. **Core queue delegation correction** - `8e9dda8e0` (fix)

## Verification

- `cargo test --manifest-path src-tauri/Cargo.toml --test command_boundary` passed: 6 tests.
- `cargo test -p romm-download-core` passed.
- `cargo fmt --check` passed.
- `cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings` passed.
- All Rust checks ran in the official `rust:1.90` Docker image with `CARGO_TARGET_DIR=/tmp/romm-cargo-target`; no Cargo target or lockfile output was written to the workspace.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 3 - Blocking build configuration] Added isolated UI entry and required Tauri icon asset**
   - **Found during:** Task 1 verification.
   - **Issue:** Tauri context generation requires the configured `desktop/ui` input and a default app icon.
   - **Fix:** Added the local UI entry point and a generated local icon used only by the desktop shell.
   - **Files modified:** `desktop/ui/index.html`, `desktop/src-tauri/icons/icon.png`.

2. **[Rule 1 - Dependency compatibility] Updated the audited stable Tauri 2 dependency chain after explicit approval**
   - **Found during:** Task 1 verification.
   - **Issue:** the initial Tauri pins resolved incompatible runtime crates.
   - **Fix:** Updated to `tauri` 2.11.5, `tauri-plugin-dialog` 2.7.3, and compatible `tauri-build` 2.6.3 after explicit human verification.
   - **Files modified:** `desktop/DEPENDENCY-AUDIT.md`, `desktop/src-tauri/Cargo.toml`.

## Known Stubs

None.

## Self-Check: PASSED

- All declared shell, auth, capability, configuration, test, audit, and documentation artifacts exist.
- All five task commits are present in Git history.
