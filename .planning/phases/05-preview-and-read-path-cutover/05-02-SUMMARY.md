---
phase: 05-preview-and-read-path-cutover
plan: 02
subsystem: backend-tests
tags: [pytest, storage-mapping, preview, watcher, downloads]
requires: [05-01]
provides: [wave-1-red-test-foundation]
affects: [05-03, 05-04, 05-05, 05-06, 05-07, 05-08]
tech-stack:
  added: []
  patterns: [source-contract RED tests, byte-exact source manifests]
key-files:
  created:
    - backend/tests/integration/test_mapped_scan.py
    - backend/tests/integration/test_scan_source_immutability.py
    - backend/tests/handler/storage/test_preview.py
    - backend/tests/endpoints/storage/test_mapping_preview.py
    - backend/tests/tasks/test_mapping_revision_jobs.py
    - backend/tests/test_watcher.py
  modified:
    - backend/tests/endpoints/roms/test_files.py
    - backend/tests/endpoints/roms/test_rom.py
key-decisions:
  - RED tests inspect explicit future contract symbols so missing behavior fails without import or collection failures.
requirements-completed: [SCAN-01, SCAN-02, SCAN-03, SCAN-04, SCAN-05, SCAN-06]
duration: 18 min
completed: 2026-08-11
---

# Phase 05 Plan 02: Wave 1 RED Test Foundation Summary

Executable RED contracts now cover mapped scan identity, immutable source manifests, bounded previews, queued mapping revisions, watcher coalescing, and delivery preflight.

## Performance

- Duration: 18 min
- Tasks: 3
- Files changed: 8

## Accomplishments

- Added common trigger and revision-state contracts for manual, scheduled, and watcher scans.
- Added source manifests comparing names, entry types, byte sizes, and SHA-256 hashes.
- Added preview, stale job, watcher flood, multi-part preflight, revision handoff, and redaction RED coverage.

## Task Commits

1. Task 1: `4571f7e01` test(05-02): add mapped scan RED contracts
2. Task 2: `c30b28d99` test(05-02): add preview and revision RED contracts
3. Task 3: `2e6415882` test(05-02): add watcher and delivery RED contracts

## Verification

- Task 1 collected 5 tests and exited 1 on the missing `MappedScanCommand` contract.
- Task 2 collected successfully and exited 1 on the missing dual-budget preview module.
- Task 3 files pass repository formatting hooks. The host lacks Connector/C and PostgreSQL headers, so an isolated uv environment was installed without native database drivers. Collection was validated separately; targeted RED execution exposed the missing watcher contract. Full endpoint execution remains dependent on the repository test database environment.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bootstrapped isolated pytest environment**

- The remote host had no `uv` and the checked-in virtual environment was unreadable.
- Installed `uv` under the remote user and created `/tmp/romm-05-02-venv`.
- Native database adapters could not build because system headers require administrator access, so collection and contract-only RED runs used the isolated environment.

## Known Stubs

None. Assertions intentionally name production contracts assigned to downstream Phase 5 plans.

## Self-Check: PASSED

All eight created or modified test files exist, all three task commits exist, and every new test module is represented in the Wave 1 validation map.
