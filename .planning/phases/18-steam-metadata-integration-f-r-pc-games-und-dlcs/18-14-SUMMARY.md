---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: 14
subsystem: database-testing
tags: [postgresql, mariadb, alembic, migration, pytest]
requires:
  - phase: 18-11
    provides: Disposable PostgreSQL migration verifier and the recorded 0118 blocker
provides:
  - Type-stable PostgreSQL replacement of the historical roms_metadata view
  - Source contracts for PostgreSQL, MariaDB, and the isolated migration cycle
affects: [phase-18-verification, backend-migrations]
tech-stack:
  added: []
  patterns:
    - Preserve historical PostgreSQL view types with a dialect-specific projection
key-files:
  created: []
  modified:
    - backend/alembic/versions/0118_pc_igdb_structured_metadata.py
    - backend/tests/models/test_pc_igdb_metadata.py
    - backend/tests/tools/test_verify_phase18_evidence.py
key-decisions:
  - "Cast only PostgreSQL generated_player_count to text, matching revision 0098 and leaving MariaDB SQL unchanged."
  - "Keep CREATE OR REPLACE VIEW and prove the existing disposable verifier's full migration cycle instead of using a destructive view replacement."
patterns-established:
  - "Historical view replacements preserve prior PostgreSQL column types with dialect-specific projections."
requirements-completed: [STEAM-02, STEAM-05]
duration: 8min
completed: 2026-09-25
---

# Phase 18 Plan 14: PostgreSQL Metadata View Compatibility Summary

**Revision 0118 now preserves the legacy PostgreSQL text type for roms_metadata.player_count while retaining MariaDB SQL and all structured PC metadata fields.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-09-25T15:06:00Z
- **Completed:** 2026-09-25T15:14:00Z
- **Tasks:** 2 completed
- **Files modified:** 3

## Accomplishments

- Reproduced PostgreSQL's real failure before the Steam migration: `CREATE OR REPLACE VIEW` attempted to change `player_count` from `text` to `character varying(100)`.
- Added RED contracts for the legacy PostgreSQL projection, MariaDB-only expressions, and all four commands in the isolated verifier.
- Matched revision 0098's type-stability convention in 0118 and verified the complete disposable PostgreSQL 16 migration cycle.

## Task Commits

1. **Task 1: Characterize the 0118 view-type failure and its portable invariant** - `4d3feab3e` (test)
2. **Task 2: Make revision 0118 type-stable on PostgreSQL and portable on MariaDB** - `dfa96d9ec` (fix)

## Files Created/Modified

- `backend/alembic/versions/0118_pc_igdb_structured_metadata.py` - Casts only PostgreSQL `generated_player_count` to `text` in both the upgrade and downgrade view definitions.
- `backend/tests/models/test_pc_igdb_metadata.py` - Pins PostgreSQL structured fields and MariaDB's non-PostgreSQL expressions.
- `backend/tests/tools/test_verify_phase18_evidence.py` - Pins the PostgreSQL 16 verifier, cleanup, heads, upgrade, downgrade, and re-upgrade contract.

## Decisions Made

- Used `generated_player_count::text AS player_count` only when `is_pg` is true. This is the exact established 0098 compatibility convention and preserves MariaDB's `VARCHAR(100)` projection.
- Preserved the existing revision ID, `CREATE OR REPLACE VIEW`, structured field aliases, column ordering, and isolated verifier. No view drop, CASCADE, data rewrite, or migration-head change was needed.

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

- RED: `4d3feab3e` introduced the missing PostgreSQL text-projection contract and failed as expected before implementation.
- GREEN: `dfa96d9ec` added the smallest dialect-specific cast, then the contracts and isolated PostgreSQL migration cycle passed.

## Verification

- `cd backend && uv run pytest --noconftest tests/models/test_pc_igdb_metadata.py::test_pc_igdb_metadata_migration_is_reversible_and_portable tests/models/test_pc_igdb_metadata.py::test_pc_igdb_metadata_postgres_view_keeps_legacy_player_count_as_text tests/models/test_pc_igdb_metadata.py::test_pc_igdb_metadata_mariadb_view_keeps_non_postgresql_expressions tests/tools/test_verify_phase18_evidence.py -q` passed: 7 passed, 1 warning. The warning is an existing permission denial writing `backend/.pytest_cache`.
- `backend/tools/verify_phase18_postgres_migration.sh` passed with exit 0. It completed `heads`, fresh `upgrade head`, `downgrade -1`, and re-`upgrade head` in a disposable PostgreSQL 16 container, which was removed by the verifier cleanup trap.
- `trunk fmt backend/alembic/versions/0118_pc_igdb_structured_metadata.py && trunk check backend/alembic/versions/0118_pc_igdb_structured_metadata.py` passed. Trunk reported the migration ignored by mypy, with no issues.
- The plan's regular focused pytest command remains blocked before assertions because `backend/pytest.ini` forces `DB_HOST=127.0.0.1`, while the available MariaDB service is Compose-network-only. Exact status from the run: 11 setup errors, all rooted in `mariadb.OperationalError: Can't connect to server on '127.0.0.1' (115)`. This is pre-existing infrastructure, unrelated to the migration correction.

## Known Stubs

None.

## Threat Flags

None. The change preserves the historical view type through a dialect-specific projection and the verifier remains isolated and self-cleaning.

## Next Phase Readiness

- The previous 0118 PostgreSQL blocker is resolved and the full isolated migration verifier is green.
- The host-focused pytest command remains blocked by the existing loopback MariaDB configuration. It does not affect the disposable PostgreSQL migration proof.

## Self-Check: PASSED

- Confirmed the migration, both contract-test files, and this summary exist.
- Confirmed task commits `4d3feab3e` and `dfa96d9ec` exist in git history.

_Phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs_
_Completed: 2026-09-25_
