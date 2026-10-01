---
phase: 22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, pc-automation, optimistic-locking]
requires:
  - phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
    provides: version-bound PC parent and component persistence conventions
provides:
  - durable, target-unique PC automation review queue
  - guarded parent and DLC component queue transitions
  - reversible portable queue schema migration
affects: [pc-automation, background-scans, administration-review-queue]
tech-stack:
  added: []
  patterns: [target identity upsert, optimistic queue and target validation]
key-files:
  created:
    - backend/models/pc_automation.py
    - backend/alembic/versions/0133_pc_automation_queue.py
    - backend/handler/database/pc_automation_handler.py
    - backend/tests/handler/database/test_pc_automation.py
  modified:
    - backend/models/__init__.py
key-decisions:
  - "Use one non-null target identity key to make parent and component queue rows unique across MariaDB, MySQL, and PostgreSQL."
  - "Retain one queue row per target while reopening it only when its target incarnation/version or candidate fingerprint changes."
  - "Treat any parent manual metadata and component metadata with a manual source as protected queue targets."
patterns-established:
  - "Queue state changes reload and lock the queue row and current target before mutating durable evidence."
  - "Provider display evidence is bounded and cover URLs reject credentials, queries, fragments, and non-HTTP(S) schemes."
requirements-completed: [D-02, D-04, D-05]
duration: 5min
completed: 2026-10-01
---

# Phase 22 Plan 01: Durable PC Automation Queue Summary

**A target-unique, version-bound PC review queue preserves manual metadata authority while retaining only bounded provider evidence.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-10-01T21:41:55Z
- **Completed:** 2026-10-01T21:46:36Z
- **Tasks:** 3/3 implemented
- **Files modified:** 6

## Accomplishments

- Added a typed SQLAlchemy queue model and a portable, reversible migration with parent/component target shape checks and a pending-list index.
- Defined TDD persistence coverage for idempotent upserts, terminal skips, fingerprint reopen, stale target rejection, retries, pagination, and manual protection.
- Implemented queue transitions that lock and reload the queue row and current parent or eligible DLC/expansion component before each mutation.

## Task Commits

1. **Task 1: Define queue persistence behavior with isolated database tests** - `2735e5618` (test)
2. **Task 2: Add the portable queue model and migration** - `b7e7ea136` (feat)
3. **Task 3: Implement version-bound queue CRUD and state transitions** - `26c8bf8e0` (feat)

## Files Created/Modified

- `backend/models/pc_automation.py` - Queue model plus typed target, state, and outcome enums.
- `backend/models/__init__.py` - Queue model registration.
- `backend/alembic/versions/0133_pc_automation_queue.py` - Portable queue table, constraints, indexes, upgrade, and downgrade.
- `backend/handler/database/pc_automation_handler.py` - Idempotent evidence persistence and guarded queue transitions.
- `backend/tests/handler/database/test_pc_automation.py` - Parent and DLC persistence transition matrix.

## Decisions Made

- A generated non-null target identity, not a nullable composite unique key, enforces one queue row for both parent and component targets on all supported dialects.
- A skipped row remains terminal only while both its stored target incarnation/version and decision fingerprint still match current evidence.
- Cover display URLs deliberately exclude query strings and fragments so durable queue evidence cannot retain signed URL credentials.

## Deviations from Plan

None - plan implementation followed the specified model, migration, handler, and test scope.

## Issues Encountered

- `uv run pytest tests/handler/database/test_pc_automation.py -q` reaches test setup but cannot connect to its configured MariaDB endpoint at `127.0.0.1:3306`. All six tests are blocked before assertions; no Docker, NAS, or Team4s service was changed.
- `uv run alembic upgrade head` cannot initialize because `ROMM_AUTH_SECRET_KEY` is absent from the local environment. A syntax/import check with a process-local placeholder passed, but no migration database cycle could run.
- `compileall` could not write existing `__pycache__` directories due to filesystem permissions. AST parsing and scoped Trunk checks succeeded without writing bytecode.

## Known Stubs

None.

## Next Phase Readiness

- Background matching and administration endpoints can use `DBPcAutomationHandler` for durable evidence and protected target validation.
- Run the focused pytest suite and migration upgrade/downgrade against the repository-supported MariaDB and PostgreSQL environments before merging.

## Self-Check: PASSED

- Confirmed all five implementation/test files exist.
- Confirmed commits `2735e5618`, `b7e7ea136`, and `26c8bf8e0` exist in Git history.
