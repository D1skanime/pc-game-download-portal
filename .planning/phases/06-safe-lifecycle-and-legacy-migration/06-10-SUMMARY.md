---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 10
subsystem: catalog-lifecycle
tags: [fastapi, sqlalchemy, retained-identity, tdd, openapi]
dependency_graph:
  requires: [06-01, 06-02, 06-03]
  provides:
    - detached save and state API lifecycle
    - atomic retained identity reconnection
    - production scan reconnection consumer
  affects: [catalog-removal, asset-api, scan-pipeline]
tech_stack:
  added: []
  patterns:
    - effective platform authorization for live and retained assets
    - deterministic row-locked retained identity claim
key_files:
  created: []
  modified:
    - backend/endpoints/responses/assets.py
    - backend/endpoints/saves.py
    - backend/endpoints/states.py
    - backend/handler/database/saves_handler.py
    - backend/handler/database/states_handler.py
    - backend/handler/database/catalog_lifecycle_handler.py
    - backend/handler/database/roms_handler.py
    - backend/endpoints/sockets/scan.py
    - backend/tests/endpoints/roms/test_catalog_removal.py
    - backend/tests/endpoints/test_saves.py
    - backend/tests/endpoints/test_states.py
    - backend/tests/handler/database/test_storage_lifecycle.py
    - backend/tests/endpoints/sockets/test_scan.py
    - frontend/src/__generated__
decisions:
  - Detached asset authorization resolves the effective platform from the live ROM or retained catalog identity and preserves 404 masking.
  - Retained reconnection accepts one exact normalized directory plus filename identity, or one unique complete CRC32, MD5, and SHA1 triple.
  - Scan reconnection runs only for newly created ROMs after durable persistence.
metrics:
  duration: 28m
  completed: 2026-08-13
---

# Phase 6 Plan 10: Detached Asset and Retained Reconnection Summary

Detached save and state APIs with retained-platform authorization, plus deterministic scan-time identity claims that atomically restore saves, states, and play sessions.

## Performance

- **Duration:** 28 minutes
- **Started:** 2026-08-13T06:31:13Z
- **Completed:** 2026-08-13T06:58:37Z
- **Tasks:** 3
- **Files modified:** 14

## Accomplishments

- Kept catalog-detached saves and states listable, fetchable, downloadable, content-replaceable, visibility-toggleable, and deletable without dereferencing a removed ROM.
- Exposed nullable `rom_id` and explicit `retained_catalog_id` contracts, refreshed generated frontend models, and preserved owned-ASSETS storage authorization.
- Added a deterministic retained identity transaction that locks candidates in ID order and atomically reconnects Save, State, and PlaySession rows.
- Wired production scan creation to claim retained identity only after the new ROM has a durable database ID.
- Added genuine RED/GREEN evidence for authorization, hidden-platform masking, weak and ambiguous match rejection, concurrency, and remove-to-scan reconnection.

## Task Commits

1. **Task 1: Specify the detached asset lifecycle**
   - `f0741c10d` test(06-10): specify detached asset lifecycle
2. **Task 2: Implement retained asset contracts and authorization**
   - `4fc7704b1` feat(06-10): support detached asset APIs
3. **Task 3: Consume retained identity during production scan reconnection**
   - `996931ea3` test(06-10): add failing retained reconnection tests
   - `3cbb608f7` feat(06-10): reconnect retained identity during scan

## Files Created/Modified

- `backend/endpoints/responses/assets.py` - Publishes nullable active ROM and retained catalog identifiers.
- `backend/endpoints/saves.py`, `backend/endpoints/states.py` - Authorize and operate on live or detached assets through their effective platform.
- `backend/handler/database/saves_handler.py`, `backend/handler/database/states_handler.py` - Include retained identities in platform filters and eager-load retained ownership.
- `backend/handler/database/catalog_lifecycle_handler.py` - Claims and reconnects one strong retained identity transactionally.
- `backend/handler/database/roms_handler.py` - Shares exact normalized catalog logical-path matching.
- `backend/endpoints/sockets/scan.py` - Consumes retained identity after durable new-ROM persistence.
- `backend/tests/endpoints/roms/test_catalog_removal.py`, `backend/tests/endpoints/test_saves.py`, `backend/tests/endpoints/test_states.py` - Cover detached lifecycle and remove-to-reconnect behavior.
- `backend/tests/handler/database/test_storage_lifecycle.py`, `backend/tests/endpoints/sockets/test_scan.py` - Cover strong matching, ambiguity, row-lock concurrency, and scan wiring.
- `frontend/src/__generated__` - Reflects nullable ROM and retained identity response contracts.

## Decisions Made

- Detached assets inherit visibility from the effective retained platform, preserving the same missing-resource 404 response when hidden.
- Live-ROM-only screenshot replacement returns a stable 409 before any file write, while owned save/state content replacement remains supported.
- Logical matching combines the retained directory and filename, normalizes separators, and never falls back after an ambiguous exact-path match.
- Hash matching requires all three CRC32, MD5, and SHA1 values and exactly one detached candidate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected retained logical identity representation**

- **Found during:** Task 3 end-to-end remove and production scan test
- **Issue:** Removal stores the retained directory and filename separately, while the first matcher draft compared only the directory column to the full scanned logical path.
- **Fix:** Compare the normalized retained directory plus filename to the normalized scanned logical path.
- **Files modified:** `backend/handler/database/catalog_lifecycle_handler.py`, `backend/tests/handler/database/test_storage_lifecycle.py`
- **Commit:** `3cbb608f7`

**2. [Rule 1 - Bug] Bounded effective-platform lookup details before content writes**

- **Found during:** Task 2 GREEN verification
- **Issue:** The first endpoint draft referenced a branch-local error string after a successful lookup.
- **Fix:** Construct the stable missing-asset detail directly at the authorization call.
- **Files modified:** `backend/endpoints/saves.py`, `backend/endpoints/states.py`
- **Commit:** `4fc7704b1`

## Test Results

- Task 1 genuine RED: 117 tests collected and failed on non-nullable detached `rom_id`.
- Task 2 focused backend suite: 117 passed.
- Task 3 focused backend suite: 100 passed.
- Plan-wide focused backend run: 209 passed, 3 warnings.
- Frontend generated-contract typecheck: `vue-tsc --noEmit` passed.
- Commit hooks: scoped formatting and lint checks passed for every task commit.
- `git diff --check`: passed.
- No source descriptor or external source mutation was introduced; detached file operations remain on the owned ASSETS capability.

## Known Stubs

None.

## Self-Check: PASSED

- Summary artifact exists at the required phase path.
- Task commits `f0741c10d`, `4fc7704b1`, `996931ea3`, and `3cbb608f7` exist.
- No task commit deleted tracked files.
