---
phase: 05-preview-and-read-path-cutover
plan: 03
subsystem: backend-storage
tags: [storage-mapping, scan, filesystem, capabilities]
requires:
  - phase: 05-01
    provides: Approved Phase 3 integration bindings
  - phase: 05-02
    provides: Mapped scan and immutable-source RED contracts
provides:
  - Mapping-bound read context with immutable revision validation
  - Stable redacted mapped-read domain errors
  - Immutable identity-bearing scan and queue commands
  - Operation-bound mapped scan, read, and hash entry points
affects: [05-04, 05-05, 05-06, 05-07, 05-08]
tech-stack:
  added: []
  patterns: [validate-open-revalidate, mapping-id-plus-revision payloads]
key-files:
  created:
    - backend/exceptions/storage_read.py
    - backend/handler/storage/read_context.py
    - backend/handler/scan_command.py
    - backend/tasks/mapping_revision.py
  modified:
    - backend/handler/database/storage_handler.py
    - backend/handler/scan_handler.py
    - backend/handler/filesystem/roms_handler.py
key-decisions:
  - "Mapped reads reconstruct operation-specific capabilities from mapping ID and integer version at execution time."
  - "Scan options are bounded immutable key-value pairs and reject path-bearing values."
requirements-completed: [SCAN-01, SCAN-02, SCAN-06]
duration: 34min
completed: 2026-08-11
---

# Phase 05 Plan 03: Mapping-bound Read and Scan Boundary Summary

Immutable mapping identity now gates scan, read, and hash capabilities with revalidation and stable redacted failures.

## Performance

- Duration: 34 min
- Started: 2026-08-11T00:00:00Z
- Completed: 2026-08-11
- Tasks: 2
- Files modified: 10

## Accomplishments

- Added a mapping repository read and a mapping-bound context that validates active state, exact version, live health, and safe resolution before issuing an operation capability.
- Added stable stale, unreachable, missing-content, and denied-access errors containing only bounded mapping identity and safe state.
- Added frozen manual, scheduled, and watcher scan commands with no reusable source paths.
- Added mapped scan orchestration plus mapped scan, read, and hash entry points for filesystem consumers.
- Added queue-safe mapping revision identity reconstruction.

## Task Commits

1. Task 1 RED: `610b7bc5b`
2. Task 1 GREEN: `60c76df2c`
3. Task 2 RED: `b5fd6a200`
4. Task 2 GREEN: `53c83a4bd`
5. Rule 3 queue contract: `a7a8d32a2`

## Verification

- Docker contract suite without database fixtures: 9 passed.
- Python compilation passed for all created and modified backend modules.
- `git diff --check` passed.
- Full configured Docker pytest reached MariaDB but was blocked by pre-existing test database migration drift: Alembic 0109 attempted to add the already-present `platform_storage_mappings.active` column.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added public read-only mapping lookup**

- Found during Task 1.
- The approved contract required mapping-ID reads through DBStorageHandler.
- Added `get_mapping` with eager storage-root loading.
- Commit: `60c76df2c`.

**2. [Rule 3 - Blocking] Added queue-safe mapping revision job identity**

- Found during overall verification.
- The assigned RED queue suite required the production contract module.
- Added a frozen mapping ID and expected revision payload that reconstructs a read context.
- Commit: `a7a8d32a2`.

**Total deviations:** 2 auto-fixed.

## Issues Encountered

- Host `uv` could not use the checkout virtualenv because it is permission-restricted.
- Docker verification connected to MariaDB through the database container network, but the existing test schema is ahead of its Alembic version marker and fails on a duplicate `active` column. No unrelated database state was modified.

## User Setup Required

None.

## Known Stubs

None.

## Threat Flags

| Flag                         | File                                    | Description                                                                       |
| ---------------------------- | --------------------------------------- | --------------------------------------------------------------------------------- |
| threat_flag: filesystem-read | backend/handler/storage/read_context.py | New trusted mapping-to-capability boundary with stale and containment validation. |

## Next Phase Readiness

- Later preview, streaming, download, watcher, and worker plans can consume MappingReadContext and MappingRevisionJob.
- The shared test database needs its existing schema/version drift repaired before fixture-backed suites can run.

## Self-Check: PASSED

- All key files exist.
- All five task and deviation commits exist.
- The Docker source-contract suite reports 9 passing tests.
- All modified Python modules compile.
