---
phase: 01-immutable-storage-foundation
verified: 2026-08-05T20:19:08Z
status: passed
score: 14/14 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 13/14
  gaps_closed:
    - "MariaDB/MySQL duplicate classification now requires errno 1062 and an approved key."
    - "Both-key positive and non-1062/unknown-shape negative tests now pass."
  gaps_remaining: []
  regressions: []
deferred:
  - truth: "Descriptor-bound protection against a path swap after point-in-time resolution"
    addressed_in: "Phase 2"
    evidence: "Phase 2 owns enforcement at filesystem access; Phase 1 opens no content file."
---

# Phase 1: Immutable Storage Foundation Verification Report

**Phase Goal:** Operators have a portable storage model whose roots and relative mappings cannot resolve outside the approved immutable library.
**Verified:** 2026-08-05T20:19:08Z
**Status:** passed
**Re-verification:** Yes, after final gap closure

## Goal Achievement

### Observable Truths

| #   | Truth                                                                  | Status   | Evidence                                                                                                              |
| --- | ---------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| 1   | Existing roots register active without source creation                 | VERIFIED | Existing absolute directory, forced immutable mode, metadata-only health, manifest/tripwire tests.                    |
| 2   | Only `external_read_only` persists                                     | VERIFIED | Named ORM and 0108 check; model rejection test.                                                                       |
| 3   | Mappings store root identity and normalized relative path only         | VERIFIED | Mapping schema has IDs, relative path, timestamps, and no host/composed path.                                         |
| 4   | Unsafe lexical forms fail before composition                           | VERIFIED | Absolute, drive, UNC, backslash, control, empty, dot, separator, traversal matrix.                                    |
| 5   | Nested, long, case-sensitive, and Unicode names survive exactly        | VERIFIED | Named resolver cases cover all forms.                                                                                 |
| 6   | Health is bounded and write-free                                       | VERIFIED | Only `lstat` and `os.access`; bounded fields and mutation tripwires.                                                  |
| 7   | Unsafe root and target states fail closed                              | VERIFIED | Missing, inactive, wrong-mode, writable, unreadable, file, and escape cases.                                          |
| 8   | Root and component symlinks fail closed                                | VERIFIED | Root and component `lstat` precede strict resolution.                                                                 |
| 9   | Registration and persistence do not mutate source                      | VERIFIED | Source manifests and mutation tripwires pass.                                                                         |
| 10  | Mapping persistence works on behavior dialects                         | VERIFIED | Fresh isolated MariaDB and PostgreSQL runs each passed 33 tests.                                                      |
| 11  | Ordered concurrency yields one commit and one bounded conflict         | VERIFIED | Root locks order by ID before mapping load; two-session test passes on both dialects.                                 |
| 12  | PostgreSQL locks and generic integrity errors are portable and precise | VERIFIED | Mapping-only `FOR UPDATE`; missing identities and unrelated errors remain bounded and distinct.                       |
| 13  | Vendor duplicate classification is truthful and bounded                | VERIFIED | PostgreSQL approved structured constraints; MariaDB/MySQL errno 1062 plus approved key; all other shapes fail closed. |
| 14  | 0108 is reversible and filesystem-free on all dialects                 | VERIFIED | MariaDB 10.11, MySQL 8.4, PostgreSQL 15 upgrade/downgrade/re-upgrade exited 0.                                        |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact                                                        | Status   | Details                                                                  |
| --------------------------------------------------------------- | -------- | ------------------------------------------------------------------------ |
| `backend/models/storage.py`                                     | VERIFIED | Substantive identities, bounded health, constraints, relationships.      |
| `backend/alembic/versions/0108_immutable_storage_foundation.py` | VERIFIED | Portable roots-first schema, reverse downgrade, no filesystem use.       |
| `backend/handler/filesystem/storage_resolver.py`                | VERIFIED | Substantive, typed, non-mutating, wired into persistence.                |
| `backend/handler/database/storage_handler.py`                   | VERIFIED | Ordered locks, overlap checks, precise vendor classification.            |
| `backend/tests/handler/filesystem/test_storage_resolver.py`     | VERIFIED | TEST-01 adversarial and immutability matrix.                             |
| `backend/tests/handler/database/test_storage_handler.py`        | VERIFIED | Ordered concurrency, both-key positives, non-1062 and unknown negatives. |
| `backend/tools/verify_storage_migrations.py`                    | VERIFIED | Unique ephemeral containers, finally cleanup, no library mount.          |

### Key Link Verification

| From           | To                           | Status | Details                                                                |
| -------------- | ---------------------------- | ------ | ---------------------------------------------------------------------- |
| platform model | storage mapping              | WIRED  | Scalar `back_populates` agrees.                                        |
| resolver       | models and typed errors      | WIRED  | Mode, active state, containment, health, and errors enforced.          |
| persistence    | resolver                     | WIRED  | Registration checks health; save normalizes and resolves every target. |
| persistence    | mapping table                | WIRED  | Ordered root lock then PostgreSQL-safe mapping-only lock.              |
| persistence    | duplicate/persistence errors | WIRED  | Structured constraint or errno-gated approved raw key only.            |

### Behavioral Spot-Checks

| Behavior                           | Result                                                                   | Status |
| ---------------------------------- | ------------------------------------------------------------------------ | ------ |
| MariaDB persistence/concurrency    | 33 passed                                                                | PASS   |
| PostgreSQL persistence/concurrency | 33 passed                                                                | PASS   |
| Vendor diagnostic matrix           | Both keys positive; unrelated, non-1062, and unknown negative cases pass | PASS   |
| Fixture cleanup                    | Mapping deletion precedes platform and root deletion                     | PASS   |

### Probe Execution

| Probe                                                                                                                                | Result                                                                                                                                                                  | Status |
| ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| `python3 backend/tools/verify_storage_migrations.py --dialects mariadb mysql postgresql --runner-container romm-dev --handler-tests` | Exit 0 in 29.6s; all cycles passed; MariaDB and PostgreSQL each passed 33 behavior tests; MySQL handler tests intentionally omitted on documented minimal 0107 baseline | PASS   |

### Requirements Coverage

| Requirement | Status    | Evidence                                    |
| ----------- | --------- | ------------------------------------------- |
| ROOT-01     | SATISFIED | Existing-root-only registration.            |
| ROOT-02     | SATISFIED | Immutable single-mode constraint.           |
| ROOT-03     | SATISFIED | Metadata-only safe health.                  |
| ROOT-04     | SATISFIED | Root path separate; mappings relative only. |
| PATH-01     | SATISFIED | Central lexical rejection.                  |
| PATH-02     | SATISFIED | Strict canonical containment.               |
| PATH-03     | SATISFIED | Existing readable directories only.         |
| PATH-04     | SATISFIED | Unicode/nesting and component containment.  |
| PATH-05     | SATISFIED | Root and component symlink rejection.       |
| TEST-01     | SATISFIED | Every required category has named coverage. |

No orphaned Phase 1 requirement exists.

### Anti-Patterns Found

No unreferenced TBD, FIXME, or XXX marker, placeholder, hollow implementation, mutation primitive, or unrestricted raw diagnostic fallback was found.

### Human Verification Required

None. Real NAS operational proof is explicitly Phase 9 work.

### Disconfirmation Pass

No partial Phase 1 requirement remained. Negative save-path tests, not classifier-only tests, assert exact bounded persistence errors. Unknown DBAPI shapes, non-1062 errors mentioning both approved keys, and unrelated PostgreSQL constraints are covered.

### Gaps Summary

No blocking or uncertain Phase 1 gap remains. PostgreSQL lock portability, generic integrity handling, errno gating, both-key positives, negative diagnostics, ordered concurrency, and fixture order are closed. Phase 2 retains the explicitly deferred descriptor-bound access race protection.

---

_Verified: 2026-08-05T20:19:08Z_
_Verifier: the agent (gsd-verifier)_
