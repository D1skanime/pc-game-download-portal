---
phase: 17-browser-download-manager
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, manifests, archive-sets, authorization]

requires:
  - phase: 17-browser-download-manager
    provides: Persisted ROM-scoped archive-set policies with ordered required and optional exact member identities
provides:
  - Server-validated archive-set selection during immutable manifest creation
  - Individual optional member exclusion with required-member completeness enforcement
  - Backwards-compatible Phase 14 component selection for unassigned ROMs
affects: [17-07 browser download selection, 17-12 browser evidence]

tech-stack:
  added: []
  patterns:
    [
      locked policy and source-member validation before filesystem evidence capture,
    ]

key-files:
  created:
    - .planning/phases/17-browser-download-manager/17-03-SUMMARY.md
  modified:
    - backend/handler/database/download_manifests_handler.py
    - backend/endpoints/responses/download_manifest.py
    - backend/endpoints/download_manifests.py
    - backend/tests/handler/database/test_download_manifests_handler.py
    - backend/tests/endpoints/test_download_manifests.py

key-decisions:
  - "An explicit archive_set_id selects the persisted policy, while selected_member_ids must contain every required member and only policy members."
  - "Requests that omit policy fields retain the existing component selection path, so ROMs without policies remain Phase 14 compatible."

patterns-established:
  - "Lock ROM, archive-set rows, selected components, and source members before capturing filesystem evidence."
  - "Mask policy validation failures through the existing bounded manifest-not-found endpoint response."

requirements-completed: [UXDL-01, SAFE-01, TEST-01]

duration: 19min
completed: 2026-09-17
---

# Phase 17 Plan 03: Policy-Aware Immutable Manifest Summary

**Immutable download manifests now enforce persisted required-member policy while allowing explicitly selected optional members without exposing source paths.**

## Performance

- **Duration:** 19 min
- **Started:** 2026-09-17T20:20:00Z
- **Completed:** 2026-09-17T20:39:48Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added typed `archive_set_id` and `selected_member_ids` manifest request fields with duplicate and bounded selection validation.
- Locked and checked ROM ownership, archive-set membership, component eligibility, exact source-member identity, required-member completeness, and optional exclusions before evidence capture.
- Preserved the existing Phase 14 whole-game and component-selection branch for ROMs without an explicit policy, with masked endpoint failures and no source-path disclosure.
- Added handler and endpoint regressions covering complete required sets, omitted optional files, invalid or foreign members, and untouched capture on rejected selections.

## Task Commits

Each task was committed atomically:

1. **Task 1: Specify required-set completion and optional-file exclusion** - `794eabdab` (test)
2. **Task 2: Enforce exact persisted selection before evidence capture** - `ca5f91e8e` (feat)

## Files Created/Modified

- `backend/handler/database/download_manifests_handler.py` - validates and locks persisted policy selections before creating immutable evidence.
- `backend/endpoints/responses/download_manifest.py` - adds bounded typed policy and selected-member request fields.
- `backend/endpoints/download_manifests.py` - passes policy selections into the existing manifest authority.
- `backend/tests/handler/database/test_download_manifests_handler.py` - covers required and optional policy behavior at the handler seam.
- `backend/tests/endpoints/test_download_manifests.py` - covers safe API serialization and masked policy rejection.

## Decisions Made

- Policy selection is explicit and ROM-scoped through `archive_set_id`; the server derives allowed exact members from persisted rows and never infers dependencies from names, paths, or kinds.
- A selected policy cannot be mixed with legacy `component_ids`, preventing ambiguous selection semantics.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Focused pytest could not initialize its fixtures because MariaDB was unavailable at `127.0.0.1:3306`; all 39 collected tests stopped at database setup. This is an environment blocker also recorded by Plan 17-02.
- Trunk formatting and checks passed for all five changed files. AST parsing passed for all changed Python files.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The browser selection work can send an explicit archive-set ID and exact selected member IDs to the existing manifest route. Focused runtime and direct-transfer regressions should be rerun once the MariaDB test service is available.

## Self-Check: PASSED

- All five declared implementation/test files and this summary exist.
- Task commits `794eabdab` and `ca5f91e8e` exist in Git history.
- No tracked files were deleted by either task commit.

---

_Phase: 17-browser-download-manager_
_Completed: 2026-09-17_
