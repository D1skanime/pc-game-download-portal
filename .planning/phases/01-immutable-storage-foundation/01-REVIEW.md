---
phase: 01-immutable-storage-foundation
reviewed: 2026-08-05T05:42:01Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - backend/handler/database/storage_handler.py
  - backend/exceptions/storage_exceptions.py
  - backend/tests/handler/database/test_storage_handler.py
  - backend/tests/models/test_storage.py
  - backend/tools/verify_storage_migrations.py
findings:
  critical: 1
  warning: 1
  info: 0
  total: 2
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-05T05:42:01Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

The PostgreSQL locking repair is valid: the mapping query now locks only `PlatformStorageMapping`, relationship loading is separate, and active roots are still locked in ascending ID order before both mapping reads. The model fixture no longer drops migrated tables, the verifier remains isolated, and no Phase 2, NAS, service, or workload scope leaked into these changes. However, the non-PostgreSQL integrity fallback still treats an arbitrary DBAPI message containing a mapping constraint name as a duplicate-key violation. The tests model PostgreSQL structured diagnostics but do not exercise or constrain that vendor fallback.

## Critical Issues

### CR-01: Raw message substring can misclassify unrelated integrity failures as duplicates

**Classification:** BLOCKER
**File:** `backend/handler/database/storage_handler.py:41-47`
**Issue:** When `error.orig.diag.constraint_name` is unavailable, `_is_mapping_unique_violation` searches the entire raw DBAPI message for either constraint name and returns true without first establishing that the error is a unique-key violation. MariaDB and MySQL expose useful error codes (duplicate entry is errno 1062), but the implementation ignores them. A foreign-key, check, trigger, or synthetic integrity failure whose diagnostic happens to mention one of these columns or constraints is therefore translated to `DuplicateStorageMappingError`, violating the requirement that only the two named uniqueness violations receive that domain error. The public error remains bounded, but its semantics are incorrect.
**Fix:** Branch by supported DBAPI diagnostics. Keep PostgreSQL's structured `diag.constraint_name` check, and for MariaDB/MySQL require duplicate-key errno 1062 before matching the reported key name. Return false for unknown DBAPI shapes rather than searching every error string.

```python
errno = getattr(error.orig, "errno", None)
if errno != 1062:
    return False
message = str(error.orig)
return any(name in message for name in cls._MAPPING_UNIQUE_CONSTRAINTS)
```

## Warnings

### WR-01: Classification tests do not cover the MariaDB/MySQL fallback contract

**Classification:** WARNING
**File:** `backend/tests/handler/database/test_storage_handler.py:217-231`
**Issue:** The focused unit test constructs only a PostgreSQL-like `diag.constraint_name`. The real handler test proves the platform uniqueness constraint on whichever database runs the suite, but it does not prove that a non-1062 MariaDB/MySQL integrity error containing a known constraint name is rejected, nor does it exercise the root/path constraint through the vendor diagnostic path. Consequently, the unsafe substring fallback above passes all added tests.
**Fix:** Parameterize representative DBAPI originals for PostgreSQL and MariaDB/MySQL. Include positive errno-1062 cases for both named constraints and negative non-1062 and unknown-shape cases whose messages contain those names. Assert that negative cases become `StoragePersistenceError`, never `DuplicateStorageMappingError`.

---

_Reviewed: 2026-08-05T05:42:01Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
