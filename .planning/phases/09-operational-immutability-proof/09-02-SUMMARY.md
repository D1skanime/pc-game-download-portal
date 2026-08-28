---
phase: 09-operational-immutability-proof
plan: 02
subsystem:
  - backend
  - testing
  - delivery
tags: [phase9, immutability, nginx, worker, restart, pytest]
requires: [09-01]
provides:
  - Per-workflow artifact envelopes for backend proof runs
  - Worker and nginx witness coverage for TEST-06 workflows
  - Restart-persistence and delivery-boundary integration verification
affects: [09-03, 09-04, backend-tools, backend-tests]
tech-stack:
  added: []
  patterns:
    [
      per-workflow evidence envelopes,
      service witness validation,
      safe route-level 404 masking for traversal-like content paths,
    ]
key-files:
  created:
    - backend/tests/integration/test_operational_immutability.py
  modified:
    - backend/tools/verify_operational_immutability.py
    - backend/tests/integration/test_scan_source_immutability.py
    - backend/tests/endpoints/roms/test_files.py
key-decisions:
  - "Workflow evidence stays split by slug with run-level and per-workflow JSON artifacts instead of one aggregated backend-only result."
  - "The traversal-like `%2F` path case is a route-level 404 boundary, not a content-disposition success path, because the `/{file_name}` segment does not safely normalize encoded slash traversal into a harmless filename."
patterns-established:
  - "TEST-06 proof requires explicit nginx witness fields for authorized and direct access statuses plus worker witness fields for durable jobs."
  - "Restart persistence is validated as a named workflow with its own before/after/diff/result envelope."
requirements-completed: [TEST-04, TEST-05, TEST-06]
duration: 55min
completed: 2026-08-28
---

# Phase 9 Plan 02: Backend Workflow Proof Summary

**Per-workflow backend evidence, nginx and worker witnesses, and restart persistence verification for the Phase 9 operational immutability harness**

## Performance

- **Duration:** 55min
- **Completed:** 2026-08-28
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Extended the Phase 9 harness from preflight-only into workflow execution with per-slug `before.json`, `after.json`, `diff.json`, and `result.json` artifacts.
- Added a dedicated backend integration suite for restart persistence and TEST-06 workflow evidence.
- Tightened the ROM file endpoint regression around traversal-like client path input to match the actual route boundary, preserving a safe 404 without leaking trusted filename data.

## Task Commits

The interrupted executor left verified but uncommitted work. The plan was closed out from the validated working tree state:

1. **Task 1 and Task 2** - pending commit in the current execution closeout

## Files Created/Modified

- `backend/tools/verify_operational_immutability.py` - workflow execution, restart evidence, nginx and worker witnesses
- `backend/tests/integration/test_operational_immutability.py` - integration checks for workflow envelopes and restart persistence
- `backend/tests/integration/test_scan_source_immutability.py` - manifest regression alignment with the shared harness
- `backend/tests/endpoints/roms/test_files.py` - route-boundary regression for traversal-like client path input

## Decisions Made

- Treated `stream-play`, `single-download`, and `multi-download` as TEST-06 workflows that must emit explicit nginx witness fields in the harness results.
- Recorded the traversal-like `..%2F..%2Fsecret.txt` request as a 404 route-boundary case, because this path never reaches the content-disposition logic that derives its filename from the trusted database row.

## Deviations from Plan

- `backend/tests/endpoints/test_streaming.py` did not require source changes. The existing assertions remained sufficient once the local MariaDB dependency was available.
- Validation required bringing up the repository's local MariaDB test service. Without it, the backend endpoint suite failed during shared test setup before reaching the new Phase 9 assertions.

## Issues Encountered

- The first verification attempt failed because no local MariaDB test service was listening on `127.0.0.1:3306`, which `backend/tests/conftest.py` requires for endpoint tests.
- A reused artifacts directory caused a `FileExistsError` in the harness fixture copy step. Re-running with a fresh `/tmp/phase9-02-*` directory resolved it cleanly.

## Verification

- `python3 backend/tools/verify_operational_immutability.py --requirement TEST-06 --artifacts /tmp/phase9-02-gk0rIA`
- `cd backend && uv run pytest tests/integration/test_operational_immutability.py tests/integration/test_scan_source_immutability.py tests/endpoints/test_streaming.py tests/endpoints/roms/test_files.py -x -q`
- `git diff --check -- backend/tests/endpoints/roms/test_files.py backend/tests/integration/test_operational_immutability.py backend/tests/integration/test_scan_source_immutability.py backend/tools/verify_operational_immutability.py`

Fresh results:

- Harness run: `status: ok`, `workflow_count: 5`
- Pytest: `60 passed, 7 skipped, 2 warnings in 16.72s`
- Diff check: passed

## Next Phase Readiness

- `09-03` can now bind browser flows to the already-established workflow slugs and TEST-06 artifact structure.
- `09-04` can rely on the backend harness for docs checks, aggregate coverage, and final `--all` execution.

## Self-Check: PASSED

- Found summary: `.planning/phases/09-operational-immutability-proof/09-02-SUMMARY.md`
- Verified harness requirement run: `TEST-06`
- Verified backend pytest suite: `60 passed, 7 skipped`
