---
phase: 12-dlc-detail-pages-for-local-pc-components
plan: 07
subsystem: database
tags: [sqlalchemy, alembic, fastapi, pc-components, dlc-media, notes]
requires:
  - phase: 12-01
    provides: DLC navigation and component route boundaries
  - phase: 12-03
    provides: isolated DLC detail rendering contracts
provides:
  - Component-owned DLC media and note persistence isolated from source evidence
  - Version-guarded component resource handler contracts and response schemas
affects:
  [
    12-dlc-detail-pages-for-local-pc-components,
    pc-metadata,
    dlc-media,
    dlc-notes,
  ]
tech-stack:
  added: []
  patterns:
    [component-scoped optimistic mutations, owned-media cleanup bookkeeping]
key-files:
  created:
    - backend/alembic/versions/0117_component_owned_media_and_notes.py
    - backend/tests/models/test_rom_component_resources.py
    - backend/tests/handler/database/test_pc_component_resources.py
  modified:
    - backend/models/rom.py
    - backend/endpoints/responses/rom.py
    - backend/handler/database/roms_handler.py
key-decisions:
  - "Owned component media uses its own table and never stores source path or digest evidence."
  - "Every component resource mutation requires the parent, DLC component, authenticated user, and component version."
patterns-established:
  - "Use component-only relationships and version predicates for DLC-owned state."
requirements-completed: [D-03, D-04, D-05, D-06, D-09, D-10, D-12]
duration: 13min
completed: 2026-09-03
---

# Phase 12 Plan 07: Component-owned resource persistence Summary

**DLC-owned media and notes now persist separately from immutable local source evidence, with parent/component/version-guarded database helpers.**

## Performance

- **Duration:** 13 min
- **Completed:** 2026-09-03T11:23:08Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- Added separate owned-media and component-note ORM relationships, cascading persistence, portable checks, indexes, and a reversible migration.
- Preserved `RomComponentLocalMedia` as source-evidence-only storage with mandatory source path and SHA-256 fields.
- Added typed component-only response/request schemas plus version-guarded media and note CRUD helpers.

## Task Commits

1. **Task 1: Specify and implement component-owned ORM and migration contracts**
   - `27db33587` `test(12-07): specify component-owned resource isolation`
   - `3328a22e8` `feat(12-07): add component-owned resource persistence`
2. **Task 2: Add version-guarded component resource database contracts and OpenAPI schemas**
   - `116c744dc` `test(12-07): specify version-guarded component resources`
   - `b50210c18` `feat(12-07): add version-guarded component resources`

## Verification

- `cd backend && ROMM_AUTH_SECRET_KEY=test-secret uv run pytest tests/handler/database/test_pc_component_resources.py tests/models/test_rom_component_resources.py -q` passed, 5 tests.
- `trunk fmt --no-fix backend/models/rom.py backend/endpoints/responses/rom.py backend/handler/database/roms_handler.py` passed.
- `trunk check --no-fix backend/models/rom.py backend/endpoints/responses/rom.py backend/handler/database/roms_handler.py` passed.

## Decisions Made

- Managed component media has a distinct `owned_path`, MIME type, role, and origin/provider identity. It cannot carry source-library evidence fields.
- Component mutations update only `RomComponent.updated_at`; parent ROM metadata and cover columns remain untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Migration portability] Shortened the Alembic revision identifier**

- **Found during:** Task 1
- **Issue:** MariaDB's existing `alembic_version.version_num` column rejected the original descriptive identifier as too long.
- **Fix:** Used the 32-character `0117_component_owned_media_notes` revision value while retaining the descriptive migration filename.
- **Files modified:** `backend/alembic/versions/0117_component_owned_media_and_notes.py`
- **Verification:** Focused persistence tests pass after upgrade.
- **Committed in:** `3328a22e8`

**2. [Rule 2 - Missing critical functionality] Eager-loaded component-owned media for detailed ROM responses**

- **Found during:** Task 2
- **Issue:** The new component schema would otherwise access a `lazy="raise"` relationship during serialization.
- **Fix:** Added explicit `selectinload(RomComponent.owned_media)` to detailed ROM loaders.
- **Files modified:** `backend/handler/database/roms_handler.py`
- **Verification:** Focused tests and Trunk checks pass.
- **Committed in:** `b50210c18`

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 2).

## Issues Encountered

- The required three-dialect migration harness could not start in this checkout: `verify_storage_migrations.py` expects a Docker runner named `romm-dev`, but no gateway exists for it. The focused MariaDB migration-backed tests passed. The complete MariaDB/MySQL/PostgreSQL harness remains to be run from the configured disposable runner environment.

## Next Phase Readiness

- Later DLC media and notes endpoints can use component-only, typed persistence helpers without authority over the parent ROM or source library.
- Run `cd backend && uv run python tools/verify_storage_migrations.py --dialects mariadb mysql postgresql` from the standard disposable migration runner before release.

## Self-Check: PASSED

- All six planned implementation and test files exist.
- All four TDD task commits exist in Git history.
