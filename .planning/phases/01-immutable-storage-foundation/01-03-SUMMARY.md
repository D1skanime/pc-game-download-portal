---
phase: 01-immutable-storage-foundation
plan: 03
subsystem: filesystem
tags: [pathlib, lstat, symlink-security, immutable-storage, health]
requires:
  - phase: 01-immutable-storage-foundation
    provides: Immutable StorageRoot model and bounded path/error contracts from plans 01-01 and 01-02
provides:
  - Metadata-only bounded root health observation
  - Canonical point-in-time directory resolution inside approved roots
  - Fail-closed configured-root and component symlink rejection
affects: [01-04, 01-05, storage-policy, platform-mapping, filesystem-consumers]
tech-stack:
  added: []
  patterns: [lstat component walk, strict canonical containment, permission observation without write probes]
key-files:
  created: []
  modified:
    - backend/handler/filesystem/storage_resolver.py
    - backend/tests/handler/filesystem/test_storage_resolver.py
key-decisions:
  - "Root health persists bounded reachable, readable, non-writable, timestamp, and safe-error observations without filesystem mutation."
  - "Mapping resolution accepts only non-empty logical paths while the explicit internal root resolver owns empty-root behavior."
patterns-established:
  - "Configured roots and every target component are rejected when lstat identifies a symlink, before strict canonical resolution."
  - "Writable root observations fail safety checks and never authorize mutation."
requirements-completed: [ROOT-03, PATH-02, PATH-03, PATH-05]
duration: 4min
completed: 2026-08-04
---

# Phase 1 Plan 3: Metadata-Only Health and Canonical Resolution Summary

**Bounded root health and strict canonical directory resolution with complete symlink rejection and no source-tree mutation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-04T21:07:11Z
- **Completed:** 2026-08-04T21:10:31Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Records reachable, readable, non-writable, checked-at, and safe-error health fields directly on a storage root using metadata and permission observation only.
- Resolves active external_read_only roots and existing readable directories with strict canonical containment.
- Rejects writable roots, configured-root symlinks, every target-component symlink, missing targets, files, unreadable targets, and sibling-prefix escapes with bounded errors.
- Proves immutable behavior with recursive before/after manifests and mutation tripwires.

## Task Commits

1. **Task 1 RED: Immutable resolution contract tests** - bb57a4839 (test)
2. **Task 2 GREEN: Canonical health and resolution** - 49ec795a5 (feat)

## Files Created/Modified

- backend/handler/filesystem/storage_resolver.py - Metadata-only root health, internal root resolution, component lstat walk, strict canonical containment, and target validation.
- backend/tests/handler/filesystem/test_storage_resolver.py - Real-tree health, immutability, permission, target, containment, and symlink coverage.

## Decisions Made

- Health returns and persists bounded observation fields without raising for ordinary unavailable or unsafe root states.
- Internal root resolution has a dedicated entry point; mapping directory resolution always requires a non-empty normalized relative path.
- Root and target readability use R_OK plus X_OK; root writability uses W_OK as an unsafe observation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected sibling-prefix fixture setup**
- **Found during:** Task 2 (canonical containment verification)
- **Issue:** The fixture omitted the lexical target, so resolution stopped at missing-target validation before exercising containment.
- **Fix:** Created the target directory before substituting the canonical sibling result.
- **Files modified:** backend/tests/handler/filesystem/test_storage_resolver.py
- **Verification:** Full resolver suite passes and the test raises StorageEscapeError.
- **Committed in:** 49ec795a5

---

**Total deviations:** 1 auto-fixed bug
**Impact on plan:** The correction ensures the planned sibling-prefix containment branch is directly proven without expanding scope.

## Issues Encountered

- The host lacks uv, and Ruff/Trunk are unavailable in the development image. Tests and Python compilation ran inside the existing RomM development container without restarting services.
- The isolated romm_test database had an inconsistent pre-existing Alembic stamp with missing 0108 tables. Recreating only that test database allowed the normal migration fixture to build the expected schema. No application database or service was changed.

## User Setup Required

None. No external service configuration is required.

## Known Stubs

None.

## Next Phase Readiness

- Plan 01-04 can use the canonical resolver for atomic storage-root registration and mapping persistence.
- Point-in-time resolution remains intentionally bounded; descriptor-relative no-follow enforcement belongs to Phase 2 consumers.

## Self-Check: PASSED

- Both modified files exist.
- Task commits bb57a4839 and 49ec795a5 exist.
- Resolver and storage-model verification passes: 54 tests.

---
*Phase: 01-immutable-storage-foundation*
*Completed: 2026-08-04*
