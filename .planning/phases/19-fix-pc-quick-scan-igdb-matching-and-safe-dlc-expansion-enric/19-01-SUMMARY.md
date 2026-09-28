---
phase: 19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric
plan: "01"
subsystem: metadata scanning
tags: [python, igdb, steam, pytest]
requires:
  - phase: 18-steam-metadata-integration-fur-pc-games-und-dlcs
    provides: Steam metadata IDs and compact-title matching boundary
provides:
  - Windows-only compact-title presentation for IGDB filename search
  - Steam-only Windows UPDATE recovery through the existing IGDB name lookup
affects: [PC scans, IGDB enrichment, DLC enrichment]
tech-stack:
  added: []
  patterns: [provider-boundary normalization, narrow metadata recovery gate]
key-files:
  created: []
  modified:
    - backend/handler/scan_handler.py
    - backend/tests/handler/test_scan_handler.py
key-decisions:
  - "Reuse Steam's compact-title boundary only at the Windows IGDB name-search fallback."
  - "Require every Steam-only UPDATE recovery predicate before opening IGDB name search."
patterns-established:
  - "Persisted IGDB IDs continue to refresh exclusively by ID."
requirements-completed: [D-01, D-02, D-03]
duration: 12min
completed: 2026-09-28
---

# Phase 19 Plan 01: Windows IGDB Lookup Recovery Summary

**Windows compact directory titles now reach IGDB as searchable spaced titles, while classic paths and persisted IGDB ID refreshes remain unchanged.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-28T11:42:00Z
- **Completed:** 2026-09-28T11:54:45Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Reused the established Steam compact-title boundary after tag removal only for Windows IGDB name searches.
- Added the narrow Steam-only Windows UPDATE recovery gate for a positive persisted Steam ID and missing IGDB ID.
- Added mocked scan-dispatch regressions for compact Windows names, spaced Windows names, classic raw names, persisted ID refreshes, and recovery-gate fields.

## Task Commits

1. **Task 1: Add the Windows IGDB lookup boundary and inner UPDATE recovery gate** - `30bcee2c0` (test), `78ade18e8` (fix), `03707a61a` (fix)
2. **Task 2: Lock the provider-dispatch boundary with regression tests** - `29c135a0c` (test)

## Files Created/Modified

- `backend/handler/scan_handler.py` - Normalizes Windows IGDB fallback titles and permits the narrow Steam-only UPDATE recovery path.
- `backend/tests/handler/test_scan_handler.py` - Exercises provider dispatch and every recovery condition without contacting IGDB.

## Decisions Made

- Reused `COMPACT_TITLE_BOUNDARY` from the Steam handler instead of defining another expression, so Windows title presentation remains consistent.
- Kept `get_rom_by_id` separate whenever a persisted IGDB ID exists, preserving the existing safer refresh behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Widened the recovery helper collection annotation**

- **Found during:** Task 2
- **Issue:** `list[str]` rejected the enum-backed metadata source list used by the regression tests because lists are invariant.
- **Fix:** Accepted a `Collection[str]`, matching the helper's membership-only use.
- **Files modified:** `backend/handler/scan_handler.py`
- **Verification:** Targeted Trunk check passed.
- **Committed in:** `03707a61a`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** No scope expansion. The correction keeps the recovery predicate type-safe for existing metadata-source callers.

## Issues Encountered

- The focused pytest command could not begin test execution because the configured MariaDB test endpoint at `127.0.0.1:3306` is unavailable. The direct mocked dispatch exercise, bytecode compilation, and targeted Trunk checks passed instead.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 19-02 can implement the matching scan-loop admission predicate so Steam-only Windows rows reach this inner recovery gate.

## Self-Check: PASSED

- Confirmed both implementation files exist and all task commits are present in Git history.

---

_Phase: 19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric_
_Completed: 2026-09-28_
