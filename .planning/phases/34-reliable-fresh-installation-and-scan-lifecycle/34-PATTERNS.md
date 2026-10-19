# Phase 34: Reliable fresh installation and scan lifecycle - Pattern Map

**Mapped:** 2026-10-18
**Environment:** Linux via team4s-linux, /home/d1sk/pc-game-download-portal
**Branch:** codex/phase-32-pgdp-naming, unchanged
**Scope:** Bounded source mapping from 34-CONTEXT.md and 34-RESEARCH.md. No live diagnosis, tests, commits or runtime changes.

## File Classification

Paths marked proposed are planning suggestions, not existing files. Wildcards denote bounded file families whose exact names the planner must choose. Existing integration targets need not all change.

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| backend/models/scan_operation.py (proposed) | model | CRUD | backend/handler/database/mapping_previews_handler.py | partial, persistence seam only |
| backend/handler/database/scan_operations_handler.py (proposed) | service | CRUD | backend/handler/database/mapping_previews_handler.py | role-match |
| backend/alembic/versions/<next>_scan_operations.py (proposed) | migration | batch | no migration excerpt inspected | no analog established |
| backend/endpoints/scan_operations.py (proposed) | controller | request-response | backend/endpoints/tasks.py | role-match |
| backend/endpoints/responses/scan_operations.py (proposed) | model | transform | backend/endpoints/tasks.py status response construction | partial |
| backend/tasks/scan_operation_dispatch.py (proposed) | service | event-driven | existing RQ integration in backend/endpoints/sockets/scan.py | partial |
| backend/handler/scan_operation_recovery.py (proposed) | service | batch | backend/handler/storage/read_context.py | partial, identity validation only |
| backend/endpoints/sockets/scan.py | controller | event-driven | existing mapped execution and ScanStats | exact integration seam |
| backend/handler/scan_handler.py | service | file-I/O | existing execute_mapped_scan call boundary | exact integration seam |
| backend/startup.py | config | event-driven | research identifies existing job restoration | research-only seam |
| backend/endpoints/setup.py | controller | request-response | existing discover_setup_folders / assign_setup_folders | exact integration seam |
| backend/endpoints/responses/setup.py | model | transform | frontend/src/services/api/setup.ts response contract | partial |
| backend/endpoints/heartbeat.py | controller | request-response | existing setup flag described in research | research-only seam |
| frontend/src/services/api/setup.ts | service | request-response | existing discoverFolders / assignFolders | exact |
| frontend/src/plugins/router.ts | route | request-response | existing setup guards, lines 571-593 | exact integration seam |
| frontend/src/v2/views/Auth/Setup.vue | component | request-response | existing finishWizard and discovery retry | exact |
| frontend/src/v2/composables/useSetupRecovery.ts (proposed) | hook | request-response | Setup.vue submission orchestration | role-match extraction |
| frontend/src/v2/data/contracts.ts | model | transform | frontend/src/v2/data/operations.ts request construction | partial |
| frontend/src/v2/data/operations.ts | utility | transform | existing buildLibraryScanRequest | exact |
| frontend/src/v2/data/adapters/legacy/scan.ts | service | event-driven | research identifies current emit boundary | research-only seam |
| frontend/src/v2/data/adapters/scanOperations.ts (proposed) | service | request-response | frontend/src/services/api/setup.ts | role-match |
| frontend/src/v2/composables/useLibraryOperation.ts | hook | event-driven | existing operation orchestration | exact integration seam |
| frontend/src/v2/composables/useScanLifecycle/index.ts | hook | event-driven | frontend/src/v2/composables/useSocketEvent/index.ts | role-match disposal |
| frontend/src/v2/composables/useScanOperationStatus.ts (proposed) | hook | request-response | frontend/src/v2/composables/useServerConnection/index.ts | role-match polling |
| frontend/src/v2/views/Scan.vue | component | event-driven | Setup.vue retry UI; RAlert primitive | role-match |
| frontend/src/v2/components/Scan/OperationSummary.vue | component | transform | existing component, path verified | integration target, not excerpted |
| frontend/src/locales/** (affected locale files) | config | transform | Setup.vue useI18n / t calls | partial |
| frontend/src/__generated__/** (regenerated if schema changes) | model | transform | backend-owned API convention in CLAUDE.md | generated, not hand-written |
| backend/tests/handler/test_scan_operations.py (proposed) and focused endpoint/task tests | test | event-driven | backend/tests/handler/test_scan_command.py | role-match |
| frontend/src/v2/composables/useScanLifecycle/index.test.ts (proposed), useLibraryOperation.test.ts, useServerConnection/index.test.ts, views/Scan.test.ts | test | event-driven | existing behavior tests in useLibraryOperation.test.ts | role-match |
| isolated fixture guard and setup/scan browser fault tests (paths to be selected) | test | request-response | no complete isolated lifecycle fault harness established | no analog |

## Pattern Assignments

### 1. Durable operation persistence, acceptance and RQ projection

Primary persistence analog: backend/handler/database/mapping_previews_handler.py, lines 6-11 and 24-39:

~~~python
from sqlalchemy import select
from sqlalchemy.orm import Session

from decorators.database import begin_session
from handler.database.base_handler import DBBaseHandler
from models.mapping_preview import MappingPreview
~~~

~~~python
    @begin_session
    def mark_pending(self, mapping_id: int, revision: int, *, session: Session = None) -> MappingPreview:  # type: ignore
        preview = session.scalar(
            select(MappingPreview)
            .where(MappingPreview.mapping_id == mapping_id)
            .with_for_update()
        )
~~~

Apply imports/session conventions to the proposed operation repository. This is a locking seam, NOT a complete idempotency protocol: a missing row is not locked by this lookup. Design unique request-key constraints, conflict handling, payload digest comparison, concurrent-start serialization and dispatch intent explicitly.

Status/auth analog: backend/endpoints/tasks.py, lines 190-196 and 346-347:

~~~python
    match TaskType(task_type):
        case TaskType.SCAN:
            return ScanTaskStatusResponse(
                task_type=TaskType.SCAN,
                meta={"scan_stats": job_meta.get("scan_stats")},
                **common_data,  # trunk-ignore(mypy/typeddict-item)
            )
~~~

~~~python
@protected_route(router.get, "/{task_id}", [Scope.TASKS_RUN])
async def get_task_by_id(request: Request, task_id: str) -> TaskStatusResponse:
~~~

Reuse _build_task_status_response, existing Job.fetch and queue connections. Imports at lines 4-8, 15 and 28-34 establish FastAPI, RQ, protected_route and shared Redis conventions. Authorize every operation lookup/mutation and enforce the intended ownership policy; a route scope alone does not establish ownership.

Error seam: tasks.py lines 356-362 maps fetch exceptions to HTTPException(404). Do not copy its broad exception classification into new recovery logic: Redis outages must remain distinguishable from missing jobs.

Progress seam: backend/endpoints/sockets/scan.py, lines 420-421:

~~~python
            update_job_meta({"scan_stats": self.to_dict()})
            await socket_manager.emit("scan:update_stats", self.to_dict())
~~~

Reuse persisted RQ scan_stats as projection input. Add durable operation lineage, version and attempt fencing around the existing execution. Events notify; authenticated snapshots reconcile. No second queue or scanner.

### 2. Immutable mapped execution and storage identity

backend/handler/scan_command.py, lines 23-30:

~~~python
@dataclass(frozen=True, slots=True)
class MappedScanCommand:
    mapping_id: int
    expected_revision: int
    trigger: ScanTrigger
    scope: ScanScope
    scan_type: str
    options: tuple[tuple[str, str], ...] = ()
~~~

Copy this identity contract by reuse/import, not by defining another command class. Validation at lines 32-57 bounds options and rejects path-bearing input.

backend/handler/storage/read_context.py, lines 83-88:

~~~python
        if (
            mapping.id != self.mapping_id
            or mapping.version != self.expected_revision
            or not mapping.active
        ):
            raise StaleMappedReadError(self.mapping_id, self.expected_revision)
~~~

Lines 90-98 additionally verify root activity, reachability, readability and read-only policy. Reuse MappingReadContext, its repository injection seam and backend/handler/filesystem/storage_resolver.py. Mapping revision/root health alone are not proof of unchanged source content across restart; absent sufficient source evidence, block recovery.

Concrete execution seam: backend/endpoints/sockets/scan.py lines 1488-1526, execute_mapping_scan, delegates through execute_mapped_scan and scopes the existing fs_rom_handler before calling scan_platforms. Preserve mapping_scan_commands, execute_mapping_scans and execute_mixed_scans as the existing command/execution pipeline; extract coherent orchestration if necessary.

Job identity seam: same file lines 335-351 derives the direct scan function identity but recognizes only that function and SCAN_LIBRARY_TASK_FUNC. Research identifies manual execute_mixed_scans jobs as missing. Unify recognition for duplicate checks, stopping and startup recovery; test actual enqueued callable identities. Do not copy the incomplete set.

Metadata warning/retry changes belong at existing execution/result boundaries. No provider-specific analog was inspected; do not create a parallel provider loop or swallow storage/auth/programming errors.

### 3. Setup mapping, routing and typed API

frontend/src/services/api/setup.ts, lines 47-53:

~~~typescript
function discoverFolders() {
  return api.get<SetupFolderDiscovery>("/setup/folders");
}
function assignFolders(assignments: SetupFolderAssignment[]) {
  return api.post<SetupFolderAssignmentResponse>("/setup/folders/assign", {
    assignments,
  });
}
~~~

Reuse the shared API client and these assignment endpoints. Response lines 24-36 already expose mappings, ready and root_health. Existing backend/endpoints/setup.py entry points are discover_setup_folders (line 19) and assign_setup_folders (line 39). Keep initial-admin public access bounded; post-enrollment recovery requires authentication.

frontend/src/v2/views/Auth/Setup.vue, lines 137-144:

~~~typescript
    await identityApi.login(adminUser.value.username, adminUser.value.password);
    await refetchCSRFToken();
    const { data } = await setupApi.assignFolders(assignments.value);
    if (!data.ready) {
      throw new Error(t("setup.folders-not-ready"));
    }
    await auth.fetchCurrentUser();
    await heartbeat.fetchHeartbeat();
~~~

Extract server reconciliation and missing-step orchestration into a focused composable. The current createdUserId guard is memory-only, and the current HOME redirect at line 145 is not the requested explicit first-scan completion action.

Routing seam: frontend/src/plugins/router.ts lines 571-593. Separate admin enrollment from server-confirmed setup completion across this guard and backend/endpoints/heartbeat.py. Do not reopen anonymous administrator creation or persist passwords.

### 4. Vue lifecycle disposal and operation contracts

frontend/src/v2/composables/useSocketEvent/index.ts, lines 50-59:

~~~typescript
  let stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    socket.off(event, wrapped);
  };

  onScopeDispose(stop);

  return { stop };
~~~

Reuse this idempotent, scope-owned cleanup with the shared socket import at line 24. Fix ownership in useScanLifecycle/index.ts at lines 60-64, where the module-global installed guard is set. Its observer unsubscribe seam is lines 49-53. Pair installation/disposal and cancel debounced work; prove remount reinstalls exactly once. Do not add a second socket or lifecycle store.

frontend/src/v2/data/operations.ts, lines 58-65:

~~~typescript
    permissions: { scopes: ["tasks:run"] },
    idempotencyKey: input.operationId,
    jobId: input.operationId,
    retry: { maxAttempts: 3 },
    execution: {
      maxConcurrency: 1,
      cancelable: true,
      resumable: true,
~~~

These are existing client contract fields, not proof of server-enforced idempotency or resumability. Preserve stable request identity during reconciliation. Adapt contracts.ts and the transport boundary to the backend schema.

useLibraryOperation.ts integration seams: observer registration line 191, optimistic running assignment line 255, cancel lines 267-281 and resume line 299. Replace optimistic accepted/running/cancelled projection with confirmed snapshots. Connection loss must not become cancellation.

### 5. Server polling and UI primitives/errors

frontend/src/v2/composables/useServerConnection/index.ts, lines 75-81:

~~~typescript
  function scheduleNext() {
    const delay = heartbeat.connected ? POLL_ONLINE_MS : POLL_OFFLINE_MS;
    setTimeout(async () => {
      await heartbeat.fetchHeartbeat({ timeout: HEARTBEAT_TIMEOUT_MS });
      scheduleNext();
    }, delay);
  }
~~~

Reuse self-rescheduling, awaited requests and per-call timeout. Operation polling needs explicit timer disposal, bounded reconciliation, stale-response/version handling and terminal-state stop. This existing application-lifetime heartbeat loop has no per-view cleanup. Its detached effect scope (lines 65-72) is an ownership example, not a replacement for operation reconciliation. Do not duplicate reachability orchestration.

UI analog: Setup.vue lines 172-190 renders loading, role="alert" and localized Retry via RSpinner, RIcon and RBtn. Imports at lines 2-5 and 16 show @v2/lib, Vue, vue-i18n and useSnackbar. Catch/finally at lines 146-155 demonstrates detail extraction and submitting reset; persistent scan failure must also remain inline.

frontend/src/v2/lib/primitives/RAlert/RAlert.vue lines 28-41 defines error/warning tones, title/text and optional closable; lines 71-75 use semantic CSS variables. Reuse RAlert and RBtn rather than new primitives; keep persistent operation failures visible. Localize cause/next action and new state labels across locale files.

### 6. Isolated fault tests

backend/tests/handler/test_scan_command.py lines 8-20 exercises real immutable command construction; lines 23-33 parameterize rejected source paths. Reuse pytest parametrization and injected repositories (MappingReadContext.repository) for deterministic identity/restart faults.

frontend/src/v2/composables/useLibraryOperation.test.ts lines 41-61 injects failing work and a sleep recorder into withRateLimitBackoff:

~~~typescript
      async () => {
        attempts += 1;
        if (attempts < 3) throw { retryable: true, retryAfterMs: 7 };
        return "ok";
      },
~~~

Reuse dependency-controlled faults and assert attempts/results. Add mount/unmount/remount and fake-timer tests for event/timer ownership and late snapshots. Existing views/Scan.test.ts uses readFileSync/source-string assertions; it is not evidence of runtime recovery. useServerConnection/index.test.ts only checks the reconnect predicate.

Safety seam: backend/tests/conftest.py lines 91-117 automatically migrates and deletes database contents. Do not run that harness until a dedicated disposable database/user/network and Redis isolation are validated before imports. No complete fail-closed isolated acceptance harness was established in this bounded mapping.

Fault coverage: immediate/double click; delayed/lost acceptance after persistence; accepted-before-enqueue crash; unavailable worker; reload/disconnect; server/worker restart; changed mapping/source; intentional cancellation and stale attempts; per-item metadata failure. Assert authoritative operation/job counts and indexed results. Production-like worker/Portainer and clean-install browser proof remain separate acceptance gates. No test was executed for this map.

## Shared Patterns

- Backend owns API schemas; regenerate frontend/src/__generated__/** after contract changes. Reuse the shared Axios/CSRF and Redis/RQ infrastructure.
- Use protected_route and Scope.TASKS_RUN for commands/status, with ownership checks and bounded safe diagnostics.
- Reuse MappedScanCommand, MappingReadContext, storage_resolver and existing scan execution. No duplicate storage/mapping resolver, source-path persistence or scan lifecycle.
- New runtime modules must remain <=500 lines. Existing scan.py (1861 lines), scan_handler.py (1603), Scan.vue (1572) and router.ts (637) need narrow integration/extraction seams. Extract operation repository, dispatch/recovery, setup recovery, status reconciliation and UI status panels by responsibility.
- Source Games stay read-only; progress/checkpoints/assets remain application-owned. Keep intentional cancellation durable and distinct from interrupted execution.
- Follow focused .claude/skills guides before implementation edits. This artifact performs source mapping only and changes no runtime code.

## No Analog Found

| Needed behavior | Existing partial reuse | Missing contract |
|---|---|---|
| Durable scan acceptance/idempotency | DB session/row locking, client idempotencyKey, RQ | unique-key/digest enforcement, atomic dispatch intent and reconciliation |
| Restart-safe continuation | mapped command/revision/read context | proven unchanged source evidence, checkpoint/lease fencing and cancellation lineage |
| Persistent enrolled-admin setup recovery | setup APIs, auth/CSRF, routing | server-derived completion and missing-step reconciliation |
| Full isolated fault/browser harness | pytest and Vitest unit seams | fail-closed fixture identity and integrated fault injection |

Use 34-RESEARCH.md for these designs. No wider search or provider survey is needed.

## Metadata

**Analog search scope:** Selected backend handlers/endpoints/tasks/tests and frontend v2 composables/data/setup/scan primitives, plus setup API and router.
**Primary pattern families:** Five: DB/RQ, immutable mapped execution, setup/API, Vue ownership/polling, UI/tests.
**Files classified:** 31 rows, including proposed families and integration-only targets.
**Files read/excerpted:** 17 source/test files plus selected symbol/path checks; research-only targets are labeled.
**Extraction date:** 2026-10-18.
**Verification:** Canonical Linux host/path/branch/origin and Phase 34 state verified before artifact creation. Existing unrelated work preserved. No runtime-cause or passing-test claim.

## Approved additive publication ownership (2026-10-19)

34-15 (wave 3, after 02) owns scan_write_fence.py, begin_session integration, scan_media_publication.py and scan_media_recovery.py. It extracts/delegates existing media writers rather than duplicating provider download logic. storage_access.py gains only the prepared-create seam over its existing staged capability. Use composition.owned[RESOURCES], open_owned_access and existing CREATE/DELETE/MKDIR capabilities; no ambient path authority. New production modules each remain <=500 logical lines.

The shared context binds operation_id, attempt_id and lease_owner. checked_scan_write(session, expected_version=None) locks existing singleton slot then operation and checks live owner/attempt/state/lease/cancel flag. Its models/session-only import boundary prevents the decorator -> repository -> decorator cycle and needs no future worker module. 34-03 binds this context to actual manual/scheduled/watcher/development execution and owns lease/dispatch/progress/catalog behavior.

Publication requires a durable bounded owned manifest before staging; streamed bytes and transformations stay outside row locks. Immutable family-compatible filenames, same-session associations and cleanup intents preserve old assets until successful replacement. The manual validator requires a direct child. COMPLETE must force refresh without pre-deleting. Include parent provider and Steam inventories, DLC import/reconcile, soundtrack embedded and orphan covers, screenshots/manuals/covers/special media and other scan-reachable artwork/badges. Broad provider handlers cannot swallow fence revocation or uncertain commits.

Recovery joins the existing scheduled/owned_media_cleanup.py runner, verifies manifest-generated exact objects and all live catalog reference surfaces before unlink, handles interrupted processing claims, and never deletes resource directories or another attempt's files. Existing legacy/base filesystem and non-scan consumers retain their contracts. Library watcher integration is backend/watcher.py, not manual/sync_folder_scan.py.

File ownership edges: 15 -> 03 for scan.py and shared fence consumption; 15 -> 04 for scan_handler.py; 03 -> 04 for worker. All earlier overlaps remain dependency ordered. Completed plans 01/02/05 and their summaries are protected. No new UI contract is needed.
