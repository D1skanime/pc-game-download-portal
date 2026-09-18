---
phase: 17-browser-download-manager
plan: 12
subsystem: testing
tags: [pytest, vitest, browser, download, source-safety]

# Dependency graph
requires:
  - phase: 15-direct-resumable-transfer
    provides: strict direct-transfer range, validator, lifecycle, and source-verification contract
  - phase: 17-browser-download-manager
    provides: archive selection, transfer sessions, browser queue, and truthful UI states
provides:
  - deterministic final endpoint and source-safety regression coverage
  - explicit blocked Firefox, Chrome, and Edge capability matrix
  - isolated download evidence record that does not generalize unavailable infrastructure
affects: [phase-17-verification, browser-download-manager]

# Tech tracking
tech-stack:
  added: []
  patterns: [RED/GREEN TDD regression gates, explicit BLOCKED browser evidence]

key-files:
  created:
    - .planning/phases/17-browser-download-manager/17-BROWSER-MATRIX.md
    - .planning/phases/17-browser-download-manager/17-DOWNLOAD-EVIDENCE.md
  modified:
    - backend/tests/endpoints/test_download_manifests.py
    - backend/tests/endpoints/test_download_transfers.py
    - frontend/src/v2/sourceMutationControls.test.ts
    - frontend/src/v2/utils/downloadManifestPath.ts

key-decisions:
  - "Unavailable browsers and MariaDB are recorded as BLOCKED, never inferred as passing browser evidence."
  - "Windows drive-letter and UNC destinations are rejected before local traversal."

patterns-established:
  - "Browser evidence records browser/version, attempted case, source facts, and destination facts separately."
  - "Automated frontend passes do not substitute for unavailable browser or database observations."

requirements-completed: [UXDL-01, SAFE-01, TEST-01]

# Metrics
duration: 20min
completed: 2026-09-18
---

# Phase 17 Plan 12: Final Download Regression and Evidence Summary

**Final download protocol regressions are committed, while unavailable browser and MariaDB observations are preserved as explicit BLOCKED evidence.**

## Performance

- **Duration:** 20 min across checkpoint continuation
- **Tasks:** 2 (Task 1 automated regressions, Task 2 evidence artifacts)
- **Files modified:** 6 plan-owned files, plus this summary

## Accomplishments

- Added endpoint coverage for closed manifest lifecycle responses, foreign transfer-owner masking, forbidden ZIP/desktop/path fields, and maximum-u64 range values.
- Added a RED/GREEN regression proving browser download destinations reject Windows drive-letter, UNC, and control-character paths.
- Recorded Firefox, Chrome, and Edge as BLOCKED because binaries are unavailable, and MariaDB as BLOCKED before endpoint fixture setup.
- Listed every required large ISO, multi-file, update-only, DLC-only, optional/required selection, resume, source-change, expiry, and before/after source-evidence case without claiming a real transfer.

## Task Commits

1. **Task 1: Add final deterministic protocol and source-safety coverage** - `309daf818` (test), `4285a7a86` (fix)
2. **Task 2: Record isolated browser matrix and download evidence** - `429ddf2c5` (docs)

**Plan metadata:** `fc8bf0b97` (docs: record browser verification blocker)

## Files Created/Modified

- `.planning/phases/17-browser-download-manager/17-BROWSER-MATRIX.md` - browser capability matrix and blocked infrastructure observations.
- `.planning/phases/17-browser-download-manager/17-DOWNLOAD-EVIDENCE.md` - required isolated cases with explicit NOT RUN and source-fingerprint status.
- `backend/tests/endpoints/test_download_manifests.py` - lifecycle and large-u64 endpoint regressions.
- `backend/tests/endpoints/test_download_transfers.py` - owner masking and forbidden field regressions.
- `frontend/src/v2/sourceMutationControls.test.ts` - unsafe browser destination regression.
- `frontend/src/v2/utils/downloadManifestPath.ts` - Windows drive-letter and UNC rejection.

## Decisions Made

- Browser-dependent claims remain pending until a browser-capable environment and live test database are available.
- No real NAS, Team4s, deployment, restart, external source root, or desktop installer was accessed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rejected Windows absolute download destinations**

- **Found during:** Task 1 RED regression
- **Issue:** The POSIX destination validator accepted `C:/...` as relative segments, despite the safety contract requiring Windows roots and UNC paths to be rejected.
- **Fix:** Added drive-letter and UNC-prefix rejection while retaining control-character and separator checks.
- **Files modified:** `frontend/src/v2/utils/downloadManifestPath.ts`
- **Verification:** RED failed before the fix; focused Vitest passed 24/24 after the fix; Trunk passed.
- **Committed in:** `4285a7a86`

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** Required source-safety correction, no authority or infrastructure scope expansion.

## Issues Encountered

- Backend focused pytest was blocked before test execution because MariaDB was unavailable at `127.0.0.1:3306`.
- Firefox, Chrome/Chromium, and Edge binaries were unavailable in the Linux checkout, so manual browser evidence is explicitly blocked.

## User Setup Required

None - no external service configuration was changed or required for the committed code. Browser and MariaDB availability are prerequisites for later verification.

## Next Phase Readiness

Automated frontend/static evidence and deterministic test additions are ready. Phase 17 verification remains pending until browser matrix cases and database-backed endpoint tests can be run in an approved isolated environment.

## Known Stubs

None in the modified implementation or test files. The evidence artifacts intentionally contain `BLOCKED` and `NOT CAPTURED` records, not product stubs.

## Threat Flags

None. The only implementation change tightens an existing local destination validator; no new endpoint, authorization path, or source access surface was added.

---

_Phase: 17-browser-download-manager_
_Plan: 12_
_Completed: 2026-09-18_

## Self-Check: PASSED

- Browser matrix, download evidence, and summary files exist and are non-empty.
- Task commits `309daf818` and `4285a7a86` exist in Git history.
- No tracked files were deleted by the task commits.
