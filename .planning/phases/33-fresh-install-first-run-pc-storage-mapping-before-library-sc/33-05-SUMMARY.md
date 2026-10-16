---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 05
subsystem: backend
tags: [storage-mapping, scan, scheduled-scan, mapped-read, authorization]
requires: [33-02]
provides: [mapping-bound-manual-scan, mapping-bound-scheduled-scan, setup-assignment-regression-coverage]
affects: [33-08]
tech-stack:
  added: []
  patterns: [mapping identity and revision are the only scan inputs, scheduled scans execute only healthy persisted mappings]
key-files:
  created: [backend/tests/integration/test_setup_folder_assignments.py]
  modified: [backend/tasks/scheduled/scan_library.py]
key-decisions:
  - Scheduled scans use execute_mapping_scans directly and skip when no healthy persisted mapping commands exist.
requirements-completed: [PGDP-33-01]
duration: 7 min
completed: 2026-10-16T19:33:58Z
---

# Phase 33 Plan 05: Assignment-to-scan and mapped-read authorization Summary

Persisted setup assignments now feed mapping-bound manual and scheduled scans, while existing mapped read/stream authorization and browser-path rejection are covered by focused regression tests.

## Completed Tasks

### Task 1: Prove assignment-to-scan and mapped read/stream authorization

- Added integration coverage that verifies assignment-derived `mapping_id` and `expected_revision` become a `MappedScanCommand`.
- Added browser-path regression coverage for absolute, traversal, and Windows-style paths, proving they do not trigger mapping lookup.
- Changed scheduled scanning to call `execute_mapping_scans` directly and return without execution when no healthy mapping commands exist. This prevents a scheduled run from falling back to the legacy deployment-root scanner.
- Existing `MappingReadContext` and ROM file endpoint tests cover stale mapping revisions, unhealthy roots, mapped streaming, and client path rejection.

## Verification

- `tests/integration/test_setup_folder_assignments.py tests/endpoints/sockets/test_scan.py tests/tasks/test_scan_library.py`: 122 passed, 3 warnings.
- `tests/endpoints/roms/test_files.py`: 17 passed, 7 skipped, 3 warnings.
- `tests/handler/storage/test_read_context.py -k "not symlink_before_issuing_handle"`: 16 passed, 1 deselected, 3 warnings.
- Source line counts: `scan_library.py` 122 lines; new integration test 59 lines. Both remain below the 500-line limit.

## Commits

- `c4361dd36` test(33-05): add assignment scan authorization coverage
- `e2e74e782` fix(33-05): keep scheduled scans mapping-bound

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Scheduled scans could fall back to legacy filesystem scanning when mappings were absent or unhealthy**
- Found during: Task 1
- Issue: `execute_mixed_scans` could invoke the legacy scan path even when `mapping_scan_commands` returned no safe persisted mapping commands.
- Fix: Use `execute_mapping_scans` and return early for an empty command list.
- Files modified: `backend/tasks/scheduled/scan_library.py`
- Verification: scheduled no-mapping test passed and full scan/setup target suite passed.
- Commit: `e2e74e782`

## Deferred Issues

- The broader unrelated `tests/handler/storage/test_read_context.py` run has one pre-existing symlink fixture collision.
- The broader unrelated `tests/integration/test_scan_source_immutability.py` run has one pre-existing DLC fixture expectation mismatch.
- The host `gsd-sdk`, Node, `uv`, and `rg` commands were unavailable; all executable verification ran inside the existing `pgdp-dev` container using a temporary pytest config. No repository compose files or `backend/pgdp_test/` files were changed.

## Self-Check: PASSED

- Summary file created in the canonical Linux checkout.
- Both task commits are present in Git history.
- Shared unrelated working-tree changes remain untouched.
