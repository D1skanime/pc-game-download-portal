---
phase: 05-preview-and-read-path-cutover
plan: 06
subsystem: backend-read-delivery
tags: [storage-mapping, hashing, streaming, range, browser-play]
requires:
  - phase: 05-03
    provides: Mapping-bound read context and stable mapped-read errors
provides:
  - Single-handle mapped hashing with safe-boundary revision validation
  - Descriptor-bound direct delivery with GET, HEAD, and Range parity
  - Mapping-authorized browser-play broker handoff
affects: [05-07, 05-08, phase-09-production-validation]
tech-stack:
  added: []
  patterns: [validate-open-revalidate, one-descriptor-per-transfer]
key-files:
  created: []
  modified:
    - backend/handler/filesystem/roms_handler.py
    - backend/endpoints/roms/files.py
    - backend/endpoints/streaming.py
key-decisions:
  - "Mapped direct delivery streams from one already-open descriptor and never reopens after a revision change."
  - "Browser-play paths are derived only after STREAM authorization of the active mapping identity."
requirements-completed: [SCAN-01, SCAN-02, SCAN-06]
duration: 35 min
completed: 2026-08-12
---

# Phase 5 Plan 6: Mapped Hashing and Direct Delivery Summary

Mapped hashing, direct downloads, HEAD/Range requests, and browser play now authorize an exact mapping revision immediately before a single-handle read or broker handoff.

## Performance

- Duration: 35 min
- Completed: 2026-08-12
- Tasks: 2
- Files modified: 5

## Accomplishments

- Added chunk-boundary revision validation for regular and ZIP hashing through one operation-bound HASH descriptor.
- Replaced legacy direct-file authority with mapped DOWNLOAD preflight and one descriptor for the complete response.
- Preserved trusted content types, disposition, nosniff, GET, HEAD, and single-range behavior.
- Bound browser play to a STREAM capability and revalidated immediately before broker launch.
- Public mapped-read failures expose only stable codes and bounded safe states.

## Task Commits

1. Task 1: `39cca3ee5` feat(05-06): bind mapped hashing
2. Task 2: `8cd13cc77` feat(05-06): bind mapped file delivery

3. Task 2 test fixtures: `9b17c3504` test(05-06): add mapped delivery fixtures
## Recovery Note

Execution resumed from an interrupted plan. Commit `39cca3ee5` was inspected as the Task 1 candidate and retained because it is scoped to mapped hashing, uses one descriptor, and validates the mapping at chunk/archive boundaries. Existing uncommitted edits in both Task 2 endpoint files were preserved where valid, completed for HEAD/Range parity and bounded response behavior, then committed atomically.

## Verification
- Task 1 exact suite passed in the disposable MariaDB/Valkey test environment: 77 passed, 1 skipped, exit 0.
- Task 2 exact suite passed in the same environment: 47 passed, 7 skipped, exit 0.
- The proven invocation uses an ephemeral Valkey sidecar and `docker run --rm --entrypoint pytest --network container:romm-db-dev` with the canonical backend bind-mounted at `/app/backend`.
- Python compilation passed for all three modified production modules and both authorized test modules.
- `git diff --check` passed.
- Source-contract checks confirmed `preflight_mapped_download`, `MappedContentResponse`, explicit HEAD routing, Range headers, and removal of `LIBRARY_BASE_PATH` authority from streaming.
- Source immutability is proven by the passing byte-exact source-manifest suite and descriptor-only production reads.
- Source immutability is preserved by descriptor-only reads. Neither task contains a source write operation, and the source-manifest suite was included in the exact Task 1 command before the environment setup blocker.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added explicit HEAD and bounded Range delivery**

- Found during Task 2 recovery.
- The interrupted draft streamed the full file for GET but did not provide the required HEAD/Range parity.
- Added the same mapped preflight for GET and HEAD, a bounded single-range parser, 206/416 headers, and descriptor-bounded chunk reads.
- Files modified: `backend/endpoints/roms/files.py`.
- Verification: compilation, source-contract checks, and successful 54-test collection.
- Commit: `8cd13cc77`.

**2. [Rule 1 - Bug] Closed mapped STREAM handles on occupied sessions**

- Found during Task 2 recovery.
- A broker session collision could return before closing the newly authorized descriptor.
- Closed the descriptor before returning the conflict and retained final cleanup around broker handoff.
- Files modified: `backend/endpoints/streaming.py`.
- Verification: compilation and diff inspection.
**3. [Rule 3 - Blocking] Added mapped endpoint fixtures with user authorization**


- Found during final Task 2 verification.
- The host lacks direct `uv` and `trunk` executables. Verification used the established disposable repository image sharing the MariaDB container network namespace with a temporary Valkey sidecar.
- Initial execution inside `romm-dev` could not reach MariaDB at loopback. No persistent deployment or database configuration was changed; the disposable invocation resolved the environment issue.
- Files modified: `backend/tests/endpoints/roms/test_files.py`, `backend/tests/endpoints/test_streaming.py`.
- Verification: both exact suites pass through the disposable MariaDB/Valkey invocation.
- Commit: `9b17c3504`.

**Total deviations:** 3 auto-fixed, one missing critical behavior, one descriptor lifecycle bug, and one blocking test-contract update. Test scope expansion was explicitly authorized.
**Total deviations:** 2 auto-fixed, one missing critical behavior and one descriptor lifecycle bug. No scope expansion.

## Issues Encountered

- The Linux host has no `uv` or `trunk` executable.
- The existing application container has the project environment, but its pytest configuration points to container-local `127.0.0.1:3306`; the MariaDB service is a separate container. Both exact suites therefore stop in the shared session fixture before executing tests. No database, Docker configuration, or unrelated file was modified.

## User Setup Required

None.

## Known Stubs

None.

- Both exact 05-06 verification suites are green. Production broker/Nginx race behavior remains part of the Phase 9 production-like gate.

| Flag | File | Description |
| --- | --- | --- |
- All five modified production and test files exist.
- Task commits `39cca3ee5`, `8cd13cc77`, and `9b17c3504` exist.
- Both exact suites exit 0 with the recorded pass counts.
- The summary records the interrupted-plan recovery and user-authorized test-fixture deviation.
- No unrelated dirty or untracked file was staged.

- Plans 05-07 and 05-08 can consume mapped direct-read behavior.
- Production broker/Nginx race behavior remains part of the Phase 9 production-like gate.
- The test container database address must be corrected by the environment owner before runtime endpoint verification can execute.

## Self-Check: PASSED

- All three modified production files exist.
- Task commits `39cca3ee5` and `8cd13cc77` exist.
- The summary records the interrupted-plan recovery and exact verification blocker.
- No unrelated dirty or untracked file was staged.

---
_Phase: 05-preview-and-read-path-cutover_
_Completed: 2026-08-12_

