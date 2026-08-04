---
phase: 01-immutable-storage-foundation
reviewed: 2026-08-04T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - backend/models/storage.py
  - backend/models/platform.py
  - backend/alembic/env.py
  - backend/alembic/versions/0108_immutable_storage_foundation.py
  - backend/tools/verify_storage_migrations.py
  - backend/exceptions/storage_exceptions.py
  - backend/handler/filesystem/storage_resolver.py
  - backend/handler/database/storage_handler.py
  - backend/handler/database/__init__.py
  - backend/tests/models/test_storage.py
  - backend/tests/handler/filesystem/test_storage_resolver.py
  - backend/tests/handler/database/test_storage_handler.py
  - backend/tests/conftest.py
  - .github/workflows/migrations.yml
findings:
  critical: 3
  warning: 3
  info: 0
  total: 6
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-04T00:00:00Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

The immutable-storage foundation has three release-blocking correctness and security defects. The mapping lock query is not valid on PostgreSQL, path validation is vulnerable to time-of-check/time-of-use symlink replacement, and database constraint failures are reported as duplicates even when the referenced platform does not exist. Test isolation and CI scope also leave material gaps.

## Critical Issues

### CR-01: PostgreSQL rejects the mapping lock query

**File:** `backend/handler/database/storage_handler.py:83-87`
**Issue:** The query combines `joinedload(PlatformStorageMapping.storage_root)`, which emits a left outer join, with an unqualified `FOR UPDATE`. PostgreSQL rejects locking the nullable side of an outer join (`FOR UPDATE cannot be applied to the nullable side of an outer join`). Every `save_mapping` call reaches this query, so mapping creation fails on a supported production dialect even though the migration itself passes.
**Fix:** Lock only the mapping table and load roots separately, for example use `selectinload` with `with_for_update(of=PlatformStorageMapping)`, or remove eager loading and fetch roots explicitly in a second query.

### CR-02: Symlink checks can be bypassed by a concurrent path swap

**File:** `backend/handler/filesystem/storage_resolver.py:123-152`
**Issue:** Each component is checked with `lstat()`, then the complete target is resolved and later returned as a pathname. An actor able to mutate the mounted archive can replace a checked directory with a symlink between those operations (or after resolution before a caller opens it). The final containment check only verifies the resolution observed at that instant and does not bind subsequent filesystem access to the checked inode. This defeats the stated symlink and traversal boundary.
**Fix:** Resolve and open components relative to an already-open root directory descriptor using `openat`-style operations with `O_NOFOLLOW` (and `O_DIRECTORY` for directories), then have callers operate through the validated descriptor. If returning a `Path` remains necessary, document that it is not a security boundary and revalidate at the actual open operation.

### CR-03: All persistence integrity failures are mislabeled as duplicate mappings

**File:** `backend/handler/database/storage_handler.py:120-123`
**Issue:** The broad `except IntegrityError` converts every constraint violation into `DuplicateStorageMappingError`. A nonexistent `platform_id`, a deleted root racing persistence, or another future constraint failure is therefore reported as a duplicate. This hides referential-integrity failures and gives callers incorrect behavior and recovery guidance.
**Fix:** Validate the platform and root under the transaction and translate only the named unique constraints to `DuplicateStorageMappingError`. Re-raise or map foreign-key and other integrity failures to their specific domain errors.

## Warnings

### WR-01: Model tests drop application tables after the session migration fixture

**File:** `backend/tests/models/test_storage.py:12-18`
**Issue:** The session-wide database setup already migrates these tables. This module fixture then drops both tables at teardown, while the session fixture does not rerun migrations. Any later test triggers the autouse cleanup in `backend/tests/conftest.py:104-106` against missing tables, making the full suite order-dependent and liable to fail after this module.
**Fix:** Remove table creation and teardown from this module. Rely on the session migration fixture and clear rows transactionally like the rest of the suite.

### WR-02: Migration CI does not run for model or Alembic environment changes

**File:** `.github/workflows/migrations.yml:3-7`
**Issue:** The workflow is triggered only by changes under `backend/alembic/versions/**`. Changes to ORM models, `backend/alembic/env.py`, or the migration verification tool can break autogeneration or cross-dialect behavior without running any migration job.
**Fix:** Add paths for `backend/models/**`, `backend/alembic/env.py`, `backend/tools/verify_storage_migrations.py`, and relevant dependency/config files.

### WR-03: register_root silently ignores its mode argument

**File:** `backend/handler/database/storage_handler.py:33-49`
**Issue:** The public method accepts a `mode` value but always stores `external_read_only`. A caller passing an unsupported mode receives success with different persisted semantics; the test at `backend/tests/handler/database/test_storage_handler.py:80-88` currently enshrines this surprising behavior.
**Fix:** Remove the parameter until additional modes exist, or reject any value other than `EXTERNAL_READ_ONLY_MODE` with a validation error.

---

_Reviewed: 2026-08-04T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
