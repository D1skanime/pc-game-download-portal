---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
plan: "02"
subsystem: database
tags: [sqlalchemy, alembic, fastapi, rq, mariadb, mysql, postgresql]
requires:
  - phase: 34-01
    provides: Guarded disposable SQL/Redis runner
provides:
  - Portable durable scan intent, item results and seeded execution slot
  - Atomic acceptance, request replay and attempt/version fencing
  - Authenticated commands and durable lookup with existing RQ projection
affects: [34-03, 34-04, 34-07, 34-08, 34-11, 34-12]
tech-stack:
  added: []
  patterns: [singleton row locking, durable dispatch intent, microsecond leases]
key-files:
  created:
    - backend/models/scan_operation.py
    - backend/alembic/versions/0139_scan_operations.py
    - backend/handler/database/scan_operations_handler.py
    - backend/handler/scan_operation_state.py
    - backend/handler/scan_operation_commands.py
    - backend/handler/scan_operation_projection.py
    - backend/endpoints/scan_operations.py
    - backend/endpoints/responses/scan_operations.py
    - backend/tests/handler/test_scan_operations.py
    - backend/tests/handler/test_scan_operation_contracts.py
    - backend/tests/endpoints/test_scan_operations.py
    - backend/tools/phase34_operation_schema.py
    - backend/utils/alembic_mysql.py
    - frontend/src/__generated__/models/ScanOperationRequest.ts
    - frontend/src/__generated__/models/ScanOperationSnapshot.ts
    - frontend/src/__generated__/models/ScanOperationMutationRequest.ts
    - frontend/src/__generated__/models/ScanOperationItemResult.ts
  modified:
    - backend/tests/conftest.py
    - backend/main.py
    - backend/models/__init__.py
    - backend/alembic/env.py
    - backend/alembic/versions/0057_multi_notes.py
    - backend/alembic/versions/0134_rom_updated_at_fractional_seconds.py
    - backend/alembic/versions/0138_rom_metadata_facet_roles_view.py
    - backend/tools/phase34.py
    - backend/tools/phase34_fixtures.py
    - backend/tools/phase34.compose.yml
    - backend/tools/tests/test_phase34_runner.py
    - frontend/src/__generated__/index.ts
key-decisions:
  - Lock the seeded slot before actor/key replay and commit acceptance with dispatch intent.
  - Preserve microseconds explicitly across SQL dialects.
  - Keep resume recovering until source verification authorizes dispatch.
  - Reserve shared tracking and Phase 33 acceptance for the orchestrator.
requirements-completed: ["D-05","D-06","D-07","D-09","D-14","D-15","D-16","SCAN-01","SCAN-06","SAFE-06"]
duration: 42 min
completed: 2026-10-18
---

# Phase 34 Plan 02: Durable Scan Operations Summary

Portable SQL scan intent now supports serialized replay, fenced state/item mutations and authenticated reconciliation.

## Scope

Tasks: 3/3. This completes 34-02 only. The requirement list describes this plan's contribution, not completed worker, recovery, UI or browser acceptance.

Verified Linux via ssh team4s-linux, root /home/d1sk/pc-game-download-portal, branch codex/phase-32-pgdp-naming and origin https://github.com/D1skanime/pc-game-download-portal.git. Isolated Alembic heads/history confirmed sole head 0138_rom_metadata_facet_roles_view before creating 0139. Recorded test window: 21:07-21:49 UTC; context reads preceded it. Source changes: 29 files, 17 created.

No Windows project writes, branch switch, worktree, nested agent, live DB reset, live scan, app restart or deployment occurred. Real Games storage was never mounted by tests. Unrelated dirty files and directories were preserved. Repository backend/pre-PR guides informed transactions, auth, migration parity, type generation and scoped verification.

## Results

- Unique actor/key acceptance and digest conflicts serialize through one seeded slot. Acceptance and dispatch intent commit together before enqueue. Replays retain original identity and terminal state.
- Dispatch claims, leases, attempt/version CAS, item writes, cancellation confirmation and explicit resume are guarded. Cleanup detaches the slot, deletes children first and restores exactly one idle singleton.
- Authenticated submit/active/key/ID/cancel/resume/retry routes use existing scopes, ownership masking and CSRF middleware. Existing mapped commands/resolver preserve revisions, subfolders and provider policies. Invalid scopes never invoke the scanner.
- Durable lookup survives response loss, Redis outages and expired RQ jobs. Existing task projection reports actual RQ status. Four operation types and exports were generated from isolated OpenAPI.

## Commits

| Step | Commit |
| --- | --- |
| Task 1 RED | c941f11b1 |
| Historical portability | 285833fb7 |
| Actual schema probe/retention | 7b7768196 |
| Task 1 GREEN | cef2aba67 |
| Task 2 RED | 964ac99c6 |
| Task 2 GREEN | dbc6acd08 |
| Task 3 RED | e6c92d031 |
| Microsecond regression repair | d0851b51d |
| Evidence/ownership repair | 76edbac2a |
| Full container identity repair | 0e5f9d348 |
| Task 3 GREEN | 1a4e5047c |

Continuation history: 7e3a212c2 fixed the parity import root; 8218b23eb recorded the checkpoint; f2c97c461 renamed/tracked it. All source hooks ran without bypass. No tracked file deletion occurred. RED commits precede GREEN. Metadata is committed separately.

## Verification

- Exact schema command: python3 backend/tools/phase34.py schema --dialects mariadb,mysql,postgresql. Exit 0 before 0139 and after the final microsecond repair. Each dialect upgraded, downgraded to 0138 and re-upgraded.
- The separate operation probe verified real operation uniqueness, actor/item FKs, state/version checks, singleton enforcement, CRUD and cascade. Generic harness tables are not counted as operation proof.
- Exact named cleanup-pair command: exit 0, 2 passed consecutively in one disposable database, repeated after final changes.
- python3 backend/tools/phase34.py backend tests/handler/test_scan_operations.py -q: final exit 0, 12 passed.
- Combined contracts/repository/endpoints: 56 passed independently on MariaDB, MySQL and PostgreSQL after the precision fix. The additional actual-RQ case brought MariaDB's combined pytest result to 57 passed.
- python3 backend/tools/phase34.py backend tests/endpoints/test_scan_operations.py -q: final exit 0, 42 passed with successful teardown.
- python3 -m unittest discover -s backend/tools/tests -p 'test_phase34*.py' -q: final 22 passed.
- Isolated npm run generate: exit 0. All four retained operation model files match generator output byte-for-byte.
- Final scoped generated-contract tree, npm run typecheck: exit 2, only five known diagnostics in MatchRom/types.test.ts and Settings/pgdpFolderMappings.ts.
- Scoped Trunk formatting/checks, hooks and git diff --check passed. Generated files follow repository lint exclusions.

Real SQL connections and bounded barriers cover concurrent first acceptance, committed-before-enqueue visibility, replay/conflict, slot release, stale state/items, lease precision, dispatch/cancel and completion/cancel races. HTTP tests cover owner/admin/anonymous/viewer, real cookie-CSRF, retry bounds, lost responses, malformed identities, absolute/drive/UNC/traversal/symlink scopes, frozen policies and Redis outage versus expiry.

## Evidence

All paths below are Linux /tmp directories containing an evidence subdirectory with commands, JUnit where applicable, source manifests and cleanup receipts.

- Repaired baseline: pgdp34-fd58fafba4984082acb437a8792e8938-wkwpma1f (MariaDB), pgdp34-91fb6eb23a0e4bc4a1238a8882cb0d70-5m38reb8 (MySQL), pgdp34-23f6a9f4b8bb447a9d1934ad83e1b582-qj82m3sl (PostgreSQL).
- Final schema: pgdp34-0334d0f46e0a422fbf1a5ca3f93eb05a-j019n4um, pgdp34-21261acdbb424cfabeded0e7f42d1c4a-02ujygw7, pgdp34-73ebdc6ba3a74a9ebf4e56bebb4bd2c1-t0vwo__c, respectively.
- Behavioral matrix, 56 each: pgdp34-72acf157b7fa406b8b05d25f2d894e21-baiqi3kr, pgdp34-a99ecd94941d4f079c5325e1918145b8-e8nj1udi, pgdp34-d8edec25553e4498a4e3e0a035a591f9-c0n6991j, respectively.
- 57-passing JUnit: pgdp34-8f48112b8f634290b5aab426f0c2e123-732d0d3_. Its surrounding ad-hoc copy workflow failed on temporary ownership; only pytest is counted as passed there.
- Final successful endpoint command: pgdp34-6dc73bb2ab6a423686ebfb596ba88275-0w5bywby.
- Successful generation, final typecheck and generated-file cleanup: pgdp34-33c1c92ee4d64ab8b36dafca225621a9-lwzuz4xh.
- Final cleanup pair: pgdp34-9a87f45f70cd4736bceae494d6631fa2-o8xxds1h.
- Final repository suite: pgdp34-e41241cd3c5f446690360db42965f6ce-gh6zfdyn.

Disposable credentials are not reproduced. Failed infrastructure/copy workflows were not counted as passing workflows.

## Deviations from Plan

1. [Rule 3 - Blocking, explicitly authorized] Repaired historical MySQL conditional DDL/text defaults and PostgreSQL timestamp/view migrations. The isolated MySQL server received its existing trigger permission setting. Baseline and final matrices passed. Commit 285833fb7.
2. [Rule 1 - Bug] Real MySQL rounded timestamps to seconds, briefly placing dispatch_due in the future and changing replay snapshots. Portable microsecond variants plus a deterministic .777777 regression fixed dispatch, lease and audit precision. Commit d0851b51d.
3. [Rule 2 - Critical] Added safe scoped validation errors, ownership-before-resume validation and an intentional E402 exception for the pre-import guard. Verified by HTTP negatives and Trunk.
4. [Rule 3 - Blocking] Extracted coherent normalization/projection modules and generated operation types as repository API rules require. Repository size is 435 nonblank/noncomment lines.
5. [Rule 3 - Blocking] Container-owned generated outputs/evidence required exact full-ID ownership checks, atomic evidence redaction and confined snapshot cleanup. Host tests and final generation teardown pass. Commits 7b7768196, 76edbac2a and 0e5f9d348.

## Known Stubs and Deferred Issues

No goal-blocking stub was introduced. Empty items/statistics represent unexecuted work. Resume records recovering with a new fenced attempt and no dispatch permission until 34-04 verifies source identity.

Dispatcher/worker and catalog-commit fencing belong to 34-03; source recovery and metadata execution to 34-04. Frontend/production/Portainer/browser gates remain with their owning plans. Existing RQ/Vue RED defects were not changed.

Global TypeScript checking remains failed on five known diagnostics. Exploratory full regeneration also exposed two pre-existing rom-store/schema mismatches; unrelated generated outputs were not retained. Existing Alembic/SQLAlchemy warnings remain. See deferred-items.md. No authentication gate occurred.

## Handoff

Final receipts verify clean=true and source_unchanged=true. Inactive owned snapshots were removed while redacted evidence remained. Final inventory found zero Phase 34 containers, volumes or networks. Shared images and Team4s resources were preserved. Disk free: approximately 19 GB root, 46 GB Docker.

STATE, ROADMAP, REQUIREMENTS and Phase 33 acceptance were not edited or staged. The orchestrator owns progress updates. Report 34-02 as 3/3 tasks complete and schedule remaining Phase 34 plans; do not mark the phase or first-scan acceptance complete.


## Self-Check: PASSED

Verified all 17 created source files and this summary exist, all 14 referenced continuation/source commits resolve, committed shared tracking matches the pre-execution baseline, git diff --check passes and the final Phase 34 Docker label inventory is empty. Final receipts retain passing SQL assertions, clean teardown and unchanged source evidence.
