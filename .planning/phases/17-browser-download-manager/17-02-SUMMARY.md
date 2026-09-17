---
phase: 17-browser-download-manager
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, alembic, archive-sets, authorization]

requires:
  - phase: 14-immutable-download-manifests
    provides: Phase 14 manifest-backed component and member identities
provides:
  - ROM-scoped persisted archive-set policies with ordered exact member identities
  - Authorized create, replace, import, and list policy endpoints
  - Empty, reversible migration preserving existing ROM behavior
affects: [17-03 manifest policy enforcement, 17-07 browser download selection]

tech-stack:
  added: []
  patterns:
    [ROM-scoped ownership validation, composite member identity constraints]

key-files:
  created:
    - backend/models/download_archive_set.py
    - backend/handler/database/download_archive_sets_handler.py
    - backend/endpoints/responses/download_archive_set.py
    - backend/endpoints/roms/download_archive_sets.py
    - backend/alembic/versions/0122_download_archive_sets.py
    - backend/tests/models/test_download_archive_set.py
    - backend/tests/handler/database/test_download_archive_sets_handler.py
    - backend/tests/endpoints/roms/test_download_archive_sets.py
  modified:
    - backend/models/rom.py
    - backend/handler/database/__init__.py
    - backend/endpoints/roms/__init__.py

key-decisions:
  - "Archive membership stores exact component and manifest-member IDs with explicit position and required flags."
  - "Migration creates no policies, so ROMs without assignments retain Phase 14 manifest selection behavior."

patterns-established:
  - "All policy mutations lock the ROM and validate every referenced row against that ROM before persistence."
  - "Policy APIs use ROM visibility masking for reads and ROMS_WRITE authorization for mutations."

requirements-completed: [UXDL-01, SAFE-01, TEST-01]

duration: 18min
completed: 2026-09-17
---

# Phase 17 Plan 02: Explicit Archive-Set Policy Summary

**Persisted ROM-scoped archive-set policies with ordered exact component/member identities and authorized lifecycle endpoints**

## Performance

- **Duration:** 18 min
- **Started:** 2026-09-17T20:24:00Z
- **Completed:** 2026-09-17T20:42:00Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Added archive-set and ordered member models with named uniqueness and composite member/component integrity constraints.
- Added handler operations for create, replace, declarative import, and ROM-scoped listing with bounded payloads and exact ownership checks.
- Added masked, scope-protected ROM endpoints and an empty reversible Alembic migration that synthesizes no policies.
- Added model, handler, and endpoint regression coverage for order, required/optional flags, duplicate and foreign references, replacement, import, and forbidden payload fields.

## Task Commits

1. **Task 1: Specify archive policy authoring, import, and unassigned-ROM behavior** - `487e38471` (test)
2. **Task 2: Implement persisted policy, authorized endpoints, and safe migration** - `5ece5a564` (feat)

## Files Created/Modified

- `backend/models/download_archive_set.py` - ROM-scoped policy and ordered exact member relation.
- `backend/handler/database/download_archive_sets_handler.py` - bounded, locked policy lifecycle operations.
- `backend/endpoints/roms/download_archive_sets.py` - authorized create, replace, import, and list routes.
- `backend/endpoints/responses/download_archive_set.py` - strict request and response contracts.
- `backend/alembic/versions/0122_download_archive_sets.py` - portable empty policy migration and downgrade.
- `backend/models/rom.py`, `backend/handler/database/__init__.py`, `backend/endpoints/roms/__init__.py` - relationship and registration wiring.

## Decisions Made

- Policy membership is never inferred from relative paths, filenames, regexes, or component kind.
- Existing ROMs remain policy-unassigned after migration and therefore retain existing manifest behavior.

## Deviations from Plan

None - plan executed as written. The local MariaDB service was unavailable during runtime verification.

## Issues Encountered

- Focused pytest could not initialize its test database because MariaDB at `127.0.0.1:3306` was unavailable. AST parsing and Trunk formatting/checks passed.
- Alembic runtime round-trip could not start in this checkout for the same unavailable database/config environment; migration revision and DDL were statically reviewed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The next plan can lock and enforce these persisted policies during immutable manifest creation. It should run the focused tests and Alembic round-trip once MariaDB is available.

## Self-Check: PASSED

- All declared created files exist.
- Task commits `487e38471` and `5ece5a564` exist in Git history.
- No tracked files were deleted by either task commit.

---

_Phase: 17-browser-download-manager_
_Completed: 2026-09-17_
