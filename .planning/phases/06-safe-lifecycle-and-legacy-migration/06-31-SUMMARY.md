---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 31
subsystem: owned-storage-integrity
tags: [filesystem, descriptors, atomic-write, tdd, storage-policy]
requires:
  - phase: 02-read-only-policy-boundary
    provides: descriptor-relative operation-bound owned storage capabilities
  - phase: 06-23
    provides: final Phase 6 review evidence identifying inherited short-write corruption
provides:
  - complete retrying writes for owned create and replace capabilities
  - failure-atomic create cleanup and replace preservation
  - deterministic short-write, interruption, invalid-progress, and cleanup regressions
affects: [phase6-final-verification, owned-asset-writes, export-writes]
tech-stack:
  added: []
  patterns:
    - memoryview-backed write-all loop with bounded progress validation
    - publish replacement content only after complete write and fsync
key-files:
  created: []
  modified:
    - backend/handler/filesystem/storage_access.py
    - backend/tests/handler/filesystem/test_storage_access.py
key-decisions:
  - "Owned byte writes retry only InterruptedError and reject zero, negative, or over-reported progress."
  - "Failed create removes only its exclusively created descriptor-relative destination, while replace preserves the prior target until full write and fsync."
patterns-established:
  - "Owned write completion: consume the full memoryview before a mutation reports success."
  - "Failure-atomic replace: keep the prior destination visible until an fsynced temporary file is atomically installed."
requirements-completed: [CAT-02]
duration: 10min
completed: 2026-08-20
---

# Phase 6 Plan 31: Failure-Atomic Owned Writes Summary

**Descriptor-relative owned creates and replacements now persist complete payloads or leave no partial publication.**

## Performance

- **Duration:** 10 minutes 40 seconds
- **Started:** 2026-08-20T13:00:39Z
- **Completed:** 2026-08-20T13:11:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added one internal write-all primitive that advances a memoryview through short writes, retries interruption, and rejects zero, negative, or over-reported progress.
- Made failed creates close their descriptor and remove only the exclusively created destination through the existing descriptor-relative parent authority.
- Kept replacement targets byte-for-byte unchanged until their temporary sibling is fully written, fsynced, closed, and atomically installed.
- Added deterministic real-capability regressions for short writes, interruption, invalid progress, partial failure, exact cleanup, empty content, and descriptor closure.
- Preserved the external deny-by-default operation policy across the broader policy and inventory gate.

## TDD Evidence

- **RED:** The exact named regression exited with Pytest status 1 and showed b"co" installed instead of b"complete-create" after the first short write.
- **GREEN:** The complete storage access module passed 47 tests after both capability methods used _write_all.
- **Broader regression:** Access, external policy, closed inventory, and task policy suites passed 326 tests.
- **REFACTOR:** No separate refactor was needed. Scoped Trunk formatting retained the minimal helper and reported no issues.

## Task Commits

1. **Task 1 RED: Specify complete and failure-atomic writes** - 4fc491fae (test)
2. **Task 2 GREEN: Make owned writes complete or failure-atomic** - b708297f8 (fix)

## Files Created/Modified

- backend/handler/filesystem/storage_access.py - Provides _write_all, failed-create cleanup, and complete pre-replace writes.
- backend/tests/handler/filesystem/test_storage_access.py - Proves byte-exact completion, bounded failure, cleanup, preservation, and descriptor closure.

## Decisions Made

- Retry only InterruptedError; every other write error remains terminal and is translated through the existing bounded storage error contract.
- Treat every non-positive or over-reported write count as invalid terminal progress rather than risking an infinite loop or incorrect buffer advance.
- Keep create and replace cleanup descriptor-relative with no raw-path fallback and no external source authority.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected scoped test typing discovered by the final Trunk gate**

- **Found during:** Task 2 static verification
- **Issue:** Two capability method calls used the wrong narrow mypy ignore code after the RED test commit.
- **Fix:** Changed only those ignores to the exact union-attr code reported by mypy.
- **Files modified:** backend/tests/handler/filesystem/test_storage_access.py
- **Verification:** Scoped Trunk checked both plan files with no issues.
- **Committed in:** b708297f8

---

**Total deviations:** 1 auto-fixed blocking issue.
**Impact on plan:** The correction was test-only typing metadata and did not change runtime behavior or scope.

## Issues Encountered

- The first RED command lacked a test-only ROMM_AUTH_SECRET_KEY and exited with infrastructure status 4. That run was rejected; the repeated isolated run produced the required behavioral status 1 and exact named failure.
- Trunk was not on the remote shell PATH. The repository-configured cached Trunk 1.25.0 binary used by the installed hooks ran the prescribed scoped formatting and checks.
- Pytest emitted the inherited unknown env option warning with pytest-env disabled and the inherited Alembic path-separator deprecation warning. Neither affected the selected test behavior.

## Verification

- Exact RED gate: status 1 with only test_owned_create_retries_short_write_to_completion failing on truncated content.
- Storage access module: 47 passed.
- Combined storage access, external policy, closed inventory, and task policy gate: 326 passed.
- Scoped Trunk: 2 files checked, no issues.
- git diff --check: passed.
- Acceptance audit: one os.write remains only inside _write_all; both owned write methods call it.
- Commit hooks: passed normally for both task commits.
- TDD sequence: 4fc491fae precedes b708297f8.

## Known Stubs

None.

## Threat Flags

None. The plan threat model covers the owned descriptor write boundary, temporary publication, untrusted kernel progress, cleanup, and bounded errors. No endpoint, authentication path, schema, dependency, or external source authority was introduced.

## User Setup Required

None.

## Cleanup

- Every test artifact was confined to Pytest tmp_path.
- No task database, database user, container, volume, service restart, deployment, or repository temporary file was created.
- All 28 baseline untracked paths remain present and untouched.

## Next Phase Readiness

Plan 06-32 can re-run the complete Phase 6 integration and adversarial verification with the inherited owned short-write warning closed.

## Self-Check: PASSED

The summary path, both modified files, and task commits 4fc491fae and b708297f8 exist. All plan verification and acceptance gates passed, no tracked deletion occurred, and the 28 baseline untracked paths were preserved.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-20_
