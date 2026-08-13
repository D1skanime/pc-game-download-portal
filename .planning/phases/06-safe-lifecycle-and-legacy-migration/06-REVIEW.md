---
phase: 06-safe-lifecycle-and-legacy-migration
reviewed: 2026-08-13T01:14:29Z
depth: standard
files_reviewed: 69
files_reviewed_list:
  - backend/alembic/versions/0110_mapping_preview_results.py
  - backend/alembic/versions/0111_safe_lifecycle_legacy_migration.py
  - backend/endpoints/responses/rom.py
  - backend/endpoints/responses/storage.py
  - backend/endpoints/roms/__init__.py
  - backend/endpoints/roms/files.py
  - backend/endpoints/sockets/scan.py
  - backend/endpoints/storage.py
  - backend/exceptions/storage_exceptions.py
  - backend/handler/database/__init__.py
  - backend/handler/database/catalog_lifecycle_handler.py
  - backend/handler/database/legacy_migration_handler.py
  - backend/handler/database/roms_handler.py
  - backend/handler/database/storage_handler.py
  - backend/handler/filesystem/storage_inventory.py
  - backend/handler/scan_handler.py
  - backend/handler/storage/__init__.py
  - backend/handler/storage/legacy_migration.py
  - backend/handler/storage/read_context.py
  - backend/models/assets.py
  - backend/models/catalog_lifecycle.py
  - backend/models/play_session.py
  - backend/models/storage.py
  - backend/tasks/manual/cleanup_catalog_assets.py
  - backend/tasks/manual/detect_legacy_storage.py
  - backend/tests/conftest.py
  - backend/tests/endpoints/roms/test_catalog_removal.py
  - backend/tests/endpoints/roms/test_rom.py
  - backend/tests/endpoints/sockets/test_scan.py
  - backend/tests/endpoints/test_storage.py
  - backend/tests/endpoints/test_storage_policy_denials.py
  - backend/tests/handler/database/test_storage_lifecycle.py
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
  - frontend/src/__generated__/models/CatalogRemovalErrorSchema.ts
  - frontend/src/__generated__/models/CatalogRemovalItemSchema.ts
  - frontend/src/__generated__/models/CatalogRemovalRequest.ts
  - frontend/src/__generated__/models/CatalogRemovalResponse.ts
  - frontend/src/__generated__/models/LegacyDetectionErrorCode.ts
  - frontend/src/__generated__/models/LegacyDetectionErrorDetail.ts
  - frontend/src/__generated__/models/LegacyDetectionErrorResponse.ts
  - frontend/src/__generated__/models/LegacyDetectionJobSchema.ts
  - frontend/src/__generated__/models/LegacyDetectionRequestSchema.ts
  - frontend/src/__generated__/models/LegacyDetectionResultSchema.ts
  - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Input.ts
  - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Output.ts
  - frontend/src/__generated__/models/LegacyImpactPlannedEffectsSchema.ts
  - frontend/src/__generated__/models/LegacyImpactPreviewRequestSchema.ts
  - frontend/src/__generated__/models/LegacyImpactPreviewSchema.ts
  - frontend/src/__generated__/models/LegacyImpactProblemSchema.ts
  - frontend/src/__generated__/models/LegacyImpactProposedMappingSchema.ts
  - frontend/src/__generated__/models/LegacyMigrationResultSchema.ts
  - frontend/src/__generated__/models/LegacyRollbackErrorCode.ts
  - frontend/src/__generated__/models/LegacyRollbackErrorDetail.ts
  - frontend/src/__generated__/models/LegacyRollbackErrorResponse.ts
  - frontend/src/__generated__/models/LegacyRollbackRequestSchema.ts
  - frontend/src/__generated__/models/LegacyRollbackStatusSchema.ts
  - frontend/src/__generated__/models/StorageConflictErrorCode.ts
  - frontend/src/__generated__/models/StorageMappingRemovalConfirmationSchema.ts
  - frontend/src/__generated__/models/StorageMappingRemovalConsequencesSchema.ts
  - frontend/src/services/api/rom.ts
findings:
  critical: 4
  warning: 3
  info: 0
  total: 7
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-08-13T01:14:29Z
**Depth:** standard
**Files Reviewed:** 69
**Status:** issues_found

## Summary

The existing files from the supplied scope were reviewed at standard depth, including the backend lifecycle and migration call chains, API contracts, tests, verification tools, and generated frontend types. The deleted generated request type was filtered, leaving 69 reviewable files.

Four blocking correctness defects remain. Catalog removal makes retained assets incompatible with current APIs and never reconnects retained identities, rollback cannot restore the catalog state it changed, and migration confirmation does not bind the source or exact catalog identity set. Three robustness defects can also produce ambiguous API failures, unbounded internal errors, or leaked verifier processes.

## Critical Issues

### CR-01 [BLOCKER]: Catalog removal makes retained saves and states invalid for existing APIs

**File:** `/home/d1sk/romm/backend/handler/database/catalog_lifecycle_handler.py:166-180`

**Issue:** Removal sets `Save.rom_id` and `State.rom_id` to `NULL`. The existing asset response contract still requires `rom_id: int`, while unfiltered user-wide save and state queries include these rows. List and detail routes can therefore raise response-validation errors, and multiple mutation and download paths dereference `asset.rom`, which is now `None`. The response claims retained user data, but the records are not safely addressable.

**Fix:**

```python
class BaseAsset(BaseModel):
    rom_id: int | None
    retained_catalog_id: int | None = None
```

Resolve detached asset authorization and file operations through `retained_catalog`, and test list, fetch, download, update, and delete after removal.

### CR-02 [BLOCKER]: Retained catalog identities are never consumed during reconnection

**File:** `/home/d1sk/romm/backend/handler/database/roms_handler.py:2695-2741`

**Issue:** Removal deletes the `Rom` after creating a `RetainedCatalogIdentity`. Scan reconnection searches only existing missing `Rom` rows and never queries retained identities. No other handler consumes them. A later scan creates a new ROM and leaves saves, states, and sessions permanently attached to the inactive identity.

**Fix:** Match a unique retained identity by normalized logical path or complete hashes under row locks, bind its `active_rom_id`, move retained ownership to the matched ROM, clear retained IDs, bump the version, and reject ambiguous matches.

### CR-03 [BLOCKER]: Rollback overwrites catalog state instead of restoring it

**File:** `/home/d1sk/romm/backend/handler/database/legacy_migration_handler.py:853-913`

**Issue:** Migration changes only uniquely normalized identities to `missing_from_fs=False`, but records only aggregate counts. Rollback sets every ROM and ROM file on the platform to `missing_from_fs=True`. It cannot distinguish changed rows from rows already visible, unmatched rows, or rows added before rollback, so an unused rollback can make unrelated catalog entries unreachable.

**Fix:** Persist exact per-ROM and per-file prior states in the migration transaction, lock and validate them on rollback, and restore only those recorded values.

### CR-04 [BLOCKER]: Migration confirmation accepts stale source and equal-count catalog changes

**File:** `/home/d1sk/romm/backend/handler/database/legacy_migration_handler.py:343-480`

**Issue:** Confirmation recomputation reduces catalog state to two counts and never reopens the detected source. The source can disappear, become unreadable or unsafe, or change contents and migration still creates the mapping. Replacing one catalog identity with another while preserving counts also passes confirmation.

**Fix:** Bind confirmation to deterministic bounded source and catalog-identity fingerprints, then recompute both under migration locks immediately before mutation and raise `legacy_impact_stale` on any change.

## Warnings

### WR-01 [WARNING]: Post-commit cache failure can turn successful removal into an HTTP 500

**File:** `/home/d1sk/romm/backend/endpoints/roms/__init__.py:2074-2083`

**Issue:** Each removal commits independently, then the endpoint calls Redis-backed cache invalidation without error handling. Redis failure returns an HTTP 500 after one or more removals already committed, leaving the client unable to infer or safely retry the outcome.

**Fix:** Make cache invalidation best-effort after the durable result, or persist an outbox and always return committed per-item outcomes.

### WR-02 [WARNING]: Mapped reads leak storage-resolution exceptions outside the bounded API contract

**File:** `/home/d1sk/romm/backend/handler/storage/read_context.py:118-147`

**Issue:** Resolution and open calls can raise unsafe-symlink, path-escape, invalid-path, or non-directory errors, but only four error classes are translated. Consumers catch `MappedReadError`, so remaining safe failures escape as internal 500 errors after first-use may already have disabled rollback.

**Fix:** Translate the complete expected `StorageResolutionError` family to bounded mapped-read states and test symlink races, invalid paths, and non-directory targets.

### WR-03 [WARNING]: Contract verifier can leak its Uvicorn process when PID validation fails

**File:** `/home/d1sk/romm/backend/tools/verify_phase6_contracts.py:197-210`

**Issue:** `uvicorn_pid` is assigned only after the PID file is read and validated. If the server starts but PID reading or validation fails, cleanup sees no PID, skips termination, and leaves the fixed port and owned files behind.

**Fix:** Let cleanup independently inspect the owned PID file, verify the exact process signature, terminate only that process, and remove only the owned files. Add PID-read and malformed-PID failure tests.

---

_Reviewed: 2026-08-13T01:14:29Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
