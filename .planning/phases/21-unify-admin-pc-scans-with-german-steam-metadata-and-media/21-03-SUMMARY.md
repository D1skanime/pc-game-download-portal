---
phase: 21-unify-admin-pc-scans-with-german-steam-metadata-and-media
plan: "03"
subsystem: metadata
tags: [steam, owned-media, httpx, pytest]
requires:
  - phase: 21-02
    provides: Atomic Steam inventory reconciliation and active candidate lookup.
provides:
  - Scan-owned, bounded Steam image download and inventory reconciliation.
  - Failure-isolated cleanup for bytes created before an unsuccessful batch handoff.
affects: [scan-handler, phase-21-plan-04]
tech-stack:
  added: []
  patterns: [complete-inventory-before-mutation, reuse-active-owned-paths]
key-files:
  created:
    - backend/handler/metadata/steam_owned_media.py
    - backend/tests/handler/metadata/test_steam_owned_media.py
  modified: []
key-decisions:
  - "Only explicit complete media mappings, including a deliberately empty mapping, may reach Steam inventory reconciliation."
  - "Existing active same-identity paths are reused before network I/O, while failed attempts remove only paths written during that attempt."
patterns-established:
  - "Scan media handlers validate provider URLs with discover_provider_media before download or catalog mutation."
  - "Post-commit retired paths are queued as cleanup intents, not deleted from the scan request."
requirements-completed: [STEAM-02, STEAM-05]
duration: 24min
completed: 2026-09-30
---

# Phase 21 Plan 03: Steam Owned-Media Reconciliation Summary

**Steam scan media now validates canonical HTTPS candidates, reuses active owned paths, and publishes only complete inventories through the locked repository batch.**

## Performance

- **Duration:** 24 min
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments

- Added a metadata-layer service that translates normalized Steam cover and screenshot patches into canonical provider candidates.
- Enforced bounded managed-client downloads, 10 MiB response limits, and writes exclusively through RomM-owned media storage.
- Added handler-only tests for canonical reuse, invalid/incomplete data, HTTP and size failures, current-attempt cleanup, lock conflicts, and deliberate empty inventories.

## Task Commits

1. **Task 1: Test the scan-owned Steam media transaction boundary** - `e8efedb84` (test)
2. **Task 2: Implement bounded candidate download and safe batch handoff** - `35c4fd419` (feat)

## Files Created

- `backend/handler/metadata/steam_owned_media.py` - Safe scan-owned Steam candidate download, active-path reuse, batch handoff, and deferred cleanup intent creation.
- `backend/tests/handler/metadata/test_steam_owned_media.py` - Isolated async service coverage with all external and database dependencies mocked.

## Decisions Made

- Treat a missing or malformed media mapping as a no-op. A mapping with both declared empty lists is the explicit empty-inventory signal and may reconcile stale Steam candidates.
- Queue returned unreferenced paths only after a successful repository handoff. Never clean reused paths or prior catalog state from a failed scan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Kept new handler tests independent of unavailable MariaDB**

- **Found during:** Task 1
- **Issue:** The repository-wide autouse database fixtures connect to `127.0.0.1:3306`, which is unavailable in the authorized environment despite this suite mocking every database dependency.
- **Fix:** The new handler-only test module overrides those fixtures locally and verifies the service without a database connection.
- **Files modified:** `backend/tests/handler/metadata/test_steam_owned_media.py`
- **Verification:** `uv run pytest tests/handler/metadata/test_steam_owned_media.py -x` passes with 6 tests.
- **Committed in:** `e8efedb84`

**Total deviations:** 1 auto-fixed (1 blocking)

## Issues Encountered

- The required combined suite begins successfully with the six handler tests, then `tests/handler/database/test_rom_media.py` cannot establish its MariaDB fixture because `127.0.0.1:3306` refuses connections. No Docker Compose, NAS, Team4s service, or external source library was accessed.

## Verification

- `trunk check handler/metadata/steam_owned_media.py tests/handler/metadata/test_steam_owned_media.py` passed.
- `uv run pytest tests/handler/metadata/test_steam_owned_media.py -x` passed, 6 tests.
- `uv run pytest tests/handler/metadata/test_steam_owned_media.py tests/handler/database/test_rom_media.py -x` is blocked by unavailable local MariaDB after the six handler tests pass.

## Next Phase Readiness

Plan 04 can call `reconcile_steam_patch_media(rom, patch)` only after durable ROM persistence and only for a successful Steam patch that contains the explicit media mapping. Database-level reconciliation validation remains pending an authorized MariaDB test environment.

## Self-Check: PASSED

- Confirmed both task commits exist in Git history.
- Confirmed both created source and test files exist.

---

_Phase: 21-unify-admin-pc-scans-with-german-steam-metadata-and-media_
_Completed: 2026-09-30_
