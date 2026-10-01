# Phase 22: Bulk Automation for PC Game and DLC Matching - Pattern Map

**Mapped:** 2026-10-01  
**Files analyzed:** 21 anticipated files or file groups  
**Analogs found:** 20 / 21

## File Classification

| New/Modified File                                                            | Role      | Data Flow        | Closest Analog                                        | Match Quality |
| ---------------------------------------------------------------------------- | --------- | ---------------- | ----------------------------------------------------- | ------------- |
| `backend/config/__init__.py`                                                 | config    | event-driven     | Existing scheduled rescan settings                    | exact         |
| `backend/tasks/scheduled/scan_library.py`                                    | task      | batch            | `ScanLibraryTask`                                     | exact         |
| `backend/handler/metadata/pc_automation.py`                                  | service   | batch            | `pc_match_handler.py` plus `scan_handler.py`          | role-match    |
| `backend/handler/metadata/pc_match_handler.py`                               | service   | transform        | Existing Steam/DLC cardinality methods                | exact         |
| `backend/handler/database/roms_handler.py`                                   | service   | CRUD             | PC version-bound application methods                  | exact         |
| `backend/models/pc_automation.py` or existing model module                   | model     | CRUD             | `RomComponentMetadata` in `models/rom.py`             | role-match    |
| `backend/alembic/versions/<revision>_pc_automation_queue.py`                 | migration | transform        | `0132_steam_scan_owned_media_state.py`                | exact         |
| `backend/endpoints/responses/rom.py`                                         | schema    | request-response | PC candidate/selection Pydantic schemas               | exact         |
| `backend/endpoints/roms/pc_automation.py`                                    | route     | request-response | `endpoints/roms/pc_metadata.py`                       | exact         |
| router registration module                                                   | route     | request-response | `endpoints/roms/__init__.py` module imports           | role-match    |
| `backend/tests/handler/metadata/test_pc_automation.py`                       | test      | batch            | `test_pc_match_handler.py` and `test_scan_handler.py` | role-match    |
| `backend/tests/tasks/test_scan_library.py`                                   | test      | event-driven     | Existing scheduled scan tests                         | exact         |
| `backend/tests/endpoints/roms/test_pc_automation.py`                         | test      | request-response | `test_pc_metadata.py`                                 | exact         |
| `backend/tests/integration/test_scan_source_immutability.py`                 | test      | file-I/O         | Existing immutable scan integration test              | exact         |
| `frontend/src/services/api/pcAutomation.ts`                                  | service   | request-response | `services/api/task.ts`                                | exact         |
| `frontend/src/stores/pcAutomation.ts`                                        | store     | CRUD             | `stores/tasks.ts`                                     | exact         |
| `frontend/src/v2/components/Settings/PcAutomationQueue.vue`                  | component | request-response | `TasksSection.vue`                                    | role-match    |
| `frontend/src/v2/views/Settings/Administration.vue`                          | component | event-driven     | Existing tab/query/scope pattern                      | exact         |
| `frontend/src/v2/components/Dialogs/MatchRomDialog.vue` and its types/events | component | request-response | Existing PC target dialog flow                        | exact         |
| `frontend/src/v2/components/Settings/PcAutomationQueue.test.ts`              | test      | request-response | `TasksSection` and `MatchRomDialog.test.ts`           | role-match    |
| `frontend/src/locales/*/settings.json` and related namespace                 | config    | transform        | Existing locale namespace parity                      | exact         |

## Pattern Assignments

### Scheduled discovery and bounded automation

#### `backend/tasks/scheduled/scan_library.py` (task, batch)

**Analog:** `backend/tasks/scheduled/scan_library.py:30-83`

**Task construction and mapping-safe scheduled execution** (lines 30-40, 70-83):

```python
class ScanLibraryTask(PeriodicTask):
    def __init__(self):
        super().__init__(
            title="Scheduled rescan",
            description="Rescans the entire library",
            task_type=TaskType.SCAN,
            enabled=ENABLE_SCHEDULED_RESCAN,
            manual_run=False,
            cron_string=SCHEDULED_RESCAN_CRON,
            func=SCAN_LIBRARY_TASK_FUNC,
        )

    async def run(self) -> dict[str, str]:
        ...
        commands = mapping_scan_commands(
            [], trigger=ScanTrigger.SCHEDULED, scope=ScanScope.LIBRARY,
            scan_type=ScanType.QUICK,
        )
        scan_stats = await execute_mapping_scans(
            commands, metadata_sources=metadata_sources,
        )
        return scan_stats.to_dict()
```

Keep `mapping_scan_commands` and `execute_mapping_scans` as the source-library read boundary. Invoke Phase 22 automation only after that scan has discovered eligible PC records. Do not add raw filesystem iteration or a watcher.

**Provider selection** (lines 50-68):

```python
source_mapping: dict[str, bool] = {
    MetadataSource.IGDB: meta_igdb_handler.is_enabled(),
    ...
}
metadata_sources = [source for source, flag in source_mapping.items() if flag]
if not metadata_sources:
    log.warning("No metadata sources enabled, unscheduling library scan")
    return scan_stats.to_dict()
```

Add Steam through the same enabled-provider map and test the scheduled PC source coverage. Production remains an explicit configuration default of `*/15 * * * *`; do not assume that an RQ cron parser accepts six-field seconds syntax. Model the 10-second UAT path as a documented, testable development override or direct task invocation.

#### `backend/tasks/tasks.py` (task infrastructure, event-driven)

**Analog:** `backend/tasks/tasks.py:89-143`

```python
class PeriodicTask(Task, ABC):
    def init(self) -> Job | None:
        job = self._get_existing_job()
        if self.enabled and not job:
            return self.schedule()
        elif job and not self.enabled:
            self.unschedule()
            return None
        return None

    def schedule(self) -> Job | None:
        if self.cron_string:
            return tasks_scheduler.cron(
                self.cron_string, func=self.func, repeat=None,
                timeout=self.timeout,
                meta={"task_name": self.title, "task_type": self.task_type.value},
            )
        return None
```

Reuse the task registry and scheduler rather than creating a process-local timer. `update_job_meta` at `backend/tasks/tasks.py:25-36` is the existing way to expose transient run progress; the review queue itself must be database-backed.

#### `backend/handler/metadata/pc_automation.py` (new handler, batch)

**Analogs:** `backend/handler/metadata/pc_match_handler.py:56-86`, `:88-120`, `:137-178`, and the PC application helpers below.

**Candidate collection remains non-persistent** (lines 56-86):

```python
class PcMetadataMatchHandler:
    """Adapt configured providers into reviewable, non-persisted candidates."""

    async def collect_candidates(
        self, rom: Rom, query: str | None = None
    ) -> dict[str, PcMetadataProviderResult]:
        title = query or rom.fs_name_no_ext or rom.fs_name
        if " " not in title:
            title = COMPACT_TITLE_BOUNDARY.sub(" ", title)
        return await self._collect_for_title(rom, title)
```

The new handler owns orchestration and state transitions: decide, version-check, apply via existing guarded helpers, or upsert a pending queue row. It must never turn `collect_candidates` into first-result-wins persistence.

**Fail-closed DLC cardinality** (lines 137-178):

```python
validated: list[dict[str, Any]] = []
...
if not self._is_valid_steam_dlc_details(metadata, parent_id):
    continue
validated.append(details)

return validated[0] if len(validated) == 1 else None
```

Use the existing tolerant title threshold only as a filter. A parent must have a trusted positive Steam ID and parent-listed relationship, and the filtered DLC set must contain exactly one item before applying. No match or tie becomes pending review.

### Durable queue and guarded persistence

#### Queue model and migration (model, CRUD)

**Model analog:** `backend/models/rom.py:812-875`  
**Migration analog:** `backend/alembic/versions/0132_steam_scan_owned_media_state.py:16-31`

**Portable migration pattern:**

```python
def upgrade() -> None:
    with op.batch_alter_table("rom_owned_media") as batch_op:
        batch_op.add_column(
            sa.Column("operator_suppressed", sa.Boolean(), nullable=False,
                      server_default=sa.false())
        )
        batch_op.alter_column("operator_suppressed", server_default=None)

def downgrade() -> None:
    with op.batch_alter_table("rom_owned_media") as batch_op:
        batch_op.drop_column("operator_suppressed")
```

Create one portable durable queue table with a unique target identity, preferably parent ROM ID plus nullable component ID and target kind. Store only provider-safe evidence: normalized query, candidate fingerprint/provider IDs, display cover URL, reason/status, expected target version or incarnation, retry timestamps/count, and skip state. Index the pending-state list/sort query. Do not store secrets or provider credentials.

Use `BaseModel` timestamps and SQLAlchemy `Mapped` annotations like the `Rom` model. Keep queue rows in RomM-owned storage, separate from immutable source library paths.

#### `backend/handler/database/roms_handler.py` (database service, CRUD)

**Analog:** `backend/handler/database/roms_handler.py:2428-2463`

```python
@begin_session
def apply_pc_metadata_candidate(
    self, id: int, expected_updated_at: datetime, data: dict[str, Any],
    session: Session = None,
) -> Rom | None:
    ...
    result = session.execute(
        update(Rom)
        .where(and_(Rom.id == id, Rom.updated_at == expected_updated_at))
        .values(**rom_values)
        .execution_options(synchronize_session="evaluate")
    )
    if result.rowcount != 1:
        return None
    session.flush()
    session.expire_all()
    return session.query(Rom).filter_by(id=id).one()
```

**Component guard:** `backend/handler/database/roms_handler.py:2488-2525` scopes the component by parent ID, allowed kind, and `updated_at` before creating its metadata relation.

All automatic, single-review, and batch applications must reload targets server-side and retain these optimistic version checks. A stale target is not a successful write: mark/requeue it for review. Reuse existing selection and media reconciliation helpers so manual fields and operator media protections remain intact.

### Queue API contract

#### `backend/endpoints/roms/pc_automation.py` and response schemas (route, request-response)

**Analog imports and router:** `backend/endpoints/roms/pc_metadata.py:1-42`

```python
from fastapi import HTTPException, Path, Query, Request, Response, status
from decorators.auth import protected_route
from exceptions.endpoint_exceptions import RomNotFoundInDatabaseException
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_rom_visible
from handler.database import db_rom_handler
from utils.router import APIRouter

router = APIRouter()
```

**Read route and response construction:** `backend/endpoints/roms/pc_metadata.py:470-495`

```python
@protected_route(router.get, "/{id}/pc-metadata-candidates", [Scope.ROMS_READ])
async def get_pc_metadata_candidates(
    request: Request,
    id: Annotated[int, Path(description="Rom internal id.", ge=1)],
    query: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> PcMetadataCandidatesResponse:
    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)
    assert_rom_visible(request, rom)
    ...
```

**Mutating route validation and conflict:** `backend/endpoints/roms/pc_metadata.py:498-585`

```python
@protected_route(router.post, "/{id}/pc-metadata-selection", [Scope.ROMS_WRITE])
async def select_pc_metadata_candidate(...):
    ...
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Unknown or unavailable PC metadata candidate")
    updated = db_rom_handler.apply_pc_metadata_candidate(
        id, selection.expected_version, candidate_fields
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="The ROM metadata changed before this selection was applied")
```

Add thin protected endpoints for paginated list/count, accept, correct/requeue, skip, and one-fingerprint batch application. Follow the existing `ROMS_READ` / `ROMS_WRITE` split unless the project has a narrower pre-existing PC-metadata scope. The server must reload every selected queue row, verify pending state, same candidate fingerprint and target kind, target visibility, and expected version before every batch write. Reject stale, mixed, tied, manually protected, or missing targets with `422`/`409`; do not trust client candidate metadata.

Place request and response Pydantic schemas in the existing response module used by the router, then regenerate `frontend/src/__generated__/` before frontend work.

### Frontend review surface

#### `frontend/src/services/api/pcAutomation.ts` (API service, request-response)

**Analog:** `frontend/src/services/api/task.ts:1-26`

```typescript
import api from "@/services/api";

async function getTaskStatus() {
  return api.get<TaskStatusResponse[]>("/tasks/status");
}

export default { getTaskStatus };
```

Use canonical generated request/response types and a small typed API module. Do not manually duplicate backend schemas in the UI.

#### `frontend/src/stores/pcAutomation.ts` (Pinia store, CRUD)

**Analog:** `frontend/src/stores/tasks.ts:6-50`

```typescript
export default defineStore("tasks", {
  state: () => ({ taskStatuses: [] as TaskStatusResponse[] }),
  actions: {
    async fetchTaskStatus(): Promise<TaskStatusResponse[]> {
      try {
        const response = await tasksApi.getTaskStatus();
        this.taskStatuses = response.data;
        return this.taskStatuses;
      } catch (error) {
        console.error("Error fetching task status: ", error);
        this.taskStatuses = [];
        return [];
      }
    },
  },
});
```

Keep page state, loading/error state, pending count, filters/sort, and page-local selected IDs in a dedicated additive store. Filters/sort belong in the Administration route query for shareable review links; open dialog and selection are ephemeral state. Use bounded page size and load-more or virtualization, never render the entire queue.

#### `frontend/src/v2/components/Settings/PcAutomationQueue.vue` (feature component, request-response)

**Analog:** `frontend/src/v2/components/Settings/TasksSection.vue:11-28, 61-102`

```typescript
import { RBtn, RIcon, RSpinner } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted, onUnmounted } from "vue";
import { useI18n } from "vue-i18n";
import { useSnackbar } from "@/v2/composables/useSnackbar";

async function runTask(name: string, title: string) {
  try {
    await taskApi.runTask(name);
    snackbar.success(t("settings.task-started", { title }));
  } catch (err) {
    snackbar.error(...);
  }
}
```

Build this as a v2 feature composite, not a primitive. Reuse `R*` primitives, `useSnackbar`, `useCan`, i18n, native linear DOM order, and `RDialog` for correction. Use control-local `:loading`, an empty state separate from loading, and determinate `RProgressLinear` where job progress is available. Ensure keyboard, touch, mouse, and gamepad operation; page-local multi-selection must expose labels and selection state accessibly.

#### `frontend/src/v2/views/Settings/Administration.vue` (view, event-driven)

**Analog:** `frontend/src/v2/views/Settings/Administration.vue:29-89`

```typescript
type Tab = "users" | "groups" | "tasks";
const validTabs: Tab[] = ["users", "groups", "tasks"];

watch(tab, (newTab) => {
  router.replace({ path: route.path, query: { ...route.query, tab: newTab } });
});

if (auth.scopes.includes("tasks.run")) {
  items.push({ id: "tasks", label: t("settings.tasks"), icon: "mdi-pulse" });
}
```

Add the queue where it naturally belongs in the admin surface, preserve tab query synchronization, and gate it with the matching write permission through `useCan` or the existing scope pattern. Do not add inline role checks.

#### `frontend/src/v2/components/Dialogs/MatchRomDialog.vue` (correction reuse, request-response)

**Analog:** `frontend/src/v2/components/Dialogs/MatchRomDialog.vue:217-228, 234-297, 300-359`

```typescript
const openPcHandler = ({ target, refresh }: Events["showPcMatchRomDialog"]) => {
  pcTarget.value = target;
  pcRefresh.value = refresh;
  ...
  searchText.value = target.label;
};
emitter?.on("showPcMatchRomDialog", openPcHandler);

...
await romApi.selectPcMetadataCandidate({ romId: pcTarget.value.romId, selection });
await pcRefresh.value?.();
snackbar.success(t("rom.rom-updated-successfully"));
```

Launch this existing manual search-and-selection flow from a pending row for correction, then refresh or resolve the queue row only after the server confirms selection. Do not build a parallel candidate picker.

### Tests

**Backend handler/task tests:** copy the existing mocked provider and safe DLC decision shapes in `backend/tests/handler/metadata/test_pc_match_handler.py`, `backend/tests/handler/test_scan_handler.py`, and `backend/tests/tasks/test_scan_library.py`. Cover: exact single parent Steam match applies via guarded paths; absent/multiple candidates upsert one pending row; exact one tolerant parent-listed DLC applies; ties queue; protected/manual metadata and media survive; retries do not duplicate rows; scheduled source mapping includes enabled Steam; and the explicit UAT interval path is testable.

**Endpoint tests:** follow `backend/tests/endpoints/roms/test_pc_metadata.py` for protected-route, malformed candidate, and `409` stale-target assertions. Add paginated list/count, accept, correction/requeue, skip, and batch cases, including mixed candidate fingerprints, mixed target kinds, stale rows, invisibility, and server-side candidate revalidation.

**Frontend tests:** mirror `frontend/src/v2/components/Dialogs/MatchRomDialog.test.ts` for mocked candidate flow and error snackbar behavior. Test queue loading/error/empty states, progress/count refresh, page selection, accept/skip, correction dialog reuse, batch rejection feedback, and keyboard-accessible controls.

## Shared Patterns

### Authentication and visibility

**Source:** `backend/endpoints/roms/pc_metadata.py:98-105, 146-157, 470-479`

Use `@protected_route`, `Scope.ROMS_READ` for listing, `Scope.ROMS_WRITE` for mutations, `RomNotFoundInDatabaseException`, and `assert_rom_visible`. Revalidate every queue target server-side, including each batch member.

### Optimistic concurrency and non-destructive PC writes

**Source:** `backend/handler/database/roms_handler.py:2428-2463, 2488-2519`

All writes take expected `updated_at`, include it in the SQL `WHERE`, and return `None` on conflict. Existing PC metadata helpers remain authoritative for provider merge and media reconciliation. Background work must neither overwrite protected/manual fields nor mutate source-library files.

### v2 errors, loading, permissions, and input

**Sources:** `.claude/skills/frontend-v2-patterns/SKILL.md`, `.claude/skills/frontend-v2-input/SKILL.md`, and `TasksSection.vue:61-102`

Use `useSnackbar` only for meaningful action outcomes, local loading on the pressed control, a separate empty state, `useCan` for client-side gating, `RDialog` for overlay scope, and the existing responsive breakpoint system. No raw watcher UI, new socket instance, raw `v-form`, or custom keyboard navigation.

### OpenAPI and localization

**Sources:** `CLAUDE.md`, `.claude/skills/frontend-i18n/SKILL.md`

Backend Pydantic schemas are the contract. Regenerate generated frontend types after API changes. Every user-visible string uses i18n and every added `en_US` key must be translated in all locale directories; run both locale parity and sorting checks.

## No Analog Found

| File/Concern                            | Role          | Data Flow    | Reason                                                                                                                                                           |
| --------------------------------------- | ------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Persistent PC automation review queue   | model/service | batch + CRUD | The repository has no durable per-item review queue. Compose it from existing SQLAlchemy model, migration, version-bound PC application, and task patterns.      |
| Ten-second UAT scheduler representation | config/task   | event-driven | Current `PeriodicTask` exposes only a cron string. Determine a supported development override or direct UAT invocation with focused tests before implementation. |

## Metadata

**Analog search scope:** `backend/{tasks,handler,models,endpoints,alembic,tests}`, `frontend/src/{v2,services,stores,locales}`, repository instructions and focused skills.  
**Files scanned:** 15 primary analogs and supporting instructions.  
**Pattern extraction date:** 2026-10-01
