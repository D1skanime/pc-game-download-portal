---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 27
subsystem: api
tags: [fastapi, storage-policy, authorization, pytest, tdd]

requires:
  - phase: 02-read-only-policy-boundary
    provides: Central deny-by-default external storage policy
  - phase: 06-safe-lifecycle-and-legacy-migration
    provides: Mixed-authority ROM update inventory and changed-filename guard
provides:
  - Changed ROM filenames are denied immediately after visibility
  - Unmatch and provider screenshot branches cannot precede rename authorization
  - Replay-safe immutable source and owned-resource regression evidence
affects: [phase-06-verification, catalog-lifecycle, rom-update-api]

tech-stack:
  added: []
  patterns:
    - Visibility before filename normalization and authorization before every effect
    - Ordered effect logs for mixed-authority endpoint regressions

key-files:
  created: []
  modified:
    - backend/endpoints/roms/__init__.py
    - backend/tests/endpoints/test_storage_policy_denials.py

key-decisions:
  - "Compute and authorize the effective submitted filename once, immediately after ROM visibility."
  - "Treat every changed normalized filename as external RENAME authority before unmatch, provider, database, cache, collection, response, owned-resource, or filesystem work."

patterns-established:
  - "Mixed-authority preflight: visibility, normalization, exact comparison, then policy authorization."
  - "Adversarial endpoint tests record ordered effects and compare exact source and owned manifests."

requirements-completed: [CAT-04]

duration: 12min
completed: 2026-08-20
---

# Phase 6 Plan 27: Early Rename Authorization Summary

**Changed ROM filenames now reach one bounded external RENAME denial immediately after visibility, before unmatch, provider, database, cache, collection, response, owned-resource, or filesystem effects.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-20T10:59:52Z
- **Completed:** 2026-08-20T11:11:47Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Moved effective filename normalization, comparison, and authorization directly after assert_rom_visible.
- Added replay-safe regressions for changed filenames combined with unmatch metadata and provider screenshots.
- Proved bounded 403 responses, exact immutable manifests, one authorization per denial, and unchanged or omitted filename compatibility.
- Preserved one precomputed filename and change decision through the existing update path.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Specify pre-effect rename denial** - 97bc6b228 (test)
2. **Task 2 GREEN: Authorize changed filename immediately after visibility** - af2b82ec9 (fix)
3. **TDD REFACTOR: Clean up typed effect tripwires** - 83854e02f (refactor)

## Files Created/Modified

- backend/endpoints/roms/**init**.py - Performs the single changed-filename RENAME authorization before every mixed-authority branch and reuses its result.
- backend/tests/endpoints/test_storage_policy_denials.py - Covers unmatch and provider screenshot bypasses, ordered effects, replay, manifests, and same-name behavior.

## Verification Evidence

- RED exact test: pytest status 1 with test_update_rom_changed_fs_name_denied_before_unmatch_effects failing because no 403 was raised.
- RED provider test: observed provider, owned:get_rom_screenshots, then authorize:rename before the production change.
- Positive control during RED: unchanged filename test passed.
- GREEN focused selection: 8 passed, 47 deselected.
- Complete test_storage_policy_denials.py: 55 passed.
- Scoped Trunk format and check on both changed files: no issues.
- Python 3.13 AST compilation: both changed files passed.
- Static call ordering: visibility line 1537, sanitize line 1539, authorization line 1542, first database update line 1547, with one RENAME authorization call.
- git diff --check: passed.
- All commits ran mandatory hooks without bypass.

## Decisions Made

- Filename authority is decided once after visibility and before any early return or metadata-provider work.
- Omitted and unchanged filenames do not request RENAME authority and retain metadata and typed owned-resource behavior.
- The existing bounded denial schema remains the public response and reveals no host or source path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provisioned the isolated test database grant**

- **Found during:** Task 1 RED
- **Issue:** The ordinary application database user could not create the exact romm_test_0627 schema required by the pytest harness.
- **Fix:** Created and granted only the task-owned schema through the existing MariaDB container, then revoked the grant and dropped the schema after verification.
- **Files modified:** None
- **Verification:** Final schema and grant counts were both 0.
- **Committed in:** Not applicable

**2. [Rule 1 - Bug] Corrected static typing in new async tripwires**

- **Found during:** Plan verification
- **Issue:** The first ordered-effect mocks used value-returning list append expressions and direct patched-function mock assertions, which triggered seven scoped mypy findings.
- **Fix:** Replaced them with typed async callbacks and explicit AsyncMock casts, then reformatted the test file.
- **Files modified:** backend/tests/endpoints/test_storage_policy_denials.py
- **Verification:** Scoped Trunk format and check passed, followed by 55 passing tests.
- **Committed in:** 83854e02f

---

**Total deviations:** 2 auto-fixed (1 blocking environment issue, 1 test typing bug).
**Impact on plan:** Both fixes were required for deterministic verification and static correctness. No product scope was added.

## Issues Encountered

- The first RED invocation returned pytest infrastructure status 4 because disabling the env plugin also removed the required auth secret. That result was rejected as RED evidence. The test was rerun with a task-only non-production secret and produced the required behavioral status 1.
- Pytest reported the inherited unknown env option and Alembic path-separator warnings; both remained non-failing and outside this plan's scope.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. This plan narrows authority on an existing endpoint and introduces no route, authentication path, schema, network client, or new storage capability.

## Cleanup

- Revoked the exact romm_test_0627 application-user grant.
- Dropped the exact romm_test_0627 schema and confirmed schema count 0 and grant count 0.
- Created no containers, volumes, deployment artifacts, or service changes.
- Preserved all 28 pre-existing untracked paths.

## Next Phase Readiness

- CAT-04's changed-filename mixed-authority blocker is closed at the endpoint boundary.
- Plan 06-28 can proceed with immutable rollback-lineage hardening.

## Self-Check: PASSED

- Both modified key files exist.
- RED, GREEN, and REFACTOR commits exist in the expected order.
- All acceptance and plan-level verification commands passed.
- Cleanup and untracked-baseline assertions passed.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-20_
