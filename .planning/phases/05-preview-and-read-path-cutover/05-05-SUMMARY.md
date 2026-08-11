---
phase: 05-preview-and-read-path-cutover
plan: 05
subsystem: scan-triggers
tags: [mapping, rq, watcher, debounce]
requires:
  - phase: 05-03
    provides: Immutable mapped scan command and executor
provides:
  - Mapping revision-bearing manual and scheduled scan entry points
  - Canonical per-mapping watcher normalization and bounded coalescing
affects: [05-06, 05-07, 05-08]
tech-stack:
  added: []
  patterns: [mapping-id-plus-revision queues, per-mapping debounce]
key-files:
  created: []
  modified:
    - backend/endpoints/sockets/scan.py
    - backend/tasks/scheduled/scan_library.py
    - backend/watcher.py
key-decisions:
  - "All triggers freeze the active mapping ID and integer revision before enqueue."
  - "Watcher hints use a fixed 30-second delay and permit no more than one queued follow-up per mapping."
requirements-completed: [SCAN-01, SCAN-02, SCAN-03, SCAN-06]
duration: 22min
completed: 2026-08-11
---

# Phase 5 Plan 5: Mapped Scan Trigger Convergence Summary

Manual, scheduled, and watcher scans now enqueue immutable mapping identities through one executor, with safe per-mapping watcher containment and bounded follow-up work.

## Performance

- Duration: 22 min
- Completed: 2026-08-11
- Tasks: 2
- Files modified: 3

## Accomplishments

- Added one common mapped scan entry point that validates mapping identity before scan execution.
- Migrated manual and scheduled triggers from platform IDs and filesystem slugs to frozen mapping IDs and revisions.
- Replaced global library path splitting with canonical mapping-root resolution for watcher events.
- Rejected outside-root and symlink-escaped events by resolving paths before mapping containment checks.
- Debounced watcher hints for 30 seconds per mapping, allowing one queued follow-up while active.
- Marked watcher jobs non-authoritative while leaving manual and scheduled scans authoritative.

## Task Commits

1. Task 1: `c10ee471e` feat(05-05): converge manual and scheduled mapped scans
2. Task 2: `6de06a3ed` feat(05-05): bound watcher scans per mapping

## Verification

- Repository formatting and lint hooks passed for all three modified production files.
- Python compilation passed in the `romm-dev` container.
- The four planned suites collected 83 tests successfully.
- Runtime execution is blocked before the first test by the existing test environment: `backend/pytest.ini` forces MariaDB at `127.0.0.1:3306`, but the application container has no database listener at that address. The exact failure is `mariadb.OperationalError: Can't connect to server on '127.0.0.1' (115)`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added batch orchestration for library scans**

- Found during Task 1.
- A library scan spans multiple platform mappings, while the landed common executor accepts one immutable mapping command.
- Added a bounded batch that executes each frozen command through the same executor and combines scan statistics.
- Files modified: `backend/endpoints/sockets/scan.py`.
- Commit: `c10ee471e`.

## Issues Encountered

- The host checkout virtual environment is permission-restricted, so compilation and test collection ran inside the existing development container.
- Runtime pytest is blocked by the container-local database address described above. No database or unrelated configuration was modified.

## Known Stubs

None.

## Threat Flags

| Flag                          | File               | Description                                                                                        |
| ----------------------------- | ------------------ | -------------------------------------------------------------------------------------------------- |
| threat_flag: filesystem-event | backend/watcher.py | Untrusted watcher paths cross into mapped scan scheduling only after canonical containment checks. |

## Next Phase Readiness

- Read-path consumers can rely on mapping ID and expected revision being present for every scan trigger.
- Production-like NAS watcher fidelity remains a Phase 9 manual gate; scheduled scans remain authoritative reconciliation.

## Self-Check: PASSED

- All three modified production files exist.
- Task commits `c10ee471e` and `6de06a3ed` exist.
- Both commits passed repository hooks.
- The planned test modules collect successfully and the runtime environment blocker is recorded exactly.
