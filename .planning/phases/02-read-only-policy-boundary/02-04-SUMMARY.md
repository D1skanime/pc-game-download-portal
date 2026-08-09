---
phase: 02-read-only-policy-boundary
plan: 04
subsystem: storage-policy
tags: [filesystem, capabilities, streaming, downloads, scanning]
requires:
  - phase: 02-read-only-policy-boundary
    provides: Closed operation policy, descriptor-bound access, and trusted owned storage composition
provides:
  - Composition-owned legacy external descriptor injection across every live read consumer
  - Exact LIST, STAT, READ, HASH, SCAN, STREAM, and DOWNLOAD enforcement at consumer seams
  - Descriptor-backed direct download streaming without FileResponse or X-Accel conversion
affects: [phase-03-mapping-api, phase-05-consumer-cutover, phase-09-nas-rollout]
tech-stack:
  added: []
  patterns:
    [
      composition-owned external identity,
      operation-bound FD capabilities,
      independent owned cache grants,
    ]
key-files:
  created:
    - backend/tests/handler/filesystem/test_external_read_consumers.py
  modified:
    - backend/handler/filesystem/base_handler.py
    - backend/handler/filesystem/storage_access.py
    - backend/handler/filesystem/firmware_handler.py
    - backend/handler/filesystem/platforms_handler.py
    - backend/handler/filesystem/roms_handler.py
    - backend/handler/scan_handler.py
    - backend/endpoints/sockets/scan.py
    - backend/watcher.py
    - backend/endpoints/heartbeat.py
    - backend/config/config_manager.py
    - backend/endpoints/streaming.py
    - backend/endpoints/roms/files.py
    - backend/endpoints/roms/__init__.py
key-decisions:
  - "Retain the single composition-owned legacy external descriptor until Phase 5 mapping lookup replaces legacy root resolution."
  - "Direct external downloads stream from DOWNLOAD capabilities and never become FileResponse or X-Accel paths."
  - "ZIP cache writes require a separate trusted owned CACHE grant from external DOWNLOAD authorization."
patterns-established:
  - "ExternalFSHandler read helpers open operation-specific descriptor capabilities before filesystem I/O."
  - "Legacy consumer compatibility may default constructors only through the exported composition-owned descriptor."
requirements-completed: [SAFE-01, SAFE-04, SAFE-06, TEST-03]
duration: 16min
completed: 2026-08-09
---

# Phase 2 Plan 4: Govern External Read Consumers Summary

**Composition-owned external identity now governs enumeration, scans, ROM reads, streaming, and downloads through exact operation capabilities while Phase 5 mapping lookup remains deferred.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-09T22:47:00Z
- **Completed:** 2026-08-09T23:03:49Z
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments

- Bound legacy external handlers to one immutable composition-owned descriptor and added LIST, STAT, READ, and capability-backed filesystem helpers.
- Added SCAN gates to scan orchestration and socket entry points, plus LIST gates to configuration, heartbeat, and watcher consumers.
- Replaced direct ROM FileResponse and X-Accel delivery with descriptor-backed DOWNLOAD streaming and independently authorized owned cache writes.
- Added runnable consumer identity and exact-operation evidence across every planned read seam.

## Task Commits

1. **Task 1 RED: Specify governed enumeration and scan consumers** - `f86d1c1ac` (test)
2. **Task 1 GREEN: Govern enumeration and scan consumers** - `9b347e93c` (feat)
3. **Task 2 RED: Specify governed ROM delivery consumers** - `2331d7309` (test)
4. **Task 2 GREEN: Govern ROM streaming and download reads** - `f074d421d` (feat)

## Files Created/Modified

- `backend/tests/handler/filesystem/test_external_read_consumers.py` - Descriptor identity, operation matrix, and response-boundary evidence.
- `backend/handler/filesystem/base_handler.py` - Capability-backed external list, stat, read, and size helpers.
- `backend/handler/filesystem/storage_access.py` - Direct support for immutable external descriptors and file-or-directory STAT.
- `backend/handler/filesystem/firmware_handler.py` - READ-bound firmware hashing.
- `backend/handler/filesystem/platforms_handler.py` - Composition descriptor injection and governed enumeration.
- `backend/handler/filesystem/roms_handler.py` - Explicit READ and HASH acquisition.
- `backend/handler/scan_handler.py`, `backend/endpoints/sockets/scan.py` - SCAN entry gates.
- `backend/watcher.py`, `backend/endpoints/heartbeat.py`, `backend/config/config_manager.py` - LIST and STAT policy gates.
- `backend/endpoints/streaming.py` - STREAM authorization from trusted provider identity.
- `backend/endpoints/roms/files.py`, `backend/endpoints/roms/__init__.py` - DOWNLOAD authorization and descriptor-backed direct streaming with separate owned CACHE grants.

## Decisions Made

- Mapping identity remains the immutable legacy descriptor exported by composition; request paths and database paths never classify storage.
- Direct external file delivery uses StreamingResponse over a DOWNLOAD capability, not raw absolute paths, FileResponse, FileRedirectResponse, or X-Accel URIs.
- ZIP cache authorization remains independent from source DOWNLOAD authorization.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extended descriptor access to trusted composition descriptors**

- **Found during:** Task 1
- **Issue:** `open_storage_access` accepted only persisted StorageRoot models, while the plan requires the immutable legacy composition descriptor.
- **Fix:** Accepted the non-forgeable ExternalStorageDescriptor directly and retained model compatibility for existing resolver tests.
- **Files modified:** `backend/handler/filesystem/storage_access.py`, `backend/handler/filesystem/base_handler.py`
- **Verification:** Storage access tests and the complete consumer matrix pass.
- **Committed in:** `9b347e93c`

**2. [Rule 1 - Bug] Updated stale mutation and redirect regression expectations**

- **Found during:** Task 2 verification
- **Issue:** Existing tests still expected external ROM rename and X-Accel delivery, both forbidden by the Phase 2 contract.
- **Fix:** Asserted pre-I/O StoragePolicyDenied for rename and absence of X-Accel on descriptor-streamed responses.
- **Files modified:** `backend/tests/handler/filesystem/test_roms_handler.py`, `backend/tests/endpoints/roms/test_rom.py`
- **Verification:** Combined plan regression passes 355 tests.
- **Committed in:** `f074d421d`

**3. [Rule 3 - Blocking] Accounted for root permission semantics in the development container**

- **Found during:** Task 2 verification
- **Issue:** The existing CHD permission-bit test cannot observe EACCES when pytest runs as root.
- **Fix:** Skip only that test when effective UID is root; non-root environments retain the original assertion.
- **Files modified:** `backend/tests/handler/filesystem/test_roms_handler.py`
- **Verification:** 355 passed, 1 root-only skip.
- **Committed in:** `f074d421d`

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All fixes were necessary to exercise the locked descriptor and denial contract without broadening Phase 5 mapping scope.

## Issues Encountered

- Host `uv` and `trunk` were unavailable. Tests ran in the existing Python 3.13 development container against an isolated `romm_test` schema; repository commit hooks formatted and checked every staged task file without bypass.
- The isolated test schema had been removed by an earlier model-suite teardown and was recreated before plan verification. No application database was touched.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. The changed endpoint surfaces implement the plan's declared T-02-READ-BYPASS and T-02-REDIRECT-BYPASS mitigations and add no new trust boundary.

## Verification Evidence

- Combined plan suite: 355 passed, 1 root-only skip, 1 Alembic configuration warning.
- Commit hooks formatted and checked all staged Python files without bypass.
- Caller path text cannot replace the composition descriptor; direct external responses contain no X-Accel redirect.

## Next Phase Readiness

- Every legacy external read seam is governed by the central policy and trusted composition identity.
- Phase 3 can add mapping administration without changing consumer lookup.
- Phase 5 remains responsible for replacing the legacy descriptor with mapping-aware lookup.

## Self-Check: PASSED

- All created and modified key files exist.
- Task commits `f86d1c1ac`, `9b347e93c`, `2331d7309`, and `f074d421d` exist.
- Both task verification sets pass together with 355 tests.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-09_
