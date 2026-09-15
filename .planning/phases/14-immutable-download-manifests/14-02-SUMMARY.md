---
phase: 14-immutable-download-manifests
plan: "02"
subsystem: database
tags: [sqlalchemy, filesystem-capabilities, sha256, immutable-manifest]
requires:
  - phase: 14-immutable-download-manifests
    provides: path-free immutable manifest ORM aggregate
provides:
  - trusted full source-evidence capture and cheap revalidation seams
  - owner-scoped atomic manifest selection and lifecycle service
affects: [14-03-manifest-api, 15-direct-download-delivery]
tech-stack:
  added: []
  patterns:
    [
      HASH-only evidence capture,
      STAT-only ordinary revalidation,
      locked aggregate construction,
    ]
key-files:
  created:
    - backend/handler/database/download_manifests_handler.py
    - backend/tests/handler/database/test_download_manifests_handler.py
  modified:
    - backend/handler/filesystem/roms_handler.py
    - backend/handler/database/__init__.py
    - backend/config/__init__.py
    - backend/models/download_manifest.py
    - backend/tests/handler/filesystem/test_roms_handler.py
key-decisions:
  - "Creation hashes through the constrained HASH capability, while ordinary GET performs STAT-only light checks."
  - "Whole-game selection includes only manifest-backed base, update, DLC, and extra components."
requirements-completed: [DLMT-01, DLMT-02, DLMT-03]
duration: 24min
completed: 2026-09-15
---

# Phase 14 Plan 02: Trusted Manifest Lifecycle Summary

**Atomic owner-scoped manifests now capture verified SHA-256 evidence and strong path-free snapshots, then use only cheap indicators during ordinary retrieval.**

## Performance

- **Duration:** 24 min
- **Completed:** 2026-09-15T21:24:18Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- Added HASH-capability-only capture with verified SHA-256, 64-bit sizes, strong versioned snapshots, and bounded source failures.
- Added STAT-only light revalidation that reports detected source changes without presenting a matching check as content proof.
- Added locked selection, owner scoping, 24-hour expiry, revocation, and source-change lifecycle transitions.

## Task Commits

1. **Task 1, RED:** `20d674a20` (`test`)
2. **Task 1, GREEN:** `64030555c` (`feat`)
3. **Task 2, RED:** `11a704888` (`test`)
4. **Task 2, GREEN:** `0d1f10a8f` (`feat`)

## Verification

- `uv run pytest tests/handler/database/test_download_manifests_handler.py tests/handler/filesystem/test_roms_handler.py -k "download_manifest or download_manifest_member" -vv`, 7 passed.
- Scoped `trunk fmt` and `trunk check` passed for every plan-owned backend file.
- The requested full `trunk check` was started from `backend/`; it did not finish within the executor's 30-second command window and emitted no findings before timeout.

## Decisions Made

- Strong snapshots use the fixed NUL-separated `romm-manifest-v1` canonical record of member ID, destination, exact size, and verified digest, then SHA-256 and strong ETag quoting.
- Phase 15 remains responsible for a fresh strong pre-transfer check; Phase 14 never invokes the full hash helper during normal GET.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected generated manifest UUIDs**

- **Found during:** Task 2
- **Issue:** The existing ORM default stringified `uuid.uuid4` rather than calling it, causing every subsequent manifest creation to collide.
- **Fix:** Call `uuid.uuid4()` in the default factory.
- **Files modified:** `backend/models/download_manifest.py`
- **Verification:** Lifecycle tests create multiple manifests successfully.
- **Committed in:** `0d1f10a8f`

**Total deviations:** 1 auto-fixed (Rule 1 bug).

## Known Stubs

None.

## Next Phase Readiness

Phase 14-03 can expose the service through an API without accepting source paths. Phase 15 must retain fresh strong per-member verification before transfer.

## Self-Check: PASSED

- All declared implementation and test files exist.
- All four task commits are present in Git history.
