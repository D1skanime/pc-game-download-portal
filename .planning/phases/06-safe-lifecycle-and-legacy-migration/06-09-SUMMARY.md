---
phase: 06-safe-lifecycle-and-legacy-migration
plan: "09"
subsystem: integration-contract-closure
tags:
  [pytest, openapi, docker, immutability, policy, mariadb, mysql, postgresql]
requires:
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "02"
    provides: catalog-removal lifecycle semantics
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "03"
    provides: mapping-removal API and typed consequences
  - phase: 06-safe-lifecycle-and-legacy-migration
    plan: "04"
    provides: cancellation and reconnection safety
  - phase: 06-safe-lifecycle-and-legacy-migration
    plans: ["05", "06", "07", "08"]
    provides: impact, atomic migration, first-use, and rollback contracts
provides:
  - final writable and read-only source immutability evidence
  - closed external mutation inventory with pre-I/O denials
  - controlled OpenAPI generation and frontend typecheck harness
  - three-dialect Phase 6 acceptance record
affects: [phase-07, phase-09, storage-policy, legacy-migration, openapi]
tech-stack:
  added: []
  patterns:
    - exact-checkout runner preflight before controlled generation
    - recorded loopback Uvicorn PID with bounded readiness and exact cleanup
    - checkout-owner Node execution with task-owned node_modules volume
key-files:
  created:
    - backend/tools/verify_phase6_contracts.py
  modified:
    - backend/tests/tools/test_verify_phase6_contracts.py
    - backend/tests/integration/test_legacy_migration.py
    - backend/tests/handler/filesystem/test_storage_inventory.py
    - backend/tests/endpoints/test_storage_policy_denials.py
    - backend/tests/endpoints/test_storage.py
    - .planning/phases/06-safe-lifecycle-and-legacy-migration/06-VALIDATION.md
key-decisions:
  - "Contract generation fails closed unless the runner binds this exact checkout to /app and loopback port 39006 is unused."
  - "The Node generator runs as the checkout owner after initializing only its task-owned node_modules volume."
  - "External mutation closure is proven by an exhaustive operation inventory plus endpoint denial before filesystem I/O."
patterns-established:
  - "Controlled contract closure: exact bind preflight, recorded PID, bounded readiness, container-shared loopback, generated types, typecheck, exact cleanup."
  - "Phase acceptance: focused isolated tests plus pristine and seeded migration cycles on MariaDB, MySQL, and PostgreSQL."
requirements-completed:
  [CAT-01, CAT-02, CAT-03, CAT-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
duration: 40min
completed: 2026-08-13
---

# Phase 6 Plan 9: Integration Immutability and Contract Closure Summary

**Phase 6 now closes source immutability, external mutation policy, generated API contracts, and migration durability across MariaDB, MySQL, and PostgreSQL**

## Performance

- **Duration:** 40 min
- **Started:** 2026-08-13T00:16:10Z
- **Completed:** 2026-08-13T00:55:51Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added a fail-closed contract-generation harness that verifies the exact checkout bind, reserves runner loopback port 39006, records one Uvicorn PID, uses bounded readiness, and cleans only task-owned resources.
- Closed writable and read-only legacy source immutability, the storage authority inventory, all external mutation denials, and the complete Phase 6 OpenAPI surface.
- Regenerated the backend-owned frontend contract and passed TypeScript typechecking without introducing Phase 7 UI.
- Passed pristine and seeded-0110 migration round trips on MariaDB, MySQL, and PostgreSQL, including handler assertions where supported.
- Promoted the Phase 6 validation record from draft to passed with evidence for CAT-01 through CAT-04 and MIG-01 through MIG-05.

## Task Commits

1. **Task 1: Specify controlled contract-closure harness** - `db1d62bcd` (test)
2. **Task 2: Implement integration immutability and contract closure** - `84d1dfc54` (feat)

## Files Created/Modified

- `backend/tools/verify_phase6_contracts.py` - Exact-checkout, loopback-only OpenAPI generation and frontend typecheck lifecycle.
- `backend/tests/tools/test_verify_phase6_contracts.py` - Runner, port, command, ownership, readiness, and cleanup contract tests.
- `backend/tests/integration/test_legacy_migration.py` - Writable/read-only rollback source-manifest closure.
- `backend/tests/handler/filesystem/test_storage_inventory.py` - Complete operation-to-authority inventory closure.
- `backend/tests/endpoints/test_storage_policy_denials.py` - Parameterized external mutation denial before filesystem observation.
- `backend/tests/endpoints/test_storage.py` - Complete Phase 6 OpenAPI path, method, and safe-schema assertions.
- `.planning/phases/06-safe-lifecycle-and-legacy-migration/06-VALIDATION.md` - Final requirement matrix and executable evidence.

## Decisions Made

- Generation is allowed only after the harness confirms the current git top-level exactly matches the host source bound to `/app` in the running container.
- Uvicorn is started only on runner loopback port 39006, identified by one recorded PID, and stopped only after its `/proc` command line matches the expected signature.
- The Node container shares only the runner network namespace, mounts the verified frontend, uses a uniquely named volume, and runs as the checkout owner to preserve repository ownership.
- External mutation coverage is closed over create, upload, write, overwrite, rename, move, copy, delete, extract, patch, mkdir, sidecar, and cover operations.

## TDD Gate Compliance

- RED: `db1d62bcd` committed five isolated unit expectations that failed only because `backend/tools/verify_phase6_contracts.py` was absent.
- GREEN: `84d1dfc54` added the controlled lifecycle and completed the integration, policy, OpenAPI, dialect, and validation closure.
- Commit order was verified in git history.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used an exact-bound isolated runner**

- **Found during:** Task 2 controlled-generation preflight
- **Issue:** The existing `romm-dev` service binds the checkout's backend and frontend separately, so it cannot satisfy the required exact checkout-to-`/app` assertion.
- **Fix:** Created the task-owned `romm-phase06-runner-0609` from the existing development image with `/home/d1sk/romm:/app` and the existing internal network. The long-running service was not changed or restarted.
- **Files modified:** None.
- **Verification:** Both the controlled generation/typecheck and three-dialect verifier ran against the exact-bound runner.
- **Committed in:** Not applicable.

**2. [Rule 1 - Bug] Preserved repository ownership during generation**

- **Found during:** Task 2 generated-file cleanup
- **Issue:** The first Node run wrote generated files and their directory as root, preventing the repository user from restoring generator-only whitespace.
- **Fix:** Initialized only the task-owned node_modules volume, ran the generator as the checkout UID/GID, repaired the three task-touched files and generated directory ownership, and added a unit assertion.
- **Files modified:** `backend/tools/verify_phase6_contracts.py`, `backend/tests/tools/test_verify_phase6_contracts.py`
- **Verification:** Harness unit tests passed 5/5, the real generation/typecheck rerun passed, and generated artifacts remained owned by UID/GID 1000:1000.
- **Committed in:** `84d1dfc54`

**3. [Rule 3 - Blocking] Re-established the isolated focused-test database grant**

- **Found during:** Task 2 final harness-unit rerun
- **Issue:** The disposable `romm_test_0609` database no longer accepted the isolated test account after dialect verification.
- **Fix:** Recreated the exact disposable database and least-scope database grant, then reran with `pytest -p no:env`, full explicit environment, and `DB_HOST=romm-db-dev`.
- **Files modified:** None.
- **Verification:** Harness unit tests passed 5/5 and the final focused suite passed 138/138.
- **Committed in:** Not applicable.

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** The deviations preserved fail-closed runner identity, repository ownership, and valid isolated database topology. No product scope, source mutation, deployment, v1 route, UI, or Team4s service was added.

## Issues Encountered

- The migration verifier intentionally emitted downgrade-preflight tracebacks while proving retained lifecycle state blocks unsafe downgrade before DDL. Its authoritative status was 0.
- Exact regeneration produced no semantic TypeScript delta; only three generator-added blank EOF lines appeared. Those generated-only whitespace changes were restored as whole tracked files after the successful typecheck.
- A manual whole-file Trunk check reported unrelated pre-existing mypy findings in older regions of `backend/tests/endpoints/test_storage.py`. The commit hook checked the seven staged GREEN files with no issues.

## Validation Evidence

- Controlled harness unit contract: 5 passed.
- Final focused integration, inventory, policy, API, and harness suite: 138 passed.
- Extended lifecycle and migration regression suite: 158 passed.
- MariaDB, MySQL, and PostgreSQL pristine plus seeded-0110 upgrade, downgrade, and re-upgrade cycles passed.
- Disposable handler contract: 47 passed where supported.
- Real controlled OpenAPI regeneration and frontend `npm run typecheck` passed.
- Commit hook checked all seven GREEN files with no issues.
- `git diff --check` passed.
- Source manifests compare path, type, mode, size, SHA-256, and symlink identity while excluding atime.

## Known Stubs

None.

## Threat Review

No unmodeled product trust boundary was introduced. The harness's task-local process, Docker volume, and runner-loopback access are the controlled-generation surfaces required by the plan. Product transaction, storage authority, bounded result, and work-budget mitigations remain covered by T-06-09A through T-06-09D.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 acceptance is complete for all nine CAT and MIG requirements.
- Phase 7 can consume the stable generated contract and lifecycle semantics without a fallback source authority.
- No blockers remain.

## Self-Check: PASSED

- The summary and all seven created or modified task artifacts exist in the canonical Linux checkout.
- RED commit `db1d62bcd` and GREEN commit `84d1dfc54` exist in the required order.
- CAT-01 through CAT-04 and MIG-01 through MIG-05 are represented in the validation and summary.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_
