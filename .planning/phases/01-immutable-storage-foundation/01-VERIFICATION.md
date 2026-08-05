---
phase: 01-immutable-storage-foundation
verified: 2026-08-05T05:46:21Z
status: gaps_found
score: 13/14 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 12/14
  gaps_closed:
    - "PostgreSQL mapping persistence now uses a mapping-only entity-qualified lock and passes isolated PostgreSQL execution."
    - "Missing platform identities and generic unrelated IntegrityError paths remain bounded and distinct."
  gaps_remaining:
    - "MariaDB/MySQL raw diagnostic fallback can misclassify a non-duplicate IntegrityError that mentions a mapping constraint name."
  regressions: []
gaps:
  - truth: "Only named mapping uniqueness violations become DuplicateStorageMappingError, with truthful vendor-specific classification"
    status: failed
    reason: "The non-PostgreSQL fallback matches a known constraint substring without requiring MariaDB/MySQL duplicate-key errno 1062."
    artifacts:
      - path: "backend/handler/database/storage_handler.py"
        issue: "_is_mapping_unique_violation uses unrestricted raw-message substring matching when diag.constraint_name is absent."
      - path: "backend/tests/handler/database/test_storage_handler.py"
        issue: "Tests cover PostgreSQL-like diagnostics only, not vendor positive and negative cases."
    missing:
      - "Require errno 1062 before matching either approved MariaDB/MySQL unique key name."
      - "Return false for unknown DBAPI shapes."
      - "Test errno-1062 positives for both keys and non-1062/unknown-shape negatives containing a known key name."
deferred:
  - truth: "Descriptor-bound protection against a symlink/path swap after point-in-time resolution"
    addressed_in: "Phase 2"
    evidence: "Phase 2 owns policy enforcement before filesystem access; Phase 1 opens no content file."
---

# Phase 1: Immutable Storage Foundation Verification Report

**Phase Goal:** Operators have a portable storage model whose roots and relative mappings cannot resolve outside the approved immutable library.
**Verified:** 2026-08-05T05:46:21Z
**Status:** gaps_found
**Re-verification:** Yes, after plan 01-06 gap closure

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                  | Status   | Evidence                                                                                 |
| --- | -------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------- |
| 1   | Existing external roots register active without creating content                       | VERIFIED | Existing-directory health gate, forced immutable mode, manifests and mutation tripwires. |
| 2   | Only external_read_only persists                                                       | VERIFIED | ORM and revision 0108 named check constraint.                                            |
| 3   | Mappings store root identity and normalized relative path only                         | VERIFIED | Mapping schema and normalization contain no NAS host path.                               |
| 4   | Unsafe lexical forms fail before composition                                           | VERIFIED | Absolute, drive, UNC, backslash, control, empty, dot and traversal cases reject.         |
| 5   | Nested, long and Unicode names are preserved                                           | VERIFIED | Adversarial resolver tests pass.                                                         |
| 6   | Health is bounded and write-free                                                       | VERIFIED | Metadata/access observation only; manifests remain unchanged.                            |
| 7   | Unsafe root and target states fail closed                                              | VERIFIED | Missing, inactive, writable, unreadable, file and escape cases reject.                   |
| 8   | Root and component symlinks fail closed at resolution time                             | VERIFIED | lstat component walk and symlink matrix.                                                 |
| 9   | Registration and mapping persistence do not mutate source                              | VERIFIED | Source manifests and mutation tripwires pass.                                            |
| 10  | Mapping persistence works atomically on behavior dialects                              | VERIFIED | 22 isolated tests pass on MariaDB and 22 on PostgreSQL.                                  |
| 11  | Concurrent overlaps yield one commit and one bounded conflict                          | VERIFIED | Coordinated two-session tests pass on MariaDB and PostgreSQL.                            |
| 12  | Missing identities and generic unrelated persistence failures are bounded and distinct | VERIFIED | Explicit handler tests pass.                                                             |
| 13  | Vendor duplicate classification is truthful and bounded                                | FAILED   | Raw fallback ignores errno; current unit test uses only diag.constraint_name.            |
| 14  | Revision 0108 is reversible and filesystem-free on all dialects                        | VERIFIED | Fresh MariaDB 10.11, MySQL 8.4 and PostgreSQL 15 cycles passed.                          |

**Score:** 13/14 truths verified

### Deferred Items

| Item                                                                     | Addressed In | Evidence                                            |
| ------------------------------------------------------------------------ | ------------ | --------------------------------------------------- |
| Descriptor-relative no-follow enforcement against concurrent replacement | Phase 2      | Phase 2 owns enforcement before actual file access. |

### Required Artifacts

| Artifact                                                      | Expected                          | Status   | Details                                                                                  |
| ------------------------------------------------------------- | --------------------------------- | -------- | ---------------------------------------------------------------------------------------- |
| backend/models/storage.py                                     | Root and mapping identities       | VERIFIED | Substantive constraints and relationships, wired to Alembic.                             |
| backend/alembic/versions/0108_immutable_storage_foundation.py | Portable schema                   | VERIFIED | All three migration cycles pass, no filesystem operation.                                |
| backend/handler/filesystem/storage_resolver.py                | Normalization, health, resolution | VERIFIED | Substantive, wired and adversarially tested.                                             |
| backend/exceptions/storage_exceptions.py                      | Bounded errors                    | VERIFIED | All storage error classes are substantive and used.                                      |
| backend/handler/database/storage_handler.py                   | Atomic persistence                | PARTIAL  | Locking fixed; vendor diagnostic fallback remains overbroad.                             |
| backend/tests/handler/filesystem/test_storage_resolver.py     | Adversarial matrix                | VERIFIED | TEST-01 and immutable evidence covered.                                                  |
| backend/tests/handler/database/test_storage_handler.py        | Race and error evidence           | PARTIAL  | Behavior passes; vendor classification matrix absent.                                    |
| backend/tools/verify_storage_migrations.py                    | Isolated dialect gate             | VERIFIED | Ephemeral containers, cleanup, MariaDB/PostgreSQL behavior and MySQL migration baseline. |

### Key Link Verification

| From                | To                           | Via                                     | Status  | Details                                                               |
| ------------------- | ---------------------------- | --------------------------------------- | ------- | --------------------------------------------------------------------- |
| models/platform.py  | models/storage.py            | scalar back_populates                   | WIRED   | Platform and mapping relationships connect.                           |
| storage_resolver.py | storage models/errors        | state checks and typed rejection        | WIRED   | Immutable mode, active state and bounded errors used.                 |
| storage_handler.py  | storage_resolver.py          | health and canonical validation         | WIRED   | Registration and save invoke resolver.                                |
| storage_handler.py  | PlatformStorageMapping       | selectin load and entity-qualified lock | WIRED   | PostgreSQL execution passes.                                          |
| storage_handler.py  | DuplicateStorageMappingError | DBAPI classification                    | PARTIAL | PostgreSQL structured path precise; raw vendor path lacks errno gate. |

### Data-Flow Trace (Level 4)

Not applicable. This phase has no dynamic rendering surface.

### Behavioral Spot-Checks

| Behavior                          | Command                                                        | Result                                            | Status           |
| --------------------------------- | -------------------------------------------------------------- | ------------------------------------------------- | ---------------- |
| MariaDB behavior/concurrency      | verify_storage_migrations.py with --handler-tests              | 22 passed                                         | PASS             |
| PostgreSQL behavior/concurrency   | same isolated verifier                                         | 22 passed                                         | PASS             |
| Current classification test       | pytest -k only_named_mapping_unique_constraints_are_duplicates | 2 passed, PostgreSQL-like diagnostics only        | PASS, INCOMPLETE |
| MariaDB/MySQL negative diagnostic | inspect _is_mapping_unique_violation                           | No errno check; known substring alone is accepted | FAIL             |

### Probe Execution

| Probe                  | Command                                                                                                                            | Result                                                                                                                                             | Status |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Three-dialect verifier | python3 backend/tools/verify_storage_migrations.py --dialects mariadb mysql postgresql --runner-container romm-dev --handler-tests | Exit 0 in 31.7s; all cycles passed; 22 MariaDB and 22 PostgreSQL behavior tests passed; MySQL behavior skipped on documented minimal 0107 baseline | PASS   |

### Requirements Coverage

| Requirement | Status    | Evidence                                                  |
| ----------- | --------- | --------------------------------------------------------- |
| ROOT-01     | SATISFIED | Existing-root-only registration and persistence tests.    |
| ROOT-02     | SATISFIED | Immutable mode ORM and DB constraint.                     |
| ROOT-03     | SATISFIED | Non-mutating health fields and manifest evidence.         |
| ROOT-04     | SATISFIED | Root path is separate; mapping is relative only.          |
| PATH-01     | SATISFIED | Central lexical rejection matrix.                         |
| PATH-02     | SATISFIED | Strict canonical containment.                             |
| PATH-03     | SATISFIED | Existing readable directory and fail-closed state checks. |
| PATH-04     | SATISFIED | Unicode, nesting and safe component containment.          |
| PATH-05     | SATISFIED | Root and component symlink rejection.                     |
| TEST-01     | SATISFIED | Every required path category has passing coverage.        |

No orphaned Phase 1 requirement exists.

### Anti-Patterns Found

| File                                                   | Line    | Pattern                              | Severity | Impact                                                           |
| ------------------------------------------------------ | ------- | ------------------------------------ | -------- | ---------------------------------------------------------------- |
| backend/handler/database/storage_handler.py            | 41-42   | Raw diagnostic substring fallback    | BLOCKER  | Non-duplicate MariaDB/MySQL errors can be mislabeled duplicates. |
| backend/tests/handler/database/test_storage_handler.py | 217-231 | PostgreSQL-only synthetic diagnostic | WARNING  | Unsafe vendor fallback passes tests.                             |

No unreferenced TBD, FIXME or XXX marker was found.

### Human Verification Required

None. The remaining gap is programmatically determinable.

### Gaps Summary

Plan 01-06 closes both original blockers: PostgreSQL mapping persistence now executes with a legal entity-qualified lock, and missing identities plus generic unrelated integrity errors remain bounded and distinct. One blocker remains. MariaDB/MySQL duplicate classification accepts an approved key-name substring without first requiring errno 1062, and no vendor-specific positive/negative tests constrain it. Phase 1 remains gaps_found until both the vendor error code and approved key name are required and negative cases are tested.

---

_Verified: 2026-08-05T05:46:21Z_
_Verifier: the agent (gsd-verifier)_
