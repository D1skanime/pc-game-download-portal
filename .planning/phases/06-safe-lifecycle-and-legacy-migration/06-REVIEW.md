---
phase: 06-safe-lifecycle-and-legacy-migration
reviewed: 2026-08-13T12:23:56Z
depth: standard
files_reviewed: 68
files_reviewed_list:
  - backend/alembic/versions/0112_phase6_gap_closure.py
  - backend/endpoints/responses/assets.py
  - backend/endpoints/responses/storage.py
  - backend/endpoints/roms/__init__.py
  - backend/endpoints/saves.py
  - backend/endpoints/sockets/scan.py
  - backend/endpoints/states.py
  - backend/endpoints/storage.py
  - backend/exceptions/storage_exceptions.py
  - backend/handler/database/catalog_lifecycle_handler.py
  - backend/handler/database/legacy_migration_handler.py
  - backend/handler/database/roms_handler.py
  - backend/handler/database/saves_handler.py
  - backend/handler/database/states_handler.py
  - backend/handler/filesystem/storage_access.py
  - backend/handler/filesystem/storage_composition.py
  - backend/handler/filesystem/storage_inventory.py
  - backend/handler/storage/legacy_migration.py
  - backend/handler/storage/read_context.py
  - backend/models/storage.py
  - backend/tasks/manual/detect_legacy_storage.py
  - backend/tests/endpoints/roms/test_catalog_removal.py
  - backend/tests/endpoints/sockets/test_scan.py
  - backend/tests/endpoints/test_saves.py
  - backend/tests/endpoints/test_states.py
  - backend/tests/endpoints/test_storage.py
  - backend/tests/handler/database/test_storage_lifecycle.py
  - backend/tests/handler/filesystem/test_storage_access.py
  - backend/tests/handler/filesystem/test_storage_inventory.py
  - backend/tests/handler/storage/test_legacy_migration.py
  - backend/tests/handler/storage/test_read_context.py
  - backend/tests/integration/test_legacy_migration.py
  - backend/tests/models/test_safe_lifecycle.py
  - backend/tests/tasks/test_detect_legacy_storage.py
  - backend/tests/tools/test_verify_phase6_contracts.py
  - backend/tests/tools/test_verify_storage_migrations.py
  - backend/tools/verify_phase6_contracts.py
  - backend/tools/verify_storage_migrations.py
  - frontend/src/components/common/Game/Dialog/DeleteRom.vue
  - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Input.ts
  - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Output.ts
  - frontend/src/__generated__/models/SaveSchema.ts
  - frontend/src/__generated__/models/ScreenshotSchema.ts
  - frontend/src/__generated__/models/StateSchema.ts
  - frontend/src/__generated__/models/UserSaveSchema.ts
  - frontend/src/__generated__/models/UserScreenshotSchema.ts
  - frontend/src/__generated__/models/UserStateSchema.ts
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
  - frontend/src/services/api/rom.ts
  - frontend/src/v2/components/Dialogs/DeleteRomDialog.test.ts
  - frontend/src/v2/components/Dialogs/DeleteRomDialog.vue
findings:
  critical: 5
  warning: 2
  info: 0
  total: 7
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-08-13T12:23:56Z
**Depth:** standard
**Files Reviewed:** 68
**Status:** issues_found

## Summary

The supplied scope contains 68 unique files despite being described as 69. Detached save/state API handling fixes former CR-01, and former WR-01 and WR-02 are fixed. Reconnection exists but is not durable (former CR-02); hashing remains underbounded (former CR-03); rollback records remain underbound (former CR-04); exact harness ownership improved but cleanup retry remains defective (former WR-03). Five blockers and two warnings remain.

## Critical Issues

### CR-01 [BLOCKER]: Upgrade rejects existing selectable detection rows

**File:** `backend/alembic/versions/0112_phase6_gap_closure.py:31-38`

**Issue:** The upgrade adds a nullable fingerprint column and immediately constrains every selectable row to have a fingerprint. Valid selectable 0111 rows cannot have one, and no backfill or invalidation runs, so such databases fail upgrade.

**Fix:** Portably invalidate pre-0112 selectable rows before the constraint, with safe stale reason/version fields, and test seeded selectable/unselectable 0111 upgrades on supported dialects.

### CR-02 [BLOCKER]: Replacement race bypasses aggregate hash limit

**File:** `backend/handler/storage/legacy_migration.py:265-305`

**Issue:** Aggregate budget is checked against `STAT`, while `HASH` receives only the per-file cap. Replacing a checked file before open with larger content below the per-file cap hashes and accepts bytes beyond the aggregate limit.

**Fix:** Cap hashing at the remaining aggregate allowance and recheck returned bytes. Test an inode swap between `STAT` and `HASH`.

### CR-03 [BLOCKER]: Retained reconnection is not crash-retry-safe

**File:** `backend/endpoints/sockets/scan.py:500-510`

**Issue:** ROM insertion commits before reconnection, which runs separately and only for `newly_added`. Failure between commits leaves detached assets; retry sees an existing ROM and permanently skips reconnect.

**Fix:** Use one transaction or invoke an idempotent durable reconnect for existing exact matches. Test failure after insertion followed by retry.

### CR-04 [BLOCKER]: Active v2 still offers source-file deletion

**File:** `frontend/src/services/api/rom.ts:805-813`

**Issue:** `deleteRomFile` remains exported and is invoked by `frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue:494-512`. The backend rejects source mutation, so active UI violates the catalog-only contract and offers an action guaranteed to fail.

**Fix:** Remove the v2 control and service export or replace them with catalog-only removal. Add an active-v2-wide regression check.

### CR-05 [BLOCKER]: Rollback lineage check is tautological

**File:** `backend/handler/database/legacy_migration_handler.py:984-1037`

**Issue:** Records omit migration-time parent identity. Rollback reads current `rom_id` into `file_lineage`, then compares the locked row to that same current value. Same-platform reparenting can pass and modify the wrong current entity.

**Fix:** Record migration-time parent plus bounded identity/version and validate them under rollback locks. Test same-platform reparenting and ROM substitution.

## Warnings

### WR-01 [WARNING]: Cleanup failure disables retry

**File:** `backend/tools/verify_phase6_contracts.py:486-505`

**Issue:** `_cleaned` is set before resource removal. If removal fails, later calls return immediately and cannot clean the exact-owned resource.

**Fix:** Clear state only after each successful removal and mark globally cleaned only when all owned resources are gone. Test failure then retry.

### WR-02 [WARNING]: Screenshot contract advertises impossible detached state

**File:** `backend/endpoints/responses/assets.py:11-16`

**Issue:** The shared base makes screenshot `rom_id` nullable and adds retained identity, despite non-null screenshot persistence and no retained-catalog field. Generated clients advertise states the server cannot produce.

**Fix:** Split response bases so only saves/states are detachable, then regenerate and type-check models.

---

_Reviewed: 2026-08-13T12:23:56Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
