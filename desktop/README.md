# RomM Desktop

`romm-desktop` is the Windows and Linux desktop shell for the isolated
`romm-download-core` crate. The shell exposes typed, redacted IPC commands and
delegates manifest validation, local path safety, transfer, hashing, and job
recovery to the core.

## Pairing and token storage

The shell pairs with an existing RomM server through `POST /api/auth/device/init`
and polls `/api/auth/device/token`. It requests only `roms.read`. The returned
`rmm_` bearer token is stored in the operating system credential store through
the native adapter. It is never written to job data, command results, events,
logs, URLs, source code, or the webview.

An expired or unauthorized pairing reports `AUTH_REQUIRED`. Start pairing again
to repair access. Pairing uses the configured server origin and the existing
verification path plus user code. It does not reuse browser cookies or passwords.

## Platform prerequisites

- Windows builds require the current Visual Studio C++ build tools and WebView2.
  The release bundle target is NSIS.
- Linux and Bazzite builds require WebKitGTK, GTK 3, and the platform packaging
  tools for the selected `deb`, `rpm`, or AppImage target. Bazzite users should
  install the development dependencies in an approved toolbox or build image.
- Rust 1.90, Rustfmt, and Clippy are used for the local checks below.

## Local-only verification

Run from `desktop/`:

```bash
cargo test --manifest-path src-tauri/Cargo.toml --test command_boundary
cargo test -p romm-download-core
cargo fmt --check
cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings
```

## Isolated large-file UAT

The real-engine loopback gate requires a writable volume with at least 30 GiB
free. It creates a uniquely named temporary root, serves one sparse 30 GiB
original file over `127.0.0.1`, interrupts after a recorded nonzero offset,
resumes with the persisted job and part, verifies SHA-256, finalizes atomically,
and removes the entire temporary root:

```bash
cargo test -p romm-download-core --test sparse_30gib_uat -- --ignored --exact sparse_30gib_resume_finalize_uat
```

Run only on an isolated local volume. A failed capacity or platform preflight is
`BLOCKED`, never a passing result. The gate has no code path to Team4s, NAS
storage, a deployed RomM, or a source library.

These checks use mocks and temporary local destination roots. This phase does
not contact a real NAS or Team4s, restart services, change source libraries, or
perform a live download.
