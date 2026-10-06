---
phase: 24-v2-quality-stabilization-and-unified-library-operations
plan: 14
subsystem: backend-scan
tags: [scan, metadata-only, socketio, metadata, artwork]
dependency_graph:
  requires: [mapped-scan-socket, provider-metadata-priority]
  provides: [metadata-only-scan-isolation]
  affects: [scan-socket, scan-handler, resource-path-persistence]
tech_stack:
  added: []
  patterns: [optional-bool-propagation, source-mocked-boundary-tests]
key_files:
  created: []
  modified:
    - backend/endpoints/sockets/scan.py
    - backend/handler/scan_handler.py
    - backend/tests/endpoints/sockets/test_scan.py
    - backend/tests/handler/test_scan_handler.py
decisions:
  - "Keep metadata_only false by default so existing scan behavior is unchanged."
  - "Preserve existing artwork URLs and persisted resource paths while allowing provider text metadata to refresh."
metrics:
  duration: "about 35 minutes"
  completed_date: "2026-10-06"
---

# Phase 24 Plan 14: Metadata-only scan isolation summary

Metadata-only scans now travel through the existing mapped socket scan lifecycle while refreshing provider text metadata without changing artwork, resource paths, owned media, or PC/DLC associations.

## Completed Task

Task 2, Isolate backend metadata-only behavior.

- Added optional `metadata_only` propagation from the scan socket through mapping, platform, ROM identification, and `scan_rom`.
- Preserved artwork URLs and persisted resource paths during metadata-only scans, including complete scans.
- Skipped SGDB artwork lookup, resource downloads, provider-media persistence, Steam owned-media reconciliation, PC/DLC component synchronization and linking, and PC automation for metadata-only scans.
- Kept the normal path unchanged when `metadata_only` is false.
- Added source-mocked tests for socket forwarding, resource-path preservation, metadata text application, SGDB suppression, Steam media suppression, and component-link suppression.

## Verification

- `backend/endpoints/sockets/scan.py`, `backend/handler/scan_handler.py`, and both touched test files compile successfully with Python `compile(...)`.
- Source-mocked handler tests: 2 passed.
- Source-mocked socket tests: 2 passed.
- Normal MariaDB-backed pytest was not run because MariaDB is unavailable on the verified Linux VM, as requested.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking environment] Used the repository's existing `.venv/bin/pytest` because `uv` is not installed on the Linux VM.**

- **Impact:** No production behavior change.
- **Verification:** Isolated source-mocked tests passed.

**2. [Rule 3 - Test isolation] Added explicit mocks for existing database-backed lifecycle lookups in the new source-mocked tests.**

- **Impact:** Keeps the requested tests independent of MariaDB.
- **Files modified:** `backend/tests/handler/test_scan_handler.py`, `backend/tests/endpoints/sockets/test_scan.py`.

None - no architectural changes were needed.

## Known Stubs

None.

## Threat Flags

None. The change adds no endpoint, authentication, filesystem authority, or schema surface.

## Self-Check: PASSED

- Summary file exists.
- Task commit `11a5e632b` exists.
- The unrelated pre-existing mapping diff in `backend/endpoints/sockets/scan.py` remains outside the task commit.
