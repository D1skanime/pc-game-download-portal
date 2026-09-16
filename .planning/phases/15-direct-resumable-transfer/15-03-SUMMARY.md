---
phase: 15-direct-resumable-transfer
plan: 03
subsystem: api
tags: [fastapi, streaming, range, etag, authorization]
requires:
  - phase: 15-direct-resumable-transfer
    provides: Owner-scoped transfer identity and hash-verified descriptor lease
provides:
  - Protected direct original-member streaming through opaque manifest URLs
  - Exact strong-validator and single-range HTTP semantics
  - Source-change, lifecycle, visibility, and disclosure regression coverage
affects: [16-rust-download-engine, direct-download-client]
tech-stack:
  added: []
  patterns:
    - Owner and visibility checks precede validator parsing and source verification.
    - A verified lease is closed by both its stream iterator and response background cleanup.
key-files:
  created: []
  modified:
    - backend/endpoints/download_manifests.py
    - backend/tests/endpoints/test_download_manifests.py
key-decisions:
  - "Range resumes require one byte-for-byte persisted quoted strong validator; wildcard, weak, list, missing, and stale values fail with a bounded 412."
  - "The endpoint emits no archive or path data and treats a non-ready or inconsistent lease as source_changed before streaming."
patterns-established:
  - "Direct transfer routes resolve opaque persisted identity, mask visibility, validate request preconditions, then stream only a verified descriptor lease."
requirements-completed: [XFER-01, XFER-02, XFER-03, XFER-04]
duration: 7min
completed: 2026-09-16
---

# Phase 15 Plan 03: Protected Direct Range Transfer Summary

**The opaque manifest-member URL now streams one hash-verified original file with strict 200, 206, 412, and 416 behavior, without ZIP packaging or source-path disclosure.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-09-16T21:15:00Z
- **Completed:** 2026-09-16T21:22:12Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added an unconditional `ROMS_READ` protected endpoint at the Phase 14 opaque member URL.
- Enforced owner/member lookup, current ROM visibility, lifecycle state, exact strong `If-Match`, and fresh verified lease checks before source bytes stream.
- Added strict ASCII u64 single-range parsing with exact 200/206 headers and deterministic 416 `Content-Range` responses.
- Covered direct original bytes, 5/80/120 GiB offsets, malformed ranges, validator rejection, source changes, and hidden or foreign access.

## Task Commits

1. **Task 1: Specify and implement protected strict-range file delivery** - `fd57e7c2a` (test), `d8faf0c08` (feat)

## Files Created/Modified

- `backend/endpoints/download_manifests.py` - Adds protected, snapshot-bound direct member streaming and strict range construction.
- `backend/tests/endpoints/test_download_manifests.py` - Adds transfer, validator, large-offset, source-change, and masking regressions.

## Decisions Made

- The binary stream has no frontend consumer before Phase 16 and does not introduce a response schema, so no generated frontend API types were changed.
- Invalid resume preconditions are rejected before acquiring a transfer lease; a verified source mismatch remains a distinct `source_changed` 412 result.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used Starlette's single background-task class**

- **Found during:** Task 1
- **Issue:** The installed FastAPI version does not export `BackgroundTask` from `fastapi.background`.
- **Fix:** Imported the compatible Starlette class, matching the installed response stack.
- **Files modified:** `backend/endpoints/download_manifests.py`
- **Verification:** Focused transfer tests and targeted Trunk checks pass.
- **Committed in:** `d8faf0c08`

## Issues Encountered

- Pytest emitted pre-existing cache permission warnings for `backend/.pytest_cache`; test execution completed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 16 can use the published member URL with `Range: bytes=<offset>-` and the exact persisted quoted snapshot in `If-Match`. A failed continuation is unambiguously non-appendable.

## Self-Check: PASSED

- Confirmed task commits `fd57e7c2a` and `d8faf0c08` exist.
- Confirmed both modified backend files exist and the targeted test and static-check commands pass.

---

_Phase: 15-direct-resumable-transfer_
_Completed: 2026-09-16_
