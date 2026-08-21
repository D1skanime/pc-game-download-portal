---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 42
subsystem: backend-storage
tags: [sqlalchemy, alembic, privacy, migration, tdd]
requires:
  - phase: 06-37
    provides: private source-observed identity digest derivation
provides:
  - digest-only durable source membership evidence
  - portable revision 0114 authority invalidation
affects: [06-44, 06-46, 06-47]
tech-stack:
  added: []
  patterns:
    [
      cascade-owned private evidence rows,
      bounded portable authority invalidation,
    ]
key-files:
  created: [backend/alembic/versions/0114_legacy_source_identities.py]
  modified:
    [backend/models/storage.py, backend/tests/models/test_safe_lifecycle.py]
key-decisions:
  - Persist only 64-character lowercase hexadecimal identity digests in a private result-owned table.
  - Invalidate selectable detection authority in bounded batches before evidence is absent on upgrade or downgrade.
metrics:
  duration: 18m
  completed: 2026-08-21
---

# Phase 6 Plan 42: Private Legacy Source Identities Summary

Durable digest-only source membership evidence with bounded cross-revision invalidation and no public response exposure.

## Accomplishments

- Added LegacyDetectionSourceIdentity with one private digest per detection result, database cascade ownership, deterministic ordering, and delete-orphan ORM ownership.
- Enforced exact 64-character lowercase hexadecimal evidence with named portable checks, uniqueness, foreign key, primary key, and ordered index.
- Added revision 0114 with bounded pre-evidence invalidation on upgrade and bounded evidence-loss invalidation before downgrade.
- Preserved public detection schemas without source identity relationships, paths, filenames, hosts, raw records, snapshots, or tokens.

## TDD Evidence

- **RED:** nonce 54f1cf2c5f47da20e9f60c9dd5df945a collected the named test and exited 1 only because the model was absent.
- **GREEN:** nonces 67e6b0357f40e8e08ee858110bda5c2c and 82a859e9796250a25cf61f84ed325395 passed all 12 model tests.
- **Independent verification:** nonce 014324c40debb6bb005e6d5ddc640004 passed all 12 model tests.
- **Migration lifecycle:** nonce 9ad29aa1291fe4ba98db3218c307525f passed upgrade head, downgrade 0113, and upgrade head on disposable MariaDB authority.
- Scoped Trunk format/check and git diff --check passed.

## Task Commits

1. **Task 1 RED:** f9f3ecf26
2. **Task 2 GREEN:** 9c2c52098

## Files Created/Modified

- backend/models/storage.py
- backend/alembic/versions/0114_legacy_source_identities.py
- backend/tests/models/test_safe_lifecycle.py

## Decisions Made

- Used nested standard REPLACE operations with CHAR_LENGTH and LOWER for a portable hexadecimal check.
- Invalidated rows in deterministic 500-row batches.
- Downgrade first targets evidence-bearing rows, then defensively invalidates any remaining selectable row.
- Left real three-dialect disposable authority to Plan 06-46 as specified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used an owned disposable test runner**

- **Found during:** Task 1 RED lifecycle
- **Issue:** The persistent romm-dev container was stopped and restart was prohibited.
- **Fix:** Used fresh nonce-owned runners from romm-romm-dev with canonical bind, romm_default, explicit environment, and task-only tmpfs.
- **Verification:** Exact cleanup and normal application SELECT 1 passed before and after.
- **Committed in:** Not applicable.

**2. [Rule 2 - Missing Critical Functionality] Invalidated all remaining selectable rows on downgrade**

- **Found during:** Task 2 migration review
- **Issue:** A corrupted selectable row without evidence could otherwise retain authority after the evidence table was dropped.
- **Fix:** Applied a second bounded pass to any remaining selectable rows.
- **Verification:** Model suite, Trunk, and migration lifecycle passed.
- **Committed in:** 9c2c52098

## Issues Encountered

- The initial persistent-runner RED and one disposable grant-quoting attempt were rejected as infrastructure evidence. Both stopped before unowned mutation or cleaned their exact owned resources.
- Inherited pytest-env and Alembic path-separator warnings did not affect verification.

## Known Stubs

None.

## Threat Flags

None. The plan threat model covers the new private database surface and isolated test authority.

## Cleanup and Continuity

- All nonce databases, principals, basetemps, and runners were removed.
- No service was restarted or deployed.
- No tracked file was deleted.
- The exact 28-entry baseline remains unchanged at SHA-256 4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1.

## Next Phase Readiness

Revision 0114 is ready for handler persistence in Plan 06-44 and three-dialect verification in Plan 06-46.

## Self-Check: PASSED

All key files and task commits exist, verification and cleanup passed, and the 28-entry baseline is preserved.
