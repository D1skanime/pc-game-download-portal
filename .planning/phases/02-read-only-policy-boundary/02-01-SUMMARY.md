---
phase: 02-read-only-policy-boundary
plan: 01
subsystem: storage-policy
tags: [python, authorization, immutable-storage, tdd]
requires:
  - phase: 01-immutable-storage-foundation
    provides: Trusted external storage root identity and immutable mode
provides:
  - Closed deny-by-default storage operation policy
  - Immutable trusted external and RomM-owned descriptors
  - Bounded typed policy denial and exhaustive mutation matrix
affects: [02-02, 02-03, external-access, owned-storage]
tech-stack:
  added: []
  patterns:
    [
      pure authorization before I/O,
      explicit owned classification,
      independent grants,
    ]
key-files:
  created:
    [
      backend/handler/filesystem/storage_policy.py,
      backend/tests/handler/filesystem/test_storage_policy.py,
    ]
  modified: [backend/exceptions/storage_exceptions.py]
key-decisions:
  - "External authorization permits only eight explicitly enumerated read operations and rejects non-enum inputs without coercion."
  - "Trusted descriptors retain only root or mapping identity and explicit owned kind."
patterns-established:
  - "Policy grants bind exactly one StorageOperation to one immutable trusted descriptor."
  - "External reads and owned writes are authorized independently."
requirements-completed: [ROOT-05, SAFE-01, SAFE-02, TEST-03]
duration: 7min
completed: 2026-08-09
---

# Phase 2 Plan 1: Closed Storage Policy Kernel Summary

**Pure deny-by-default authorization with eight external read capabilities, explicit RomM-owned destinations, and 261 pre-I/O matrix tests**

## Performance

- **Duration:** 7 min
- **Started:** 2026-08-09T22:05:42Z
- **Completed:** 2026-08-09T22:12:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added the complete Phase 2 `StorageOperation` enum and exact external allowlist.
- Added composition-created immutable external and owned descriptors with lexical root-disjointness validation.
- Added one bounded `StoragePolicyDenied` contract that omits raw paths and filesystem details.
- Proved every mutation and unknown operation denies before filesystem observation or mutation primitives can run.

## Task Commits

1. **Task 02-01-01: Specify the closed authorization matrix** - `69f50cac8` (test)
2. **Task 02-01-02: Implement policy, ownership descriptors, and bounded denial** - `945365317` (feat)

## Files Created/Modified

- `backend/handler/filesystem/storage_policy.py` - Closed operation model, trusted descriptors, pure policy grants, and root-disjointness validation.
- `backend/exceptions/storage_exceptions.py` - Stable bounded storage policy denial.
- `backend/tests/handler/filesystem/test_storage_policy.py` - Exhaustive allow, deny, unknown, ownership, non-forgeability, and pre-I/O matrix.

## Decisions Made

- Unknown operation values remain unknown and deny, rather than being coerced into enum members.
- Owned authorization requires a closed `OwnedStorageKind`; being outside an external root never implies ownership.
- Grants carry an operation and descriptor identity only, never a reusable path.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The host has no `uv` binary, so verification ran inside the existing `romm-dev` container against the bind-mounted canonical backend. The pure policy suite overrides shared database fixtures and performs no database or filesystem access.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Next Phase Readiness

- Plan 02-02 can bind descriptor-relative filesystem access to the operation grants.
- Plan 02-03 can own composition providers and startup root-overlap validation.

## Self-Check: PASSED

- All three implementation and test files exist.
- Commits `69f50cac8` and `945365317` exist in repository history.
- The focused policy suite passes with 261 tests.
- The TDD RED commit precedes the GREEN implementation commit.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-09_
