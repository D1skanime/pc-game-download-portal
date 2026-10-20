---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
plan: "01"
subsystem: testing
tags: [docker, pytest, unittest, vitest, vue, pinia, rq, redis, mariadb]
requires:
  - phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
    provides: Existing setup and immutable storage mapping foundation, browser acceptance still open
provides:
  - Pre-import and destructive-fixture disposable-target guard
  - Standalone labelled SQL/Redis runner with read-only synthetic Games
  - Real RQ and Vue scope behavioral RED reproductions
  - PGDP setup and scan UI behavior contract
affects: [34-02, 34-03, 34-05, 34-06, 34-07, 34-08, 34-11, 34-12]
tech-stack:
  added: []
  patterns: [pre-import target authority, isolated internal Docker network, exact-label cleanup, assertion-specific RED evidence]
key-files:
  created:
    - backend/tools/phase34_target_guard.py
    - backend/tools/tests/test_phase34_target_guard.py
    - backend/tools/phase34.py
    - backend/tools/phase34.compose.yml
    - backend/tools/phase34_fixtures.py
    - backend/tools/tests/test_phase34_runner.py
    - backend/tests/endpoints/sockets/test_scan_job_identity.py
    - frontend/src/v2/composables/useScanLifecycle/index.test.ts
    - .planning/phases/34-reliable-fresh-installation-and-scan-lifecycle/34-UI-CONTRACT.md
  modified: [backend/tests/conftest.py, backend/pytest.ini]
key-decisions:
  - Reject every xdist worker until independently provisioned worker targets exist; never share destructive fixtures across workers.
  - Keep both production defects intentionally RED for their repair plans; the live incident root cause remains unconfirmed.
  - Delegate final fault, Portainer and evidence commands to the exact helpers owned by 34-08.
  - Leave STATE, ROADMAP, REQUIREMENTS and Phase 33 acceptance to the orchestrator.
requirements-completed: ["D-05","D-09","D-10","D-13","D-14","D-15","D-16","SAFE-05","SAFE-06","SCAN-06","UI-06"]
duration: 22 min
completed: 2026-10-18
---

# Phase 34 Plan 01: Guarded Test Infrastructure and Defect Reproductions Summary

**Disposable SQL/Redis tests now require verified targets before application imports, and actual RQ jobs and disposed Vue scopes reproduce both researched defects.**

## Performance

- First recorded execution timestamp: 2026-10-18T20:11:13Z. Preflight and initial context reads preceded it.
- Completed: 2026-10-18, approximately 20:33 UTC.
- Tasks: 3/3.
- Files: 11 implementation/test/contract files, plus this summary.
- Canonical environment: Linux via team4s-linux, /home/d1sk/pc-game-download-portal.
- Branch retained: codex/phase-32-pgdp-naming.
- Origin verified: https://github.com/D1skanime/pc-game-download-portal.git.
- No branch switch, worktree, live DB reset, live scan or deployment.

## Accomplishments

1. The dependency-free guard runs before third-party/application imports in the root conftest, before engine construction, and again at database creation, migration and cleanup entries against the resolved SQLAlchemy target. It validates generated identity, driver, credentials, exact service/network observations, internal-network ownership and actual Redis run_id. Target-affecting pytest-env defaults were removed. Ordinary backend pytest invocations now intentionally fail closed without the disposable manifest.
2. The runner uses one explicit Compose file and /dev/null as its env file. Each run owns a generated project, SQL/Redis services, internal network and output volumes. Eight synthetic platform directories live outside the repository and mount read-only. Application .env files, dirty Compose overrides, shared external networks and the Docker socket are absent. Commands and JUnit results are retained, credentials are redacted from command logs, and teardown checks labels before removing only that project's resources.
3. Regression tests exercise the actual RQ Job callable identity, actual queue enumeration and stop lookup, plus the actual lifecycle installer/useSocketEvent with real Vue component/effect scopes and Pinia. The UI contract preserves locked state, timing, ownership, localization and accessibility obligations.

## Task Commits

| Task | Commit | Result |
| --- | --- | --- |
| 1 RED | c4c21304e | Behavioral assertion proves unsafe collection reaches a dependency before validation |
| 1 GREEN | b38a4d7ea | Guard, guard tests, conftest and pytest-env changes |
| 2 | 817205125 | Disposable runner, Compose, fixtures and runner tests |
| 3 | 37cc7f452 | Actual RQ/Vue RED tests and UI contract |
| Bounded runner correction | 63f02bfc5 | Exact 34-08 helper delegation, CLI selector correction and two routing tests |

All commits ran repository hooks without bypasses. Post-commit deletion checks found no tracked-file deletions.

## Actual Verification

| Command/check | Actual result |
| --- | --- |
| python3 -m unittest discover -s backend/tools/tests -p test_phase34_target_guard.py -v | 6 passed after Task 1 |
| python3 -m unittest discover -s backend/tools/tests -p 'test_phase34*.py' -v | Final 19 passed, 0 failures/errors, 0.064 seconds |
| python3 backend/tools/phase34.py backend --smoke | Exit 0, 1 pytest passed through real conftest, pytest-env, migrations and guarded cleanup |
| python3 backend/tools/phase34.py reproduce --expect-defects | Exit 0 only after validating both exact expected assertion-failure sets |
| Isolated ./node_modules/.bin/eslint src/v2/composables/useScanLifecycle/index.test.ts | Exit 0 |
| Scoped trunk fmt and trunk check --no-fix --no-progress for changed code | Passed; commit hooks also passed |
| Isolated npm run typecheck | Exit 2, five diagnostics in two pre-existing files, detailed below |
| Runtime module logical-line check | phase34.py 479, phase34_fixtures.py 322, phase34_target_guard.py 143 |
| Final Docker label inventory | No remaining Phase 34 containers, volumes or networks |

Guard negatives test import boundaries, invalid application/localhost targets, inherited overrides, worker identities, manifest/network/service tampering, resolved URL drift, Redis identity mismatch and destructive fixture entry. Spies verify no connection/mutation for rejected static targets. Runner tests cover generated config precedence, command construction, target/path rejection, cleanup confinement, independent dialect dispatch, and rejection of import/infrastructure errors as RED evidence.

### Retained Linux evidence

- Smoke: /tmp/pgdp34-b0e72320933647dbb052c931f113b24f-jy4w4l0f/evidence.
  backend.xml records tests=1, failures=0, errors=0. cleanup.json records clean=true and source_unchanged=true.
- Final RED: /tmp/pgdp34-75ec012d63e84f90b88161dac99c088f-4axbv8oh/evidence.
  Includes commands.json, rq-red.xml, vue-red.xml, red-proof.json, source-before.json, source-after.json and cleanup.json.
- Isolated frontend lint/typecheck: /tmp/pgdp34-687ac44d8ab6457f88150711b34a21f9-ohjb8fbe/evidence.
  Commands retain exit 0 for ESLint and exit 2 for typecheck. Cleanup and source immutability both passed.
- Each run's adjacent control/manifest.json retains generated SQL/Redis names, observed full service/network identities and the Redis instance run_id. Disposable credentials are not reproduced here.

The final RED run removed its three containers, two volumes and one network. Its cleanup receipt records empty remaining-resource lists and byte/hash/size/mtime-equivalent synthetic source manifests. Real Games storage was never mounted or modified.

### Exact RED observations

Backend: 6 cases, 3 intended failures and 3 passing controls, zero setup/collection errors.

- test_manual_running_job_is_recognized: P34_RQ_RUNNING, lookup returned None for a real execute_mixed_scans Job.
- test_manual_queued_job_is_recognized: P34_RQ_QUEUED, actual queued job ID absent from lookup.
- test_stop_finds_manual_job: P34_RQ_STOP, status stayed queued rather than canceled.
- Redis save/fetch/callable readiness and watcher/scheduled recognition controls passed.

Frontend: 3 cases, 3 intended failures, initialized actual Vue scopes and Pinia.

- P34_REMOUNT: first install had five listeners, disposal had zero, fresh owner had zero instead of five.
- P34_OWNERS: two owners initially shared five listeners, disposal of one removed all five while the other survived.
- P34_DEBOUNCE: pending work mutated scanningPlatforms after final disposal.

No module reset occurs between disposal and remount within a case. Separate cases reset modules for independent baselines. Network/API/store collaborators are controlled fixtures; installScanLifecycle, useSocketEvent, Vue disposal and the scanning Pinia store execute real code.

These observations establish source defects. They do not establish that the live setup/auth-to-AppLayout route caused the observed 0/0 incident. Plan 34-08 must trace that route in the actual browser.

## Files Created/Modified

Created: the nine paths in key-files.created. The guard owns target authority; phase34.py owns CLI/service lifecycle; phase34_fixtures.py owns synthetic fixture generation and validation commands; the two host unittest files own boundary coverage; backend/frontend regressions preserve actual defects; 34-UI-CONTRACT.md carries downstream UI obligations.

Modified: backend/tests/conftest.py and backend/pytest.ini. No scanner, resolver, application endpoint, schema or UI runtime implementation changed.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 3 - Blocking] Snapshot symlink handling.**
   Initial smoke preparation encountered an existing dangling frontend resource symlink. Preserve symlinks without following external targets. The initial attempt failed and cleaned up; it was not RED evidence. Host snapshot behavior tests and the successful real smoke verify the fix. Commit: 817205125.

2. **[Rule 1 - Bug] Exact Vitest JUnit names.**
   Vitest prefixes case names with the suite name. The first combined run correctly rejected mismatched names despite both actual defect suites failing as expected. Match the exact qualified names. The final runner accepts only the intended assertion sets. Commit: 37cc7f452.

3. **[Rule 3 - Blocking] Empty canonical frontend dependency directory.**
   Host Trunk initially could not import @eslint/js. Isolated ESLint passed. Initialized only the existing ignored frontend/node_modules directory from the existing developer image using a network-disabled throwaway container and non-overwriting copy. No manifest, lockfile or tracked source was changed. Canonical Trunk and all commit hooks then passed.

4. **[Rule 1 - Bug] Deferred-gate routing.**
   Final review found unconditional deferred-mode errors and an e2e path inconsistent with 34-08 ownership. Delegate to backend/tools/phase34_faults.py, phase34_portainer.py and phase34_evidence.py with exact CLI options; missing helpers fail before launch. A routing test also exposed --mode overwriting the subcommand selector. Give that option its own destination. An initial regression-test iteration provisioned and cleaned a disposable SQL/Redis harness instead of reaching a helper; no production/fault helper, live scan or deployment ran. The final 19-test suite is host-only and forbids provisioning in delegation tests. Commit: 63f02bfc5.

No shared tracking updates were performed, as explicitly required by this plan and the user.

## Known Stubs and Deferred Gates

- No goal-blocking application stubs were introduced. Empty collections in the runner are accumulators; empty/mock collaborators in tests are intentional isolation boundaries.
- backend/tools/phase34.py lines 470-484 delegates fault, production and evidence modes to helpers owned by 34-08. Those helpers do not yet exist. Their absence is an explicit nonzero gate, never a passing placeholder.
- The matrix commands enforce separate MariaDB 10.11, MySQL 8.4 and PostgreSQL 15 provisioning, upgrade, downgrade to 0138_rom_metadata_facet_roles_view, re-upgrade and constraint/CRUD probe. This plan verified command enforcement through host behavior tests and actual MariaDB smoke migration only. The full three-dialect matrix was not executed or claimed passed.
- Full quality/build/locale, fault, Portainer and in-app browser acceptance remain later gates. They were not executed or marked passed here.
- The source defects intentionally remain RED. 34-03 repairs RQ recognition; 34-11 repairs listener/status ownership. The plan's references to 34-07 for lifecycle GREEN are superseded by the actual dependency/write-ownership map naming 34-11.

## Deferred Issues

Isolated full TypeScript checking remains failed on pre-existing diagnostics:

- frontend/src/v2/components/MatchRom/types.test.ts:52, TS2352.
- frontend/src/v2/components/Settings/pgdpFolderMappings.ts:32, TS2322.
- The same file:33, TS2677; :34, two TS18047 diagnostics.

No new lifecycle-test diagnostics were reported. These unrelated files were not modified. Plan 34-08 must retain this failed quality gate until resolved with orchestrator direction. This summary does not claim the full frontend is green.

## Authentication Gates

None.

## Orchestrator Handoff

- Completed plan 34-01, tasks 3/3, 11 implementation/test/contract files, approximately 22 minutes.
- Coverage IDs are copied verbatim above for this plan's infrastructure/RED/contract scope, not a claim that the entire Phase 34 behavior is implemented.
- Ready for the next dependency wave, including 34-02 and 34-05.
- Record progress centrally only after reviewing this committed summary.
- STATE.md, ROADMAP.md and REQUIREMENTS.md were neither edited nor staged. Their hashes match the initial baseline.
- All pre-existing dirty tracked files, Phase 33 UAT/VALIDATION and untracked Media/pgdp_test directories remain preserved. Phase 33 browser acceptance remains open.

## Self-Check: PASSED

Verified all nine created implementation/test/contract files exist, both modified files exist, every listed code commit resolves, no tracked deletion occurred, and the final expected-RED evidence reports both required suites with clean teardown. The summary is committed separately from task code.
