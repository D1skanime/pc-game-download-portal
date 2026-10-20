# Phase 33: Fresh Install First Run, PC Storage Mapping Before Library Scan - Pattern Map

**Mapped:** 2026-10-15
**Repository:** `/home/d1sk/pc-game-download-portal` on the verified Linux checkout
**Context status:** Phase 33 has no `CONTEXT.md` or `RESEARCH.md`; scope was derived from the requested concerns and current implementation.
**Files analyzed:** 25 primary analogs
**Analogs found:** 25 / 25

## File Classification

| New/Modified Area | Role | Data Flow | Closest Analog | Match Quality |
| --- | --- | --- | --- | --- |
| `backend/endpoints/heartbeat.py` setup-library contract | endpoint/controller | request-response + filesystem read | same file, `get_setup_library_info()` | exact |
| `backend/handler/filesystem/platforms_handler.py` | filesystem handler | file I/O + transform | same file, `get_platforms()` / `detect_library_structure()` | exact |
| `backend/endpoints/storage.py` | endpoint/controller | CRUD + request-response | same file, mapping routes | exact |
| `backend/models/storage.py` | model | CRUD/persistence | same file, `StorageRoot` and `PlatformStorageMapping` | exact |
| `backend/handler/filesystem/storage_resolver.py` | utility/service | file I/O + validation | same file, `resolve_directory()` | exact |
| `backend/endpoints/sockets/scan.py` | scan controller | event-driven + request-response | `mapping_scan_commands()` call site | exact |
| `backend/tasks/scheduled/scan_library.py` | task/service | batch + event-driven | same file, scheduled scan gating | exact |
| `backend/tests/endpoints/test_heartbeat.py` | backend test | request-response | setup-library tests | exact |
| `backend/tests/endpoints/test_storage.py` | backend test | CRUD + auth/error contract | storage mapping route tests | exact |
| `backend/tests/endpoints/storage/test_legacy_bootstrap_paths.py` | backend test | file I/O + mapping bootstrap | same file | exact |
| `backend/tests/handler/filesystem/test_platforms_handler.py` | backend test | file I/O | empty-library and structure tests | exact |
| `backend/tests/tasks/test_scan_library.py` | backend test | batch/event-driven | unmapped scan skip test | exact |
| `frontend/src/v2/views/Home.vue` | view/controller | request-response + conditional routing | empty-library state | exact |
| `frontend/src/v2/views/Auth/Setup.vue` | view/controller | request-response + wizard state | first-run wizard orchestrator | exact |
| `frontend/src/v2/components/Auth/SetupStepPlatforms.vue` | component | transform/presentation | detected structure/platform display | exact |
| `frontend/src/v2/views/Storage/PlatformStorageMapping.vue` | view/controller | CRUD + file I/O browsing | storage mapping wizard | exact |
| `frontend/src/v2/views/Storage/PlatformStorageMapping.test.ts` | frontend test | request-response | mapping missing/unmapped state test | exact |
| `frontend/src/v2/components/Settings/FolderMappingsSection.vue` | component/controller | CRUD + transform | admin platform-folder mapping table | role-match |
| `frontend/src/v2/components/Settings/FolderMappingPlatformCell.vue` | component | request-response UI | mapping picker cell | role-match |
| `frontend/src/v2/router/routes.ts` | route registry | request-response/navigation | existing setup and mapping route entries | exact |
| `frontend/src/v2/router/routeInventory.ts` | route metadata | transform/navigation | route outcome registry | exact |
| `frontend/src/v2/composables/useLibraryOperation.ts` | composable/service | event-driven + request-response | scan operation lifecycle | role-match |
| `frontend/src/v2/composables/useScanLifecycle/index.ts` | composable/service | streaming/event-driven | global scan socket lifecycle | exact |
| `.planning/phases/22-*/22-UAT.md` | UAT artifact | batch + browser request-response | isolated synthetic PC-library UAT | role-match |
| `.planning/phases/27-*/27-UAT.md` | UAT artifact | deployment/request-response | clean-install UAT evidence table | role-match |

## Pattern Assignments

### Fresh-install and empty-library routing

**Primary analog:** `frontend/src/v2/views/Home.vue` (lines 93-150, 177-230)

Use a computed empty state that waits for all initial fetches to finish before deciding the library is empty. The existing guard combines all relevant collections/platforms/ROM loading flags with empty result checks:

```ts
const isEmpty = computed(
  () =>
    !fetchingPlatforms.value &&
    !fetchingCollections.value &&
    !fetchingRecent.value &&
    recentRoms.value.length === 0 &&
    continuePlayingRoms.value.length === 0 &&
    filledPlatforms.value.length === 0 &&
    allCollections.value.length === 0,
);
```

The filesystem snapshot is lazy and permission-tolerant. It calls `setupApi.getLibraryInfo()` only once when the empty state appears and hides the optional chips if the request fails. Keep this separation between catalog emptiness and filesystem discovery.

**Routing analogs:** `frontend/src/v2/router/routes.ts` lines 8-20 and `frontend/src/v2/router/routeInventory.ts` lines 1-25. Add routes to both registries, use lazy imports, and keep route keys synchronized with `ROUTES`.

### Setup wizard state and first-run probe

**Primary analog:** `frontend/src/v2/views/Auth/Setup.vue` (lines 1-109, 118-209, 230-301)

The view owns wizard state and async flights; step components remain presentation-oriented and emit/model their values. Copy these patterns:

```ts
const step = ref<1 | 2 | 3>(1);
const libraryInfo = ref<SetupLibraryInfo>({ ...EMPTY_LIBRARY_INFO });
const loadingLibrary = ref(true);
const libraryError = ref<string | null>(null);

const canProceed = computed(() => {
  if (step.value === 1) return !loadingLibrary.value;
  // validate the current step before allowing navigation
  return true;
});

async function loadLibraryInfo() {
  loadingLibrary.value = true;
  libraryError.value = null;
  try {
    const { data } = await setupApi.getLibraryInfo();
    if (data) libraryInfo.value = data;
  } catch {
    libraryError.value = t("setup.loading-library-failed");
  } finally {
    loadingLibrary.value = false;
  }
}
```

The template has explicit loading and retry-error states before the step transition. Preserve `:disabled="!canProceed || submitting"`, button-level `:loading`, and `onMounted(loadLibraryInfo)`.

**Backend probe analog:** `backend/endpoints/heartbeat.py` lines 192-288. It exposes `/api/setup/library`, detects Structure A (`roms/{platform}`) or B (`{platform}/roms`), returns `existing_platforms` with `fs_slug` and `rom_count`, and always returns supported platform metadata. Access is public only while no admin users exist; otherwise the route requires the platform-read scope.

**Setup display analog:** `frontend/src/v2/components/Auth/SetupStepPlatforms.vue` lines 1-37 and 40-87. Normalize detected filesystem slugs through the supported-platform map, display the detected structure pattern, and render an explicit `RAlert` when no platforms are detected.

### Empty-library filesystem bootstrap and platform-to-subfolder mapping

**Primary analog:** `backend/handler/filesystem/platforms_handler.py` lines 37-95 and 110-161.

The handler gives Structure A precedence, falls back to `ROMS_FOLDER_NAME` when detection is inconclusive, resolves filesystem slugs before constructing paths, and creates the default `roms` folder when no structure exists:

```py
def get_platform_fs_structure(self, fs_slug: str) -> str:
    resolved_slug = resolve_filesystem_slug(
        fs_slug,
        lambda slug: Path(
            self.base_path,
            self._build_platform_fs_structure(slug, cnfg),
        ).exists(),
    )
    return self._build_platform_fs_structure(resolved_slug, cnfg)

@staticmethod
def _build_platform_fs_structure(fs_slug: str, cnfg) -> str:
    return (
        f"{fs_slug}/{cnfg.ROMS_FOLDER_NAME}"
        if cnfg.has_structure_path_b
        else f"{cnfg.ROMS_FOLDER_NAME}/{fs_slug}"
    )
```

For a fresh empty root, `get_platforms()` catches missing target errors, calls `create_library_structure()`, logs the bootstrap, and returns `[]`. Do not interpret a missing folder as an internal error or as a non-empty flat platform list.

**Setup test analog:** `backend/tests/endpoints/test_heartbeat.py` lines 113-265 covers Structure A, Structure B, no detected structure, and filesystem-error fallback. Reuse the patching style and assert the complete response contract, especially `detected_structure`, `existing_platforms`, and `supported_platforms`.

### Admin storage mapping UI

**Primary analog:** `frontend/src/v2/views/Storage/PlatformStorageMapping.vue` lines 1-181, 183-317, 319-378, 381-527, 530-741.

This is the closest exact analog for a platform-to-storage-subfolder flow. Copy its state shape and four-step safety sequence:

```ts
interface Draft {
  rootId: number | null;
  relativePath: string;
  testedKey: string | null;
}

async function testDraft() {
  if (draft.value.rootId === null) return;
  testing.value = true;
  try {
    await storageApi.testMapping({
      platform_id: platformId.value,
      storage_root_id: draft.value.rootId,
      relative_path: draft.value.relativePath,
      ...(mapping.value ? { mapping_id: mapping.value.id } : {}),
    });
    draft.value.testedKey = testKey.value;
    step.value = 4;
  } finally {
    testing.value = false;
  }
}
```

The UI loads roots, mapping, and preview in parallel (`Promise.all`), treats a 404 or `platform_mapping_missing` conflict as the normal unmapped state, uses `RSkeletonBlock` for first load, and uses `safeMessage()` to convert bounded API error details into snackbar text. Saving selects `createMapping` versus `updateMapping` and sends `expected_version` for optimistic concurrency.

The template uses `RSteps` for Root → Folder → Test → Save, `RList`/`RListItem` for browsing, and `RBtn :loading` on mutations. Removal obtains server-side consequences before `useConfirm`, keeps original files unchanged, and sends the expected version and observed consequence count.

**Admin table analog:** `frontend/src/v2/components/Settings/FolderMappingsSection.vue` lines 1-36, 70-166, 217-330, 333-411. It demonstrates the established admin mapping surface: `RTable`, typed rows, sortable/filterable derived data, scope/config writability gating, refresh on mount, and success/error snackbars after API mutations. `FolderMappingPlatformCell.vue` is the closest picker-cell analog.

### Backend storage mapping contract

**Primary analog:** `backend/endpoints/storage.py` lines 1-115, 963-1044, 1125-1207.

Keep endpoints thin: `@protected_route`, `assert_admin(request)`, typed response models, handler delegation, and bounded conversion of `StorageResolutionError` into stable API responses. The create/update route pattern is:

```py
@protected_route(
    router.post,
    "/mappings",
    [Scope.USERS_WRITE],
    status_code=status.HTTP_201_CREATED,
    response_model=StorageMappingSchema,
    responses=_MAPPING_RESPONSES,
)
def create_storage_mapping(request: Request, body: StorageMappingCreateSchema):
    assert_admin(request)
    try:
        mapping = db_storage_handler.create_mapping(
            body.platform_id,
            body.storage_root_id,
            body.relative_path,
            **_actor(request),
        )
    except StorageResolutionError as error:
        if isinstance(error, (DuplicateStorageMappingError, StorageMappingOverlapError)):
            _raise_mapping_conflict(error)
        _raise_safe_storage_error(error)
    return _mapping_schema(mapping)
```

The preview route reads the active mapping and root, calls `preview_storage_mapping`, and returns bounded counts/cursors. The model analog is `backend/models/storage.py` lines 35-102: roots are external read-only, mapping paths are relative, mappings carry `active` and `version`, and relationships are explicit.

**Path-safety analog:** `backend/handler/filesystem/storage_resolver.py` lines 60-83 and 266-348. Normalize POSIX relative paths, allow `""` only when explicitly representing the root, reject backslashes/drives/absolute paths/`.`/`..`, require active external read-only roots, reject symlinks, resolve strictly, and verify the target remains under the approved root.

### Scan gating and lifecycle

**Backend analog:** `backend/endpoints/sockets/scan.py` lines 1728-1750. Build scan commands through `mapping_scan_commands`; catch `MissingPlatformStorageMappingError`; emit `scan:done_ko` with a bounded user-facing message; return when the command list is empty. This is the gate that must prevent a fresh install from scanning before mapping exists.

**Scheduled-scan analog:** `backend/tasks/scheduled/scan_library.py` lines 51-95 and `backend/tests/tasks/test_scan_library.py` lines 95-136. Check the feature flag, collect enabled metadata sources, build mapped commands, and skip execution when no active mappings produce commands. Do not let an unmapped platform make the scheduled scan fail.

**Frontend lifecycle analog:** `frontend/src/v2/composables/useScanLifecycle/index.ts` lines 1-23, 49-69, 71-115, 195-224. Install the socket lifecycle once, notify observers on started/stats/completed/failed, update the scanning store, reconcile platforms after `scan:done`, and surface `scan:done_ko` through the snackbar channel. `useLibraryOperation.ts` lines 137-180 is the higher-level operation state machine for queued/running/completed/retryable/failed outcomes.

## Test and UAT Assignments

### Backend tests

- `backend/tests/endpoints/test_heartbeat.py:113-265`: setup-library response contract, Structure A/B, empty detection, and graceful filesystem failure.
- `backend/tests/handler/filesystem/test_platforms_handler.py`: use the existing empty-library, path-construction, and directory-listing tests as the analog for fresh-root bootstrap and `roms/{platform}` versus `{platform}/roms`.
- `backend/tests/endpoints/test_storage.py`: preserve authorization-before-handler assertions, typed OpenAPI response assertions, conflict/error-code assertions, and bounded serialization. The existing tests around lines 720-793 show the preview/confirmation style and the absence of raw filesystem details.
- `backend/tests/endpoints/storage/test_legacy_bootstrap_paths.py:1-14`: keep platform-specific legacy bootstrap tests isolated and explicit when PC/Windows aliases are involved.
- `backend/tests/tasks/test_scan_library.py:95-136`: direct analog for “no active mapping means no scan execution.”

### Frontend tests

- `frontend/src/v2/views/Storage/PlatformStorageMapping.test.ts:1-123`: hoisted API mocks, mocked router/store/composables/primitives, `flushPromises`, and the assertion that `platform_mapping_missing` renders the unmapped state rather than a generic error.
- Add setup/empty-routing coverage beside the existing router and setup tests, following `frontend/src/v2/router/v2Boot.test.ts:26-68` for importable route/boot invariants and the `Home.vue` empty-state contract for loading-versus-empty behavior.
- If a new v2 primitive is introduced, follow `.claude/skills/frontend-v2-components/SKILL.md`: one `R*` folder, story, theme variants, and `play()` for meaningful interaction. Prefer existing primitives and feature composites here.

### UAT artifact

**Primary analog:** `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md` lines 8-22, 24-38, 128-163. Use a disposable synthetic PC fixture, a read-only source mount, unique Compose project identity, pre/post manifest evidence, and browser steps that first register the root and mapping, then run the scan. Never use the live library, NAS path, real ROMs, production database, or real credentials.

**Install proof analog:** `.planning/phases/27-reproduzierbare-portainer-docker-installation-f-r-die-romm-v/27-UAT.md` lines 1-23. Record scenario/result/evidence rows for rendered stack, empty disposable state, healthy app/database, first-run behavior, and exact cleanup. Browser evidence is required for the routing and mapping experience; container health alone is not sufficient for those UI claims.

## Shared Patterns

### Authorization and permission boundaries

- Backend routes use `@protected_route` plus `assert_admin`/scope constants before observing or mutating storage state.
- Setup library information is public only for the no-admin first-run window; once an admin exists, platform-read authorization is required.
- v2 feature views use `useCan("app.admin")` where appropriate. Existing settings mapping uses the working `authStore.scopes.includes("platforms.write") && CONFIG_FILE_WRITABLE` gate; preserve the backend as source of truth.

### Empty, loading, and error states

- Do not render an empty state while initial requests are still pending.
- Use `RSkeletonBlock` for known first-load layouts, `RSpinner` for an indeterminate non-control load, and inline `RBtn :loading` for actions.
- Field/input errors stay in place; meaningful operation failures use `useSnackbar()`; 401/403 handling remains centralized in the API layer.
- A missing mapping is a normal unmapped state, not a generic failure. Unreachable roots and invalid paths remain explicit error states.

### Storage safety

- Canonical mapping state is `(storage_root_id, relative_path, version)`.
- Root mode is `external_read_only`; original files remain unchanged.
- Validate paths before filesystem access, reject symlink/escape cases, and use server-side preview/consequence checks before destructive mapping removal.

### Frontend architecture

- New frontend work belongs under `frontend/src/v2/`, uses `@v2/lib` primitives and aliases, and keeps feature logic in views/composables rather than primitives.
- Keep wizard-level async state in the orchestrator and pass typed data into step components.
- Use one global scan lifecycle subscription and one scanning store so the empty-home CTA, scan view, navbar indicator, and operation composables observe the same state.

## No Analog Found

No exact existing artifact was found for a single combined “fresh install must complete PC storage mapping before the first library scan” browser UAT. Compose the new UAT from Phase 22’s read-only synthetic-library/browser sequence and Phase 27’s clean-install evidence table. No product-code pattern is missing for the individual routing, setup, mapping, platform-folder, scan-gating, or test concerns.

## Metadata

**Analog search scope:** `backend/endpoints`, `backend/handler/filesystem`, `backend/models`, `backend/tasks`, `backend/tests`, `frontend/src/v2/views`, `frontend/src/v2/components`, `frontend/src/v2/composables`, `frontend/src/v2/router`, `frontend/src/services`, `frontend/e2e`, and prior phase UAT artifacts.
**Primary files scanned:** 25, excluding generated files, caches, and `__pycache__`.
**Project instructions applied:** `CLAUDE.md`, `.claude/skills/backend-development/SKILL.md`, `.claude/skills/frontend-v2-components/SKILL.md`, `.claude/skills/frontend-v2-patterns/SKILL.md`, `.claude/skills/pre-pr-verification/SKILL.md`.

## Phase 33 Plan Traceability

The following analogs are explicitly assigned to affected plan tasks:

| Pattern analog | Affected task | Required use |
|---|---|---|
| Fresh-install and empty-library routing, Home.vue loading guard | 33-03 Task 1 | Keep catalog emptiness separate from legacy filesystem discovery; do not render scan before readiness settles. |
| Setup wizard state and first-run probe, Setup.vue | 33-02 Task 1 | Keep async flights in the setup orchestrator and keep step components presentation-only. |
| Admin storage mapping UI, PlatformStorageMapping.vue | 33-02 Task 1 | Hand off to the existing Root -> Folder -> Test -> Save workflow; do not create a second mapping surface. |
| Backend storage mapping contract, storage.py and storage_handler.py | 33-01 Task 1 | Persist root Games plus relative_path pc through existing typed endpoint/handler contracts. |
| Storage safety, storage_resolver.py | 33-01 Task 1, 33-03 Task 1, and 33-03 Task 2 | Preserve normalized relative paths, containment, symlink, root-health, and external_read_only enforcement. |
| Scan gating and lifecycle, scan.py and useScanLifecycle | 33-03 Task 2 | Add earlier browser gating while preserving one lifecycle subscriber and the server fail-closed socket. |
| Frontend test assignments, PlatformStorageMapping.test.ts and v2Boot.test.ts | 33-01 Task 2, 33-02 Task 1, 33-03 Task 1, and 33-03 Task 2 | Reuse hoisted mocks, flushPromises, route invariants, and bounded missing-mapping assertions. |
| Phase 22 synthetic read-only UAT | 33-04 Task 2 | Use disposable PC fixture, read-only mount, pre/post manifest, and exact cleanup. |
| Phase 27 clean-install evidence table | 33-04 Task 2 | Record fresh stack, health, first-run ordering, browser evidence, and cleanup as scenario/result/evidence rows. |
| Phase 32 containerized validation | 33-04 Task 1 | Run frontend/backend gates through romm-dev and preserve infrastructure limitations explicitly. |
