# Phase 17 Browser Download Manager Matrix

Status: BLOCKED for manual browser observation in this checkout.

This matrix records only what was observed from the Linux execution environment. No browser binary was installed, no browser profile was opened, and no result below is a claim about a real user download.

## Environment probes

| Browser    | Probe                                                                     | Result                                                      |
| ---------- | ------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Firefox    | `command -v firefox` and `firefox --version`                              | BLOCKED, binary unavailable                                 |
| Chrome     | `command -v google-chrome google-chrome-stable chromium chromium-browser` | BLOCKED, binaries unavailable                               |
| Edge       | `command -v microsoft-edge microsoft-edge-stable`                         | BLOCKED, binaries unavailable                               |
| Playwright | Frontend package and `frontend/playwright/` inspected                     | NOT RUN, installed browser executables were not provisioned |
| MariaDB    | Focused pytest against configured `127.0.0.1:3306`                        | BLOCKED, connection refused/timed out before database setup |

## Required capability matrix

| Case                                          | Firefox | Chrome  | Edge    | Evidence status                                                      |
| --------------------------------------------- | ------- | ------- | ------- | -------------------------------------------------------------------- |
| Standard multi-file game handoff              | BLOCKED | BLOCKED | BLOCKED | No browser binary or live app/database                               |
| Enhanced File System Access detection         | BLOCKED | BLOCKED | BLOCKED | No browser binary                                                    |
| Directory-picker denial and Standard fallback | BLOCKED | BLOCKED | BLOCKED | No browser binary                                                    |
| Keyboard, touch, and gamepad controls         | BLOCKED | BLOCKED | BLOCKED | No browser binary; local Vitest fixtures cover native controls only  |
| Dark and light theme rendering                | BLOCKED | BLOCKED | BLOCKED | No browser binary; local Vitest fixtures cover theme attributes only |
| Greater-than-4-GiB ISO download               | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |
| Multi-file game and split ordering            | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |
| Update-only selection                         | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |
| DLC-only selection                            | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |
| Optional-member exclusion                     | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |
| Required-set rejection                        | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |
| Enhanced resume with strict 206               | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |
| Source-change handling (412)                  | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |
| Expired/revoked handling (409/410)            | BLOCKED | BLOCKED | BLOCKED | No browser binary, live app, or MariaDB                              |

## Safe automated observations

- `cd frontend && npm run test -- DownloadAccessibility DownloadManager DownloadSelectionDialog DownloadTransferHistory PcComponents useBrowserDownloadQueue downloadManifestPath sourceMutationControls`: **PASS**, 8 files and 42 tests.
- `cd frontend && npm run typecheck`: **PASS**.
- Locale parity and sorting checks: **PASS**.
- File-scoped Trunk checks and Python AST parsing: **PASS**.
- `cd backend && uv run pytest tests/endpoints/test_download_manifests.py tests/endpoints/test_download_transfers.py -q`: **BLOCKED** during fixture setup because MariaDB was unavailable.

These automated observations do not substitute for the browser matrix above.

## Infrastructure boundary

No real NAS mount, Team4s system, external source root, deployment, service restart, or desktop installer was accessed or changed.
