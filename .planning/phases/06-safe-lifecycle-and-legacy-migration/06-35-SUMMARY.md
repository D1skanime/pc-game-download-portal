---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 35
subsystem: api
tags: [fastapi, storage, migration, headers, pytest, tdd]
requires:
  - phase: 06-08
    provides: mapping-bound download reads and productive first-use authority
provides:
  - metadata-only HEAD validation through STAT without rollback consumption
  - productive GET first-use preservation through DOWNLOAD
  - bounded RFC 5987 Content-Disposition serialization from trusted database names
affects: [phase-06-verification, legacy-rollback, rom-download-api]
tech-stack:
  added: []
  patterns:
    [metadata-only mapped capability, escaped ASCII fallback, RFC 5987 filename]
key-files:
  created: []
  modified:
    - backend/endpoints/roms/files.py
    - backend/tests/endpoints/roms/test_files.py
    - backend/tests/integration/test_legacy_migration.py
key-decisions:
  - "HEAD opens a STAT capability and closes it after revision revalidation; only GET opens DOWNLOAD and consumes first-use."
  - "Content-Disposition rejects C0/C1 controls, escapes an ASCII fallback, and emits a UTF-8 RFC 5987 filename from the database name."
patterns-established:
  - "Metadata-only requests use non-productive capabilities while preserving the same mapping revision boundary."
  - "Response filenames cross the header boundary only through a private bounded serializer."
requirements-completed: [MIG-02, MIG-04]
duration: 18min
completed: 2026-08-21
---

# Phase 6 Plan 35: Metadata-Only HEAD and Safe Download Headers Summary

**HEAD now validates mapped file metadata without consuming rollback eligibility, while GET retains productive first-use marking and trusted database filenames serialize safely.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-21T10:38:55Z
- **Completed:** 2026-08-21T10:57:17Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Split the shared content route so HEAD opens `StorageOperation.STAT`, validates regular-file metadata and the exact mapping revision, closes the capability, and leaves migration first-use fields unchanged.
- Preserved GET ordering through the existing DOWNLOAD preflight, including first-use CAS before descriptor open, revision revalidation, range streaming, and close semantics.
- Added a private Content-Disposition builder that rejects C0/C1 controls with a static 400, escapes quote and backslash in the ASCII fallback, uses `download` when the fallback is empty, and emits `filename*` with UTF-8 percent encoding.
- Added real migration endpoint proofs for HEAD rollback eligibility, GET first-use exactly once, capability closure, range headers, and unchanged source manifests.

## TDD Gate Compliance

- **RED:** `46afa369b` ran the exact HEAD rollback selector, exited 1 with the expected behavioral failure, and showed HEAD had reached the productive download path. No collection, setup, database, or runner failure was accepted as RED.
- **GREEN:** `fc27ea5af` passed 34 focused HEAD, rollback, Content-Disposition, and content-route tests on a fresh isolated lifecycle.
- **Independent gate:** `p0635_pv` passed 52 affected endpoint/integration tests with 7 existing skips, then passed all 17 mapped-read context regressions. Exact cleanup and application DB continuity passed.

## Task Commits

1. **Task 1 RED: Specify non-productive HEAD and safe headers** - `46afa369b` (test)
2. **Task 2 GREEN: Separate HEAD metadata from downloads** - `fc27ea5af` (feat)

## Files Created/Modified

- `backend/endpoints/roms/files.py` - STAT-only HEAD preflight, preserved DOWNLOAD GET path, and bounded Content-Disposition serialization.
- `backend/tests/endpoints/roms/test_files.py` - Quote, backslash, Unicode, control, database-authority, and path-privacy header regressions.
- `backend/tests/integration/test_legacy_migration.py` - Real completed-migration HEAD/GET rollback eligibility and source-manifest proofs.

## Decisions Made

- Kept HEAD and GET on one route while branching before productive preflight, so visibility and trusted media/disposition selection remain shared but storage authority does not.
- Rejected controls before storage access and returned only a static error detail, so rejected filenames cannot leak through a header, path, or traceback.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used an owned disposable test runner**

- **Found during:** Task 1 RED lifecycle
- **Issue:** The plan names `romm-dev`, but it was stopped and project service restart was prohibited.
- **Fix:** Used a fresh nonce-owned disposable runner from the existing development image for each lifecycle, with the repository backend bind-mounted and exact runner cleanup proof.
- **Files modified:** None
- **Verification:** All valid lifecycles passed their expected RED or GREEN result; every runner was absent afterward and shared services were not restarted.
- **Committed in:** Not applicable

**2. [Rule 1 - Bug] Isolated header serialization from intentional path denial**

- **Found during:** Task 2 GREEN lifecycle
- **Issue:** The embedded-backslash header regression attempted a real mapped open, but storage path normalization correctly denies backslashes before a file can be opened, producing 409 instead of exercising header serialization.
- **Fix:** Kept the database filename and full endpoint response assertion, while isolating the STAT preflight in that test. This preserves path denial and tests the header boundary directly.
- **Files modified:** `backend/tests/endpoints/roms/test_files.py`
- **Verification:** The focused 34-test gate and independent 52-test affected suite passed.
- **Committed in:** `fc27ea5af`

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 3). No product scope expanded.

## Issues Encountered

- Early RED harness attempts failed on shell quoting and a missing local client fixture. Both were rejected as RED evidence, their owned resources were removed, and the valid RED was rerun from a fresh 128-bit lifecycle.

## Cleanup and Continuity

- Every valid lifecycle used a fresh validated 128-bit nonce database, principal, basetemp, and disposable runner with authoritative pre-mutation absence checks and independent ownership flags.
- Cleanup proved the exact database, principal, basetemp, and runner absent after each lifecycle; normal application `SELECT 1` passed before and after.
- Source manifests remained unchanged across HEAD and GET integration requests.
- No service was started or restarted, and nothing was deployed.
- All 28 pre-existing untracked status entries were preserved.

## Known Stubs

None.

## Threat Flags

None - the HEAD/GET authority split and filename header boundary were both registered in the plan threat model, with no new endpoint, schema, or trust boundary.

## User Setup Required

None.

## Next Phase Readiness

WR-01 and WR-03 are behaviorally closed. MIG-02 and MIG-04 now have direct endpoint and migration evidence, with no blockers remaining.

## Self-Check: PASSED

- All three modified files and commits `46afa369b` then `fc27ea5af` exist.
- RED and GREEN ordering, full affected tests, mapped-read regressions, commit-hook scoped Trunk checks, `git diff --check`, source manifests, exact cleanup, and normal DB continuity passed.
- The summary exists at the required phase path and the tracked worktree was clean before this artifact was written.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-21_
