---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
plan: 07
subsystem: backend metadata scanning
tags: [steam, scan, pc-metadata, pytest, trunk]
requires:
  - phase: 18-04
    provides: Shared guarded Steam metadata normalizer
provides:
  - Stored-App-ID-first Steam resolution for automatic PC scans
  - Platform-gated Steam search with classic-ROM isolation
  - Non-fatal Steam provider behavior alongside existing scan providers
affects: [automatic scans, PC metadata, Steam integration]
tech-stack:
  added: []
  patterns:
    [stored-identity-first provider resolution, isolated provider degradation]
key-files:
  created: [backend/tests/handler/test_scan_handler.py]
  modified:
    - backend/handler/scan_handler.py
    - backend/tests/handler/metadata/test_steam_merge.py
key-decisions:
  - "Automatic Steam scans resolve a persisted App ID directly and reject a mismatched returned ID."
  - "Steam name search is restricted to win, linux, and mac; dos, win3x, and win9x accept only explicit persisted IDs."
patterns-established:
  - "Provider-specific automatic scan logic stays inside an isolated resolver and returns an empty mapping on remote failure."
requirements-completed: [STEAM-02, STEAM-04, STEAM-05]
duration: 15min
completed: 2026-09-25
---

# Phase 18 Plan 07: Stored-ID-First Steam Scan Summary

**Automatic Steam scanning now refreshes the persisted App ID directly, searches only eligible modern PC platforms, and degrades safely without affecting other metadata providers.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-25T13:26:00Z
- **Completed:** 2026-09-25T13:41:29Z
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- Added a PC-only Steam scan resolver that refreshes persisted IDs before any filename-based lookup.
- Restricted Steam name searches to win, linux, and mac, while allowing only direct stored-ID resolution for dos, win3x, and win9x.
- Added regression coverage for direct lookup identity, call counts, excluded and classic platforms, malformed results, and timeout isolation.

## Task Commits

1. **Task 1: Characterize stored-ID, platform eligibility, and provider-failure scan boundaries** - `ed0ed9b04` (test)
2. **Task 2: Implement the narrow automatic Steam scan resolver** - `6518c57a9` (feat)
3. **Task 2 auto-fix: retain persisted Steam scan identity** - `52038a145` (fix)

## Files Created/Modified

- `backend/handler/scan_handler.py` - resolves Steam only for supported PC scan paths and applies the shared normalizer.
- `backend/tests/handler/test_scan_handler.py` - covers stored-ID, eligibility, classic-ROM, and failure boundaries.
- `backend/tests/handler/metadata/test_steam_merge.py` - records malformed-data preservation and deterministic provenance ordering.

## Decisions Made

- A direct Storefront response must return the exact persisted App ID, otherwise it is discarded.
- Steam errors are converted to an empty result inside the Steam resolver, preserving concurrent IGDB, Moby, and LaunchBox processing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rejected mismatched direct Steam results**

- **Found during:** Task 2
- **Issue:** A malformed direct provider response could carry an App ID different from the stored identity.
- **Fix:** Discarded a direct result unless its `steam_id` exactly equals the persisted ID.
- **Files modified:** `backend/handler/scan_handler.py`, `backend/tests/handler/test_scan_handler.py`
- **Verification:** Focused resolver tests pass, including the mismatched-ID regression.
- **Committed in:** `52038a145`

---

**Total deviations:** 1 auto-fixed bug.
**Impact on plan:** Correctness hardening only, with no scope expansion.

## Issues Encountered

- The regular focused Pytest command cannot initialize because this host has no MariaDB listener at `127.0.0.1:3306`. The failure occurs in the session database fixture before test assertions. The same suites passed with `--noconftest` (14 passed), and Trunk passed for all changed files.

## Known Stubs

None.

## Next Phase Readiness

- Automatic scans use the Plan 18-04 normalizer without adding Steam to classic provider dispatch.
- The local database environment must be available for the normal integration Pytest invocation.

---

_Phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs_
_Completed: 2026-09-25_

## Self-Check: PASSED

- All planned code, test, and summary files exist.
- Task commits `ed0ed9b04`, `6518c57a9`, and `52038a145` exist in Git history.
