---
phase: 06-safe-lifecycle-and-legacy-migration
reviewed: 2026-08-20T14:11:45Z
depth: standard
files_reviewed: 115
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
  - backend/endpoints/roms/__init__.py
  - backend/endpoints/roms/files.py
  - backend/endpoints/roms/manual.py
  - backend/endpoints/roms/patch.py
  - backend/endpoints/screenshots.py
  - backend/endpoints/sockets/scan.py
  - backend/endpoints/storage.py
  - backend/handler/database/catalog_lifecycle_handler.py
  - backend/handler/database/legacy_migration_handler.py
  - backend/handler/database/roms_handler.py
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
  - backend/tests/endpoints/test_storage.py
  - backend/tests/endpoints/test_storage_policy_denials.py
  - backend/tests/handler/database/test_storage_lifecycle.py
  - backend/tests/handler/filesystem/test_storage_access.py
  - backend/tests/handler/filesystem/test_storage_inventory.py
  - backend/tests/handler/storage/test_legacy_migration.py
  - backend/tests/integration/__init__.py
  - backend/tests/integration/test_legacy_migration.py
  - backend/tests/models/test_safe_lifecycle.py
  - backend/tests/tools/test_verify_phase6_contracts.py
  - backend/tests/tools/test_verify_storage_migrations.py
  - backend/tools/verify_phase6_contracts.py
  - backend/tools/verify_storage_migrations.py
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
  - frontend/src/components/Details/MediaTab.vue
  - frontend/src/components/Gallery/AppBar/Platform/FirmwareDrawer.vue
  - frontend/src/components/common/Game/Dialog/DeleteManual.vue
  - frontend/src/components/common/Game/Dialog/EditRom.vue
  - frontend/src/components/common/Game/Dialog/ManualUploadTarget.vue
  - frontend/src/components/common/Platform/Dialog/DeleteFirmware.vue
  - frontend/src/components/common/Platform/Dialog/UploadFirmware.vue
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
  - frontend/src/v2/components/Auth/SetupStepPlatforms.vue
  - frontend/src/v2/components/Dialogs/DeleteManualDialog.vue
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
  - frontend/src/v2/sourceMutationControls.test.ts
  - frontend/src/v2/sourceMutationInventory.test.ts
  - frontend/src/v2/views/Upload.vue
findings:
  critical: 4
  warning: 3
  info: 0
  total: 7
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-08-20T14:11:45Z
**Depth:** standard
**Files Reviewed:** 115
**Status:** issues_found

## Summary

The 115-file Phase 06 source scope was reviewed against current HEAD `f7420c24ed0b47cb4a9e1d4067b8670f3b394123`, including endpoint-to-handler call chains, storage authority boundaries, migration upgrade/downgrade logic, generated contracts, active-v2 controls, and the submitted tests. Four blockers and three warnings remain.

The historical late rename guard, mutable ORM incarnation token, incorrect lower-bound flag, dynamic element-access inventory gap, and single-short-write issues are closed at this HEAD and are not repeated below. The findings below are separate current defects. No tests were executed during this read-only review; current code and test coverage were inspected directly.

## Critical Issues

### CR-01 [BLOCKER]: Migration reconnects catalog rows without proving the source files exist

**File:** `backend/handler/database/roms_handler.py:2673-2697`

**Issue:** `reconnect_legacy_catalog` treats every catalog ROM whose database logical path is unique as reconnectable, then clears `missing_from_fs` on that ROM and every child `RomFile`. It never intersects those catalog identities with the files actually observed under the detected legacy mapping. The impact preview uses the same catalog-only uniqueness rule in `backend/handler/database/legacy_migration_handler.py:350-378`. A canonical directory containing only `one.gb` therefore causes a unique but absent `two.gb` catalog row, plus all of its sidecars, to be reported and persisted as reachable. This violates D-19: missing source entries must remain preserved and unreachable.

**Fix:** Bind detection to a private, bounded inventory of normalized source identities, such as persisted SHA-256 path identities that are never exposed by the API. Compute preview counts and migration updates from the exact source/catalog intersection, and update only child files whose own identities were observed. Add an integration case with one present file, one uniquely named absent catalog ROM, and an absent child sidecar; only the present identity may become reachable.

### CR-02 [BLOCKER]: Failed or concurrent manual uploads can destroy the existing manual

**File:** `backend/endpoints/roms/manual.py:97-127`, `frontend/src/services/api/rom.ts:499-524`

**Issue:** The backend deletes every prior manual with a different extension before it has received the replacement, then streams directly into the final filename. A disconnect or parser/write failure removes the partial destination but cannot restore the prior manual. Re-uploading the same extension can truncate the current manual before the request succeeds. The frontend also starts every selected manual upload concurrently with `Promise.allSettled`; same-extension requests can write the same destination concurrently, while different-extension requests race while deleting each other's files and updating `path_manual`. This is direct owned-data loss and can leave the database pointing at a deleted or nondeterministic file.

**Fix:** Accept one primary manual per operation, stage it under a unique owned temporary name, fsync it, atomically publish it, commit the new `path_manual`, and only then remove the superseded extension. Serialize or reject multi-file primary-manual uploads. Add disconnect, mid-write, same-extension retry, different-extension replacement, and concurrent-request tests proving the previous manual remains byte-identical unless the replacement fully succeeds.

### CR-03 [BLOCKER]: Screenshot upload bypasses hidden ROM and platform visibility

**File:** `backend/endpoints/screenshots.py:53-94`

**Issue:** `add_screenshot` loads the requested ROM and immediately derives its platform slug and writes the asset, but never calls `assert_rom_visible`. Any authenticated principal with `ASSETS_WRITE` can submit the ID of a ROM or platform hidden from that user and create a file and database relationship against it. Download correctly applies the hidden-resource boundary at lines 149-151, so upload is inconsistent with the same endpoint module and with other ROM-scoped mutation routes. The submitted screenshot tests cover hidden downloads but no hidden upload.

**Fix:** Call `assert_rom_visible(request, rom, not_found_detail="ROM not found")` immediately after the ROM lookup and before path derivation or any write. Add hidden-ROM and hidden-platform upload tests that assert 404 masking, zero filesystem calls, and no database row.

### CR-04 [BLOCKER]: Owned create publishes a partial final file across process failure

**File:** `backend/handler/filesystem/storage_access.py:422-446`

**Issue:** The new write-all loop closes the normal short-write defect, but `OwnedCreate.create` still opens the final destination before writing and never fsyncs it. A worker crash, forced termination, or host failure during the write leaves the partial final filename visible; a crash after the method returns can also lose acknowledged data. Exception cleanup only covers Python-visible `OSError`, and even that cleanup is skipped if `os.close` itself raises at line 437. This does not meet the advertised complete-or-no-publication owned-write contract.

**Fix:** Write and fsync a uniquely named descriptor-relative temporary file, close it safely, then publish with an atomic no-replace operation and fsync the parent directory. Cleanup must run independently of close errors. Add a subprocess crash test that terminates during write and proves the final name is absent, plus close-error and durability-path tests.

## Warnings

### WR-01 [WARNING]: HEAD requests permanently consume migration rollback eligibility

**File:** `backend/endpoints/roms/files.py:225-250`

**Issue:** GET and HEAD share `get_romfile_content`. Both call `preflight_mapped_download`, which opens `StorageOperation.DOWNLOAD`; `MappingReadContext.open` marks that as first productive use before the method-specific HEAD branch closes the descriptor without transferring content. A health probe, link checker, or browser HEAD request therefore makes direct rollback permanently ineligible even though no download occurred. That contradicts D-15's "first used productively" boundary.

**Fix:** Separate metadata-only HEAD preflight from productive download preflight, or add an explicit `mark_first_use=False` path for HEAD that still validates the mapping and opens/stat-checks the descriptor. Mark first use only when a GET/stream will commit content. Add an integration test proving HEAD preserves eligibility while GET or the first emitted byte consumes it.

### WR-02 [WARNING]: The semantic inventory still ignores direct fetch and callable-client mutations

**File:** `frontend/src/v2/sourceMutationInventory.test.ts:307-328, 396-443`

**Issue:** Client discovery recognizes imported Axios/API objects, and call extraction immediately skips call expressions whose callee is not property or element access. Direct `fetch(url, { method: "POST" })`, callable `axios(config)`, `api.request({ method, url })`, and equivalent wrappers are therefore omitted instead of failing closed. A reachable live service already contains a direct keepalive POST via `fetch("/api/play-sessions", ...)`; the inventory sees the sibling `api.post` but silently omits this second mutation path. The gate still cannot support its claim that every active-v2 mutation call is inventoried.

**Fix:** Extract global `fetch`, callable Axios clients, and `.request(config)`; resolve or fail closed on their method and URL fields. Add negative fixtures through `finalInventorySource` for each syntax and assert that an unresolved transport call fails the test rather than returning an empty inventory.

### WR-03 [WARNING]: Raw catalog filenames can break or corrupt download response headers

**File:** `backend/endpoints/roms/files.py:196-241`

**Issue:** The response correctly ignores the client-supplied path parameter, but it inserts the source-derived database filename directly into a quoted `Content-Disposition` header. External library filenames may contain quotes, control characters, or non-Latin Unicode. Quotes produce an invalid filename parameter, CR/LF can reach the server's header validation path, and non-Latin names can raise during Starlette's Latin-1 header encoding, turning valid Japanese or other Unicode ROM downloads into 500 responses.

**Fix:** Build Content-Disposition with a vetted helper that emits an escaped ASCII fallback and RFC 5987 `filename*=UTF-8''...` value, rejects control characters, and never interpolates a raw source filename. Add tests for quotes, CR/LF, and non-Latin filenames.

---

_Reviewed: 2026-08-20T14:11:45Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
