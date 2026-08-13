---
phase: 06-safe-lifecycle-and-legacy-migration
status: passed
nyquist_validation: enabled
requirements:
  [CAT-01, CAT-02, CAT-03, CAT-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
created: 2026-08-12
validated: 2026-08-13
---

# Phase 6: Safe Lifecycle and Legacy Migration - Validation

## Objective

Prove every outcome changes only explicit RomM-owned state, preserves external source byte-for-byte, fails closed under conflicts/races, and works on MariaDB, MySQL and PostgreSQL. [VERIFIED: .planning/config.json]

## Requirement Matrix

| Req    | Evidence                                                                                                                                   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| CAT-01 | API and generated OpenAPI describe catalog removal with no source-delete input.                                                            |
| CAT-02 | Owned dependency and asset changes pass while writable/read-only source manifests remain equal.                                            |
| CAT-03 | Removal retention, unreachable state, revision, and audit assertions pass atomically.                                                      |
| CAT-04 | The closed mutation inventory denies create/upload/write/overwrite/rename/move/copy/delete/extract/patch/mkdir/sidecars/covers before I/O. |
| MIG-01 | Candidate tests accept only exact `roms/<fs_slug>` and `<fs_slug>/roms` forms.                                                             |
| MIG-02 | Pristine and seeded-0110 round trips pass on MariaDB, MySQL, and PostgreSQL.                                                               |
| MIG-03 | Missing, empty, unreadable, ambiguous, unsafe, and conflicting cases remain manual.                                                        |
| MIG-04 | Integration tests prove mapping, migration, and first-use state survives restarts.                                                         |
| MIG-05 | API tests prove no source fallback and observable result/status expiry.                                                                    |

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

- [x] `backend/tests/endpoints/roms/test_catalog_removal.py`
- [x] `backend/tests/handler/database/test_storage_lifecycle.py`
- [x] `backend/tests/handler/storage/test_legacy_migration.py`

## Plan Assignment and Executable Gates

- Plans 01 and 08 extend backend/tools/verify_storage_migrations.py and run pristine plus seeded-0110 upgrade/downgrade/re-upgrade in uniquely named disposable MariaDB, MySQL and PostgreSQL containers after verifying the runner bind mount is this checkout.
- Plan 03 owns the D-04 typed mapping-removal consequence and ordinary confirmation contract plus endpoint/OpenAPI tests.
- Plan 07 owns only productive first-use CAS consumer wiring. Plan 08 exclusively owns D-15/D-16 rollback eligibility, rollback mutation, restart persistence, endpoint/OpenAPI tests, and dialect verification.
- Plan 09 first creates RED unit expectations for the absent controlled-generation harness, then implements the harness, runs final characterization and the real three-dialect verifier, regenerates OpenAPI types, and typechecks the frontend.

## Revision 2 Wave Assignment

Wave 1: 01. Wave 2: 02 and 03. Wave 3: 04 (depends 01,03). Wave 4: 05. Wave 5: 06. Wave 6: 07. Wave 7: 08. Wave 8: 09. Same-wave plans have no file overlap.

## Final Execution Evidence

| Gate                                              | Result                        |
| ------------------------------------------------- | ----------------------------- |
| Controlled harness unit contract                  | 5 passed                      |
| Focused Phase 6 closure suite                     | 138 passed                    |
| Extended lifecycle and migration regression suite | 158 passed                    |
| MariaDB pristine and seeded-0110 round trips      | passed                        |
| MySQL pristine and seeded-0110 round trips        | passed                        |
| PostgreSQL pristine and seeded-0110 round trips   | passed                        |
| Disposable-dialect handler contract               | 47 passed where supported     |
| Controlled OpenAPI generation                     | passed on loopback port 39006 |
| Frontend TypeScript typecheck                     | passed                        |

The focused suite ran in the existing isolated development runner with
`pytest -p no:env`, complete explicit database/Redis/auth settings, and
`DB_HOST=romm-db-dev`. Writable and read-only fixture cases compare path, type,
mode, size, SHA-256, and symlink identity while deliberately excluding atime.

The long-running `romm-dev` service exposes separate backend and frontend bind
mounts rather than the plan's required exact checkout-to-`/app` bind. The real
generation and dialect gates therefore used the task-owned
`romm-phase06-runner-0609` container, bound from this verified checkout to
`/app` on the existing internal network. The harness used only loopback inside
that runner, recorded its exact Uvicorn PID, used a uniquely named Node volume,
and removed only task-owned process files and the volume.

No deployment, Team4s service, v1 route, Phase 7 UI, source mutation, published
port, host networking, or fallback authority was introduced.
