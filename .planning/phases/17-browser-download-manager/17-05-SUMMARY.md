---
phase: 17-browser-download-manager
plan: 05
subsystem: backend
tags: [sqlalchemy, scheduled-tasks, browser-downloads, retention]

# Dependency graph
requires:
  - phase: 17-browser-download-manager
    provides: path-free browser transfer sessions and bounded event journal
provides:
  - locked 90-day terminal transfer-history retention
  - fail-closed stale reconciliation for inactive manifests
  - hourly database-only cleanup task
affects: [browser-download-manager, download-history]

# Tech tracking
tech-stack:
  added: []
  patterns:
    [fixed cleanup batch cap, terminal timestamp cutoff, scheduled DB handler]
key-files:
  created:
    - backend/tasks/scheduled/cleanup_download_transfer_sessions.py
    - backend/tests/tasks/scheduled/test_cleanup_download_transfer_sessions.py
  modified:
    - backend/handler/database/download_transfers_handler.py
    - backend/startup.py
    - backend/tests/handler/database/test_download_transfers_handler.py
decisions:
  - "Use an inclusive 90-day cutoff based on terminal ended_at, with a fixed maximum batch of 100 rows per run."
  - "Expired or non-valid manifests make active sessions terminal stale and append bounded stale events before later observations are rejected."
metrics:
  duration: 8min
  completed: 2026-09-17
---

# Phase 17 Plan 05: Browser Transfer History Retention Summary

**Locked 90-day database retention and fail-closed manifest expiry reconciliation for browser transfer sessions.**

## Performance

- **Tasks:** 2
- **Files modified:** 5
- **Task commits:** `313bbc352` (RED), `e3e523628` (GREEN)

## Accomplishments

- Added frozen-clock coverage for exact cutoff eligibility, capped repeatable deletion, dependent event cascade, stale lifecycle, and task scheduling.
- Added one locked handler operation that reconciles active sessions whose manifests are expired or inactive, then deletes terminal sessions at or beyond 90 days.
- Added an enabled hourly `PeriodicTask` and startup registration. The cleanup path performs no filesystem or source-root operations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Avoided a scheduled-package circular import.**

- **Found during:** Task 2 focused import check
- **Issue:** Exporting the task from `tasks.scheduled.__init__` caused a cycle while metadata handlers imported scheduled modules during database-handler initialization.
- **Fix:** Kept startup’s explicit task import and made the database singleton import lazy inside the task cleanup seam.
- **Files modified:** `backend/tasks/scheduled/cleanup_download_transfer_sessions.py`
- **Commit:** `e3e523628`

## Verification

- PASS: Trunk checks for all changed backend and test files.
- PASS: Python source compilation via `compile()` and `git diff --check`.
- BLOCKED: Focused pytest could not initialize because MariaDB is unavailable at `127.0.0.1:3306` (`Can't connect to server`, errno 115).

## Known Stubs

None.

## Self-Check: PASSED

- `backend/tasks/scheduled/cleanup_download_transfer_sessions.py` exists.
- `backend/handler/database/download_transfers_handler.py` contains `cleanup_sessions`.
- Commits `313bbc352` and `e3e523628` are present in git history.

_Phase: 17-browser-download-manager_
_Plan: 05_
