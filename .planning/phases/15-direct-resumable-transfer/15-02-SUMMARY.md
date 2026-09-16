---
phase: 15-direct-resumable-transfer
plan: 02
subsystem: filesystem
tags: [python, descriptor-streaming, sha256, concurrency, direct-transfer]
requires:
  - phase: 14-immutable-download-manifests
    provides: Immutable member evidence and quoted strong snapshot format
provides:
  - Freshly hash-verified descriptor lease for one persisted manifest member
  - Process-local transfer bound spanning verification and stream cleanup
affects: [15-03, direct-download-endpoint]
tech-stack:
  added: []
  patterns:
    - Hash verification retains the same descriptor for the subsequent sequential stream.
    - A transfer slot is released exactly once by the lease cleanup path.
key-files:
  created: []
  modified:
    - backend/config/__init__.py
    - backend/handler/filesystem/roms_handler.py
    - backend/tests/handler/filesystem/test_roms_handler.py
key-decisions:
  - "A source difference is a bounded SOURCE_CHANGED result with no lease."
  - "The HASH capability descriptor is retained after verification, so no second path-based open is needed."
patterns-established:
  - "Verified transfer: acquire, hash and compare immutable evidence, then stream the same descriptor until finally cleanup."
requirements-completed: [XFER-01, XFER-03, XFER-04]
duration: 31min
completed: 2026-09-16
---

# Phase 15 Plan 02: Strongly Verified Bounded Transfer Lease Summary

**A direct-transfer lease now rehashes one trusted manifest member, compares its exact Phase-14 strong snapshot, and retains a bounded read-only descriptor only for an unchanged source.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-09-16T20:43:00Z
- **Completed:** 2026-09-16T21:14:10Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Added a positive `DOWNLOAD_MANIFEST_TRANSFER_MAX_CONCURRENCY` process setting.
- Added a typed result and lease that holds one HASH-authorized descriptor from fresh verification through iterator cleanup.
- Proved exact strong-snapshot validation, SOURCE_CHANGED without a stream, 5/80/120 GiB accounting, and slot release after early close and read errors.

## Task Commits

1. **Task 1: Specify and implement a strongly verified bounded transfer lease** - `a10e8b8cb` (test), `ecda04d42` (feat)

## Files Created/Modified

- `backend/config/__init__.py` - Defines the validated transfer concurrency setting.
- `backend/handler/filesystem/roms_handler.py` - Provides the strong verification result and descriptor-backed streaming lease.
- `backend/tests/handler/filesystem/test_roms_handler.py` - Covers matching and changed evidence, synthetic large totals, read-only streaming, and cleanup paths.

## Decisions Made

- Retain the descriptor used for HASH verification rather than resolving or reopening a source path for streaming.
- Treat descriptor, metadata, SHA-256, destination, persisted file identity, and quoted snapshot differences as `SOURCE_CHANGED` before exposing an iterator.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The complete filesystem test file has two unrelated fixture-environment failures: a non-writable legacy test-library path and an extra committed PC fixture member. The focused Phase-15 command passed with 10 tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 15-03 can use `await fs_rom_handler.open_verified_download_manifest_member(rom, persisted_member)`. A `READY` result contains `lease.size_bytes`, `lease.snapshot`, and `lease.iter_chunks(start, length)`; `SOURCE_CHANGED` has no lease.

## Self-Check: PASSED

- Confirmed both task commits exist and all plan-owned files are present.

---

_Phase: 15-direct-resumable-transfer_
_Completed: 2026-09-16_
