---
phase: 17-browser-download-manager
plan: 04
subsystem: api
tags: [fastapi, sqlalchemy, alembic, browser-downloads, audit-history]

# Dependency graph
requires:
  - phase: 17-browser-download-manager
    provides: immutable browser download manifests and direct member transfer authority
provides:
  - owner-scoped path-free browser transfer sessions, item snapshots, and bounded event journal
  - protected history and observation API that cannot authorize file delivery
  - portable MariaDB/MySQL/PostgreSQL migration and state-transition tests
affects: [browser-download-manager, download-history, browser-transfer-queue]

# Tech tracking
tech-stack:
  added: []
  patterns:
    [
      owner-scoped SQLAlchemy journal,
      append-only ordinal events,
      server-fact versus browser-observation status separation,
    ]

key-files:
  created:
    - backend/models/download_transfer.py
    - backend/handler/database/download_transfers_handler.py
    - backend/endpoints/responses/download_transfer.py
    - backend/endpoints/download_transfers.py
    - backend/alembic/versions/0123_download_transfer_sessions.py
    - backend/tests/models/test_download_transfer.py
    - backend/tests/handler/database/test_download_transfers_handler.py
    - backend/tests/endpoints/test_download_transfers.py
  modified:
    - backend/handler/database/__init__.py
    - backend/main.py

key-decisions:
  - "Transfer sessions retain only manifest/member identities, selected totals, timestamps, and bounded observations, never paths, URLs, tokens, or local handles."
  - "served is emitted only by the server-side mark_served operation; standard browser handoff cannot become served or verified through the client route."
  - "Enhanced verified requires an exact local digest equality observation and remains history only, never delivery authority."

patterns-established:
  - "Every transfer read and mutation is scoped by authenticated owner, with hidden and foreign records masked."
  - "State transitions lock the session and item, reject closed or illegal transitions, enforce monotonic bounded bytes, and append a unique ordinal event."

requirements-completed: [UXDL-01, SAFE-01, TEST-01]

# Metrics
duration: 15min
completed: 2026-09-17
---

# Phase 17 Plan 04: Browser Transfer Journal Summary

**Owner-scoped, path-free browser transfer history with truthful handoff, served, verification, stale, and cancellation semantics**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-17T20:34:00Z
- **Completed:** 2026-09-17T20:49:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added durable session, item, and append-only event models with BigInteger counters, owner/manifest relationships, retention-ready timestamps, and no filesystem or credential fields.
- Added locked handler operations for owner-scoped creation/history, bounded observations, server-only served transitions, digest-bound enhanced verification, cancellation, and stale 409/410/412 mapping.
- Added protected ROM-read API routes with strict payloads and hidden-owner masking, registered the router, and added a reversible migration plus model/handler/endpoint tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Specify truthful owner-only session journal behavior** - `5bdb5c980` (test)
2. **Task 2: Implement session journal and protected observation routes** - `8e398b9ed` (feat)

## Files Created/Modified

- `backend/models/download_transfer.py` - Path-free session, item, and event ORM models with bounded statuses and counters.
- `backend/handler/database/download_transfers_handler.py` - Owner-scoped locked lifecycle and observation operations.
- `backend/endpoints/download_transfers.py` and `backend/endpoints/responses/download_transfer.py` - Protected history and observation contract.
- `backend/alembic/versions/0123_download_transfer_sessions.py` - Reversible transfer-journal schema migration.
- `backend/tests/models/test_download_transfer.py` - Persistence, cascade, path-redaction, and bounded-field contract tests.
- `backend/tests/handler/database/test_download_transfers_handler.py` - Owner masking and illegal transition tests.
- `backend/tests/endpoints/test_download_transfers.py` - Auth, payload, and truthful standard-mode response tests.
- `backend/main.py` - Router registration required for the new API to be reachable.

## Decisions Made

- Session metadata remains observational and cannot be used as a member-delivery credential.
- Client event ingestion explicitly rejects `served`; only server-owned transfer code may record that fact.
- Session creation rejects expired, revoked, or otherwise inactive manifests before copying member snapshots.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Registered the transfer router in the application.**

- **Found during:** Task 2
- **Issue:** The plan declared the endpoint module but omitted `backend/main.py`; without registration, all protected routes were unreachable.
- **Fix:** Imported and included the router under `/api`.
- **Files modified:** `backend/main.py`
- **Verification:** Ruff/static checks pass; route module imports under configured environment.
- **Committed in:** `8e398b9ed`

**2. [Rule 1 - Bug] Normalized item activity timestamps to UTC.**

- **Found during:** Final static review after Task 2
- **Issue:** One observation path used the host-local timezone helper, which could make history timestamps inconsistent across deployments.
- **Fix:** Record activity with explicit UTC timestamps.
- **Files modified:** `backend/handler/database/download_transfers_handler.py`
- **Verification:** Trunk Ruff checks pass.
- **Committed in:** `636f690a7`

**Total deviations:** 2 auto-fixed (Rule 1, Rule 2)

**Impact on plan:** Required application wiring only, no new authority or scope expansion.

## Issues Encountered

- Focused pytest and Alembic round-trip verification could not start because MariaDB is unavailable at `127.0.0.1:3306` (`Can't connect to server`, errno 115). Static AST parsing, import checks with configured environment, `git diff --check`, and Trunk Ruff checks passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The journal and protected API are ready for the browser queue to create sessions and report observations. Run the focused pytest suite and `alembic upgrade head && alembic downgrade -1` once MariaDB is available. The transfer journal remains non-authoritative by construction.

## Self-Check: PASSED

- `backend/models/download_transfer.py` exists.
- `backend/handler/database/download_transfers_handler.py` exists.
- `backend/endpoints/download_transfers.py` exists.
- Migration `backend/alembic/versions/0123_download_transfer_sessions.py` exists.
- Commits `5bdb5c980` and `8e398b9ed` are present in git history.

---

_Phase: 17-browser-download-manager_
_Plan: 04_
_Completed: 2026-09-17_
