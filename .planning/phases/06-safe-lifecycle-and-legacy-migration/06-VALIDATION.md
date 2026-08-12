---
phase: 06-safe-lifecycle-and-legacy-migration
status: draft
nyquist_validation: enabled
requirements:
  [CAT-01, CAT-02, CAT-03, CAT-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
created: 2026-08-12
---

# Phase 6: Safe Lifecycle and Legacy Migration - Validation

## Objective

Prove every outcome changes only explicit RomM-owned state, preserves external source byte-for-byte, fails closed under conflicts/races, and works on MariaDB, MySQL and PostgreSQL. [VERIFIED: .planning/config.json]

## Requirement Matrix

| Req    | Evidence                                                                       |
| ------ | ------------------------------------------------------------------------------ |
| CAT-01 | API/OpenAPI says catalog removal and accepts no source-delete input.           |
| CAT-02 | exact owned dependency/asset set changes; source manifest never changes.       |
| CAT-03 | removal retains catalog/history, marks unreachable, revises/audits atomically. |
| CAT-04 | all source mutations remain denied before I/O.                                 |
| MIG-01 | only exact `roms/<fs_slug>` and `<fs_slug>/roms` candidates.                   |
| MIG-02 | upgrade/downgrade/re-upgrade and transactions pass on all dialects.            |
| MIG-03 | missing/empty/unreadable/ambiguous/unsafe/conflicting means manual mapping.    |
| MIG-04 | mapping/migration/use state survives API/worker restart.                       |
| MIG-05 | no source fallback; result/status expiry observable.                           |

## Test Layers

- Pure: exact candidate construction, unique matching, budgets, safe serialization, state transitions.
- Handler: removal retention; atomic migration; injected failure after every flush; rollback/use race; overlap and stale-version rejection.
- API: auth before observation, safe errors, stale confirmation, independent per-platform commits, OpenAPI contract.
- Policy: mutation denial and source-authority inventory remain closed.
- Integration: writable and read-only source fixtures, restart, worker and actual three-dialect containers.

## Cancellation Boundaries

| Scenario             | Boundary                                  |
| -------------------- | ----------------------------------------- |
| queued after removal | before first I/O                          |
| scan mid-run         | next bounded batch, before reconciliation |
| hash mid-run         | next chunk/file                           |
| stream/download      | before response commitment                |
| multi-file           | before each member                        |
| replacement mapping  | old ID/revision never redirects           |

Instrument descriptor opens and DB writes. After invalidation no later open/reconciliation may occur under stale identity. Already-open single-file reads may finish after their final boundary; do not claim descriptor revocation. [ASSUMED]

## Immutability Evidence

For success, rejection, injected crash, rollback and retry, capture source path/type/mode/size/hash/symlink identity before/after on writable and read-only-mounted fixtures. Assert source byte/structure equality and allowed owned changes separately. Exclude atime until Phase 9. [VERIFIED: Phase 2/5 patterns]

## Concurrency and Dialects

Use barriers, not sleeps, for migrate/migrate, migrate/create, remove/read, rollback/first-use and confirm/lifecycle races. Run pristine upgrade, seeded-0110 upgrade, downgrade and re-upgrade in isolated MariaDB, MySQL, PostgreSQL containers. Restart API/workers and prove persistence/stale queued-work failure. [VERIFIED: Phase 3 pattern]

## Adversarial Cases

- aliases, case/whitespace/Unicode variants, configured bindings, both canonical candidates;
- absolute/UNC/drive/traversal/symlink/missing/file/writable/disabled/unreadable paths;
- unknown/stale/expired/replayed/cross-platform result and rollback IDs;
- budget exhaustion, filesystem/catalog change after preview;
- cleanup crash/retry and exception path sentinels.

## Wave 0

- [ ] `backend/tests/endpoints/roms/test_catalog_removal.py`
- [ ] `backend/tests/handler/database/test_storage_lifecycle.py`
- [ ] `backend/tests/handler/storage/test_legacy_migration.py`

## Plan Assignment and Executable Gates

- Plans 01 and 08 extend backend/tools/verify_storage_migrations.py and run pristine plus seeded-0110 upgrade/downgrade/re-upgrade in uniquely named disposable MariaDB, MySQL and PostgreSQL containers after verifying the runner bind mount is this checkout.
- Plan 03 owns the D-04 typed mapping-removal consequence and ordinary confirmation contract plus endpoint/OpenAPI tests.
- Plan 07 owns only productive first-use CAS consumer wiring. Plan 08 exclusively owns D-15/D-16 rollback eligibility, rollback mutation, restart persistence, endpoint/OpenAPI tests, and dialect verification.
- Plan 09 first creates RED unit expectations for the absent controlled-generation harness, then implements the harness, runs final characterization and the real three-dialect verifier, regenerates OpenAPI types, and typechecks the frontend.

## Revision 2 Wave Assignment

Wave 1: 01. Wave 2: 02 and 03. Wave 3: 04 (depends 01,03). Wave 4: 05. Wave 5: 06. Wave 6: 07. Wave 7: 08. Wave 8: 09. Same-wave plans have no file overlap.
