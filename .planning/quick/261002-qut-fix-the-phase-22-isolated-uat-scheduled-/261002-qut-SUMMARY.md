---
quick_task: 261002-qut
status: complete
subsystem: pc-automation-uat
tags: [rq, rq-scheduler, docker-compose, pc-automation, vue]
requires:
  - phase: 22
    provides: PC automation review queue and isolated text-fixture UAT
provides:
  - Recurring disposable RQ scheduler and low-priority worker topology
  - Mapped-only scheduled scan no-op behavior
  - Server-derived queue target titles distinct from provider evidence
affects: [phase-22-uat, pc-automation, scheduled-scans]
tech-stack:
  added: []
  patterns:
    - RQ Scheduler connects explicitly to the isolated Redis service.
    - Queue display titles are resolved from authorized ROM/component records.
key-files:
  modified:
    - backend/tasks/scheduled/scan_library.py
    - backend/docker-compose.pc-integration-test.yml
    - backend/endpoints/roms/pc_automation.py
    - frontend/src/v2/components/Settings/PcAutomationQueue.vue
key-decisions:
  - "Use rqscheduler with an explicit queue Redis URL, because rq-scheduler interval jobs are not served by RQ's built-in worker scheduler."
  - "Treat an empty active-mapping command list as a successful scheduled no-op."
requirements-completed: [D-05, D-07, D-08]
duration: 41min
completed: 2026-10-02
---

# Quick Task 261002-qut: Scheduled PC UAT and Target Visibility Summary

**Disposable RQ scheduling now detects a newly added synthetic Sekiro fixture automatically, while queue cards identify the authoritative game or DLC being reviewed.**

## Accomplishments

- Scheduled scans skip an empty active-mapping set and retain the recurring ten-second RQ interval semantics.
- The disposable Compose topology runs `rqscheduler` and a `RomMWorker` on the shared isolated Redis `low` queue.
- Queue responses derive `target_title` from the visible ROM or scoped component, and the v2 card shows provider evidence separately.
- A fresh isolated project automatically created the Sekiro catalog row and pending review row after the fixture was added, with a byte-identical post-addition source manifest.

## Task Commits

1. **Task 1: Resilient mapped-only recurring scan** - `32ee12dfb`
2. **Task 2: Authoritative reviewed target on queue cards** - `9625eae38`
3. **Task 3: Disposable scheduler-worker UAT** - `31fe3b577`
4. **Generated contract refresh** - `9f159ebd3`

## Verification

- Disposable-container focused suite: `22 passed, 1 deselected` for scheduled scan, source immutability, and queue route tests.
- Frontend OpenAPI generation against the disposable UAT stack and `npm run typecheck` passed.
- `trunk check --no-fix` passed for the Compose, scheduled-scan test, and UAT record.
- Project `romm-phase22-qut-1790974495` ran scheduler, worker, app, Redis, MariaDB, and nginx only. It was removed with its exact volumes and network; the temporary fixture root was moved to local trash.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pointed scheduler and worker at disposable Redis explicitly**

- **Found during:** Task 3
- **Issue:** `rqscheduler` defaults to localhost and could not reach the Compose `queue` service.
- **Fix:** Added `--url redis://queue:6379/0` to both service commands.
- **Verification:** The worker executed recurring `low` jobs and automatically discovered Sekiro.
- **Committed in:** `31fe3b577`

## Remaining UAT Work

The automatic-scan proof is complete. Phase 22 still needs the browser review actions, including Skip without Conflict, correction/claim behavior, and stale-conflict proof, before Phase 22 itself can be approved.

## Self-Check: PASSED

- All listed commits exist.
- The isolated scheduler proof and cleanup are recorded in `22-UAT.md`.
