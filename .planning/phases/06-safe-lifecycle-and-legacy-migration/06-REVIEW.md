---
phase: 06-safe-lifecycle-and-legacy-migration
reviewed: 2026-08-24T08:45:09Z
depth: standard
files_reviewed: 132
files_reviewed_list:
  - backend/alembic/versions/0110_mapping_preview_results.py
  - backend/alembic/versions/0111_safe_lifecycle_legacy_migration.py
  - backend/alembic/versions/0112_phase6_gap_closure.py
  - backend/alembic/versions/0113_legacy_change_lineage.py
  - backend/alembic/versions/0114_legacy_source_identities.py
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
  - backend/handler/database/__init__.py
  - backend/handler/database/catalog_lifecycle_handler.py
  - backend/handler/database/legacy_migration_handler.py
  - backend/handler/database/manual_handler.py
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
  - backend/tests/endpoints/roms/test_files.py
  - backend/tests/endpoints/roms/test_manual.py
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
  - backend/tests/tools/test_verify_phase6_acceptance.py
  - backend/tests/tools/test_verify_phase6_contracts.py
  - backend/tests/tools/test_verify_storage_migrations.py
  - backend/tests/utils/test_rom_patcher.py
  - backend/tools/verify_phase6_acceptance.py
  - backend/tools/verify_phase6_contracts.py
  - backend/tools/verify_storage_migrations.py
  - backend/utils/rom_patcher/patcher.py
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
  - frontend/src/services/api/rom.test.ts
  - frontend/src/services/api/rom.ts
  - frontend/src/services/api/screenshot.test.ts
  - frontend/src/services/api/setup.ts
  - frontend/src/stores/upload.test.ts
  - frontend/src/stores/upload.ts
  - frontend/src/v2/components/Auth/SetupStepPlatforms.vue
  - frontend/src/v2/components/Dialogs/DeleteManualDialog.vue
  - frontend/src/v2/components/Dialogs/EditRomDialog.vue
  - frontend/src/v2/components/Dialogs/GlobalDialogs.vue
  - frontend/src/v2/components/Dialogs/MatchRomDialog.vue
  - frontend/src/v2/components/Gallery/DeleteFirmwareDialog.vue
  - frontend/src/v2/components/Gallery/FirmwareTab.test.ts
  - frontend/src/v2/components/Gallery/FirmwareTab.vue
  - frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue
  - frontend/src/v2/components/GameDetails/ManualSubtab.test.ts
  - frontend/src/v2/components/GameDetails/ManualSubtab.vue
  - frontend/src/v2/components/GameDetails/ManualViewerControls.test.ts
  - frontend/src/v2/components/GameDetails/MarkdownViewer.vue
  - frontend/src/v2/components/GameDetails/MediaTab.vue
  - frontend/src/v2/components/GameDetails/PatcherTab.vue
  - frontend/src/v2/components/GameDetails/PdfViewer.vue
  - frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue
  - frontend/src/v2/components/MatchRom/MatchRomBodyGrid.vue
  - frontend/src/v2/components/MatchRom/MatchRomBodyList.vue
  - frontend/src/v2/components/MatchRom/types.ts
  - frontend/src/v2/sourceMutationControls.test.ts
  - frontend/src/v2/sourceMutationInventory.test.ts
  - frontend/src/v2/views/Upload.vue
findings:
  critical: 4
  warning: 1
  info: 0
  total: 5
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-08-24T08:45:09Z
**Depth:** standard
**Files Reviewed:** 132
**Status:** issues_found

## Summary

The 132-file final Phase 06 source scope was derived from all 47 summary frontmatters and reviewed at current HEAD `02d1a50930d60a0feb4bf2316f999bbda4c22023`. Two deleted paths were excluded. Current endpoint, storage, migration, model, verifier, generated contract, frontend, locale, and test code were reviewed, with called helpers inspected where necessary.

Four blockers and one warning remain. Earlier stale-confirmation, blanket-rollback, HEAD first-use, unsafe-header, short-write, and crash-publication defects are closed and not repeated. No tests or services were run during this read-only static review.

## Critical Issues

### CR-01 [BLOCKER]: File-only evidence makes folder and multi-file ROMs permanently unmatched

**File:** `backend/handler/database/legacy_migration_handler.py:467-496`

**Issue:** Detection persists digests only for regular files (`backend/handler/storage/legacy_migration.py:287-348`), but selection requires a ROM's own `fs_path/fs_name` digest before selecting it or any child. A folder game is represented by a ROM whose `fs_name` is the directory, while evidence contains only files below it. Its directory digest can never occur, so every folder or multi-file ROM stays `missing_from_fs` despite exact observed children. Tests cover only a flat ROM.

**Fix:** Persist typed directory and file identities, selecting the folder ROM by exact directory identity and children by file identity, or derive an exact unambiguous folder boundary from children. Test migration and rollback for nested folder ROMs with present and absent children.

### CR-02 [BLOCKER]: Newly uploaded primary manuals cannot be found or deleted

**File:** `backend/endpoints/roms/manual.py:115-119, 418-430`

**Issue:** Upload stores a random token path, but discovery recognizes only `{rom.id}.pdf/.md` (`backend/handler/filesystem/resources_handler.py:499-510, 581-600`). Thus upload followed by `DELETE /{id}/manuals` returns 404 without deleting or clearing the database. Redownload discovery also ignores the upload. The visible primary manual is not manageable through its API.

**Fix:** Make validated `rom.path_manual` authoritative for existence and deletion. Remove the competing fixed-name convention or migrate legacy files. Test upload-delete and restart for random PDF/Markdown paths with no orphan.

### CR-03 [BLOCKER]: Redownload bypasses CAS and can orphan a successful upload

**File:** `backend/endpoints/roms/manual.py:182-218`, `frontend/src/v2/components/GameDetails/ManualSubtab.vue:112-114, 186-190, 267-275`

**Issue:** Upload uses CAS, but redownload writes fixed `{rom.id}.pdf` and unconditionally updates `path_manual`. Frontend pending state excludes `redownloadingManual`, so Replace remains enabled. If upload wins CAS first, later redownload overwrites the path and orphans that committed upload. A failed redownload can also clear the reference to a valid random-path upload.

**Fix:** Use the same staging, durability, CAS, and cleanup primitive for redownload, preserving the old path on every failure. Include redownload in UI pending state and enforce backend serialization. Test both race orderings and failed downloads.

### CR-04 [BLOCKER]: Hidden-ROM screenshots remain mutable through update and delete

**File:** `backend/endpoints/screenshots.py:178-226`

**Issue:** Upload/download enforce visibility, but update/delete mutate an owner screenshot by ID without checking its now-hidden ROM/platform. Hidden entities must read as nonexistent. Retained IDs still allow public-state changes or owned file/row deletion, an authorization bypass untested for hidden update/delete.

**Fix:** Call `assert_rom_visible(request, screenshot.rom, not_found_detail="Screenshot not found")` before all effects in both routes. Test hidden ROM/platform update/delete for indistinguishable 404 and zero effects.

## Warnings

### WR-01 [WARNING]: Close-error cleanup can close an unrelated descriptor

**File:** `backend/handler/filesystem/storage_access.py:447-469`

**Issue:** `_close_descriptor` and `abort` retry `os.close` after it raises. Linux can report a close error after releasing the number; another thread can reuse it before retry, which then closes an unrelated file/socket. The test simulates a consumed descriptor but not concurrent reuse.

**Fix:** Treat the descriptor as consumed after one close call; never retry its number. Continue name cleanup and preserve the original error. Test reuse with a sentinel descriptor.

---

_Reviewed: 2026-08-24T08:45:09Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
