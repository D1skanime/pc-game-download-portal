---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: 02
subsystem: database
tags: [alembic, sqlalchemy, postgresql, docker-compose, steam]
requires:
  - phase: 17-browser-download-manager
    provides: Download migration chain through revision 0125
provides:
  - Nullable Steam App ID and provenance columns for PC ROMs and components
  - A single-head, reversible Steam persistence migration
  - A disposable PostgreSQL migration verifier on the canonical Compose network
affects: [steam-metadata, pc-component-enrichment, migrations]
tech-stack:
  added: []
  patterns: [Compose-derived disposable PostgreSQL migration verification]
key-files:
  created:
    - backend/alembic/versions/0126_add_steam_metadata.py
    - backend/tools/verify_phase18_postgres_migration.sh
  modified:
    - backend/models/rom.py
    - backend/tests/models/test_pc_igdb_metadata.py
key-decisions:
  - "Steam metadata remains nullable provenance and does not create a global component App-ID constraint."
  - "Steam persistence follows the actual 0125 download chain, replacing the uncommitted 0119 collision."
  - "PostgreSQL verification derives credentials and network identity from Compose and cleans up its unique container on every exit."
patterns-established:
  - "Migration verifiers must use a unique database and Compose network discovery, never host ports or shared services."
requirements-completed: [STEAM-02, STEAM-04, STEAM-05]
duration: 7min
completed: 2026-09-25
---

# Phase 18 Plan 02: Portable Steam Persistence Summary

**Nullable Steam identity and provenance persist beside existing metadata through a single reversible Alembic head, with isolated PostgreSQL verification.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-09-25T09:29:25Z
- **Completed:** 2026-09-25T09:36:00Z
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments

- Characterized nullable Steam fields, source mappings, shared component IDs, and the required current migration parent.
- Replaced the uncommitted parallel `0119` scaffold with revision `0126_add_steam_metadata` after the current download-chain head.
- Added a fail-closed PostgreSQL 16 verifier that discovers Compose credentials and network, uses a unique database, and preserves the first failure while cleaning up.

## Task Commits

1. **Task 1: Characterize Steam persistence and migration graph requirements** - `756d1c43c` (test)
2. **Task 2: Replace the conflicting Steam migration with a single-head portable revision** - `65ad31bba` (feat)
3. **Task 3: Add an isolated PostgreSQL migration verifier on the canonical Compose network** - `2ddc29242` (feat), `0a9133dcf` (fix)

## Files Created/Modified

- `backend/models/rom.py` - Nullable Steam IDs, provenance JSON, and provider-source mappings.
- `backend/alembic/versions/0126_add_steam_metadata.py` - Reversible portable Steam columns after revision 0125.
- `backend/tools/verify_phase18_postgres_migration.sh` - Disposable canonical-network PostgreSQL migration verifier.
- `backend/tests/models/test_pc_igdb_metadata.py` - Persistence and migration-source contract assertions.

## Decisions Made

- Steam App IDs are observational provider identities. Component IDs remain shareable, with no global uniqueness constraint or index.
- `steam_metadata` stays provenance-only. It does not feed generic display fields or introduce another component creation route.
- The verifier never contacts a shared PostgreSQL service, Authentik database, or host port.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Made the verifier fail on network discovery errors before parsing output**

- **Found during:** Task 3
- **Issue:** A process-substitution pipeline could mask a failed `docker network ls` command.
- **Fix:** Capture the network listing as a guarded command before splitting it into the unique canonical network.
- **Files modified:** `backend/tools/verify_phase18_postgres_migration.sh`
- **Verification:** `trunk check` and an isolated verifier run confirmed the first Alembic failure is retained and the disposable container is removed.
- **Committed in:** `0a9133dcf`

**Total deviations:** 1 auto-fixed (1 bug fix).

## Issues Encountered

- The local Compose environment does not export `POSTGRES_USER` or `POSTGRES_PASSWORD`, so the verifier correctly fails closed unless those values are configured.
- A fresh disposable PostgreSQL 16 run reached the single `0126_add_steam_metadata` head, but full upgrade stops at the pre-existing `20260831_add_pc_rom_components.py` duplicate `romcomponentkind` enum creation. The verifier preserved status `1` and removed the container. This baseline issue is recorded in `deferred-items.md`.
- The prescribed pytest subset cannot connect to its configured `127.0.0.1:3306` MariaDB test database in this checkout, including from `romm-dev`; this is separate from the Alembic graph result.

## User Setup Required

The canonical Compose environment must define `POSTGRES_USER` and `POSTGRES_PASSWORD` before the PostgreSQL verifier can run its full proof.

## Next Phase Readiness

Steam scan and enrichment plans can rely on the nullable model and a single current migration head. PostgreSQL full-chain verification remains blocked by the documented pre-existing enum migration collision.

## Self-Check: PASSED

- Verified all four implementation and test artifacts exist.
- Verified task commits `756d1c43c`, `65ad31bba`, `2ddc29242`, and `0a9133dcf` exist in Git history.
