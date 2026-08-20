---
phase: 06-safe-lifecycle-and-legacy-migration
status: passed
nyquist_validation: enabled
requirements:
  [CAT-01, CAT-02, CAT-03, CAT-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
created: 2026-08-12
validated: 2026-08-20
---

# Phase 6: Safe Lifecycle and Legacy Migration - Validation

## Objective

Prove that catalog removal and legacy layout migration change only explicit
RomM-owned state, preserve external source content and structure, fail closed
under races and conflicts, and remain portable across MariaDB, MySQL, and
PostgreSQL.

## Requirement Matrix

| Req    | Current executable evidence                                                                                                                                    |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CAT-01 | The IDs-only catalog-removal request and generated contract pass, with no source-delete input.                                                                 |
| CAT-02 | Detached save, state, and play-session value survives catalog removal and reconnects on existing-ROM scan retry after an injected post-insert failure.         |
| CAT-03 | Mapping removal, lifecycle revision, audit, retention, and owned cleanup assertions commit atomically.                                                         |
| CAT-04 | The closed backend inventory denies every external mutation family before I/O, while the complete active-v2 inventory contains no external mutation authority. |
| MIG-01 | Detection accepts only literal `roms/<fs_slug>` and `<fs_slug>/roms` candidates.                                                                               |
| MIG-02 | Pristine and seeded 0110/0111 lifecycles, 0112/0113 lineage, restart, guarded downgrade, cleanup, and re-upgrade pass on all three dialects.                   |
| MIG-03 | Missing, empty, unreadable, ambiguous, unsafe, conflicting, over-budget, and concurrently replaced observations remain non-selectable.                         |
| MIG-04 | Mapping, migration, first-use state, and rollback lineage survive the verifier restart boundary.                                                               |
| MIG-05 | Status is explicit and expiring, and no legacy fallback or mutation authority remains.                                                                         |

## Final Execution Evidence

| Gate                                            | Current result                                                                                                               |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Task 1 adversarial closure                      | 140 passed, 4 warnings, 20.58 seconds                                                                                        |
| Harness and mapped-read contracts               | 48 passed, 2 warnings                                                                                                        |
| Post-remediation affected backend               | 138 passed, 2 warnings, 4.44 seconds                                                                                         |
| Full Phase 6 lifecycle and migration regression | 315 passed, 4 warnings, 131.70 seconds                                                                                       |
| Task 2 cleanup feedback                         | 11 passed, 20 deselected, 2 warnings                                                                                         |
| Task 2 frontend feedback                        | 3 files, 23 tests passed                                                                                                     |
| MariaDB migration verifier                      | pristine and seeded lifecycles passed; 59 handler/model tests passed                                                         |
| MySQL migration verifier                        | pristine and seeded lifecycles passed; handler tests correctly skipped on the minimal 0107 baseline                          |
| PostgreSQL migration verifier                   | pristine and seeded lifecycles passed; 59 handler/model tests passed                                                         |
| Controlled OpenAPI contract                     | exact-checkout runner passed and cleaned every owned resource                                                                |
| Generated frontend contract                     | 257 files; screenshot schemas coherent; zero screenshot incarnation-token fields                                             |
| Focused frontend closure                        | 4 files and 26 tests passed                                                                                                  |
| Full frontend suite                             | 53 files and 653 tests passed                                                                                                |
| Frontend typecheck                              | passed with a 4096 MB Node heap                                                                                              |
| Production frontend build                       | passed with 4,463 modules and 744 PWA entries                                                                                |
| Locale parity and sorting                       | all 17 peer locales complete and sorted                                                                                      |
| Active-v2 inventory                             | 436 production modules, 13 external mutation operations, 10 owned descriptors, 19 route families, zero forbidden authorities |
| Phase 6 backend static scope                    | 18 production files, zero Trunk issues                                                                                       |
| Phase 6 frontend static scope                   | 29 files, zero direct repository ESLint errors                                                                               |
| Diff and repository state                       | `git diff --check` passed; tracked tree clean; 28 pre-existing untracked files preserved                                     |
| Cleanup and normal application access           | all owned resource counts zero; normal application `SELECT 1` returned 1 before and after cleanup                            |

## Commands and Topology

The authoritative dialect command was:

```text
cd backend && python3 tools/verify_storage_migrations.py --dialects mariadb mysql postgresql --handler-tests --handler-test-repetitions 1
```

The prescribed `/home/d1sk/.local/bin/uv` launcher could not traverse the
root-owned checkout virtual environment, so the same standard-library verifier
was run with host `python3`. It created unique disposable database containers,
used mapped ephemeral ports, ran against the canonical read-only application
checkout through `romm-dev`, and removed every container. MariaDB, MySQL, and
PostgreSQL each passed pristine upgrade, seeded 0110 and seeded 0111 upgrade
through 0112/0113, restart, expected guarded downgrade refusal, exact rollback,
cleanup, downgrade, and re-upgrade. The guarded-downgrade tracebacks were
expected assertion evidence and not failures.

The controlled contract command retained the exact plan arguments:

```text
cd backend && python3 tools/verify_phase6_contracts.py --source-container romm-dev --checkout /home/d1sk/romm --expected-image romm-romm-dev --network romm_default --user 1000:1000 --entrypoint /bin/sleep --command infinity --env-allowlist DB_HOST,DB_NAME,DB_PASSWD,DB_PORT,DB_USER,REDIS_DB,REDIS_HOST,REDIS_PORT,REDIS_SSL,ROMM_BASE_PATH --port 39006
```

The same host `uv` traversal failure required the standard-library
`python3` launcher. The harness verified the exact checkout, immutable image,
allowlist, UID 1000, read-only bind, no published ports, and task-owned cleanup.
Generation produced only terminal blank lines in three legacy models.
`git diff --check` detected them and an exact reverse patch removed only those
whitespace changes. The generated tree is byte-clean and contract-clean.

The post-remediation backend regression command ran these suites in the existing
isolated application runner with explicit `DB_NAME=romm_test_0623`,
`pytest -p no:env -p no:cacheprovider`, and no service restart:

```text
tests/endpoints/roms/test_catalog_removal.py
tests/endpoints/test_saves.py
tests/endpoints/test_screenshots.py
tests/endpoints/test_states.py
tests/endpoints/test_storage_policy_denials.py
tests/handler/database/test_storage_lifecycle.py
tests/handler/filesystem/test_storage_inventory.py
tests/handler/storage/test_legacy_migration.py
tests/integration/test_legacy_migration.py
tests/models/test_safe_lifecycle.py
tests/tools/test_verify_storage_migrations.py
```

The frontend commands were `npm run test`,
`NODE_OPTIONS=--max-old-space-size=4096 npm run typecheck`, the task-owned
`mktemp` and trap build wrapper around `npm run build`, and both locale
scripts. The build output directory used the
`/tmp/romm-p0623-build.*` prefix and was removed by the trap.

## Adversarial and Immutability Coverage

The current tests directly prove:

- catalog removal followed by an injected failure after ROM insertion and an
  existing-ROM scan retry reconnects detached saves, states, and play sessions;
- writable and read-only source manifests preserve path, kind, mode, size,
  SHA-256, and symlink identity across success, rejection, crash, retry,
  rollback, and restart;
- atime remains intentionally excluded until Phase 9;
- stale and replayed confirmation, same-platform reparent, timestamp-colliding
  row substitution, immutable rollback lineage collision, symlink replacement,
  path replacement, and injected transaction failure fail closed;
- STAT-to-HASH replacement cannot exceed either the per-file or remaining
  aggregate byte budget and rejects concurrent replacement;
- mapping removal and external create, upload, write, overwrite, rename, move,
  copy, delete, extract, patch, mkdir, sidecar, and cover paths are denied before
  I/O;
- owned create, replace, delete, and directory capabilities remain available
  only through typed owned descriptors;
- contract-runner cleanup is retryable after a first cleanup failure.

## Static and Privacy Classification

The literal broad Plan 23 Trunk diagnostic used a temporary checkout. Its
frontend ESLint process could not resolve `@eslint/js` from that checkout and
reported 465 runner failures. A later 47-file exact Phase 6 changed-file run had
no code issues and only 16 repetitions of the same frontend runner failure.
Direct ESLint from the repository dependency topology checked all 29 Phase 6
frontend files with the exact repository configuration and returned zero errors.

Backend findings were classified before editing:

- Class A, caused by the two Task 1 commits: none.
- Class B, inherited inside Plans 18 through 26: capability type narrowing and
  one stale variable in `backend/endpoints/sockets/scan.py`; capability type
  narrowing and two silent best-effort cleanup handlers in
  `backend/endpoints/roms/patch.py`.
- Class C, outside Phase 6: two mypy findings in
  `backend/endpoints/export.py`; Black findings in
  `backend/endpoints/roms/screenshot.py`,
  `backend/endpoints/roms/soundtrack.py`, and
  `backend/endpoints/streaming.py`; six ESLint findings in
  `MarkdownViewer.vue`, `RDateField.vue`, and `Player/Stream.vue`.

Only Class B was changed. Commit `d2bf9d2f7` added static-only narrowing,
removed the unused value, and replaced silent cleanup swallowing with bounded
warnings. Hooks passed, the affected 138-test suite passed, and the exact
18-file backend Phase 6 Trunk scope returned zero issues. No rule was disabled,
ignored, or weakened. Trunk also ran its configured security and secret-aware
checks over the Phase 6 backend scope, and the closed source-mutation inventories
passed on both stacks.

## Cleanup Proof

After every acceptance gate:

- task database `romm_test_0623`: 0;
- task-owned database users: 0;
- migration and contract containers: 0;
- contract Node volumes: 0;
- contract environment, log, PID, and build temporary artifacts: 0;
- verifier and contract processes: 0;
- normal application `SELECT 1`: 1 before cleanup and 1 after cleanup;
- tracked changes: 0 before this evidence update;
- pre-existing untracked files: 28, unchanged.

No global or normal application grant was changed. No source content, project
service, deployment, published port, host network, v1 route, or persistent
runtime was mutated.
