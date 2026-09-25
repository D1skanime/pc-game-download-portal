---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: 11
subsystem: database-testing
tags: [mariadb, postgresql, alembic, pytest, docker-compose]
requires:
  - phase: 18-02
    provides: Steam persistence migration and disposable PostgreSQL verifier
provides:
  - Canonical-network MariaDB runner with isolated schema cleanup
  - PostgreSQL-safe component enum migration lifecycle
  - Command-backed evidence for the remaining product and historical migration blockers
affects: [phase-18-verification, backend-migrations, backend-tests]
tech-stack:
  added: []
  patterns:
    [
      Compose-network disposable database verification,
      explicit PostgreSQL enum lifecycle,
    ]
key-files:
  created:
    [
      backend/tools/verify_phase18_backend_tests.sh,
      backend/tests/tools/test_verify_phase18_evidence.py,
    ]
  modified:
    [
      backend/alembic/versions/20260831_add_pc_rom_components.py,
      backend/alembic/versions/0116_pc_component_local_media.py,
      backend/tools/verify_phase18_postgres_migration.sh,
      .planning/phases/18-steam-metadata-integration-f-r-pc-games-und-dlcs/18-VALIDATION.md,
    ]
key-decisions:
  - "Use the existing Compose services and unique disposable schemas instead of host-loopback test defaults."
  - "Stop at the unrelated 0118 PostgreSQL view migration rather than broaden the minimal enum correction."
patterns-established:
  - "PostgreSQL enum migrations explicitly create an ENUM with create_type=False before table DDL."
  - "Disposable Compose test schemas validate generated identifiers before grant, cleanup, and deletion."
requirements-completed: []
duration: 13min
completed: 2026-09-25
---

# Phase 18 Plan 11: Reproducible Backend and Migration Evidence Summary

**Canonical-network MariaDB test execution and PostgreSQL enum lifecycle fixes, with two product-test failures and one pre-existing PostgreSQL baseline blocker recorded exactly.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-09-25T14:40:00Z
- **Completed:** 2026-09-25T14:53:19Z
- **Tasks:** 3 executed, 0 fully passing
- **Files modified:** 7

## Accomplishments

- Added an executable runner that creates, grants access to, and removes only a uniquely generated MariaDB test schema on the canonical Compose network.
- Corrected the 0115 `romcomponentkind` PostgreSQL lifecycle and the directly exposed 0116 companion enum lifecycle so table DDL does not create either type twice.
- Made the disposable PostgreSQL verifier use Compose-equivalent defaults when optional PostgreSQL variables are absent.
- Recorded final exit statuses and evidence paths without logging credentials.

## Task Commits

1. **Test coverage before fixes** - `2523646d6` (test)
2. **Task 1: Canonical-network MariaDB runner** - `8ba5568cc` (feat)
3. **Task 2: PostgreSQL enum lifecycle** - `b18bd69f8` (fix)
4. **Task 3: PostgreSQL verifier defaults** - `662190667` (fix)

## Files Created/Modified

- `backend/tools/verify_phase18_backend_tests.sh` - Runs the exact focused suite in `romm-dev` against a generated MariaDB schema on `romm-db-dev` and cleans only generated resources.
- `backend/tests/tools/test_verify_phase18_evidence.py` - Guards the runner network contract and the PostgreSQL enum creation conventions.
- `backend/alembic/versions/20260831_add_pc_rom_components.py` - Prevents PostgreSQL from recreating `romcomponentkind` during table creation.
- `backend/alembic/versions/0116_pc_component_local_media.py` - Applies the same safe lifecycle to the directly blocking companion enum.
- `backend/tools/verify_phase18_postgres_migration.sh` - Resolves optional PostgreSQL Compose variables to their Compose defaults.
- `.planning/phases/18-steam-metadata-integration-f-r-pc-games-und-dlcs/18-VALIDATION.md` - Records final command status and output-path evidence.

## Decisions Made

- Reused only the already-running canonical Compose services. The test runner neither binds host database ports nor restarts services.
- Did not change historical revision 0118 after its unrelated PostgreSQL view-type failure was exposed. That correction is outside the minimal enum-focused scope of this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected the directly blocking 0116 PostgreSQL enum lifecycle**

- **Found during:** Task 2
- **Issue:** After 0115 passed, fresh PostgreSQL migration failed because 0116 created `romcomponentlocalmediarole` before passing an enum that table DDL attempted to create again.
- **Fix:** Used the repository PostgreSQL `ENUM(..., create_type=False)` convention with explicit `checkfirst=True` creation.
- **Files modified:** `backend/alembic/versions/0116_pc_component_local_media.py`, `backend/tests/tools/test_verify_phase18_evidence.py`
- **Verification:** The disposable PostgreSQL verifier passed 0115 and 0116 before reaching the unrelated 0118 blocker.
- **Committed in:** `b18bd69f8`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The minimal companion lifecycle fix was necessary to verify the corrected 0115 baseline. No service, shared database, NAS path, or secret was touched.

## Known Stubs

None.

## Issues Encountered

- `backend/tools/verify_phase18_backend_tests.sh` exited 1 after 184 passing tests. The remaining failures are `test_pc_parent_steam_selection_resolves_details_before_guarded_persistence` (409 instead of 200) and `test_pc_component_steam_provenance_preserves_existing_provider_metadata` (`None` instead of a persisted component). They are product failures outside this infrastructure and migration plan.
- `backend/tools/verify_phase18_postgres_migration.sh` exited 1 at revision 0118 after passing 0115 and 0116. PostgreSQL rejects a `roms_metadata` view replacement that changes `player_count` from `text` to `varchar(100)`.

## Threat Flags

None. The runner operates only on a validated generated schema, an isolated `/tmp` path, and a uniquely named disposable PostgreSQL container.

## Next Phase Readiness

- MariaDB migration round-trip passed with exit status 0.
- The focused backend suite and PostgreSQL full round-trip remain blocked by the failures above. Do not mark the Phase 18 requirements complete until those commands exit 0.

## Self-Check: PASSED

_Phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs_
_Completed: 2026-09-25_
