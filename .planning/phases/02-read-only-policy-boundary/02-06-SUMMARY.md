---
phase: 02-read-only-policy-boundary
plan: 06
subsystem: filesystem-security
tags: [capabilities, descriptors, archives, patching, zip, exporters, audio]
requires:
  - phase: 02-03
    provides: trusted storage composition and owned storage descriptors
  - phase: 02-04
    provides: descriptor-relative external read capabilities
provides:
  - Closed owned read, create, replace, delete, and directory capabilities
  - Descriptor-only archive, ROM patch, ZIP cache, exporter, and audio seams
  - Explicit subprocess descriptor inheritance for archives and patching
affects: [02-07, 02-08, 02-09]
tech-stack:
  added: []
  patterns:
    [
      operation-bound filesystem capabilities,
      explicit pass_fds,
      independently authorized source and destination,
    ]
key-files:
  created: [backend/tests/utils/test_rom_patcher.py]
  modified:
    [
      backend/handler/filesystem/storage_access.py,
      backend/utils/archives.py,
      backend/utils/rom_patcher/patcher.py,
      backend/utils/zip_cache.py,
      backend/utils/gamelist_exporter.py,
      backend/utils/pegasus_exporter.py,
      backend/utils/audio_tags.py,
    ]
key-decisions:
  - "Breaking capability-only utility APIs replace raw Path and string compatibility at transformation seams."
  - "Generated exporter files are written to owned resources storage rather than the external library."
patterns-established:
  - "Subprocesses receive only /proc/self/fd arguments backed by explicit pass_fds."
  - "External inputs and owned outputs are authorized and closed independently."
requirements-completed: [ROOT-05, SAFE-02, SAFE-04, SAFE-06, TEST-03]
duration: 27min
completed: 2026-08-10
---

# Phase 2 Plan 6: Capability Consumer Cutover Summary

**Descriptor-bound archive and patch inputs, independently authorized ZIP/export outputs, and owned-only audio mutations without raw-path compatibility fallbacks**

## Performance

- **Duration:** 27 min
- **Started:** 2026-08-10T09:16:50Z
- **Completed:** 2026-08-10T09:43:31Z
- **Tasks:** 3
- **Files modified:** 18

## Accomplishments

- Added separate closed owned capabilities for reads, creates, atomic replacements, deletes, and directory operations.
- Converted archive and Node patch subprocesses to descriptor arguments with explicit inherited FD lists and deterministic cleanup.
- Converted ZIP cache construction to DOWNLOAD capabilities plus owned atomic replacement, and cut production callers over.
- Converted gamelist and Pegasus output to owned replacement capabilities, with scan and API callers supplying authority explicitly.
- Enforced owned-only audio read, replace, and delete operations.

## Task Commits

1. **Task 1: Build the closed capability foundation** - `13aeb8fe1`, `b87109531`
2. **Task 2: Cut archives and patching over to capabilities** - `eaaa75567`, `8c0b875ac`, `9df78fd1d`, `2966bd718`
3. **Task 3: Cut ZIP, export and audio flows over to capabilities** - `85fa2382e`, `f39beae0a`, `04406739e`, `3c05798a7`, `293d1af69`, `3d312c9ae`, `33d18d6c5`, `3b60a5d62`

## Files Created/Modified

- `backend/handler/filesystem/storage_access.py` - Closed owned capabilities and descriptor lending for explicit child-process output.
- `backend/utils/archives.py` - Descriptor archive adapters with explicit inherited FDs.
- `backend/utils/rom_patcher/patcher.py` - Capability-only ROM and patch inputs plus owned output.
- `backend/utils/zip_cache.py` - DOWNLOAD inputs copied into owned atomic replacement output.
- `backend/utils/gamelist_exporter.py` - Logical resource references and owned destination output.
- `backend/utils/pegasus_exporter.py` - Logical resource references and owned destination output.
- `backend/utils/audio_tags.py` - Owned-only audio mutations.
- `backend/endpoints/roms/patch.py`, `backend/endpoints/roms/__init__.py`, `backend/endpoints/export.py`, `backend/endpoints/sockets/scan.py` - Production capability composition.

## Decisions Made

- Applied the user-approved breaking cutover. No raw Path/string compatibility overloads remain at the changed utility seams.
- Export metadata now lands in classified owned resources storage, because an external library cannot be a write destination.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added writable descriptor lending to owned create capabilities**

- **Found during:** Task 2
- **Issue:** Node patching required an output descriptor, but the initial closed create capability exposed only byte creation.
- **Fix:** Added a scoped subprocess file context that creates with no-follow flags and always closes its FD.
- **Files modified:** `backend/handler/filesystem/storage_access.py`
- **Verification:** ROM patch capability tests pass and assert exact `pass_fds`.
- **Committed in:** `2966bd718`

**2. [Rule 2 - Missing Critical] Added atomic binary output to owned replacement capabilities**

- **Found during:** Task 3
- **Issue:** Large ZIP output could not safely use an in-memory byte replacement.
- **Fix:** Added scoped binary replacement with fsync, atomic replace, and failure cleanup.
- **Files modified:** `backend/handler/filesystem/storage_access.py`
- **Verification:** ZIP cache tests pass with descriptor sources and owned output.
- **Committed in:** `293d1af69`

**Total deviations:** 2 auto-fixed (2 missing critical). **Impact:** Both preserve the closed authority model and avoid generic write capability.

## Issues Encountered

- The broad endpoint regression command reaches pre-existing Phase 02-05 expectation conflicts: convert-to-folder and delete-ROM tests expect HTTP 200 while the accepted policy implementation returns HTTP 403. These files were not changed by this plan. Before those unrelated failures, 458 tests passed and one skipped. The focused filesystem, archive, patcher, ZIP, exporter, audio, ROM handler, file, and soundtrack suites passed.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Capability-only transformation seams are ready for the remaining sync, watcher, cleanup, and task cutovers in 02-07.
- The Phase 02-05 endpoint expectation conflict remains for the final inventory and validation plans to reconcile.

## Self-Check: PASSED

- All key files exist.
- All fourteen task commits are present on `codex/pc-module-analysis`.
- Focused capability and caller regressions pass.
- Raw Path/string signature searches at changed utility seams are empty.
- No known stubs or new unmodeled network, authentication, schema, or file trust boundary was introduced.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-10_
