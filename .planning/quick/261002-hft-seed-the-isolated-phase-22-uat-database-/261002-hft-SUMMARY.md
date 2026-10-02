---
status: complete
quick_task: 261002-hft
subsystem: testing
tags: [uat, docker, mariadb, storage-mapping, pc-automation]
requires:
  - phase: 22
    provides: isolated PC automation UAT fixtures and source-immutability checks
provides:
  - Idempotent disposable-database seeding for the Phase 22 `win` fixture root
  - Read-only root and Windows mapping verification before browser quick scan
affects: [phase-22-uat, pc-automation]
tech-stack:
  added: []
  patterns: [disposable UAT seeder with fail-closed storage mapping validation]
key-files:
  created:
    - backend/tools/seed_phase22_uat_database.py
    - backend/tests/tools/test_seed_phase22_uat_database.py
  modified: []
key-decisions:
  - "Seed only the disposable root `/romm/library/roms` and exact `win` mapping."
  - "Treat existing incompatible mappings as errors, never repair them destructively."
requirements-completed: []
metrics:
  tests_passed: 10
  completed: 2026-10-02
---

# Quick Task 261002-hft: Seed the isolated Phase 22 UAT database

**An idempotent read-only UAT seeder creates or validates the disposable Windows fixture root and its active `win` mapping without triggering a scan.**

## Accomplishments

- Added `seed_phase22_uat_database.py`, which waits for the disposable database,
  requires `e2e_admin`, validates `/romm/library/roms` as active and
  `external_read_only`, discovers or registers `win`, and creates only the
  exact `win` mapping when none exists.
- The seeder emits non-secret root, platform, and mapping identifiers as JSON.
- Added seven database-free tests covering creation, repeatability, missing
  admin, missing fixture platform, unsafe or unreachable roots, and
  incompatible active mappings.
- Ran the seeder twice in the active uniquely named isolated Compose project.
  Both invocations reported root id 1, platform id 1, mapping id 1, and the
  exact root and relative path contract. The mounted `win` directory was
  readable and non-writable.

## Verification

- `cd backend && uv run pytest tests/tools/test_seed_phase22_uat_database.py tests/integration/test_scan_source_immutability.py -q`
  passed with 10 tests. Pytest emitted one non-fatal local cache permission
  warning.
- The pre-commit hook formatted and checked both created files successfully.
- The isolated fixture digest remained
  `ceacf5a123f312a7ae7ec10ff8d81b395906815092ce005cd4ba1dac6021051b`
  before and after the quick scan.

## Task Commit

1. **Task 1: Add an idempotent isolated Phase 22 database seeder and focused tests** - `2fcbf7262` (`fix(uat): seed isolated Phase 22 database`)

## Decisions Made

- Use the existing storage handler's root registration and health checks,
  rather than adding UAT-specific filesystem write probes.
- A correct existing mapping is reused. An incompatible one is refused so the
  seeder cannot deactivate or replace prior data.

## Deviations from Plan

None. The code and tests were implemented as planned. The UAT record update
is handled separately by the coordinating workflow.

## Known Limitation

The plan's combined verification command includes
`tests/tools/test_seed_phase9_database_platforms.py`. Its existing arcade-only
mock provides two platform lookups even though the old Phase 9 seeder also
looks up `win`, causing an independent `StopIteration`. The Phase 22 seeder
tests and source-immutability tests pass; this unrelated Phase 9 test was not
changed.

## Next Phase Readiness

The isolated stack is ready to seed before a browser Quick Scan. Cleanup stays
limited to its unique Compose project and explicitly created temporary UAT
directory.

## Self-Check: PASSED

- `backend/tools/seed_phase22_uat_database.py` exists.
- `backend/tests/tools/test_seed_phase22_uat_database.py` exists.
- Commit `2fcbf7262` exists.
