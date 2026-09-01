---
phase: 10-pc-integration-model
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, pc-components, sha256, scanner]
requires:
  - phase: 09-operational-immutability-proof
    provides: read-only external-storage capabilities
provides:
  - Explicit PC component rows with per-file SHA-256 manifests
  - Read-only component discovery for exact folder layouts
  - Stable database reconciliation for repeated component scans
affects: [pc-downloads, scanner, rom-model]
tech-stack:
  added: []
  patterns:
    - Rooted capability hashing for external PC component files
    - Path-keyed reconciliation that preserves unchanged row identities
key-files:
  created:
    - backend/alembic/versions/20260831_add_pc_rom_components.py
  modified:
    - backend/models/rom.py
    - backend/handler/filesystem/roms_handler.py
    - backend/handler/database/roms_handler.py
    - backend/handler/scan_handler.py
key-decisions:
  - "Only exact top-level component folder names are classified; all other layouts are unresolved."
  - "Component and member rows reconcile by relative path so unchanged manifests retain identity."
requirements-completed:
  [PCMOD-01, PCMOD-02, PCMOD-03, PCMOD-04, PCSAFE-01, PCTEST-01]
duration: 43min
completed: 2026-09-01
---

# Phase 10 Plan 01: PC Integration Model Summary

**Read-only PC component manifests with explicit kinds, SHA-256 evidence, and stable repeated-scan reconciliation.**

## Performance

- **Duration:** 43 min
- **Started:** 2026-09-01T07:31:00Z
- **Completed:** 2026-09-01T08:14:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added one-to-many component and manifest-member persistence for each logical ROM.
- Added a rooted, read-only parser for exact PC component folders and their regular-file SHA-256 manifests.
- Reconciled component scans by component and member relative paths, preserving unchanged database identities and logging unresolved layouts.

## Task Commits

1. **Task 1: Define component and manifest persistence** - `031bc1858` (feat)
2. **Task 2: Discover only explicit PC component layouts and build manifests** - `3d54d43ed` (feat)
3. **Task 3: Reconcile repeated scans without source mutation** - `c06da8b6c` (feat)

## Files Created/Modified

- `backend/models/rom.py` - Component models, enum values, relationships, and portable path length.
- `backend/alembic/versions/20260831_add_pc_rom_components.py` - Schema migration for component and manifest tables.
- `backend/handler/filesystem/roms_handler.py` - Explicit layout parser and rooted manifest builder.
- `backend/handler/database/roms_handler.py` - Transactional row reconciliation.
- `backend/handler/scan_handler.py` - Windows scanner integration and unresolved-layout warning.
- `backend/tests/models/test_rom.py` - Persistence and uniqueness tests.
- `backend/tests/handler/filesystem/test_roms_handler.py` - Read-only manifest and traversal tests.
- `backend/tests/handler/test_fastapi.py` - Reconciliation identity and scan-log tests.

## Decisions Made

- Classify only exact configured folder names (`base`, `update`, `dlc`, `hotfix`, `language-pack`, and `extra`). Unknown and nested layouts persist as `unresolved`.
- Store member paths relative to the logical PC ROM root, allowing unique paths inside each component and deterministic reconciliation.
- Use a 700-character component path limit because a 1000-character UTF-8 unique index exceeds MariaDB's portable index limit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Persisted enum values rather than Python enum member names**

- **Found during:** Task 1
- **Issue:** SQLAlchemy serialized `UPDATE` while the migration stores `update`, preventing ORM reads.
- **Fix:** Configured the ORM enum to serialize its lowercase string values.
- **Files modified:** `backend/models/rom.py`
- **Verification:** Focused persistence test passes against MariaDB.
- **Committed in:** `031bc1858`

**2. [Rule 1 - Bug] Made unique component paths portable on MariaDB**

- **Found during:** Task 1
- **Issue:** A UTF-8 `VARCHAR(1000)` composite unique index cannot be created within MariaDB's index-byte limit.
- **Fix:** Limited persisted component and member paths to 700 characters in the model and migration.
- **Files modified:** `backend/models/rom.py`, `backend/alembic/versions/20260831_add_pc_rom_components.py`
- **Verification:** Created and removed equivalent MariaDB probe tables, then ran migration downgrade and upgrade on the test database.
- **Committed in:** `031bc1858`

**3. [Rule 2 - Missing critical functionality] Added the database-handler reconciliation boundary**

- **Found during:** Task 3
- **Issue:** The plan required transactional reconciliation but omitted the existing database handler that owns database sessions.
- **Fix:** Added a narrow `sync_rom_components` method and scanner coverage in the actual existing scanner test module.
- **Files modified:** `backend/handler/database/roms_handler.py`, `backend/tests/handler/test_fastapi.py`
- **Verification:** Repeated scans preserve unchanged component and member IDs; a changed digest updates only its member.
- **Committed in:** `c06da8b6c`

**Total deviations:** 3 auto-fixed (2 Rule 1, 1 Rule 2).

## Verification

- `docker compose run ... uv run pytest -c /dev/null -p pytest_asyncio -o asyncio_mode=auto tests/models/test_rom.py tests/handler/filesystem/test_roms_handler.py tests/handler/test_fastapi.py -q` passed: 102 passed, 1 skipped.
- `alembic downgrade -1 && alembic upgrade head` passed against the isolated local test database, which finished at `0115_pc_rom_components` with both new tables present.
- `trunk fmt` passed for all eight plan files.
- `trunk check` has one pre-existing mypy error at `backend/handler/scan_handler.py:229`, introduced by commit `9b347e93ca`. It is outside this plan's diff and was not changed.

## Known Stubs

None.

## Next Phase Readiness

PC component persistence and read-only scan manifests are ready for download and UI consumers. The unrelated scanner mypy issue remains deferred.

## Self-Check: PASSED

- All eight implementation and test files exist.
- Task commits `031bc1858`, `3d54d43ed`, and `c06da8b6c` exist.
