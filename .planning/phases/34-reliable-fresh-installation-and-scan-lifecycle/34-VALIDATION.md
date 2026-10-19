---
phase: 34
slug: reliable-fresh-installation-and-scan-lifecycle
status: planned-not-executed
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-18
---
# Phase 34 Validation Strategy

Original plan set created 2026-10-18; additive revision 2026-10-19. Plans 01/02/05 are completed with evidence in their unchanged summaries. The harness and UI-CONTRACT now exist. Remaining task rows are planned, not passing evidence. This revision ran only planning validation, with no runtime implementation/tests, live DB, scan or deployment. No application database fallback is permitted.

## Execution boundary and infrastructure

Canonical target: Linux over ssh team4s-linux, /home/d1sk/pc-game-download-portal. Planning preflight confirmed branch codex/phase-32-pgdp-naming and origin https://github.com/D1skanime/pc-game-download-portal.git. Reverify at execution. Preserve dirty runtime files and unrelated planning changes.

Run all commands below from the canonical repository root. 34-01-1 is a standard-library unittest command outside backend/tests, so it cannot import the destructive parent conftest. The target guard must run before config/handler imports, engine construction, migrations, database creation and clear_database; check the resolved URL again at destructive fixture entry. Reject localhost/application DB names, missing run manifests, inherited targets, application Redis and unowned cleanup resources. Guard negatives assert zero connection/destruction calls.

The Phase34 runner owns a generated project/run token, disposable MariaDB plus Redis services, internal network, minimal test-only credentials, read-only eight-platform synthetic Games fixture and separate owned outputs. It passes environment before imports and overrides pytest.ini's current forced localhost credentials safely. It never loads application .env or dirty development Compose overrides. Every cleanup validates exact labels/ownership. Schema parity independently provisions MariaDB 10.11, MySQL 8.4 and PostgreSQL 15 and performs upgrade, downgrade to the actual pre-phase head, re-upgrade and constraint/CRUD checks.

## Task verification map

Task IDs are plan-task. Every task has an automated command and expected behavior. planned means not executed. No source-string-only check can satisfy a lifecycle, auth, race or fault row.

| Task | Wave | Exact command | Required outcome | Status |
| --- | --- | --- | --- | --- |
| 34-01-1 | 1 | `python3 -m unittest discover -s backend/tools/tests -p test_phase34_target_guard.py -v` | Invalid or application-like targets produce zero engine/connect/create/delete/flush calls, including direct pytest collection and xdist. Valid generated targets retain isolation after pytest-env loading. | completed, verified in 34-01-SUMMARY.md; not rerun by revision |
| 34-01-2 | 1 | `python3 -m unittest discover -s backend/tools/tests -p 'test_phase34*.py' -v` | The CLI rejects unsafe targets before process launch, advertises exact commands, and can run a safe empty isolated pytest smoke with explicit targets. All three database migration directions are enforced by schema mode, not inferred from SQLite. | completed, verified in 34-01-SUMMARY.md; not rerun by revision |
| 34-01-3 | 1 | `python3 backend/tools/phase34.py reproduce --expect-defects` | Both defects have reproducible assertion failures with initialized fixtures. Infrastructure failures cannot count as RED, and the live root cause remains explicitly unconfirmed. | completed, verified in 34-01-SUMMARY.md; not rerun by revision |
| 34-02-1 | 2 | `python3 backend/tools/phase34.py schema --dialects mariadb,mysql,postgresql` | All three isolated dialects upgrade/downgrade/re-upgrade with equivalent uniqueness, seeded-lock and foreign-key behavior; contracts expose only safe logical identities. | completed, verified in 34-02-SUMMARY.md; not rerun by revision |
| 34-02-2 | 2 | `python3 backend/tools/phase34.py backend tests/handler/test_scan_operations.py::test_cleanup_first_operation_creator tests/handler/test_scan_operations.py::test_cleanup_second_operation_creator -q && python3 backend/tools/phase34.py backend tests/handler/test_scan_operations.py -q` | Concurrent same-key submissions leave one row and one dispatch intent. Crashing after commit leaves a lookup-visible pending dispatch. Stale attempts and conflicting resumes produce zero state/item writes. Two consecutive operation-creating tests share one guarded disposable DB and each starts with empty children/operations and exactly one idle singleton slot. | completed, verified in 34-02-SUMMARY.md; not rerun by revision |
| 34-02-3 | 2 | `python3 backend/tools/phase34.py backend tests/endpoints/test_scan_operations.py -q` | Authorization and CSRF fail closed for every route; response loss reconciles by original request key; unsafe scope never reaches scanner/filesystem; accepted pending-dispatch remains observable during Redis failure. | completed, verified in 34-02-SUMMARY.md; not rerun by revision |
| 34-03-1 | 4 | `python3 backend/tools/phase34.py backend tests/tasks/test_scan_operation_dispatch.py -q` | Every injected crash leaves exactly one durable operation with recoverable dispatch and at most one executing attempt. Lost acknowledgements do not create a second job identity; pending acceptance remains queryable. | planned |
| 34-03-2 | 4 | `python3 backend/tools/phase34.py backend tests/endpoints/sockets/test_scan_job_identity.py -q` | Real RQ jobs for all scan families are found and controlled through one boundary; scheduled/manual/watcher attempts cannot overlap the global slot; development and worker modes share acceptance semantics. | planned |
| 34-03-3 | 4 | `python3 backend/tools/phase34.py backend tests/tasks/test_scan_operation_worker.py -q` | Barrier races prove stale writes roll back at the real transaction boundary. stopping persists until confirmed/fenced stop, old completion cannot overwrite it, and indexed results committed before cancellation remain. | planned |
| 34-04-1 | 5 | `python3 backend/tools/phase34.py backend tests/handler/test_scan_operation_checkpoint.py -q` | Only committed server-owned checkpoints are resumable; missing or insufficient proof blocks. Snapshot polling/reconnect causes no scan/hash work, and test counters prove revalidation is scoped/batched. | planned |
| 34-04-2 | 5 | `python3 backend/tools/phase34.py backend tests/tasks/test_scan_operation_recovery.py -q` | Valid interrupted fixtures resume once after fencing. Changed/unproven identity blocks without scanner invocation. Cancelled operations remain cancelled until explicit authorized Resume, with existing results retained. | planned |
| 34-04-3 | 5 | `python3 backend/tools/phase34.py backend tests/handler/test_scan_metadata_result.py -q` | Readable games index despite provider faults, affected game/provider pairs remain visible, targeted retry touches only authorized failed metadata, and security/programming failures are not swallowed. | planned |
| 34-05-1 | 2 | `python3 backend/tools/phase34.py backend tests/handler/test_setup_recovery.py -q` | Snapshot recovers the correct incomplete step and saved assignments using actual DB state; completed installations remain usable and no status check mutates data or enqueues scans. | completed, verified in 34-05-SUMMARY.md; not rerun by revision |
| 34-05-2 | 2 | `python3 backend/tools/phase34.py backend tests/endpoints/test_setup_recovery.py -q` | Post-enrollment recovery requires admin authentication, uncertain saves preserve prior mappings, only missing work is repeated, and all setup actions create zero scan jobs. | completed, verified in 34-05-SUMMARY.md; not rerun by revision |
| 34-06-1 | 5 | `python3 backend/tools/phase34.py frontend src/v2/composables/useSetupRecovery/index.test.ts` | Memory loss and response loss recover the existing admin and assignments without secret persistence, duplicated accounts or duplicate saved mapping work. | planned |
| 34-06-2 | 5 | `python3 backend/tools/phase34.py frontend src/v2/views/Auth/Setup.test.ts src/v2/composables/useSetupRouteGuard/index.test.ts` | All route and partial-success flows are behavioral tests. Completion is explicit, the existing account/mappings remain, and no navigation or finish event silently enqueues scanning. | planned |
| 34-07-1 | 4 | `python3 backend/tools/phase34.py frontend src/v2/data/operations.test.ts` | Backend-generated setup/operation types exist, normalization preserves all existing scan policies and scope, and request identity remains stable across reconciliation. | planned |
| 34-07-2 | 4 | `python3 backend/tools/phase34.py frontend src/v2/data/adapters/scanOperations.test.ts` | One typed command adapter provides stable-key lookup and confirmed snapshots; response loss cannot trigger an independent emit or a duplicate request identity. | planned |
| 34-08-1 | 9 | `python3 backend/tools/phase34.py backend tests/integration/test_scan_operation_faults.py -q && python3 backend/tools/phase34.py e2e --suite lifecycle` | Real service faults show accepted-before-enqueue recovery and stale-worker rejection at commit. Browser state and durable operation/catalog counts agree for every required scenario. | planned |
| 34-08-2 | 9 | `python3 backend/tools/phase34.py production --mode portainer --suite fresh-install` | Separate production worker/Portainer and actual in-app browser acceptance have retained evidence, exact fixture/job/catalog identities and unchanged source manifests. Phase33 remains open on any unmet gate; no live service or source library is touched. | planned |
| 34-08-3 | 9 | `python3 backend/tools/phase34.py schema --dialects mariadb,mysql,postgresql && python3 backend/tools/phase34.py quality && python3 backend/tools/phase34.py evidence --assert-complete` | All required evidence and quality gates pass or the phase remains openly blocked with exact failures. Phase33 closure is recommended only when full fresh-install-through-completed-scan acceptance passes. | planned |
| 34-09-1 | 6 | `python3 backend/tools/phase34.py quality --scope setup-locales --locales en_US,en_GB,bg_BG,cs_CZ` | All en_US, en_GB, bg_BG, cs_CZ recovery values are translated, key/interpolation parity matches en_US, and mounted locale lookup renders cause/action text without raw keys. | planned |
| 34-09-2 | 6 | `python3 backend/tools/phase34.py quality --scope setup-locales --locales de_DE,es_ES,fr_FR,hu_HU,it_IT` | All de_DE, es_ES, fr_FR, hu_HU, it_IT recovery values are translated, key/interpolation parity matches en_US, and mounted locale lookup renders cause/action text without raw keys. | planned |
| 34-10-1 | 7 | `python3 backend/tools/phase34.py quality --scope setup-locales --locales ja_JP,ko_KR,pl_PL,pt_BR` | All ja_JP, ko_KR, pl_PL, pt_BR recovery values are translated, key/interpolation parity matches en_US, and mounted locale lookup renders cause/action text without raw keys. | planned |
| 34-10-2 | 7 | `python3 backend/tools/phase34.py quality --scope setup-locales --locales ro_RO,ru_RU,tr_TR,zh_CN,zh_TW` | All ro_RO, ru_RU, tr_TR, zh_CN, zh_TW recovery values are translated, key/interpolation parity matches en_US, and mounted locale lookup renders cause/action text without raw keys. | planned |
| 34-11-1 | 5 | `python3 backend/tools/phase34.py frontend src/v2/composables/useScanLifecycle/index.test.ts` | Real Vue disposal/remount restores exactly one listener set and one state update per event; timers and stale callbacks cannot survive owner disposal. | planned |
| 34-11-2 | 5 | `python3 backend/tools/phase34.py frontend src/v2/composables/useScanOperationStatus/index.test.ts` | Reload/reopen/reconnect restores the same job and progress with zero submit/cancel calls, no overlapping polls and no stale version rollback. | planned |
| 34-12-1 | 6 | `python3 backend/tools/phase34.py frontend src/v2/composables/useLibraryOperation.test.ts` | Facade states derive from server snapshots, uncertain acceptance never duplicates work, stopping waits for confirmation and intentional cancellation requires explicit Resume. | planned |
| 34-12-2 | 6 | `python3 backend/tools/phase34.py frontend src/v2/views/Scan.test.ts` | Mounted scan UI exposes persistent causes/actions and confirmed state with exact command-count assertions. Scan.vue gains only narrow presentation wiring; the new panel stays <=500 lines. | planned |
| 34-13-1 | 7 | `python3 backend/tools/phase34.py quality --scope scan-locales --locales en_US,en_GB,bg_BG,cs_CZ` | All en_US, en_GB, bg_BG, cs_CZ recovery values are translated, key/interpolation parity matches en_US, and mounted locale lookup renders cause/action text without raw keys. | planned |
| 34-13-2 | 7 | `python3 backend/tools/phase34.py quality --scope scan-locales --locales de_DE,es_ES,fr_FR,hu_HU,it_IT` | All de_DE, es_ES, fr_FR, hu_HU, it_IT recovery values are translated, key/interpolation parity matches en_US, and mounted locale lookup renders cause/action text without raw keys. | planned |
| 34-14-1 | 8 | `python3 backend/tools/phase34.py quality --scope scan-locales --locales ja_JP,ko_KR,pl_PL,pt_BR` | All ja_JP, ko_KR, pl_PL, pt_BR recovery values are translated, key/interpolation parity matches en_US, and mounted locale lookup renders cause/action text without raw keys. | planned |
| 34-14-2 | 8 | `python3 backend/tools/phase34.py quality --scope scan-locales --locales ro_RO,ru_RU,tr_TR,zh_CN,zh_TW` | All ro_RO, ru_RU, tr_TR, zh_CN, zh_TW recovery values are translated, key/interpolation parity matches en_US, and mounted locale lookup renders cause/action text without raw keys. | planned |

## Source coverage audit

ROADMAP Phase34 now records the derived goal and locked D-01 through D-16 contracts: recover incomplete fresh setup and reach a completed first library scan with confirmed durable state, bounded actionable failures, safe restart/cancel recovery and unchanged source storage. The Phase33 dependency means its implemented mapping foundation; its still-open browser acceptance is repeated after stabilization, not a circular prerequisite.

No formal Phase34 requirement IDs were assigned. Use D-01 through D-16 as traceable phase contracts plus existing IDs below, without marking historic requirements complete or inventing PGDP-34 identifiers. SAFE-01 refers to the central read-only storage contract and also preserves the later same-ID transfer safety contract; no transfer feature is added.

| Source | ID / feature | Plans | Coverage |
| --- | --- | --- | --- |
| GOAL | Derived reliable clean setup through first completed scan, normal scan parity and recovery | 01-15 | COVERED by plans, runtime acceptance open |
| REQ | MAP-01, MAP-03, MAP-04, MAP-06 | 05, 06, 08 | COVERED, reuse active mapping foundation |
| REQ | SCAN-01, SCAN-02, SCAN-06 | 02, 03, 04, 07, 08 | COVERED |
| REQ | SAFE-01, SAFE-02, SAFE-05, SAFE-06 | 01, 03, 04, 08 | COVERED |
| REQ | UI-01, UI-03, UI-04, UI-06 | 05, 06, 09-14, 08 | COVERED |
| RESEARCH | Actual listener disposal defect and live-root-cause uncertainty | 01-3, 11-1, 08-1/2 | COVERED |
| RESEARCH | execute_mixed_scans actual RQ callable recognition | 01-3, 03-2 | COVERED |
| RESEARCH | Durable acceptance, key/digest, global slot, dispatch crash gap | 02, 03-1, 08-1 | COVERED |
| RESEARCH | Lease/attempt/version fencing at real catalog commits | 15-1/2, 03-3, 04-2, 08-1 | COVERED |
| RESEARCH | Attempt-owned media staging, COMPLETE preservation and non-atomic SQL/FS recovery | 15-1/2/3, 03-3, 08-1 | COVERED by executable tasks, unimplemented |
| RESEARCH | Source evidence beyond mapping revision, checkpoint trust, bounded scope proof | 04-1/2 | COVERED, unprovable evidence blocks |
| RESEARCH | Authenticated enrolled-admin setup and public enrollment boundary | 05, 06 | COVERED |
| RESEARCH | Per-item provider errors and metadata-only retry with existing merges | 04-3, 12, 13/14, 08-1 | COVERED |
| RESEARCH | Existing status/tasks, Redis/RQ, mapping resolver, one scanner/client | 02-3, 03-1/2, 04, 07 | COVERED |
| RESEARCH | Fail-closed test target, dialect parity, real worker/Portainer/browser proof | 01, 08 | COVERED |
| RESEARCH | Types generation, locale parity, PGDP tokens/input, existing quality failures | 06, 07, 09-14, 08-3 | COVERED |
| CONTEXT | D-01 through D-16 | See decision map | COVERED |

Excluded by explicit source scope: recognition/matching redesign, new download features and unrelated broad visual redesign. Existing subfolder scans, provider/media policy and safety semantics are preserved through the shared operation boundary. No locked decision is deferred or reduced.

## Decision coverage

Every decision has task actions with its ID or explicit inclusive ID range and plan must_haves/contract references. Translation task ownership is exact across all eighteen locales; no UI behavior or locale is dropped.

| Decision | Required behavior | Plan-task coverage |
| --- | --- | --- |
| D-01 | Retain administrator and saved assignments | 05, 06, 09/10, 08 |
| D-02 | Root cause and Retry check | 05, 06, 09/10, 08 |
| D-03 | Reconcile uncertain save and repeat missing work only | 05, 06, 08 |
| D-04 | Completion screen and explicit first-scan CTA | 05, 06, 09/10, 08 |
| D-05 | Confirmed start/queued/running and locked repeated submit | 01, 02, 03, 07, 11, 12, 13/14, 08 |
| D-06 | Durable replay-safe acceptance and enqueue recovery | 02, 03, 07, 12, 08 |
| D-07 | Persistent stalled-job cause and action | 15 publication failure, 03, 04, 11, 12, 13/14, 08 |
| D-08 | Per-game metadata warnings and targeted retry | 04, 12, 13/14, 08 |
| D-09 | Reload/reopen restores same operation | 01, 02, 07, 11, 12, 08 |
| D-10 | Disconnect does not cancel; reconnect restores | 01, 11, 12, 13/14, 08 |
| D-11 | Trusted source/mapping evidence and fenced restart | 15 exact publication recovery, 03, 04, 12, 08 |
| D-12 | Confirmed stop, retained results, explicit Resume | 15 both SQL/FS race orders, 03, 04, 12, 13/14, 08 |
| D-13 | Localized PGDP UI and input accessibility | 01 UI contract, 06, 09/10, 11/12, 13/14, 08 |
| D-14 | Existing scanner, resolver, mapping, RQ/tasks and client | All plans, no parallel execution/transport stack |
| D-15 | Coherent bounded runtime seams and bounded plan scopes | 15 three bounded modules, 03/04/06/07/11/12 decomposition, 08 gate |
| D-16 | Linux, immutable source and isolated owned outputs | 01 guard, all execution boundaries, 08 gate |

## Dependencies and write ownership

| Wave | Plans | Needs / creates |
| --- | --- | --- |
| 1 | 34-01 | Guarded disposable runner, actual RED tests, declared UI contract |
| 2 | 34-02, 34-05 | Operation schema/API plus guarded cleanup; disjoint setup backend |
| 3 | 34-15 | Shared fence, attempt-owned media publication and exact recovery after 02 |
| 4 | 34-03, 34-07 | Durable dispatch/worker fencing consuming 15; disjoint generated contracts/adapter |
| 5 | 34-04, 34-06, 34-11 | Checkpoint/provider recovery; setup runtime; lifecycle/status, all disjoint |
| 6 | 34-09, 34-12 | Setup first nine locales; disjoint scan facade/presentation |
| 7 | 34-10, 34-13 | Setup second nine locales; disjoint scan first nine locales |
| 8 | 34-14 | Scan second nine locales after authoritative en_US batch |
| 9 | 34-08 | Final integrated and production/browser acceptance after both locale chains |

34-15 declares fifteen exact files, including only a narrow storage_access prepared-create seam. Other plan manifests remain at or below twelve. Locale plans 09/10/13/14 each own nine files. Plan07 owns contract generation. New edges: 02->15->03; 15->04 transitively through03. Shared scan.py is owned first by15 then03; scan_handler by15 then04; worker by03 then04. Completed01/02/05 ownership/waves are preserved. Unfinished old waves >=3 shift by one, including07's conservative wave4 placement. Existing dependencies are retained; final08 is wave9. No same-wave overlap or dependency cycle is permitted.

## Defect proof and uncertainty

User-supplied direct runtime-source reproduction transpiled the actual useScanLifecycle installer with installed TypeScript and mocked stores/subscription scope cleanup. Observed: listeners_after_first_install=5, listeners_after_scope_disposal=0, listeners_after_reinstall=0. This behavior-reproduces the lifecycle defect. It does not prove the live auth/setup-to-app route caused the observed hang. 01-3 retains the real Vue scope reproduction and records its RED assertion, then 11-1 must make it GREEN without module reset. 01-3 separately constructs real RQ Job identity for execute_mixed_scans; no source text matching substitutes for that assertion. Keep both regression files after repair.

## Required fault/security proof

Use real services and synchronization barriers for durable acceptance before enqueue, enqueue before acknowledgement, unavailable worker, lease takeover, cancellation and stale catalog commits. The authoritative assertions are SQL operation/item/catalog rows, RQ job IDs, execution lease/attempt/version, actual browser events and immutable fixture manifests. Every route receives anonymous/viewer/foreign-owner/admin/CSRF negatives. Path tests include POSIX absolute, drive, UNC, traversal, symlink swap and revision/source changes before I/O.

Source evidence must be server-created, committed with checkpoints and derived from existing manifest/descriptor identity. Poll/reconnect does not hash or rescan. Restart validates affected scope in bounded batches and existing persisted evidence; superficial root/mapping stats do not prove unchanged contents. Missing proof blocks automatically and offers an explicit user action. Stale workers must fail inside the real catalog-write transaction, not only at progress publication.

## Sampling and evidence gates

Run a task's focused command after its changes. Infrastructure and fake-timer tests target under 60 seconds per batch; real fault/schema/build suites may aggregate bounded batches with progress and per-case deadlines. No watch mode or unbounded acknowledgement waits.

quality --scope setup-locales|scan-locales --locales <comma-separated-codes> sets PGDP_TEST_LOCALES and runs actual mounted vue-i18n rendering plus scoped key/interpolation/sort checks for exactly the requested batch. The source en_US batch precedes its followers. Incomplete sibling batches do not need to pass global parity yet; full all-eighteen-locale parity is mandatory at the final gate. Full quality includes isolated OpenAPI regeneration, typecheck, full frontend tests, build, locale parity/sorting, maintainability and scoped Trunk. Known prior MatchRom/types.test.ts, Settings/pgdpFolderMappings.ts or sourceMutationInventory errors remain failed gates if still present. A PostgreSQL migration failure before this phase is also a failed parity gate, not an excuse to omit that dialect.

production --mode portainer requires an approved Portainer connection and operates on a new labelled disposable stack only. Real worker and production DEV_MODE=false must be exercised. Missing Portainer/browser support is reported promptly as a blocked gate. No credentials are collected. Browser proof includes fresh account, partial assignment/save loss, login/reload continuation, explicit completion CTA, one first scan, indexed fixture games, worker/cancel/provider faults, both themes and all supported input modalities. The final in-app browser walkthrough is required before recommending Phase33 33-06 closure.

Evidence index records command/exit status, fixture run ID, SQL/Redis target identity, revision/build, operation/job/attempt IDs, catalog counts, redacted screenshots, source manifests and cleanup verification. Keep nyquist_compliant=false and wave_0_complete=false until actual guarded tests exist and execute successfully. Document creation alone does not change either flag.

## Original planning sign-off and orchestrator handoff (historical)

- Fourteen PLAN.md files, 33 tasks, eight waves; only plans and this validation document are planner outputs.
- 34-UI-CONTRACT.md is a declared future artifact of 01-3 and an explicit input for UI/acceptance plans; the embedded contract in 34-01-PLAN.md is available immediately.
- 0139 is a proposed filename, not a uniqueness guarantee. Executor must inspect current Alembic heads and revision collisions before writing, resolve a unique revision and update exact plan paths/baseline if necessary.
- Needed orchestrator updates: proposed Phase34 goal above; derive formal requirements from all D-01..D-16 while retaining mapped SCAN/MAP/SAFE/UI contracts; record fourteen plans and revised dependencies; retain Phase33 acceptance as open until 34-08 proof.
- Do not mutate ROADMAP.md, STATE.md, REQUIREMENTS.md, 34-PATTERNS.md or Phase33 artifacts from this planning task.
- No commit, branch change, runtime code edit, live scan, DB reset or deployment is part of planning.

## Revision iteration 1 blocker resolution

1. 34-02 explicitly owns backend/tests/conftest.py. Guarded cleanup detaches the execution-slot FK, deletes new item/checkpoint children before operations and before catalog/user rows, then restores exactly one idle seeded slot. Its two named operation-creating tests run consecutively in one runner invocation against the same disposable DB, each asserting clean child/operation tables and singleton state before leaving committed data for autouse cleanup.
2. 34-03-3 and 34-04-2 cover both race orderings without lock deadlock. Takeover-first pauses BEFORE fence-lock acquisition, lets cancellation/revocation commit, then rejects stale writes. Commit-first commits/releases the valid fenced transaction before cancellation acknowledgement; that legitimate result is retained and all subsequent stale writes fail. Synchronization has deadlines, bounded joins and propagated exceptions, with no sleeps or lock-dependent waits under the held fence.
3. 34-06 owns eight setup runtime/test files. 34-07 owns twelve generated-contract/adapter files. 34-11 owns four lifecycle/status files; 34-12 owns five scan facade/UI files. Locale batches 09/10 (setup) and 13/14 (scan) each own nine exact files, covering all eighteen locales once per namespace. Final08 waits for 10 and 14 and remains the real isolated Portainer/worker/in-app-browser Phase33 reacceptance gate.

No runtime test, code edit, commit, branch change, database reset or deployment was performed during this document revision.

## Approved additive revision validation (2026-10-19)

This section supersedes original planning-only/current-count statements above, not historical evidence. Fifteen plans, 36 tasks, nine waves; actual completion remains 3/15 (01/02/05). Do not change STATE or requirement checkboxes from this revision. Existing UI-CONTRACT is valid and unchanged.

| Task | Wave | Exact command | Required outcome | Status |
| --- | --- | --- | --- | --- |
| 34-15-1 | 3 | `python3 backend/tools/phase34.py backend tests/handler/test_scan_write_fence.py -q` | Real SQL cancellation-first and commit-first, explicit/nested sessions, owner/lease/attempt/slot/intent checks and clean context disposal. No future worker dependency. | planned |
| 34-15-2 | 3 | `python3 backend/tools/phase34.py backend tests/handler/test_scan_media_publication.py -k publication_protocol -q` | Real capability bytes and SQL associations survive failures before/after publish and commit; uncertain commit resolves before exact orphan cleanup; no network under DB lock. | planned |
| 34-15-3 | 3 | `python3 backend/tools/phase34.py backend tests/handler/test_scan_write_fence.py tests/handler/test_scan_media_publication.py -q` | All scan media families including COMPLETE, parent/DLC/Steam and soundtrack pass both race orders; revoked stream has zero final writes/associations and old/new/upload/source assets survive exact cleanup. | planned |

All three added tasks use the existing pre-import disposable-target guard, isolated SQL/Redis, synthetic read-only Games and retained source/cleanup manifests. Test files are implementation outputs, not existing successful tests. 34-08-1 must additionally inject actual media publication/SQL failure and interruption across the same barriers with the real worker; evidence completeness requires those outcomes.

### Completed evidence and current open gates

- 34-01-SUMMARY.md: completed safe harness and defect reproduction; 34-02-SUMMARY.md: completed durable authority with actual portable SQL and cleanup receipts; 34-05-SUMMARY.md: completed setup recovery. Their plans/summaries are protected. No tests were repeated by this revision.
- User-provided latest evidence: setup/recovery 39, frontend 15 and host 23 checks pass; full TypeScript and build pass. Full frontend: 1009 pass, four fail (three Vue RED cases owned by11 and pre-existing POST setup assignment authority-inventory failure owned by06/07). This is not full green.
- Actual RQ job tests: three pass, three fail, checkpoint commit 567e0b80e. Recognition remains RED in03. 34-03 is unimplemented, 0/3 tasks with no product task commits.
- No completed media fault suite, production-like Portainer proof or fresh-install first-scan browser acceptance is inferred. New15 is unimplemented. Checker review is pending.

### Additive four-source coverage audit

| Source | ID / constraint | Executable coverage | Status |
| --- | --- | --- | --- |
| GOAL | Durable first/normal scan, restart/cancel, immutable source | Existing01-14 plus15 publication prerequisite | COVERED by plan set; acceptance open |
| REQ | D-01 through D-16 (ROADMAP phase IDs) | Existing decision table;15 explicitly adds D-07/11/12/14/15/16 | COVERED, no completion marks |
| REQ | SCAN-02, SCAN-06, SAFE-02, SAFE-06 | 15-1/2/3,03-3,08-1; prior mapped IDs retained above | COVERED |
| RESEARCH | Actual 34-02 CAS/leases/global slot, owned capabilities and existing cleanup task | 15-1/2,03-3 | COVERED, one authority |
| RESEARCH | COMPLETE pre-delete, resource streaming, parent/Steam/DLC associations, soundtrack/orphan cleanup | 15-2/3,08-1 | COVERED, explicit failure barriers |
| CONTEXT | D-07 failure cause; D-11 restart; D-12 preserve results | 15-1/2/3 plus unchanged operation/status plans | COVERED |
| CONTEXT | D-14 reuse; D-15 <=500 lines; D-16 immutable Games/Linux | 15 contract, decomposition and every task | COVERED |
| CONTEXT | Deferred recognition redesign and download features | Excluded; existing UI-CONTRACT preserved | EXCLUDED by explicit scope |

No new source item is omitted or deferred. Historical coverage rows remain valid except the explicitly superseded counts/ownership. Independent checker assesses implementation determinism, file budget, lock order, commit uncertainty and exact cleanup. Parent orchestrator then controls execution.
