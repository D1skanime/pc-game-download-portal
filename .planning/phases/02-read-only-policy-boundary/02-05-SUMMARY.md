---
phase: 02-read-only-policy-boundary
plan: 05
subsystem: api-security
tags: [fastapi, storage-policy, read-only, tdd]
requires:
  - phase: 02-read-only-policy-boundary
    provides: trusted composition descriptors and operation-bound external reads
provides:
  - Bounded HTTP 403 translation for direct storage-policy denials
  - Pre-I/O external mutation guards on ROM, firmware, and platform routes
  - Explicit owned output grants for assets, resources, and patch temporaries
affects: [02-06, 02-08, endpoint-regression-tests]
tech-stack:
  added: []
  patterns: [trusted-provider route guards, bounded API denial translation]
key-files:
  created:
    - backend/endpoints/storage_policy.py
    - backend/tests/endpoints/test_storage_policy_denials.py
  modified:
    - backend/endpoints/roms/upload.py
    - backend/endpoints/roms/patch.py
    - backend/endpoints/roms/files.py
    - backend/endpoints/roms/__init__.py
    - backend/endpoints/roms/manual.py
    - backend/endpoints/roms/screenshot.py
    - backend/endpoints/roms/soundtrack.py
    - backend/endpoints/saves.py
    - backend/endpoints/states.py
    - backend/endpoints/collections.py
    - backend/endpoints/firmware.py
    - backend/endpoints/platform.py
key-decisions:
  - "Direct endpoint denials expose only code, operation, storage class, and logical storage identity."
  - "Owned asset, resource, and temporary outputs authorize independently from external inputs."
patterns-established:
  - "API routes authorize against composition-owned descriptors before database, request-body, temporary-file, or filesystem work."
requirements-completed: [SAFE-02, SAFE-03, SAFE-04, SAFE-06, TEST-03]
duration: 18min
completed: 2026-08-10
---

# Phase 2 Plan 5: Mutation Endpoint Policy Boundary Summary

**Trusted composition descriptors now gate real mutation endpoints before I/O with bounded 403 denials and independent owned-output grants**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-09T23:00:00Z
- **Completed:** 2026-08-09T23:18:00Z
- **Tasks:** 2 completed
- **Files modified:** 15

## Accomplishments

- Added one direct-API translator for the typed storage policy denial.
- Guarded the registered ROM, firmware, and platform mutation routes with the immutable external provider before I/O.
- Bound save, state, collection, and patch outputs to explicit owned descriptors.
- Added a 28-case real-route matrix covering operation, provider identity, non-forgeability, bounded fields, and pre-I/O behavior.

## Task Commits

1. **Task 1 RED** - `017f3de00`
2. **Task 1 GREEN** - `43d819b7a`
3. **Task 2 RED** - `a4656fe4f`
4. **Task 2 GREEN** - `3e4b5c329`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added a shared API denial translator**

- **Found during:** Task 1
- **Issue:** The typed domain denial had no bounded direct-API translation.
- **Fix:** Added an endpoint-layer translator returning exact HTTP 403 fields.
- **Files modified:** `backend/endpoints/storage_policy.py`
- **Verification:** Policy matrix passes 28 tests.
- **Committed in:** `43d819b7a`

## Issues Encountered

- Legacy external mutation-success tests were replaced with bounded pre-I/O denial regressions per the explicit plan contract.
- Host uv is unavailable. Verification used the existing development container and isolated `romm_test` database.

## Verification

- `test_storage_policy_denials.py`: 28 passed.
- Policy matrix plus `test_platform.py`: 40 passed.
- Python compilation passed for all modified endpoint modules.
- Commit hooks formatted and checked every staged file without bypass.
- Exact Task 1 combined regression: 42 passed, 7 superseded legacy delete cases skipped.

## Known Stubs

None.

## Threat Flags

None. All new surface is within the plan's declared API-bypass and disclosure threat model.

## Next Phase Readiness

Ready for Plan 02-06. The external mutation surface is bounded and governed.

## Self-Check: PASSED

- All created and modified implementation files exist.
- All four task commits exist.
- Focused policy and Task 2 verification pass.
- Both plan verification commands pass; commit hooks passed without bypass.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-10_
