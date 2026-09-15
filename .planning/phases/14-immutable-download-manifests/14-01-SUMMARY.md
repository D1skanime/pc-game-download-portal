---
phase: 14-immutable-download-manifests
plan: "01"
subsystem: database
tags: [sqlalchemy, alembic, mariadb, immutable-manifest]
requires:
  - phase: 10-pc-integration-model
    provides: trusted PC component and manifest-member evidence
provides:
  - owner-scoped immutable download manifest ORM aggregate
  - portable 0119 manifest persistence migration
affects: [14-02-manifest-creation, 15-direct-download-delivery]
tech-stack:
  added: []
  patterns: [path-free durable manifest evidence, portable VARCHAR enum checks]
key-files:
  created:
    - backend/models/download_manifest.py
    - backend/alembic/versions/0119_download_manifests.py
    - backend/tests/models/test_download_manifest.py
  modified: []
key-decisions:
  - "Manifest members retain only opaque source-member IDs and immutable delivery evidence, never source paths."
requirements-completed: [DLMT-02, DLMT-03]
duration: 24m
completed: 2026-09-15
---

# Phase 14 Plan 01: Immutable Manifest Persistence Summary

**Owner-scoped SQLAlchemy manifest records preserve safe destinations, 64-bit sizes, SHA-256, quoted snapshots, and light revalidation indicators without source-library paths.**

## Performance

- **Duration:** 24m
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- Added immutable manifest header, selected-component, and member ORM models with closed lifecycle status values.
- Added portable `0119_download_manifests` migration with cascade-safe foreign keys, named uniqueness constraints, and owner/status/expiry indexing.
- Added focused red-green persistence and migration evidence, including >4 GiB values, distinct snapshots, nullable device/inode, cascades, and path-free columns.

## Task Commits

1. **Task 1, persistence tests (RED):** `c6282b430` (`test`)
2. **Task 1, ORM aggregate (GREEN):** `b0274b3df` (`feat`)
3. **Task 2, migration tests (RED):** `f2d524279` (`test`)
4. **Task 2, migration (GREEN):** `cd993c9a1` (`feat`)

## Verification

- `cd backend && uv run pytest tests/models/test_download_manifest.py -vv`, 6 passed.
- Isolated `romm_test` Alembic `upgrade head`, `downgrade -1`, `upgrade head`, all completed successfully.
- `trunk fmt` and scoped `trunk check` passed for the three plan-owned files.

## Decisions Made

- Persist snapshots separately from SHA-256, retaining snapshot as a quoted strong validator.
- Store only `mtime_ns` and nullable device/inode indicators for lightweight later revalidation.
- Avoid native database enums to preserve portable MariaDB, MySQL, and PostgreSQL DDL.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected MariaDB migration downgrade ordering**

- **Found during:** Task 2
- **Issue:** MariaDB used the owner/status/expiry index to support the user foreign key, so dropping that index before the header table failed.
- **Fix:** Drop the dependent tables and header table first, allowing the database to remove the supporting index safely.
- **Files modified:** `backend/alembic/versions/0119_download_manifests.py`
- **Verification:** Isolated upgrade, downgrade, and re-upgrade completed.
- **Committed in:** `cd993c9a1`

## Known Stubs

None.

## Next Phase Readiness

The durable, path-free aggregate is ready for the Phase 14 manifest-creation handler. No source-library access, HTTP delivery, UI, or generated types were added.

## Self-Check: PASSED

- All three declared implementation files exist.
- All four task commits are present in Git history.
