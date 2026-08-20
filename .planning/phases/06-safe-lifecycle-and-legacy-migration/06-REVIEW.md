---
phase: 06-safe-lifecycle-and-legacy-migration
reviewed: 2026-08-20T06:34:41Z
depth: standard
files_reviewed: 129
files_reviewed_list:
  - backend/alembic/versions/0110_mapping_preview_results.py
  - backend/alembic/versions/0111_safe_lifecycle_legacy_migration.py
  - backend/alembic/versions/0112_phase6_gap_closure.py
  - backend/alembic/versions/0113_legacy_change_lineage.py
  - backend/endpoints/firmware.py
  - backend/endpoints/heartbeat.py
  - backend/endpoints/responses/assets.py
  - backend/endpoints/responses/rom.py
  - backend/endpoints/responses/storage.py
  - backend/endpoints/roms/files.py
  - backend/endpoints/roms/__init__.py
  - backend/endpoints/roms/manual.py
  - backend/endpoints/roms/patch.py
  - backend/endpoints/saves.py
  - backend/endpoints/screenshots.py
  - backend/endpoints/sockets/scan.py
  - backend/endpoints/states.py
  - backend/endpoints/storage.py
  - backend/handler/database/catalog_lifecycle_handler.py
  - backend/handler/database/legacy_migration_handler.py
  - backend/handler/database/roms_handler.py
  - backend/handler/database/saves_handler.py
  - backend/handler/database/states_handler.py
  - backend/handler/database/storage_handler.py
  - backend/handler/filesystem/storage_access.py
  - backend/handler/filesystem/storage_inventory.py
  - backend/handler/scan_handler.py
  - backend/handler/storage/legacy_migration.py
  - backend/handler/storage/read_context.py
  - backend/models/assets.py
  - backend/models/catalog_lifecycle.py
  - backend/models/play_session.py
  - backend/models/rom.py
  - backend/models/storage.py
  - backend/tasks/manual/cleanup_catalog_assets.py
  - backend/tasks/manual/detect_legacy_storage.py
  - backend/tests/endpoints/roms/test_catalog_removal.py
  - backend/tests/endpoints/sockets/test_scan.py
  - backend/tests/endpoints/test_saves.py
  - backend/tests/endpoints/test_screenshots.py
  - backend/tests/endpoints/test_states.py
  - backend/tests/endpoints/test_storage_policy_denials.py
  - backend/tests/endpoints/test_storage.py
  - backend/tests/handler/database/test_storage_lifecycle.py
  - backend/tests/handler/filesystem/test_storage_access.py
  - backend/tests/handler/filesystem/test_storage_inventory.py
  - backend/tests/handler/storage/test_legacy_migration.py
  - backend/tests/handler/storage/test_read_context.py
  - backend/tests/integration/__init__.py
  - backend/tests/integration/test_legacy_migration.py
  - backend/tests/models/test_safe_lifecycle.py
  - backend/tests/tasks/test_detect_legacy_storage.py
  - backend/tests/tools/test_verify_phase6_contracts.py
  - backend/tests/tools/test_verify_storage_migrations.py
  - backend/tools/verify_phase6_contracts.py
  - backend/tools/verify_storage_migrations.py
  - frontend/src/components/common/Game/Dialog/DeleteManual.vue
  - frontend/src/components/common/Game/Dialog/EditRom.vue
  - frontend/src/components/common/Game/Dialog/ManualUploadTarget.vue
  - frontend/src/components/common/Platform/Dialog/DeleteFirmware.vue
  - frontend/src/components/common/Platform/Dialog/UploadFirmware.vue
  - frontend/src/components/Details/MediaTab.vue
  - frontend/src/components/Gallery/AppBar/Platform/FirmwareDrawer.vue
  - frontend/src/__generated__/index.ts
  - frontend/src/__generated__/models/CatalogRemovalRequest.ts
  - frontend/src/__generated__/models/CatalogRemovalResponse.ts
  - frontend/src/__generated__/models/LegacyDetectionResultSchema.ts
  - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Input.ts
  - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Output.ts
  - frontend/src/__generated__/models/LegacyImpactPreviewSchema.ts
  - frontend/src/__generated__/models/LegacyMigrationResultSchema.ts
  - frontend/src/__generated__/models/LegacyRollbackErrorCode.ts
  - frontend/src/__generated__/models/LegacyRollbackErrorDetail.ts
  - frontend/src/__generated__/models/LegacyRollbackErrorResponse.ts
  - frontend/src/__generated__/models/LegacyRollbackRequestSchema.ts
  - frontend/src/__generated__/models/LegacyRollbackStatusSchema.ts
  - frontend/src/__generated__/models/ScreenshotSchema.ts
  - frontend/src/__generated__/models/StorageMappingRemovalConfirmationSchema.ts
  - frontend/src/__generated__/models/StorageMappingRemovalConsequencesSchema.ts
  - frontend/src/__generated__/models/UserScreenshotSchema.ts
  - frontend/src/locales/bg_BG/rom.json
  - frontend/src/locales/cs_CZ/rom.json
  - frontend/src/locales/de_DE/rom.json
  - frontend/src/locales/en_GB/rom.json
  - frontend/src/locales/en_US/rom.json
  - frontend/src/locales/es_ES/rom.json
  - frontend/src/locales/fr_FR/rom.json
  - frontend/src/locales/hu_HU/rom.json
  - frontend/src/locales/it_IT/rom.json
  - frontend/src/locales/ja_JP/rom.json
  - frontend/src/locales/ko_KR/rom.json
  - frontend/src/locales/pl_PL/rom.json
  - frontend/src/locales/pt_BR/rom.json
  - frontend/src/locales/ro_RO/rom.json
  - frontend/src/locales/ru_RU/rom.json
  - frontend/src/locales/tr_TR/rom.json
  - frontend/src/locales/zh_CN/rom.json
  - frontend/src/locales/zh_TW/rom.json
  - frontend/src/services/api/firmware.ts
  - frontend/src/services/api/platform.ts
  - frontend/src/services/api/rom.ts
  - frontend/src/services/api/setup.ts
  - frontend/src/v2/components/AppShell/UserMenu.vue
  - frontend/src/v2/components/Auth/SetupStepPlatforms.vue
  - frontend/src/v2/components/Dialogs/DeleteManualDialog.vue
  - frontend/src/v2/components/Dialogs/DeleteRomDialog.test.ts
  - frontend/src/v2/components/Dialogs/DeleteRomDialog.vue
  - frontend/src/v2/components/Dialogs/EditRomDialog.vue
  - frontend/src/v2/components/Dialogs/ManualUploadTargetDialog.vue
  - frontend/src/v2/components/Dialogs/MatchRomDialog.vue
  - frontend/src/v2/components/Gallery/DeleteFirmwareDialog.vue
  - frontend/src/v2/components/Gallery/FirmwareTab.test.ts
  - frontend/src/v2/components/Gallery/FirmwareTab.vue
  - frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue
  - frontend/src/v2/components/GameDetails/ManualSubtab.vue
  - frontend/src/v2/components/GameDetails/MediaTab.vue
  - frontend/src/v2/components/GameDetails/PatcherTab.vue
  - frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue
  - frontend/src/v2/components/MatchRom/MatchRomBodyGrid.vue
  - frontend/src/v2/components/MatchRom/MatchRomBodyList.vue
  - frontend/src/v2/components/MatchRom/types.ts
  - frontend/src/v2/components/Settings/SettingsSidebar.vue
  - frontend/src/v2/sourceMutationControls.test.ts
  - frontend/src/v2/sourceMutationInventory.test.ts
  - frontend/src/v2/views/Auth/Setup.vue
  - frontend/src/v2/views/Gallery/Platform.vue
  - frontend/src/v2/views/Home.vue
  - frontend/src/v2/views/Upload.test.ts
  - frontend/src/v2/views/Upload.vue
findings:
  critical: 2
  warning: 4
  info: 0
  total: 6
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-08-20T06:34:41Z
**Depth:** standard
**Files Reviewed:** 129
**Status:** issues_found

## Summary

The final Phase 06 implementation and its gap closures were reviewed against the live `1da8069a4` tree. All seven findings from the previous authoritative review are resolved: active-v2 source mutation controls/services were removed, reconnect work is in the scan transaction/retry path, seeded 0111/0112 upgrade safety and aggregate HASH budgeting were repaired, rollback is bound to immutable entity and parent lineage, cleanup failures remain retryable, and screenshot API/generated contracts agree on live ownership while saves and states remain detachable.

Six different defects remain. Two can violate mutation atomicity or publish truncated owned data and are blockers. Four warnings make bounded detection results inaccurate, leave the rollback-lineage token invariant bypassable by a supported ORM update form, leave the semantic regression gate blind to the dynamic syntax it claims to cover, and make cleanup retries fail forever after an already-absent environment file.

## Critical Issues

### CR-01 [BLOCKER]: ROM rename authorization runs after state-changing branches and owned screenshot writes

**File:** `backend/endpoints/roms/__init__.py:1539-1583, 1670-1744, 1767-1774`

**Issue:** The endpoint authorizes a changed `fs_name` only at lines 1770-1773. A request with `unmatch_metadata=true` returns through lines 1539-1583 before reaching that guard and commits database changes instead of rejecting the forbidden rename attempt. On the normal path, metadata-provider results can populate `url_screenshots`, and `get_rom_screenshots` downloads/overwrites RomM-owned screenshot files at lines 1730-1741 before the request is rejected with 403. An authenticated ROM writer can therefore combine a changed `fs_name` with unmatch or a metadata rematch and cause durable partial effects from a request whose external rename is denied. The new denial test only exercises a form that never produces `url_screenshots`, so its tripwire does not cover the live side-effect ordering.

**Fix:** Immediately after loading the ROM and calling `assert_rom_visible`, sanitize and compare the submitted `fs_name`, then call `authorize_api_storage_operation(StorageOperation.RENAME, legacy_external_storage)` before the `unmatch_metadata` branch, provider calls, database updates, or any resource-handler call. Keep the computed name for later use. Add tests for changed `fs_name` plus `unmatch_metadata=true` and changed `fs_name` plus a provider response containing screenshot URLs; assert 403 and zero database, provider, and resource effects.

### CR-02 [BLOCKER]: Owned byte writes can silently install truncated files

**File:** `backend/handler/filesystem/storage_access.py:410-424, 456-479`

**Issue:** `OwnedCreate.create` and `OwnedReplace.replace` each call `os.write` once and ignore its returned byte count. POSIX permits a successful short write, especially at filesystem quota, size-limit, or space boundaries. `OwnedReplace` then fsyncs and atomically replaces a valid existing gamelist/Pegasus export with the truncated temporary file; `OwnedCreate` can make a partial uploaded patch appear complete. If `OwnedCreate` raises after creating its destination, it also leaves that file behind, and the patch endpoint does not add the name to its cleanup list until `create` returns. This is silent data corruption and can strand per-request artifacts.

**Fix:** Implement a shared write-all helper that advances a `memoryview` until every byte is written, treats a zero-byte write as an error, and retries `InterruptedError`. For `OwnedCreate`, unlink the newly created destination on every failed/incomplete write. For `OwnedReplace`, retain the existing temporary-file cleanup and call `os.replace` only after the full-length write and fsync succeed. Add short-write and mid-write-exception tests for both capabilities, including preservation of the prior replace target.

## Warnings

### WR-01 [WARNING]: Budget-limited legacy observations are labelled exact

**File:** `backend/handler/storage/legacy_migration.py:151-169, 216-227, 267-350`

**Issue:** Every early return caused by the entry, time, per-file, aggregate, or descriptor-hash budget constructs `_CandidateObservation(..., lower_bound=False, ...)`, even though `observed_files` and `observed_bytes` describe only the prefix traversed before the budget stopped inspection. The test named `test_entry_budget_reports_observed_lower_bound` at `backend/tests/handler/storage/test_legacy_migration.py:142-155` explicitly asserts the incorrect `False` value. Results are unselectable, so this does not authorize an unsafe migration, but admin/API consumers are told incomplete counts are exact and can materially underestimate migration size.

**Fix:** Set `lower_bound=True` on all budget-exhaustion returns after partial observation (entry, time, file-byte, aggregate-byte, and hash budget/deadline cases), while leaving exact terminal states false. Update tests to assert lower-bound semantics for each budget reason and confirm the API persists/returns the flag.

### WR-02 [WARNING]: ORM executemany updates bypass incarnation-token immutability

**File:** `backend/models/rom.py:689-709`

**Issue:** Mapper updates reject attribute history changes, while the session hook checks only the private `statement._values` mapping. SQLAlchemy's supported ORM bulk-update-by-primary-key form passes values in `execute_state.parameters` (for example `session.execute(update(Rom), [{"id": id, "incarnation_token": token}])`), leaving `_values` empty; mapper `before_update` events do not run for that bulk operation. A future bulk maintenance path can therefore rewrite a ROM or ROM-file token without tripping either hook. Rollback treats those tokens as the immutable row-incarnation authority, so the safety property currently depends on every future caller avoiding a normal ORM update API. Existing tests cover only `.values(incarnation_token=...)`.

**Fix:** Reject `incarnation_token` in every dict/list entry in `execute_state.parameters` as well as in statement values, and cover ORM executemany plus legacy bulk-mapping paths. If the invariant must survive all application and direct-SQL writers, enforce it at the database boundary with dialect-appropriate immutable-column triggers and migration tests.

### WR-03 [WARNING]: The active-v2 semantic inventory silently drops dynamic API calls

**File:** `frontend/src/v2/sourceMutationInventory.test.ts:137-153, 182-200, 225-265, 797-826`

**Issue:** Route extraction accepts only string literals and template expressions, and call extraction accepts only identifier receivers with property access such as `api.delete(...)`. It drops concatenated/variable routes, element access such as `api["delete"](...)`, and namespace-import clients without producing a failure. The negative test advertised as covering "dynamic calls" bypasses extraction by constructing a `RawCall` manually and invoking `finalAuthority`, so it cannot detect this blind spot. A forbidden active-v2 call such as `api["delete"]("/roms/" + romId + "/files/" + fileId)` can pass the final gate unnoticed. Independent inspection found no such live call now, but the security regression contract is not enforced.

**Fix:** Make unknown client-call syntax fail closed, support element access and namespace imports, and resolve safe constant/concatenated route expressions (or report them as unclassifiable failures). Run negative fixtures through the same `extractRawCalls`/inventory entry point used for repository files and assert that each fixture is extracted and classified forbidden.

### WR-04 [WARNING]: Cleanup treats an already-absent owned environment file as a permanent failure

**File:** `backend/tools/verify_phase6_contracts.py:518-531`

**Issue:** The cleanup path catches every `OSError` from unlinking `_env_file`, records a failure, and retains the path for retry. `FileNotFoundError` means the owned resource is already absent and cleanup has achieved its postcondition, but every subsequent cleanup attempt repeats the same failure forever. The Docker cleanup branches correctly classify already-absent resources as success; the environment-file branch is inconsistent. External temp cleanup or a prior partial cleanup can therefore make the verifier impossible to finish cleanly despite no resource remaining.

**Fix:** Catch `FileNotFoundError` separately and clear `_env_file`; retain it only for other `OSError` failures. Add a test where the env file is removed before cleanup and assert cleanup succeeds and remains idempotent, while preserving the existing fail-once retry test.

---

_Reviewed: 2026-08-20T06:34:41Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
