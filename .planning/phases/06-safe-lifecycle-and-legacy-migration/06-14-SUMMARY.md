---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 14
subsystem: lifecycle-robustness
tags: [fastapi, storage, docker, fault-injection, tdd]
dependency_graph:
  requires: [06-10, 06-12]
  provides:
    - unambiguous post-commit catalog removal responses
    - complete bounded mapped-read resolution translation
    - exact-ID disposable contract verifier runner lifecycle
  affects: [catalog-removal, mapped-reads, contract-verification]
tech_stack:
  added: []
  patterns:
    - independent best-effort post-commit side effects
    - exhaustive bounded storage-resolution classification
    - nonce-owned inert container with pre-start parity inspection
key_files:
  created: []
  modified:
    - backend/endpoints/roms/__init__.py
    - backend/handler/storage/read_context.py
    - backend/tools/verify_phase6_contracts.py
    - backend/tests/endpoints/roms/test_catalog_removal.py
    - backend/tests/handler/storage/test_read_context.py
    - backend/tests/integration/test_legacy_migration.py
    - backend/tests/tools/test_verify_phase6_contracts.py
key_decisions:
  - Cache and smart-collection refresh failures are logged independently after commit and never alter durable catalog outcomes.
  - Caller and target resolution failures map to missing content, root failures map to unreachable storage, policy failures map to denial, and mapping identity failures map to stale reads.
  - The verifier copies only the exact approved environment allowlist into a mode-0600 file and removes only Docker's full returned runner ID.
requirements_completed: [CAT-02, MIG-04]
metrics:
  duration: 22m
  completed: 2026-08-13
---

# Phase 6 Plan 14: Bounded Lifecycle Robustness Summary

Catalog removal now preserves committed truth across cache faults, mapped reads translate every expected resolution failure, and contract verification runs in an exactly owned disposable container.

## Performance

- **Duration:** 22 minutes
- **Started:** 2026-08-13T08:17:47Z
- **Completed:** 2026-08-13T08:39:27Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Isolated filter-cache invalidation and smart-collection refresh behind independent best-effort post-commit boundaries with bounded operation-only logs.
- Classified the complete expected mapped-read failure family into stable missing, unreachable, denied, and stale contracts without filesystem or OS detail.
- Rebuilt the contract harness around a unique labeled sleeper container, strict source environment allowlist, immutable image identity, pre-start parity inspection, full-ID cleanup, and mode-0600 temporary environment.
- Added failure-path coverage for source and runner mismatch, absent or malformed PID state, reused PID signature, Docker command failures, redaction, and repeated cleanup.

## Task Commits

1. **Task 1 RED: Durable catalog-removal outcomes** - `5fc6b687f` (test)
2. **Task 1 GREEN: Preserve committed catalog results** - `a768d1ec0` (fix)
3. **Task 2 RED: Bounded mapped-read failure family** - `d3a69f0bb` (test)
4. **Task 2 GREEN: Complete mapped-read translation** - `8e8a0841f` (fix)
5. **Task 3 RED: Isolated verifier runner lifecycle** - `25335e728` (test)
6. **Task 3 GREEN: Exact-owned disposable runner** - `ff6f28680` (fix)
7. **Scoped verification fixes** - `a5250b49d` (test)

## Files Created/Modified

- `backend/endpoints/roms/__init__.py` - Keeps committed removal responses authoritative when dependent cache work fails.
- `backend/handler/storage/read_context.py` - Converts all expected resolution and mapping failures to bounded mapped-read errors.
- `backend/tools/verify_phase6_contracts.py` - Creates, inspects, runs, and exactly removes a nonce-owned isolated runner.
- `backend/tests/endpoints/roms/test_catalog_removal.py` - Injects independent post-commit dependency failures and asserts exact durable outcomes.
- `backend/tests/handler/storage/test_read_context.py` - Covers bounded error codes, states, disclosure limits, and first-use ordering.
- `backend/tests/integration/test_legacy_migration.py` - Keeps the adjacent first-use fixture valid under the Phase 06-12 selectable fingerprint constraint.
- `backend/tests/tools/test_verify_phase6_contracts.py` - Exercises the isolated runner success and failure matrix.

## Decisions Made

- Post-commit dependency failures carry only bounded operation context in logs, never raw exception details or source identities.
- A final `StorageResolutionError` catch maps unknown expected bounded resolution failures to unreachable storage after specific target, policy, and identity cases.
- The approved `romm-dev` source is inspected once for tag, immutable image ID, one approved network, and nonempty exact allowlist values.
- Uvicorn PID state is validated only inside the task-owned runner; cleanup never signals host PIDs or searches by name, label, or PID.

## TDD Gate Compliance

- Task 1 RED failed because the filter-cache exception escaped after a committed detach.
- Task 2 RED failed because `InvalidRelativePathError` escaped the mapped-read boundary.
- Task 3 RED failed at collection because the isolated runner environment contract did not yet exist.
- All RED commits precede their corresponding GREEN commits.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated the adjacent first-use integration seed**

- **Found during:** Task 2 adjacent integration verification
- **Issue:** The older seed created a selectable detection result without the source fingerprint required by Phase 06-12.
- **Fix:** Added one bounded lowercase 64-hex fixture fingerprint.
- **Files modified:** `backend/tests/integration/test_legacy_migration.py`
- **Verification:** Mapped-read and adjacent integration suite passed 40 tests.
- **Committed in:** `8e8a0841f`

**2. [Rule 1 - Bug] Closed scoped lint findings in fault-injection tests**

- **Found during:** Plan-wide scoped Trunk verification
- **Issue:** One legacy blind exception assertion no longer stated the bounded contract, and the fake env-file path was not narrowed for mypy.
- **Fix:** Asserted `MissingMappedContentError` directly and narrowed the optional path before stat.
- **Files modified:** `backend/tests/handler/storage/test_read_context.py`, `backend/tests/tools/test_verify_phase6_contracts.py`
- **Verification:** Focused post-fix suite passed 42 tests and scoped Trunk passed all seven files.
- **Committed in:** `a5250b49d`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes were required for adjacent compatibility and scoped verification. No product scope, deployment, persistent service restart, source mutation, or unrelated cleanup was added.

## Issues Encountered

- The host does not expose `uv`; tests ran inside the existing development image without restarting or modifying its service.
- The repository pytest configuration points DB_HOST to container-local loopback. Tests used the task-owned `romm_test_0614` database with explicit container-network hosts and `-p no:env`.
- Installed Trunk 1.25 does not accept `--no-cache`; the scoped CI check ran with the supported `--ci` option.

## Verification

- Task 1 focused gate: 11 passed.
- Task 2 mapped-read and adjacent integration gate: 40 passed.
- Task 3 verifier lifecycle gate: 25 passed.
- Plan-wide focused gate: 76 passed, 3 existing warnings.
- Post-lint focused gate: 42 passed.
- Scoped Trunk: 7 files checked, no issues.
- `git diff --check`: passed.
- Commit hooks formatted and checked every task commit without bypass.
- Task-owned database and user `romm_test_0614` were dropped.
- No `romm-phase06-contract-*` containers or task-owned Node volumes remain.

## Known Stubs

None.

## Threat Flags

None. All post-commit, filesystem error, environment-secret, Docker identity, PID-state, and cleanup surfaces are covered by the plan threat model.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WR-01, WR-02, and WR-03 are closed with fault-injection evidence.
- Plan 06-15 can run the real controlled contract harness against the completed Phase 6 contract changes.
- No blockers remain.

## Self-Check: PASSED

- All seven modified files exist in the canonical Linux checkout.
- RED, GREEN, and scoped verification commits exist in git history in the required order.
- CAT-02 and MIG-04 are represented in the plan and summary.
- Tracked worktree content is clean; pre-existing unrelated untracked files were preserved.
