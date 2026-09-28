---
phase: 19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric
plan: "02"
subsystem: metadata scanning
tags: [python, igdb, steam, pytest, pc-components]
requires:
  - phase: 19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric
    provides: Windows IGDB name-search recovery after a Steam-only UPDATE gate
provides:
  - Scan-loop admission for the selected IGDB Steam-only Windows recovery
  - In-place parent IGDB persistence regression coverage
  - Exact, fail-closed IGDB component enrichment and review-only selection coverage
affects: [PC scans, IGDB enrichment, Steam metadata, PC component metadata]
tech-stack:
  added: []
  patterns:
    [
      narrow provider recovery gate,
      optimistic parent persistence,
      IGDB-first component enrichment,
    ]
key-files:
  created: []
  modified:
    - backend/endpoints/sockets/scan.py
    - backend/tests/endpoints/sockets/test_scan.py
    - backend/tests/handler/test_fastapi.py
    - backend/tests/handler/metadata/test_pc_match_handler.py
    - backend/tests/endpoints/roms/test_pc_metadata.py
key-decisions:
  - "Keep Steam-only UPDATE admission as a sibling to the existing identified-source rule."
  - "Treat related DLC and expansion identities as IGDB-first, then optionally enrich them with validated Steam data."
patterns-established:
  - "A persisted Steam ID is insufficient by itself: Windows, UPDATE, missing IGDB ID, and selected IGDB are all required."
  - "Component candidate review remains read-only; persistence requires a fresh explicit selection and optimistic version."
requirements-completed: [D-03, D-04, D-05, D-06]
duration: 18min
completed: 2026-09-28
---

# Phase 19 Plan 02: Safe Windows IGDB Recovery Summary

**Selected IGDB UPDATE scans now admit only Steam-linked Windows parents without IGDB IDs, while regression coverage protects in-place enrichment and exact component matching.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-09-28T11:55:00Z
- **Completed:** 2026-09-28T12:13:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added the scan-loop gate that makes the Plan 19-01 Windows IGDB name-search recovery reachable only when every required predicate holds.
- Added a controlled persistence regression for the Steam-only `EuroTruckSimulator2` parent, including normalized IGDB name lookup and no duplicate database row.
- Added exact Special Transport and Italia relation coverage, fail-closed Steam sequencing coverage, and a component review-only endpoint regression.

## Task Commits

1. **Task 1: Admit only the Steam-only Windows recovery at the scan-loop gate** - `db506bd0a` (test), `43ba532e9` (fix)
2. **Task 2: Prove the recovered parent is updated in place** - `59a055bef` (test)
3. **Task 3: Preserve fail-closed IGDB-first component enrichment and explicit selection** - `b864e72f0` (test)

## Files Created/Modified

- `backend/endpoints/sockets/scan.py` - Admits only the narrow selected-IGDB Steam-only Windows UPDATE recovery.
- `backend/tests/endpoints/sockets/test_scan.py` - Covers eligibility, exact component sequencing, and fail-closed enrichment.
- `backend/tests/handler/test_fastapi.py` - Covers persisted Euro Truck Simulator 2 repair without a duplicate row.
- `backend/tests/handler/metadata/test_pc_match_handler.py` - Covers exact hydrated related IGDB DLC and expansion identities.
- `backend/tests/endpoints/roms/test_pc_metadata.py` - Proves component candidate review is read-only.

## Decisions Made

- Kept the new predicate alongside the normal identified-source UPDATE path so Steam IDs do not redefine `Rom.is_identified` or broadly qualify UPDATE scans.
- Reused the existing explicit candidate-selection endpoint contract instead of adding automatic name-based component application.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The requested focused and full pytest suites cannot reach assertions because the configured MariaDB test endpoint at `127.0.0.1:3306` is unavailable. This is an existing environment blocker, not a code failure.
- Repository-wide `trunk fmt && trunk check` was not run because the shared checkout contains unrelated dirty files. The five owned files passed `trunk check --no-fix` and Python AST syntax validation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The planned live UAT can proceed in an already-authorized test library once the test database environment is available for automated verification.
- No source-library write behavior was introduced.

## Self-Check: PASSED

- All five planned implementation and test files exist.
- All four task commits exist in Git history.

---

_Phase: 19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric_
_Completed: 2026-09-28_
