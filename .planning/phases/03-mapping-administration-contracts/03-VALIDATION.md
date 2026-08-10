---
phase: 03
slug: mapping-administration-contracts
status: executed
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-10
---

# Phase 03 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property                  | Value                                                                                                                                                                                                                                                                                        |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Framework**             | pytest 9.x, pytest-asyncio 1.x, pytest-xdist 3.x, Hypothesis 6.x                                                                                                                                                                                                                             |
| **Config file**           | `backend/pytest.ini`, root `pyproject.toml`, `backend/tests/conftest.py`                                                                                                                                                                                                                     |
| **Quick run command**     | `cd backend && uv run pytest tests/endpoints/test_storage.py tests/handler/database/test_storage_handler.py tests/handler/filesystem/test_storage_resolver.py -x -q`                                                                                                                         |
| **Full phase command**    | `cd backend && uv run pytest tests/endpoints/test_storage.py tests/handler/database/test_storage_handler.py tests/handler/filesystem/test_storage_resolver.py tests/models/test_storage.py tests/tools/test_verify_storage_migrations.py -x`                                                 |
| **Container fallback**    | `docker exec romm-dev sh -lc 'cd /app/backend && uv run pytest <selection> -x'` because host `uv` is unavailable                                                                                                                                                                             |
| **Cross-dialect command** | `python3 backend/tools/verify_storage_migrations.py --dialects mariadb mysql postgresql` plus `python3 backend/tools/verify_storage_migrations.py --dialects mariadb postgresql --handler-tests --handler-test-repetitions 10`                                                               |
| **Trunk CI gate**         | `trunk_tmp="$(mktemp -d)" && curl -fsSL https://trunk.io/releases/trunk -o "$trunk_tmp/trunk" && chmod u+x "$trunk_tmp/trunk" && "$trunk_tmp/trunk" version && "$trunk_tmp/trunk" check --all`; this reproduces pinned `trunk-action` launcher setup and `.trunk/trunk.yaml` pins CLI 1.25.0 |
| **Contract gate**         | Start task-owned Uvicorn in `romm-dev` on unexported `127.0.0.1:39003`, poll `/openapi.json`, then run Node 24 with `--network container:romm-dev` and matching explicit `openapi` CLI flags; PID-signature trap cleanup is mandatory and host networking is forbidden                       |
| **Estimated runtime**     | Narrow task selection: target 30 seconds or less; focused phase suite: target 120 seconds or less; cross-dialect and generated-contract gates measured separately                                                                                                                            |

## Isolated OpenAPI Generation Gate

The executable command is the `<automated>` block in `03-06-PLAN.md` Task 2. Its verified environment contract is:

1. `romm-dev` bind-mounts the canonical backend at `/app/backend` and provides `uv` plus `curl`. Start only `uv run uvicorn main:app --host 127.0.0.1 --port 39003 --no-access-log` with the test-only `ROMM_AUTH_SECRET_KEY`; do not run `main.py`, migrations, workers, or watchers.
2. Container port 3000 is already the RomM Vite listener and maps to host port 3100 in this checkout. Leave it untouched. Port 39003 is loopback-only inside the existing `romm-dev` network namespace and has no host publication.
3. Preflight the task PID file before installing the trap. The trap kills only the PID whose `/proc/<pid>/cmdline` matches the exact Uvicorn host/port signature, then removes only the task PID/log and dynamically named task node_modules volume. `pkill`, `killall`, and broad process matching are forbidden.
4. Poll `http://127.0.0.1:39003/openapi.json` from `romm-dev` for at most 60 seconds. A timeout is a failed gate and still runs cleanup.
5. Run `node:24-bookworm` with `--network container:romm-dev`; host network mode is forbidden. Invoke local `./node_modules/.bin/openapi` against the same loopback URL with the exact generator flags from `frontend/package.json`, then run `npm run typecheck`.
6. Do not inspect, restart, stop, or connect to Team4s containers/services, and do not use host port 3000.

## Sampling Rate and Gates

- **After every task commit:** Run the narrowest affected test selection from the map with `-x -q`.
- **After every plan:** Run every test file changed or introduced by that plan plus `git diff --check`.
- **After every plan wave:** Run the full phase command. If the wave changes a migration, also run the cross-dialect command. If it changes a route or response schema, also regenerate OpenAPI types and run frontend typecheck.
- **Before `$gsd-verify-work`:** Run the full backend suite, the full phase command, all three migration dialects plus ten MariaDB/PostgreSQL handler repetitions, the official pinned-launcher Trunk CI gate, generated OpenAPI types, frontend typecheck, and the source-mutation evidence.
- **Max feedback latency:** 30 seconds per task-level sample, 120 seconds per focused phase sample. Migration/container and full-repository gates may exceed 120 seconds and therefore run only at wave or phase boundaries.
- **Failure rule:** Stop the current task or wave on the first failing automated gate. Do not defer a red test to a later plan.
- **No watch mode:** Every command terminates and returns an exit status suitable for CI.

## Provisional Per-Task Verification Map

Final task IDs and waves must replace these provisional rows after planning. Each final implementation task must inherit at least one automated command from its requirement row.

| Provisional Task   | Requirement                                     | Threat Ref                                          | Secure Behavior                                                                                                                                                          | Test Type               | Automated Command                                                                                                                                                       | File Exists                | Status  |
| ------------------ | ----------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ------- |
| 03-01-T2           | MAP-02, AUD-01, AUD-02                          | T-03-AUDIT-LOSS, T-03-INACTIVE-RESERVE              | Existing mappings migrate to active/version 1; inactive rows release identities; audit snapshots survive actor/mapping lifecycle without storing container paths         | model/migration         | `cd backend && uv run pytest tests/models/test_storage.py tests/tools/test_verify_storage_migrations.py -x`                                                             | Planned in 03-01 RED/GREEN | planned |
| 03-02-T2, 03-04-T2 | API-01, API-04                                  | T-03-ENUM, T-03-HEALTH-WRITE                        | Admin receives live safe health; GET emits no database update; anonymous and non-admin callers learn no root structure                                                   | endpoint/filesystem     | `cd backend && uv run pytest tests/endpoints/test_storage.py -k "root and (health or auth)" -x`                                                                         | Planned in 03-02 and 03-04 | planned |
| 03-02-T2, 03-04-T2 | API-02, API-04                                  | T-03-TRAVERSAL, T-03-SYMLINK, T-03-CURSOR, T-03-DOS | Only immediate contained directories appear in bounded deterministic pages; replayed/malformed cursor and traversal fail safely                                          | property/endpoint       | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py tests/endpoints/test_storage.py -k "browse or cursor or traversal or symlink" -x`        | Planned in 03-02 and 03-04 | planned |
| 03-03-T2, 03-05-T2 | MAP-01, MAP-03, MAP-05, API-03                  | T-03-SOURCE-MUTATION, T-03-PATH-LEAK                | Mapping test validates target and active conflicts but writes no mapping, audit, catalog, or source bytes                                                                | handler/endpoint        | `cd backend && uv run pytest tests/handler/database/test_storage_handler.py tests/endpoints/test_storage.py -k "test_mapping or non_mutating or conflict" -x`           | Planned in 03-03 and 03-05 | planned |
| 03-03-T2, 03-05-T2 | MAP-01, MAP-02, MAP-04, MAP-05, API-03          | T-03-DUPLICATE-RACE, T-03-OVERLAP-RACE              | Ordered locks allow distinct siblings and serialize duplicate/ancestor/descendant active inserts; errors expose IDs but no paths                                         | integration/concurrency | `cd backend && uv run pytest tests/handler/database/test_storage_handler.py tests/endpoints/test_storage.py -k "create or concurrent or overlap or duplicate" -x`       | Planned in 03-03 and 03-05 | planned |
| 03-03-T2, 03-05-T2 | MAP-02, MAP-03, MAP-06, API-03                  | T-03-STALE-WRITE, T-03-FALLBACK                     | Create never revives history; explicit reactivation/update/deactivate require current integer version; stale commands return typed 409; removal preserves catalog/source | handler/endpoint        | `cd backend && uv run pytest tests/handler/database/test_storage_handler.py tests/endpoints/test_storage.py -k "version or update or remove or activate or missing" -x` | Planned in 03-03 and 03-05 | planned |
| 03-03-T2, 03-05-T2 | AUD-01, AUD-02, API-04                          | T-03-REPUDIATION, T-03-PATH-LEAK                    | Mutation and audit append commit atomically; read/test/preview create no audit; admin-only keyset history is filtered, newest first, and path-safe                       | model/handler/endpoint  | `cd backend && uv run pytest tests/models/test_storage.py tests/handler/database/test_storage_handler.py tests/endpoints/test_storage.py -k audit -x`                   | Planned in 03-03 and 03-05 | planned |
| 03-06-T1           | MAP-03, MAP-06, API-03, TEST-02                 | T-03-FALLBACK, T-03-UNBOUNDED                       | Preview returns the fixed count/ID/version/truncated/cursor allowlist, no candidate names/paths, and is bounded/non-mutating with typed missing-mapping conflict         | endpoint/integration    | `cd backend && uv run pytest tests/endpoints/test_storage.py -k preview -x`                                                                                             | Planned in 03-06           | planned |
| 03-06-T2           | API-01, API-02, API-03, API-04, AUD-02, TEST-02 | T-03-SCHEMA-LEAK                                    | OpenAPI exposes typed admin contracts and stable errors but never `container_path`, NAS paths, raw errors, or unrelated mapping paths                                    | OpenAPI/static          | `cd backend && uv run pytest tests/endpoints/test_storage.py -k "openapi or schema or leak" -x`                                                                         | Planned in 03-06           | planned |

## Requirements Coverage Matrix

| Requirement | Automated Coverage                                                              | Phase Gate Evidence                                                   |
| ----------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| MAP-01      | Successful contained assignment through handler and API                         | Focused suite plus cross-dialect migration                            |
| MAP-02      | Active lifecycle, second-active rejection, concurrent creation                  | Model, handler concurrency, and migration suite                       |
| MAP-03      | Source manifest and mutation tripwires across test/create/update/remove/preview | Focused suite plus final before/after manifest review                 |
| MAP-04      | Multiple distinct sibling directories under one root                            | Handler and API integration tests                                     |
| MAP-05      | Equal, ancestor, descendant, and canonical cross-root overlap                   | Resolver/handler concurrency and HTTP 409 tests                       |
| MAP-06      | Typed `platform_mapping_missing`, no fallback or empty success                  | Endpoint tests for browse/test/preview and scan-related contract seam |
| API-01      | Live root health, no GET persistence, safe response schema                      | Endpoint test and SQL update tripwire                                 |
| API-02      | Relative-only contained browse, stable bounded cursor                           | Property, resolver, and endpoint tests                                |
| API-03      | Read/create/update/test/preview/remove typed routes                             | Endpoint lifecycle matrix and generated OpenAPI types                 |
| API-04      | Anonymous 401, authenticated non-admin 403, admin success                       | Parameterized endpoint authorization matrix                           |
| AUD-01      | Actor/time/platform/action and old/new snapshots in same transaction            | Handler rollback/commit tests and audit query tests                   |
| AUD-02      | No host, NAS, raw error, or unrelated path leakage                              | Sentinel-based response, OpenAPI, and audit tests                     |
| TEST-02     | Entire API behavior matrix                                                      | `backend/tests/endpoints/test_storage.py` plus focused phase suite    |

## Wave 0 Requirements

- [ ] Add `backend/tests/endpoints/test_storage.py` with reusable authenticated admin, non-admin, and anonymous clients; live root fixtures; safe error sentinels; lifecycle matrix; browse cursors; preview; and OpenAPI assertions.
- [ ] Extend `backend/tests/handler/filesystem/test_storage_resolver.py` with immediate-directory browse, global deterministic order, `heapq.nsmallest(limit + 1)` O(limit) retention, hard scan-ceiling rejection, malformed/query-mismatched cursor rejection, symlink/traversal cases, and a late-smaller-entry fixture that forbids premature termination after one page.
- [ ] Extend `backend/tests/handler/database/test_storage_handler.py` with integer version conflicts, active/inactive lifecycle, ordered concurrent create/update, active-only overlap, atomic audit, rollback, catalog preservation, and source mutation tripwires.
- [ ] Extend `backend/tests/models/test_storage.py` with lifecycle defaults, version increment contract, portable indexes/constraints, audit field allowlist, bounded actor snapshot, and no destructive audit relationship.
- [ ] Extend `backend/tools/verify_storage_migrations.py` and its tests for pristine 0109 downgrade/re-upgrade plus pre-DDL rejection of real inactive/versioned/audited lifecycle history on MariaDB, MySQL, and PostgreSQL; add `--handler-test-repetitions` for explicit concurrency repetitions.
- [ ] Add a reusable recursive source manifest fixture that excludes atime and captures relative name, kind, size, mode, modification timestamp, link target, and content hash where applicable.
- [ ] Extend mutation tripwires to test, preview, create, update, deactivate, reactivate, and removal. Guard write-mode `open`, temporary files, mkdir, unlink, rename, replace, copy, move, extraction, and scanner/catalog mutation calls.
- [ ] Add two-session concurrency fixtures proving one winner and one bounded 409-equivalent domain conflict without deadlock or raw vendor diagnostics.
- [ ] Add cursor fixtures with version, root/parent or filter binding, maximum encoded length, final sort key, invalid encoding, wrong types, and stale/replayed query context.
- [ ] Add generated-contract checks or a deterministic OpenAPI snapshot assertion for every public storage request, response, and error model.

## Plan, Wave, and Phase Gates

### Per-Plan Gate

1. All tests named in the plan task's `<automated>` block pass.
2. Source mutation tests run for every plan that touches resolver, lifecycle, preview, or persistence.
3. `git diff --check` is clean and the plan changes no out-of-scope scanner/UI behavior.
4. Migration plans prove both upgrade and downgrade locally before their plan summary is accepted.

### Per-Wave Gate

1. Full phase command passes.
2. Cross-dialect verifier passes pristine round trips and lifecycle-history downgrade preflight after any schema change.
3. Generated OpenAPI and frontend typecheck pass after any route/schema change.
4. Concurrency handler tests pass exactly ten repetitions each on MariaDB and PostgreSQL when lifecycle locking changes.
5. No response, audit row, or captured log includes sentinel absolute/NAS/unrelated paths or raw SQL/OS text.

### Phase Completion Gate

1. Full backend pytest suite is green.
2. Full Phase 3 suite is green with no xfail or skip hiding a Phase 3 requirement.
3. MariaDB, MySQL, and PostgreSQL each pass pristine 0109 upgrade/downgrade/re-upgrade and fail closed before DDL for inactive/versioned/audited lifecycle history.
4. The official Trunk launcher used by pinned CI action `75699af...` reports CLI 1.25.0 from `.trunk/trunk.yaml` and `trunk check --all` passes.
5. Backend OpenAPI generation and frontend typecheck pass.
6. Source tree manifests are byte-for-byte equivalent before and after every mapping lifecycle operation.
7. Independent verification maps all thirteen Phase 3 requirements to passing evidence.

## Manual-Only Verifications

| Behavior                                                                                     | Requirement           | Why Manual                                                                                                                    | Test Instructions                                                                                                                       |
| -------------------------------------------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Real NAS latency, protocol-specific permissions, mount transitions, and access-time behavior | API-01, API-02        | The approved production NAS and maintenance window are Phase 9 scope; local/container fixtures cannot prove protocol behavior | Do not activate or mutate production NAS in Phase 3. Phase 9 runs the approved read-only mount matrix and records operational evidence. |
| Browser administration usability                                                             | API-01 through API-03 | V2 administration UI is Phase 7 and its design contract is Phase 4                                                            | No Phase 3 browser acceptance is required. Validate only backend OpenAPI and generated client compatibility.                            |

All Phase 3 backend behaviors, authorization decisions, pagination contracts, path-safety properties, concurrency rules, and audit semantics must be automated. Manual checks cannot substitute for any Phase 3 requirement.

## Latency Budget and Flake Policy

| Sample                               | Target                                         | Action if Exceeded                                                                                      |
| ------------------------------------ | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Single unit/property selection       | 10 seconds                                     | Narrow selection or reduce only non-security Hypothesis examples locally; keep CI profile authoritative |
| Endpoint or handler task selection   | 30 seconds                                     | Split by keyword/test node while retaining direct requirement coverage                                  |
| Focused phase suite                  | 120 seconds                                    | Partition by resolver, handler, endpoint, and model at task level; keep combined run at wave gate       |
| Cross-dialect migration              | Measured separately, expected over 120 seconds | Run at schema wave and phase gates, never after unrelated tasks                                         |
| Full backend plus generated contract | Measured separately                            | Run once at final phase gate and in CI                                                                  |

- A security/concurrency test that flakes is red, not acceptable evidence.
- Repeat concurrency tests enough to exercise both transaction orderings; record the repeat count in the implementing plan.
- Do not weaken Hypothesis profiles, timeouts, or assertions to meet latency targets.
- If a focused task command exceeds 30 seconds, record the measured runtime and split the selection while keeping every task sampled.

## Validation Sign-Off

- [x] Final plan task IDs and waves replace all provisional rows.
- [x] Every final task has an automated verification command or an explicit RED dependency.
- [x] Sampling continuity has no three consecutive tasks without automated verification.
- [x] RED tasks cover every missing test, fixture, migration, and generated-contract reference.
- [x] No watch-mode flags are used.
- [x] Task-level feedback latency is measured and remains below 30 seconds.
- [x] Focused phase feedback latency is measured and remains below 120 seconds.
- [x] MariaDB, MySQL, and PostgreSQL migration cycles pass.
- [x] All API/OpenAPI/audit path-leak assertions pass.
- [x] `nyquist_compliant: true` is set only after the final plan-task map is complete.
- [x] `wave_0_complete: true` is set only after every Wave 0 test/fixture exists and passes.

**Approval:** execution evidence complete; repository-wide Nginx and Trunk debt is recorded in deferred-items.md
