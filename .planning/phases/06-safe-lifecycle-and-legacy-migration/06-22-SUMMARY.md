---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 22
subsystem: contract-verification-and-asset-lifecycle
tags: [cleanup, docker, openapi, pydantic, typescript, tdd]
requires:
  - phase: 06-14
    provides: controlled Phase 6 OpenAPI generation harness
  - phase: 06-15
    provides: detached save and state catalog lifecycle
provides:
  - retry-safe exact cleanup state for every harness-owned resource
  - live-ROM-only screenshot API and generated client contracts
  - detachable save and state contracts preserved across nested schemas
affects: [phase6-contract-harness, screenshot-api, generated-types]
tech-stack:
  added: []
  patterns:
    - clear per-resource ownership only after confirmed removal or explicit absence
    - specialize lifecycle fields at concrete asset schemas
key-files:
  created: []
  modified:
    - backend/tools/verify_phase6_contracts.py
    - backend/tests/tools/test_verify_phase6_contracts.py
    - backend/endpoints/responses/assets.py
    - backend/tests/endpoints/test_screenshots.py
    - backend/tests/endpoints/test_saves.py
    - backend/tests/endpoints/test_states.py
    - frontend/src/__generated__/models/ScreenshotSchema.ts
    - frontend/src/__generated__/models/UserScreenshotSchema.ts
key-decisions:
  - "Retain ownership state independently for runner, volume, and environment file until exact removal or explicitly classified absence succeeds."
  - "Require live rom_id only for screenshot schemas while keeping save and state lifecycle fields nullable and detachable."
patterns-established:
  - "Aggregate cleanup failures without suppressing later exact retries for the resources that remain owned."
requirements-completed: [CAT-01, CAT-02]
duration: 18m
completed: 2026-08-13
---

# Phase 6 Plan 22: Retry-Safe Cleanup and Screenshot Lifecycle Summary

**Per-resource cleanup ownership now survives partial failures, while screenshot contracts require a live ROM without weakening detachable save and state behavior.**

## Performance

- **Duration:** 18 minutes 2 seconds
- **Started:** 2026-08-13T17:29:49Z
- **Completed:** 2026-08-13T17:47:51Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- Made cleanup retry each still-owned exact runner ID, Node volume, and environment file independently.
- Classified only explicit Docker absence as successful cleanup, retained failed ownership state, aggregated bounded resource-only errors, and declared completion only after every resource was absent.
- Split shared response metadata from lifecycle ownership so screenshots require `rom_id` and expose no `retained_catalog_id`.
- Preserved nullable `rom_id`, retained catalog identity, and nested live screenshot contracts for save and state schemas.
- Regenerated controlled frontend contracts and passed the disposable OpenAPI generation and 4096 MB frontend typecheck gate.

## TDD Evidence

- **Task 1 RED:** Existing tests passed before the new partial-cleanup case failed on premature `_cleaned` state.
- **Task 1 GREEN:** All 31 cleanup harness tests passed, including retry, malformed PID, signature mismatch, explicit absence, aggregation, redaction, and idempotency cases.
- **Task 2 RED:** The focused contract gate failed because screenshot `rom_id` was nullable.
- **Task 2 GREEN:** The focused 12-test contract gate and full 129-test screenshot/save/state suite passed.
- **REFACTOR:** No separate implementation refactor was required; a final test-helper typing correction preserved behavior and passed all gates.

## Task Commits

1. **Task 1 RED: Specify cleanup retry semantics** - `67074d318` (test)
2. **Task 1 GREEN: Retain failed cleanup ownership** - `acbb687d5` (fix)
3. **Task 2 RED: Specify asset ownership contracts** - `a8ba56e53` (test)
4. **Task 2 GREEN: Align screenshot contract with persistence** - `2439259ef` (fix)
5. **Task 2 verification fix: Type cleanup harness factory** - `8dc7a376b` (test)

## Files Created/Modified

- `backend/tools/verify_phase6_contracts.py` - Tracks and clears cleanup ownership independently with bounded aggregate failure reporting.
- `backend/tests/tools/test_verify_phase6_contracts.py` - Covers partial, malformed, missing, mismatched, idempotent, and retry cleanup paths.
- `backend/endpoints/responses/assets.py` - Specializes required screenshot ownership and detachable save/state ownership.
- `backend/tests/endpoints/test_screenshots.py` - Locks runtime and JSON Schema screenshot ownership.
- `backend/tests/endpoints/test_saves.py` and `backend/tests/endpoints/test_states.py` - Preserve detachable parent contracts and live nested screenshots.
- Six generated asset model files - Reflect the authoritative specialized OpenAPI schemas.

## Decisions Made

- Treat cleanup ownership state as a per-resource retry ledger, not a one-shot global guard.
- Accept Docker cleanup absence only for explicit missing-container or missing-volume diagnostics.
- Keep lifecycle ownership out of the shared asset base so each concrete persistence model defines only states it can produce.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Invoked the standard-library contract harness with the host interpreter**

- **Found during:** Task 2 controlled generation
- **Issue:** Host `uv run` could not canonicalize the root-owned project virtual-environment interpreter.
- **Fix:** Invoked the same standard-library harness with host `python3`; the harness still ran authoritative backend generation and frontend generation/typecheck inside its exact isolated containers.
- **Files modified:** None.
- **Verification:** The controlled harness exited zero and removed its exact runner, volume, and environment file.
- **Committed in:** Not applicable, environment-only invocation.

**2. [Rule 3 - Blocking] Corrected a test-helper type construction exposed by the final scoped gate**

- **Found during:** Final scoped Trunk verification
- **Issue:** A dynamically typed kwargs dictionary obscured constructor argument types and failed mypy.
- **Fix:** Used explicit default and injected-unlinker constructor paths with an annotated callable.
- **Files modified:** `backend/tests/tools/test_verify_phase6_contracts.py`.
- **Verification:** Cleanup suite passed 31 tests and Trunk reported no issues across all six scoped source/test files.
- **Committed in:** `8dc7a376b`.

**3. [Rule 3 - Blocking] Completed the metadata commit with the verified host identity**

- **Found during:** Plan closeout
- **Issue:** The disposable Node GSD handler staged the exact tracking set but had no Git author identity.
- **Fix:** Committed the exact staged summary and tracking files from the verified Linux checkout with mandatory hooks.
- **Files modified:** None beyond the planned summary and tracking files.
- **Verification:** The final commit contains exactly four planned files and no tracked deletion.
- **Committed in:** Final metadata commit.

---

**Total deviations:** 3 auto-fixed blocking issues.
**Impact on plan:** Both fixes preserved the exact isolated harness, threat model, test coverage, and acceptance criteria.

## Issues Encountered

- Controlled generation introduced blank trailing lines in three unchanged legacy generated models; those incidental whitespace-only changes were removed before commit while all intended generated asset changes were retained.
- Existing Alembic path-separator and read-only pytest-cache warnings did not affect the focused test result.

## Verification

- Cleanup harness: 31 passed after implementation and again after the typing correction.
- Focused asset contract gate: 12 passed, 117 deselected.
- Full screenshot/save/state endpoint suite: 129 passed.
- Controlled OpenAPI generation and frontend typecheck: passed in disposable containers with UID 1000, read-only checkout, and 4096 MB Node memory.
- Scoped Trunk: six files checked, no issues.
- `git diff --check`: passed.
- Acceptance grep: required screenshot ownership and detachable save/state contracts passed.
- Commit hooks: passed without bypass for all task commits.
- TDD sequence: `67074d318` precedes `acbb687d5`; `a8ba56e53` precedes `2439259ef`.
- Cleanup: task database and grant removed; no labeled runner, prefixed Node volume, environment file, test container, or task temp log remains.

## Known Stubs

None.

## Threat Flags

None. Exact cleanup resources and asset lifecycle schema boundaries were covered by the plan threat model; no new endpoint, authentication path, filesystem authority, or schema trust boundary was introduced.

## Next Phase Readiness

Controlled contract generation can recover deterministically after partial cleanup failures, and generated screenshot clients now match runtime persistence states.

## Self-Check: PASSED

- Summary artifact exists at the required phase path.
- Task commits `67074d318`, `acbb687d5`, `a8ba56e53`, `2439259ef`, and `8dc7a376b` exist.
- All twelve modified files exist and no task commit deleted tracked files.
- Stub scan found no TODO, FIXME, placeholder, coming-soon, or unavailable markers.
- Exact task-owned resource audit is empty.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_
