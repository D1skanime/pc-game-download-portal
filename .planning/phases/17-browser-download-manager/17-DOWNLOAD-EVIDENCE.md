# Phase 17 Isolated Download Evidence

Status: BLOCKED, no browser-capable isolated fixture was available in the execution environment.

The evidence below intentionally distinguishes deterministic code/test observations from user-visible browser transfers. No successful real download is claimed.

## Commands attempted

| Command or probe                                                                                                                                                                                        | Result                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `cd backend && uv run pytest tests/endpoints/test_download_manifests.py tests/endpoints/test_download_transfers.py -q`                                                                                  | BLOCKED before tests, MariaDB at `127.0.0.1:3306` unavailable |
| `cd frontend && npm run test -- sourceMutationControls useBrowserDownloadQueue downloadManifestPath`                                                                                                    | PASS, 4 files and 24 tests                                    |
| `cd frontend && npm run test -- DownloadAccessibility DownloadManager DownloadSelectionDialog DownloadTransferHistory PcComponents useBrowserDownloadQueue downloadManifestPath sourceMutationControls` | PASS, 8 files and 42 tests                                    |
| `cd frontend && npm run typecheck`                                                                                                                                                                      | PASS                                                          |
| `python3 frontend/src/locales/check_i18n_locales.py`                                                                                                                                                    | PASS                                                          |
| `python3 frontend/src/locales/check_i18n_sorted.py`                                                                                                                                                     | PASS                                                          |
| `trunk check --ci` on changed files                                                                                                                                                                     | PASS                                                          |
| `command -v firefox`, Chrome/Chromium probes, Edge probes                                                                                                                                               | BLOCKED, no binaries installed                                |

## Required isolated cases

| Case                      | Status            | Source before/after | Destination/result | Notes                                |
| ------------------------- | ----------------- | ------------------- | ------------------ | ------------------------------------ |
| Greater-than-4-GiB ISO    | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |
| Multi-file game           | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |
| Update-only               | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |
| DLC-only                  | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |
| Optional-member exclusion | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |
| Required-set rejection    | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |
| Enhanced resume           | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |
| Source-change response    | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |
| Expired/revoked response  | BLOCKED / NOT RUN | NOT CAPTURED        | NOT CAPTURED       | Browser and live MariaDB unavailable |

For every blocked case, the required source tree, file size, SHA-256, and access-time before/after comparison is **NOT CAPTURED**. It would be misleading to manufacture a before/after result without running the isolated browser flow.

## Automated safety evidence

The local frontend tests cover strict resume response classification, destination traversal rejection, required/optional selection presentation, truthful handoff/status wording, and source-mutation disclosure guards. Backend endpoint tests were extended for lifecycle masking, owner masking, forbidden ZIP/desktop/path payloads, and u64 range values, but their database-backed execution remains blocked by unavailable MariaDB.

## Explicit boundary

No real NAS, Team4s, deployment, restart, external source root, or desktop installer was accessed, modified, or treated as evidence. This artifact is a blocked evidence record, not a browser sign-off.
