---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: 10
subsystem: metadata
tags: [igdb, steam, dlc, safety, testing]
requires:
  - phase: 18-05
    provides: IGDB-first Steam DLC enrichment and validation
provides:
  - Fail-closed IGDB detail hydration before automatic Steam DLC enrichment
  - Regression coverage for no Steam lookup or component write after hydration failure
affects: [scan, pc-components, steam-metadata]
tech-stack:
  added: []
  patterns: [hydrated identity gates external metadata lookup]
key-files:
  created: []
  modified:
    - backend/handler/metadata/pc_match_handler.py
    - backend/tests/handler/metadata/test_pc_match_handler.py
    - backend/tests/endpoints/sockets/test_scan.py
key-decisions:
  - "Only a matching, named IGDB detail candidate may authorize automatic Steam DLC enrichment."
patterns-established:
  - "Cached IGDB relationship data remains discovery-only when detail hydration is unavailable or invalid."
requirements-completed: [STEAM-03, STEAM-05]
duration: 10min
completed: 2026-09-25
---

# Phase 18 Plan 10: Fail-Closed IGDB DLC Hydration Summary

Automatic Steam DLC enrichment now requires a matching, named IGDB detail record, so a hydration failure cannot trigger Steam lookup or component persistence.

## Accomplishments

- Returned `None` when IGDB detail hydration is unavailable, raises, returns a non-detail, changes the IGDB ID, or loses the title.
- Preserved the existing successful hydrated IGDB candidate behavior.
- Added regression coverage proving the `None` socket gate skips both Steam lookup and component metadata persistence.

## Task Commits

1. `d42e1b80c` `test(18-10): specify fail-closed IGDB hydration`
2. `0a3a5f9bc` `fix(18-10): fail closed on IGDB DLC hydration`

## Verification

- `cd backend && uv run pytest --noconftest -q [seven focused regression nodes]` passed: 7 passed.
- `trunk fmt` and `trunk check` passed for all three changed files.
- The plan's normal pytest command remains blocked before test assertions because the configured MariaDB endpoint at `127.0.0.1:3306` is unavailable. A normal-conftest single-test run reproduced `mariadb.OperationalError: Can't connect to server on '127.0.0.1' (115)`.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- Confirmed all three modified implementation and regression-test files exist.
- Confirmed both task commits exist in Git history.
