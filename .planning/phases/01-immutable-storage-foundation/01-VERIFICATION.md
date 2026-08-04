---
phase: 01-immutable-storage-foundation
verified: 2026-08-04T21:30:47Z
status: gaps_found
score: 12/14 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Mappings validate and save atomically on every supported database dialect"
    status: failed
    reason: "The mapping lock query combines joinedload of storage_root with an unqualified FOR UPDATE. PostgreSQL rejects locking the nullable side of the emitted outer join, so save_mapping cannot reach persistence on a supported dialect."
    artifacts:
      - path: "backend/handler/database/storage_handler.py"
        issue: "Lines 83-87 use joinedload(PlatformStorageMapping.storage_root).with_for_update()."
      - path: "backend/tests/handler/database/test_storage_handler.py"
        issue: "Persistence behavior is exercised against MariaDB only; no PostgreSQL handler execution catches the invalid SQL."
    missing:
      - "Lock only PlatformStorageMapping rows on PostgreSQL and load roots separately, for example with selectinload and with_for_update(of=PlatformStorageMapping)."
      - "Add a PostgreSQL save_mapping behavioral test, not only migration DDL coverage."
  - truth: "Persistence failures remain typed, bounded, and semantically correct"
    status: failed
    reason: "Every IntegrityError is translated to DuplicateStorageMappingError, including foreign-key failures for nonexistent platforms or raced root deletion."
    artifacts:
      - path: "backend/handler/database/storage_handler.py"
        issue: "Lines 120-123 classify all database constraint failures as duplicates."
      - path: "backend/tests/handler/database/test_storage_handler.py"
        issue: "No test covers nonexistent platform_id, root deletion races, or non-unique integrity failures."
    missing:
      - "Validate referenced identities in the transaction and translate only named unique constraints to DuplicateStorageMappingError."
      - "Add tests for foreign-key and other non-duplicate IntegrityError paths."
deferred:
  - truth: "Descriptor-bound protection against a symlink/path swap after point-in-time resolution"
    addressed_in: "Phase 2"
    evidence: "Phase 2 requires one deny-by-default policy before filesystem access and coverage of every operation addressing an external root; Phase 1 PLANs explicitly accept TOCTOU because Phase 1 opens no content file."
---

# Phase 1: Immutable Storage Foundation Verification Report

**Phase Goal:** Operators have a portable storage model whose roots and relative mappings cannot resolve outside the approved immutable library.
**Verified:** 2026-08-04T21:30:47Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                       | Status   | Evidence                                                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Existing external roots register active and health inspection does not create content       | VERIFIED | `register_root` requires an absolute existing directory, calls metadata-only `check_storage_root_health`, forces active immutable mode, and the registration tests use manifests and mutation tripwires. |
| 2   | Only `external_read_only` persists                                                          | VERIFIED | ORM and revision 0108 define named check constraints restricting mode to `external_read_only`.                                                                                                           |
| 3   | Mappings contain root identity plus a normalized relative path, never a NAS host path       | VERIFIED | `PlatformStorageMapping` has only identity, timestamp, and `relative_path` columns; normalization precedes persistence.                                                                                  |
| 4   | Unsafe lexical forms fail before filesystem composition                                     | VERIFIED | `normalize_relative_path` rejects POSIX absolute, Windows drive/UNC/backslash, control characters, empty/dot/traversal segments before constructing target paths.                                        |
| 5   | Valid nested, long, and Unicode archive names are preserved exactly                         | VERIFIED | Normalizer returns the original string unchanged; parameterized and property tests cover composed/decomposed Unicode and nesting.                                                                        |
| 6   | Health is bounded and write-free                                                            | VERIFIED | Health uses `lstat`, `os.access`, and field assignment only; tests compare source manifests and tripwire mutation primitives.                                                                            |
| 7   | Missing, inactive, writable, unreadable, file-target, and escaped targets fail closed       | VERIFIED | Resolver checks active immutable roots, existence, directory type, permissions, canonical containment, and typed errors.                                                                                 |
| 8   | Point-in-time configured-root and component symlinks fail closed                            | VERIFIED | Root and every target component are checked with `lstat`; symlink-position and target-form tests exist. Descriptor-bound post-check use is deferred to Phase 2.                                          |
| 9   | Existing deployment roots register without creation                                         | VERIFIED | Handler health-gates before flush and tests assert identical source manifests.                                                                                                                           |
| 10  | Mappings validate and save atomically on supported dialects                                 | FAILED   | PostgreSQL rejects the joined eager-load plus unqualified `FOR UPDATE` query at `storage_handler.py:83-87`.                                                                                              |
| 11  | Duplicate and overlap races fail closed on the exercised MariaDB path                       | VERIFIED | Ordered active-root locks, recheck, uniqueness constraints, and coordinated two-session tests exist.                                                                                                     |
| 12  | Persistence errors are typed, bounded, and correct                                          | FAILED   | Broad `IntegrityError` handling mislabels all constraint failures as duplicates.                                                                                                                         |
| 13  | Writable fixtures remain identical through health, resolution, registration, and validation | VERIFIED | Resolver and handler test suites record before/after manifests and install mutation tripwires.                                                                                                           |
| 14  | Revision 0108 is reversible and filesystem-free across MariaDB, MySQL, and PostgreSQL       | VERIFIED | Migration contains schema operations only; verifier and pinned CI jobs define independent upgrade/downgrade/re-upgrade cycles for all three dialects. Current rerun was unavailable, noted below.        |

**Score:** 12/14 truths verified

### Deferred Items

| #   | Item                                                                                   | Addressed In | Evidence                                                                                                                                                                     |
| --- | -------------------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Descriptor-relative, no-follow enforcement against concurrent symlink/path replacement | Phase 2      | Phase 2 owns policy enforcement before actual filesystem access. Phase 1 PLAN 01-03 and 01-05 explicitly scope resolution to point-in-time checks and open no content files. |

### Required Artifacts

| Artifact                                                        | Expected                                         | Status   | Details                                                                                                             |
| --------------------------------------------------------------- | ------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------- |
| `backend/models/storage.py`                                     | Root and mapping identities                      | VERIFIED | Substantive models, named constraints, relationships, and health fields; imported by handlers and Alembic metadata. |
| `backend/alembic/versions/0108_immutable_storage_foundation.py` | Portable reversible schema                       | VERIFIED | Creates roots before mappings and drops in reverse order; no filesystem import or data transform.                   |
| `backend/handler/filesystem/storage_resolver.py`                | Pure normalization, health, canonical resolution | VERIFIED | Substantive and wired into persistence; point-in-time boundary only.                                                |
| `backend/exceptions/storage_exceptions.py`                      | Bounded domain errors                            | PARTIAL  | Substantive and wired, but handler applies duplicate error too broadly.                                             |
| `backend/handler/database/storage_handler.py`                   | Root and mapping persistence                     | FAILED   | Substantive and registered, but PostgreSQL lock SQL is invalid and integrity classification is overbroad.           |
| `backend/tests/handler/filesystem/test_storage_resolver.py`     | Adversarial filesystem matrix                    | VERIFIED | Covers lexical, Unicode, health, target, containment, symlink, and immutable-manifest cases.                        |
| `backend/tests/handler/database/test_storage_handler.py`        | Transaction and race evidence                    | PARTIAL  | Good MariaDB coverage; missing supported PostgreSQL handler execution and non-duplicate integrity cases.            |
| `.github/workflows/migrations.yml`                              | Three-dialect migration gate                     | PARTIAL  | Three dialect jobs exist, but pull-request paths include only `backend/alembic/versions/**`.                        |

### Key Link Verification

| From                         | To                          | Via                                    | Status | Details                                                                         |
| ---------------------------- | --------------------------- | -------------------------------------- | ------ | ------------------------------------------------------------------------------- |
| `backend/models/platform.py` | `backend/models/storage.py` | scalar `back_populates` relationship   | WIRED  | Platform has optional scalar `storage_mapping`; mapping links back to platform. |
| `storage_resolver.py`        | `storage_exceptions.py`     | typed rejection                        | WIRED  | Resolver raises bounded storage-domain exceptions.                              |
| `storage_resolver.py`        | `models/storage.py`         | mode and active state                  | WIRED  | Root resolution checks `active` and exact immutable mode.                       |
| `storage_handler.py`         | `storage_resolver.py`       | health and canonical target validation | WIRED  | Registration calls health; mapping load calls normalization and resolution.     |
| resolver tests               | resolver public contracts   | direct calls                           | WIRED  | Tests invoke normalization, health, root resolution, and directory resolution.  |

### Data-Flow Trace (Level 4)

Not applicable. This phase adds backend persistence and resolution primitives, not a dynamic rendering surface or consumer cutover.

### Behavioral Spot-Checks

| Behavior                               | Command                                                | Result                                                                                                                                | Status |
| -------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Focused phase suite                    | `docker exec romm-dev ... uv run pytest ...`           | Existing container has no `uv`; repository virtualenv points to stale `/app/.venv/bin/python3`. No service was restarted or replaced. | SKIP   |
| Python compilation                     | host `python3 -m compileall` on phase modules          | Interpreter attempted writes into root-owned `__pycache__` and was denied; no source file changed.                                    | SKIP   |
| Static PostgreSQL lock-path inspection | inspect SQLAlchemy query at `storage_handler.py:83-87` | Joined eager load emits outer join combined with unqualified `FOR UPDATE`; known PostgreSQL-invalid shape remains current.            | FAIL   |

### Probe Execution

No phase probe scripts are declared. Migration verification is a stateful ephemeral-container tool and was not rerun because this verification was constrained not to alter running services; its code and CI contract were inspected instead.

### Requirements Coverage

| Requirement | Source              | Status    | Evidence                                                                                           |
| ----------- | ------------------- | --------- | -------------------------------------------------------------------------------------------------- |
| ROOT-01     | Roadmap/Plans 01-04 | SATISFIED | Existing-root-only active registration exists and is non-mutating.                                 |
| ROOT-02     | Roadmap/Plan 01-01  | SATISFIED | ORM and DB constraint permit immutable mode only. The ignored public `mode` argument is a warning. |
| ROOT-03     | Roadmap/Plan 01-03  | SATISFIED | Reachable/readable/non-writable/timestamp/safe error fields are populated without a write probe.   |
| ROOT-04     | Roadmap/Plan 01-01  | SATISFIED | Root container path is separate; mapping stores no absolute or host path.                          |
| PATH-01     | Roadmap/Plan 01-02  | SATISFIED | Central lexical rejection covers required forms.                                                   |
| PATH-02     | Roadmap/Plan 01-03  | SATISFIED | Root and target are strictly resolved and checked with `relative_to`.                              |
| PATH-03     | Roadmap/Plan 01-03  | SATISFIED | Existing readable directories only; missing/file/inactive/escape cases reject.                     |
| PATH-04     | Roadmap/Plan 01-02  | SATISFIED | Valid names preserved; containment avoids string prefixes.                                         |
| PATH-05     | Roadmap/Plan 01-03  | SATISFIED | Configured-root and each component symlink are rejected at resolution time.                        |
| TEST-01     | Roadmap/Plan 01-05  | SATISFIED | Named tests cover every listed adversarial category.                                               |

No orphaned Phase 1 requirement was found.

### Anti-Patterns Found

| File                                          | Line    | Pattern                                    | Severity | Impact                                                                         |
| --------------------------------------------- | ------- | ------------------------------------------ | -------- | ------------------------------------------------------------------------------ |
| `backend/handler/database/storage_handler.py` | 83-87   | `joinedload` plus unqualified `FOR UPDATE` | BLOCKER  | Mapping persistence fails on PostgreSQL.                                       |
| `backend/handler/database/storage_handler.py` | 120-123 | broad `IntegrityError` classification      | BLOCKER  | Referential and future constraint failures are falsely reported as duplicates. |
| `backend/tests/models/test_storage.py`        | 12-18   | module fixture drops migrated tables       | WARNING  | Full-suite outcome is order-dependent after this module.                       |
| `.github/workflows/migrations.yml`            | 3-7     | narrow path trigger                        | WARNING  | Model, Alembic environment, and verifier changes can bypass migration CI.      |
| `backend/handler/database/storage_handler.py` | 38, 48  | ignored `mode` argument                    | WARNING  | Unsupported caller input succeeds with different persisted semantics.          |

No unreferenced TBD, FIXME, or XXX debt marker was identified in the reviewed phase implementation.

### Human Verification Required

None. The observable blocking defects are statically determinable. Real NAS activation and operational atime proof are explicitly outside Phase 1 and scheduled for Phase 9.

### Gaps Summary

The immutable schema, lexical boundary, metadata-only health, point-in-time canonical resolution, and adversarial fixtures are substantive and wired. The phase nevertheless cannot pass because the persistence layer is not behaviorally portable: its mapping lock query fails on PostgreSQL, and its error boundary misclassifies all integrity failures as duplicate mappings. These are current-code defects, not SUMMARY discrepancies or human-only uncertainties.

The code review's symlink TOCTOU concern is real but explicitly scoped to actual file use in Phase 2, so it is recorded as deferred rather than used to fail Phase 1. The remaining three review warnings are confirmed and should be fixed with the blockers because they weaken test determinism, CI coverage, and API semantics.

---

_Verified: 2026-08-04T21:30:47Z_
_Verifier: the agent (gsd-verifier)_
