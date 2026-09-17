# Desktop dependency audit

Direct dependencies are audited before they are added to the workspace. The
review uses the official crates.io sparse index and the RustSec advisory
database on 2026-09-17. No package below is marked `[SUS]` or `[SLOP]`.

| Crate                   | Exact version | Official source / owner                         | License           | Advisory result            | Direct purpose                                                                      |
| ----------------------- | ------------- | ----------------------------------------------- | ----------------- | -------------------------- | ----------------------------------------------------------------------------------- |
| `serde`                 | `1.0.229`     | crates.io, `serde-rs/serde`                     | MIT OR Apache-2.0 | No RustSec advisory listed | Closed manifest wire-schema deserialization and validated model serialization.      |
| `serde_json`            | `1.0.151`     | crates.io, `serde-rs/json`                      | MIT OR Apache-2.0 | No RustSec advisory listed | Parse untrusted manifest JSON at the single validation boundary.                    |
| `uuid`                  | `1.26.1`      | crates.io, `uuid-rs/uuid`                       | Apache-2.0 OR MIT | No RustSec advisory listed | Parse and type opaque manifest and member identities.                               |
| `unicode-normalization` | `0.1.25`      | crates.io, `unicode-rs/unicode-normalization`   | MIT OR Apache-2.0 | No RustSec advisory listed | Detect portable NFC and NFD destination collisions before persistence.              |
| `unicode-casefold`      | `0.2.0`       | crates.io, `lfairy/unicode-casefold`            | MIT OR Apache-2.0 | No RustSec advisory listed | Detect Unicode case-folded destination collisions before persistence.               |
| `sha2`                  | `0.10.9`      | crates.io, `RustCrypto/hashes`                  | MIT OR Apache-2.0 | No RustSec advisory listed | Verify completed local files against manifest SHA-256 before recovery accepts them. |
| `tauri`                 | `2.11.5`      | crates.io, `tauri-apps/tauri`                   | MIT OR Apache-2.0 | No RustSec advisory listed | Typed native shell and constrained webview IPC boundary.                            |
| `tauri-build`           | `2.6.3`       | crates.io, `tauri-apps/tauri`                   | MIT OR Apache-2.0 | No RustSec advisory listed | Generates the checked Tauri configuration at build time.                            |
| `tauri-plugin-dialog`   | `2.7.3`       | crates.io, `tauri-apps/plugins-workspace`       | MIT OR Apache-2.0 | No RustSec advisory listed | Native-only destination folder chooser.                                             |
| `keyring`               | `4.2.0`       | crates.io, `open-source-cooperative/keyring-rs` | MIT OR Apache-2.0 | No RustSec advisory listed | OS credential-store access for the device bearer token.                             |
| `reqwest`               | `0.12.24`     | crates.io, `seanmonstar/reqwest`                | MIT OR Apache-2.0 | No RustSec advisory listed | Origin-bound native device authorization HTTP adapter.                              |

`cargo audit` is not available in the host environment. The focused RustSec
advisory database review above is the pre-install advisory gate; the workspace
will run `cargo audit` when the project toolchain adds that approved command.
