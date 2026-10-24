# ZockArchive Desktop

`romm-desktop` is the Windows and Linux desktop shell for the isolated
`romm-download-core` crate. The shell exposes typed, redacted IPC commands and
delegates manifest validation, local path safety, transfer, hashing, and job
recovery to the core.

## Display and compatibility identities

The window, HTML title and shell display ZockArchive Desktop. The technical
Tauri `productName` remains `RomM Desktop`: Tauri 2.11.5's bundled NSIS template
uses it in the uninstall registry key, saved installation location and default
installation directory. Changing it requires a separately verified installer
migration. Installer names and OS shortcuts can therefore retain RomM Desktop.
See the [upstream installer template](https://github.com/tauri-apps/tauri/blob/tauri-v2.11.5/crates/tauri-bundler/src/bundle/windows/nsis/installer.nsi).

The bundle ID `org.romm.desktop`, credential service and `device-token` account,
`romm-desktop` pairing client, typed IPC/capabilities, Rust crate names and
`.romm-jobs.json` store remain compatible. Transfer part and replacement suffixes
also remain stable. Display metadata never migrates credentials or local jobs.
Native app-data path and installed upgrade compatibility require platform
verification; the UI build alone does not prove either.

Packaging icons must be supplied by the operator. No ZockArchive artwork is
included or generated; the existing empty bundle icon list is retained.

## Pairing and token storage

The shell pairs with an existing ZockArchive server through `POST /api/auth/device/init`
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
storage, a deployed ZockArchive, or a source library.

These checks use mocks and temporary local destination roots. This phase does
not contact a real NAS or Team4s, restart services, change source libraries, or
perform a live download.
