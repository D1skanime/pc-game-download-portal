---
phase: 22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung
plan: 02
subsystem: automation
tags: [pc, steam, rq-scheduler, mapped-scans, fail-closed]
requires:
  - phase: 22-01
    provides: version-bound PC automation queue persistence
provides:
  - bounded Steam parent and parent-listed DLC automation decisions
  - mapped scheduled discovery with Steam metadata and development interval support
affects: [pc-automation, scheduled-scans, admin-review]
tech-stack:
  added: []
  patterns:
    [exact-one Steam decision, queue-on-uncertainty, RQ interval scheduling]
key-files:
  created:
    - backend/handler/metadata/pc_automation.py
  modified:
    - backend/handler/scan_handler.py
    - backend/tasks/scheduled/scan_library.py
    - backend/tasks/tasks.py
    - backend/config/__init__.py
    - backend/startup.py
key-decisions:
  - "Use the existing mapped scan and guarded database application paths, never raw library traversal."
  - "Allow automatic application only after the existing matcher has reduced Steam parent or parent-listed DLC candidates to one valid result."
  - "Use RQ Scheduler interval scheduling for the development-only ten-second path and retain a five-field fifteen-minute production cron."
requirements-completed: [D-01, D-02, D-03, D-04, D-07, D-08]
duration: 14min
completed: 2026-10-01
---

# Phase 22 Plan 02: PC Automation and Scheduled Discovery Summary

**Fail-closed Steam parent and DLC automation runs only after mapped discovery, queues uncertainty, and supports a development-only RQ ten-second interval.**

## Performance

- **Duration:** 14 min
- **Tasks:** 3/3 implemented
- **Files modified:** 9

## Accomplishments

- Added `PcAutomationHandler`, which normalizes parent folder titles, requires one validated Steam identity, preserves protected metadata, and queues uncertainty or provider failures.
- Restricted component handling to DLC and expansion targets with a trusted parent Steam identity and the matcher's parent-listed relationship validation.
- Added Steam to scheduled metadata sources, changed the production default to `*/15 * * * *`, and added the disabled-by-default, development-only 10-second RQ interval task.

## Task Commits

1. **Task 1: Specify safe automatic parent and DLC decision outcomes** - `f62c64212` (test)
2. **Task 2: Implement bounded automation using existing guarded metadata paths** - `bd7c52825` (feat), `58e31adc0` (fix)
3. **Task 3: Configure mapped periodic discovery and the exact 10-second UAT interval runner** - `98807f837` (feat)

## Files Created/Modified

- `backend/handler/metadata/pc_automation.py` - bounded parent and DLC decision/application handler.
- `backend/handler/scan_handler.py` - invokes automation using durable catalog records after mapped discovery.
- `backend/tasks/scheduled/scan_library.py` - Steam source map and UAT interval task.
- `backend/tasks/tasks.py` - reusable RQ Scheduler interval task.
- `backend/config/__init__.py`, `backend/startup.py`, `env.template` - explicit production and development scheduling configuration.
- `backend/tests/handler/metadata/test_pc_automation.py`, `backend/tests/tasks/test_scan_library.py` - decision and scheduler contracts.

## Deviations from Plan

None - plan implementation used the declared files and existing mapped scan, Steam matching, and guarded persistence seams.

## Issues Encountered

- All focused pytest commands stop during shared test setup because the configured MariaDB endpoint at `127.0.0.1:3306` is unavailable. The tests do not reach their assertions. No services, Docker configuration, NAS paths, or source libraries were changed.
- A direct runtime scheduler probe was blocked by the repository's local storage configuration attempting to create `/romm` paths, which is not writable in this checkout. AST parsing and scoped Trunk checks passed for changed production files.

## Known Stubs

None.

## Next Phase Readiness

- The central review/API phase can consume queued outcomes produced by uncertain or protected automatic decisions.
- Re-run focused test suites in the supported MariaDB test environment before merge.

## Self-Check: PASSED

- Confirmed the automation handler, scheduled task implementation, and both test files exist.
- Confirmed commits `f62c64212`, `bd7c52825`, `58e31adc0`, and `98807f837` exist in Git history.
