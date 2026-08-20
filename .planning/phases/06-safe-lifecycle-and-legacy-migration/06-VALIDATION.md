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

## Final Verdict

Plan 06-32 passed every acceptance gate on Linux checkout
`/home/d1sk/romm`, branch `codex/pc-module-analysis`, at source HEAD
`bd4ffd10b`. All 28 observable must-haves and all nine Phase 6 requirements
have current behavioral evidence. No deployment, service restart, branch
change, source-content mutation, or persistent runtime change occurred.

The failures recorded in the previous `06-VERIFICATION.md` are superseded by
Plans 06-27 through 06-31 and the fresh Plan 06-32 execution below.

## Requirement Matrix

| Req    | Fresh executable evidence                                                                                                    |
| ------ | ---------------------------------------------------------------------------------------------------------------------------- |
| CAT-01 | The IDs-only catalog removal request, API contract, and source-delete rejection pass in the complete backend set.            |
| CAT-02 | Catalog removal preserves retained saves, states, and play history; scan reconnection and owned-write integrity pass.        |
| CAT-03 | Mapping removal, lifecycle revision, audit, retention, cleanup intent, and cancellation behavior pass atomically.            |
| CAT-04 | Changed names are denied before every effect; active-v2 element, dynamic, alias, namespace, and route forms are fail-closed. |
| MIG-01 | Only `roms/{fs_slug}` and `{fs_slug}/roms` are automatically detected; custom names remain manual.                           |
| MIG-02 | MariaDB, MySQL, and PostgreSQL pass pristine, seeded, rollback, restart, re-upgrade, collision, and immutable-token probes.  |
| MIG-03 | Unsafe, ambiguous, incomplete, and budget-limited observations remain unselectable with truthful bounded metadata.           |
| MIG-04 | Mapping, migration, rollback lineage, and incarnation identity survive database restart on every dialect.                    |
| MIG-05 | Detection status is explicit, expiring, lower-bound aware, path-safe, and cannot become fallback authority.                  |

## Fresh Execution Results

| Gate                                      | Result                                                                                                                                                                 |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fail-closed environment preflight         | Linux; exact root, branch, origin, project identity, and clean tracked baseline verified                                                                               |
| Focused remaining-gap matrix              | 43 passed, 130 deselected, 2 inherited warnings, exit 0                                                                                                                |
| Complete deduplicated Phase 6 backend set | 577 passed, 4 inherited warnings, 184.55 seconds, exit 0                                                                                                               |
| MariaDB lifecycle verifier                | Pristine, seeded 0110/0111, 0113 lineage, guarded downgrade, rollback, restart, re-upgrade, collision, and bulk forms passed; 59 handler/model tests passed            |
| MySQL lifecycle verifier                  | Same lifecycle and immutable-token matrix passed; handler tests correctly skipped on the minimal 0107 baseline                                                         |
| PostgreSQL lifecycle verifier             | Same lifecycle matrix passed; 59 handler/model tests passed                                                                                                            |
| Controlled generated-contract verifier    | Exact checkout/image/network/user/allowlist/port contract passed, exit 0, all owned resources removed                                                                  |
| Generated frontend contract               | 257 tracked generated files byte-identical before and after cleanup                                                                                                    |
| Focused active-v2 inventory and controls  | 2 files, 26 tests passed, exit 0                                                                                                                                       |
| Full frontend suite                       | 53 files, 659 tests passed, exit 0                                                                                                                                     |
| Frontend typecheck                        | `NODE_OPTIONS=--max-old-space-size=4096`, exit 0                                                                                                                       |
| Production build                          | 4,463 modules, 744 PWA entries, 790 output files, trapped output removed, exit 0                                                                                       |
| Locale parity and sorting                 | 17 peer locales complete and sorted, exit 0                                                                                                                            |
| Active-v2 inventory                       | 436 production modules, 19 reachable services, 13 external mutation operations, 10 owned descriptor kinds, 19 reviewed route families, zero forbidden live authorities |
| Plans 27-31 backend static scope          | 9 files, Trunk reported no issues                                                                                                                                      |
| Plans 27-31 frontend static scope         | Repository-topology ESLint reported zero errors                                                                                                                        |
| Repository diff gate                      | `git diff --check` passed                                                                                                                                              |
| Cleanup and normal access                 | Every exact task-owned resource absent; normal application `SELECT 1` returned 1 before and after                                                                      |

## Commands and Exit Status

### Focused gap regressions

Run in the existing application container with task-only database
`romm_test_0632`, `-p no:env`, and `-p no:cacheprovider`:

```text
docker exec -e DB_NAME=romm_test_0632 -e ROMM_AUTH_SECRET_KEY=[test-only] --workdir /app/backend romm-dev /app/.venv/bin/pytest -p no:env -p no:cacheprovider tests/endpoints/test_storage_policy_denials.py tests/handler/database/test_storage_lifecycle.py tests/handler/storage/test_legacy_migration.py tests/handler/filesystem/test_storage_access.py -k "changed_fs_name or incarnation_tokens or lower_bound or deadline or owned_create_retries_short_write or owned_replace_retries_short_write or owned_writes_retry_interrupted or owned_writes_reject_invalid_progress or owned_writes_rollback_after_partial_failure" -x
```

Exit 0. The 43 selected cases prove:

- changed `fs_name` denial precedes unmatch, provider, database, cache,
  collection, response, owned-resource, and filesystem effects;
- unchanged `fs_name` retains metadata and owned-resource behavior;
- Rom and RomFile tokens reject instance flush, statement values, query update,
  ORM executemany, bulk mapping, and bulk save forms;
- entry, time, file, aggregate, descriptor deadline, and returned-byte budget
  exits expose `lower_bound=true` through persistence and public serialization;
- owned create and replace retry short and interrupted writes, reject invalid
  progress, clean failed creates, and preserve replace targets on failure.

### Complete backend regression

```text
docker exec -e DB_NAME=romm_test_0632 -e ROMM_AUTH_SECRET_KEY=[test-only] --workdir /app/backend romm-dev /app/.venv/bin/pytest -p no:env -p no:cacheprovider tests/endpoints/roms/test_catalog_removal.py tests/endpoints/sockets/test_scan.py tests/endpoints/test_saves.py tests/endpoints/test_screenshots.py tests/endpoints/test_states.py tests/endpoints/test_storage.py tests/endpoints/test_storage_policy_denials.py tests/handler/database/test_storage_lifecycle.py tests/handler/filesystem/test_storage_access.py tests/handler/filesystem/test_storage_inventory.py tests/handler/storage/test_legacy_migration.py tests/handler/storage/test_read_context.py tests/integration/test_legacy_migration.py tests/models/test_safe_lifecycle.py tests/tasks/test_detect_legacy_storage.py tests/tools/test_verify_phase6_contracts.py tests/tools/test_verify_storage_migrations.py -x
```

Exit 0, 577 passed. No restrictive `-k` selector was used.

### Three-dialect lifecycle authority

The quoted in-container launcher failed before resource creation because the
application image intentionally has no Docker client. The same checked-in
standard-library verifier was then run with the already proven host launcher:

```text
cd backend && python3 tools/verify_storage_migrations.py --dialects mariadb mysql postgresql --handler-tests --handler-test-repetitions 1
```

Exit 0. MariaDB, MySQL, and PostgreSQL each passed pristine upgrade, seeded
0110 and 0111 upgrade, bounded 0112 normalization, 0113 lineage, guarded
downgrade refusal, exact rollback, restart, re-upgrade, timestamp-collision
substitution rejection, and the complete ORM mutation matrix. The displayed
downgrade tracebacks are expected negative evidence. MariaDB and PostgreSQL
each passed 59 handler/model tests; MySQL handler tests were skipped only for
the declared minimal 0107 baseline.

### Controlled contract and generated tree

```text
cd backend && python3 tools/verify_phase6_contracts.py --source-container romm-dev --checkout /home/d1sk/romm --expected-image romm-romm-dev --network romm_default --user 1000:1000 --entrypoint /bin/sleep --command infinity --env-allowlist DB_HOST,DB_NAME,DB_PASSWD,DB_PORT,DB_USER,REDIS_DB,REDIS_HOST,REDIS_PORT,REDIS_SSL,ROMM_BASE_PATH --port 39006
```

Exit 0. The generator emitted one terminal blank line in each of three legacy
generated models. A checked exact reverse patch removed only those task-owned
formatting side effects. SHA-256 manifests for all 257 generated files then
matched the preflight baseline byte for byte. No OpenAPI or frontend contract
change remains.

### Frontend and static gates

```text
docker exec --workdir /app/frontend romm-dev npm run test -- src/v2/sourceMutationInventory.test.ts src/v2/sourceMutationControls.test.ts
docker exec --workdir /app/frontend romm-dev npm run test
docker exec -e NODE_OPTIONS=--max-old-space-size=4096 --workdir /app/frontend romm-dev npm run typecheck
docker exec --workdir /app/frontend romm-dev npm run build -- --outDir /tmp/romm-p0632-build.<nonce>
docker exec --workdir /app/frontend romm-dev python3 src/locales/check_i18n_locales.py
docker exec --workdir /app/frontend romm-dev python3 src/locales/check_i18n_sorted.py
```

All exited 0. The build used a `mktemp` directory guarded by an EXIT trap;
the exact output directory was absent afterward.

Trunk checked all nine Plans 27-31 backend files with no issues. Its temporary
frontend checkout could not resolve `@eslint/js` and reported a runner
failure, not a code finding. The repository-owned ESLint dependency topology
then checked `frontend/src/v2/sourceMutationInventory.test.ts` with exit 0.
No lint rule was disabled or weakened.

## Source Manifest Proof

Before every source-sensitive flow, its test fixture records a sorted manifest.
Every comparison uses the complete tuple below, not hashes alone:

- normalized root-relative path;
- entry type;
- permission mode;
- byte size;
- SHA-256 digest for every regular file;
- symlink identity and exact symlink target;
- atime intentionally excluded until Phase 9.

Writable and read-only fixtures retain the same tuple across catalog removal,
mapping removal, detection, preview, confirmation, migration, injected failure,
retry, first use, rollback, restart, filename denial, owned cleanup, and scan
reconnection. All corresponding assertions passed in the 577-test set. Source
content and structure were unchanged.

## Inventory Closure

The live extractor and inventory entry point directly cover property access,
string element access, default/named/aliased/namespace/nested clients, literal
and immutable concatenated routes, and shared-service calls. Mutable methods,
mutable routes, conditional receivers, and non-reducible expressions fail
closed with bounded importer-only diagnostics. The live repository inventory
found zero forbidden active-v2 authorities.

## Cleanup Proof

Cleanup used only exact task-owned identities and never broad discovery for
deletion:

- database `romm_test_0632`: 0;
- task database grants: 0;
- exact dialect containers: 0;
- contract-labeled containers and Node volumes: 0;
- contract environment, log, and PID files: 0;
- trapped build directories: 0;
- verifier and contract processes: 0;
- generated contract differences: 0 across 257 files;
- tracked differences before evidence write: 0;
- pre-existing untracked status entries: 28, exact baseline preserved;
- normal application `SELECT 1`: 1 before and 1 after cleanup.

No credentials were printed or persisted. No normal application grant, service,
deployment, published port, branch, source tree, or persistent runtime was
changed.
