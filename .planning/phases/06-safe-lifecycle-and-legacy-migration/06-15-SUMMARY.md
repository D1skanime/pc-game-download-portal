---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 15
subsystem: lifecycle-migration-closure
tags: [catalog-removal, legacy-migration, docker, openapi, dialects]
requires:
  - phase: 06-10..14
    provides: Gap-closure lifecycle, migration, rollback, policy, and contract behavior
  - phase: 06-16..17
    provides: Complete source-safe locale contract
provides:
  - Final adversarial lifecycle and migration regression evidence
  - Fail-closed disposable OpenAPI contract harness
  - Authoritative MariaDB, MySQL, and PostgreSQL round-trip evidence
affects: [phase-06-verification, phase-07]
tech-stack:
  added: []
  patterns:
    - Disposable runners are validated against immutable image configuration before start
    - Failure diagnostics redact all inherited and allowlisted environment values
key-files:
  created:
    - .planning/phases/06-safe-lifecycle-and-legacy-migration/06-15-SUMMARY.md
  modified:
    - backend/tests/endpoints/roms/test_catalog_removal.py
    - backend/tools/verify_phase6_contracts.py
    - backend/tests/tools/test_verify_phase6_contracts.py
    - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Input.ts
    - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Output.ts
    - .planning/phases/06-safe-lifecycle-and-legacy-migration/06-VALIDATION.md
key-decisions:
  - Treat immutable image environment values as part of exact runner parity while injecting only the approved source allowlist.
  - Prepare inaccessible image-owned runtime paths only inside the disposable runner, then prove Python and Uvicorn execute as UID 1000.
patterns-established:
  - Controlled contract generation uses a read-only checkout, loopback API, no published ports, exact full-ID cleanup, and redacted errors.
requirements-completed:
  [CAT-01, CAT-02, CAT-03, CAT-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
duration: 51m
completed: 2026-08-13
---

# Phase 6 Plan 15: Final Adversarial Closure Summary

Source-immutable catalog lifecycle closure with a fail-closed OpenAPI runner and authoritative three-dialect migration round trips.

## Performance

- **Duration:** 51 minutes
- **Started:** 2026-08-13T11:15:30Z
- **Completed:** 2026-08-13T12:06:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Closed the production catalog-removal flow through retained save and state use, later scan reconnection, and byte-exact source-manifest preservation.
- Locked controlled OpenAPI generation to the approved image, environment, network, user, entrypoint, command, checkout bind, workdir, loopback port, and exact owned cleanup contract.
- Regenerated the two changed lifecycle confirmation models and passed generated frontend typechecking.
- Passed the focused 291-test Phase 6 suite, mapped-read and harness failures, all three migration dialects, full frontend tests, locale gates, and production build.

## Task Commits

1. **Task 1: Close lifecycle, migration, policy, and immutability regressions** - `8b04fa553` (test)
2. **Task 2: Run controlled contracts, dialects, frontend gates, and update evidence** - `4b97377b4` (test)

## Files Created/Modified

- `backend/tests/endpoints/roms/test_catalog_removal.py` - Production removal, retained use, scan reconnection, and manifest-equality closure.
- `backend/tools/verify_phase6_contracts.py` - Exact disposable runner parser, immutable image parity, UID verification, redacted diagnostics, and cleanup.
- `backend/tests/tools/test_verify_phase6_contracts.py` - Parser, mismatch, redaction, runtime, PID-signature, readiness-failure, and cleanup tests.
- `frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Input.ts` - Generated source and catalog fingerprint inputs.
- `frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Output.ts` - Generated source and catalog fingerprint outputs.
- `.planning/phases/06-safe-lifecycle-and-legacy-migration/06-VALIDATION.md` - Actual final commands, counts, topology, warnings, and cleanup evidence.

## Decisions Made

- Included immutable image environment entries in expected runner parity because Docker retains those values even when the allowlisted source values come from the mode-0600 environment file.
- Allowed execute traversal to the image-bundled Python and ownership of the validated `/app` runtime directory only inside the disposable runner. Default-user Python and Uvicorn UID 1000 checks follow before contract generation.
- Reported readiness failures through a bounded log tail after replacing every inherited and allowlisted environment value.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Modeled immutable image environment parity**

- **Found during:** Task 2 real harness pre-start inspection
- **Issue:** Docker retained image environment entries that the harness had not included in its exact expectation.
- **Fix:** Inspected the resolved immutable image ID, merged its environment with the exact approved source allowlist, and continued to write only allowlisted values to the owned environment file.
- **Files modified:** `backend/tools/verify_phase6_contracts.py`, `backend/tests/tools/test_verify_phase6_contracts.py`
- **Committed in:** `4b97377b4`

**2. [Rule 3 - Blocking] Prepared image-owned runtime paths inside the disposable runner**

- **Found during:** Task 2 real Uvicorn startup
- **Issue:** The approved image's Python target was below mode-0700 `/root`, and its configured `/app` runtime path was not writable by UID 1000.
- **Fix:** Inside the exact owned runner only, granted root traversal, validated the runtime path resolves below `/app` and is not a symlink, created it for UID 1000, then verified default-user Python and Uvicorn UID 1000.
- **Files modified:** `backend/tools/verify_phase6_contracts.py`, `backend/tests/tools/test_verify_phase6_contracts.py`
- **Committed in:** `4b97377b4`

**3. [Rule 2 - Missing Critical Functionality] Added secret-safe startup diagnostics**

- **Found during:** Task 2 readiness investigation
- **Issue:** A generic readiness error could not distinguish an application startup failure while direct logs could expose environment values.
- **Fix:** Added a bounded log tail that redacts every inherited and allowlisted value before inclusion in an error.
- **Files modified:** `backend/tools/verify_phase6_contracts.py`, `backend/tests/tools/test_verify_phase6_contracts.py`
- **Committed in:** `4b97377b4`

**4. [Rule 3 - Blocking] Raised the frontend verification heap budget**

- **Found during:** Task 2 standalone frontend typecheck
- **Issue:** Node exhausted its default 2 GB heap.
- **Fix:** Re-ran typecheck, full tests, and build with the same explicit 4096 MB heap used by the controlled harness.
- **Files modified:** None.
- **Committed in:** Not applicable, environment-only correction.

**Total deviations:** 4 auto-fixed correctness and environment issues.
**Impact on plan:** Changes remained inside the controlled harness, its tests, and task-owned disposable resources. Product behavior, external source, services, and deployment state were unchanged.

## Issues Encountered

- Backend gates emitted existing short test auth-key, pytest-env configuration, Alembic path-separator, and HTTP 422 constant warnings.
- `npm ci` reported eight existing audit findings. Frontend tests and build emitted existing router, cache fallback, story accessibility TODO, Browserslist, CSS pseudo-class, dependency eval, and bundle-size warnings. All required gates passed.

## Verification

- Focused lifecycle/migration/policy suite: 291 passed, 5 warnings, 167.61 seconds in isolated MariaDB topology.
- Harness unit and failure contract: 26 passed; harness plus mapped-read contract: 43 passed.
- Real controlled harness: exit 0 in 45.8 seconds with exact configuration, UID 1000 Uvicorn, OpenAPI generation, frontend typecheck, and owned cleanup.
- MariaDB and PostgreSQL: pristine and seeded-0110 round trips plus 54 handler tests each passed.
- MySQL: pristine and seeded-0110 round trips passed; handler tests intentionally skipped on the minimal 0107 baseline.
- Frontend: focused 3 tests, full 51 files and 632 tests, typecheck, 17-peer locale parity, sorting, and 4,467-module production build passed.
- Scoped Trunk and `git diff --check` passed. Both task commits passed hooks and deleted no tracked files.
- Exact cleanup passed for the isolated database and grant, runtime directory, logs, runner and dialect containers, Node volumes, environment files, and verifier process.

## Known Stubs

None.

## Threat Flags

None. The controlled network, environment, filesystem, process, and generated-contract surfaces are all covered by the plan threat model and fail-closed tests.

## User Setup Required

None. No deployment or persistent service restart was performed.

## Next Phase Readiness

- All nine Phase 6 requirements have final focused, dialect, harness, frontend, locale, and production evidence.
- `06-VALIDATION.md` is current; the prior verification and review documents remain untouched for the final verifier rewrite.
- The tracked tree is clean after summary and tracking commits; unrelated untracked files are preserved.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_

## Self-Check: PASSED

- All six declared modified files and this summary exist in the canonical Linux checkout.
- Task commits `8b04fa553` and `4b97377b4` exist in git history.
- All recorded focused, dialect, harness, frontend, locale, static, hook, and cleanup evidence was observed in this execution.
- No known stub, unmodeled threat surface, deployment, persistent restart, tracked deletion, or external-source mutation remains.
