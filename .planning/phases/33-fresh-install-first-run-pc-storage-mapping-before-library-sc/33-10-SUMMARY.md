---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 10
subsystem: scan-catalog-lifecycle
tags: [scan, collection-folders, lifecycle, owned-media, scheduled-scan]
requires:
  - phase: 34
    provides: Durable mapped scan operations and checked publication
provides:
  - Explicit collection promotion and durable parent suppression
  - Shared manual and scheduled discovery of new direct child games
  - Atomic retirement, retained user state and exact reference-safe cleanup
affects: [phase-33-uat, scan, catalog-lifecycle]
requirements-completed: []
completed: 2026-10-19
---

# Phase 33 Plan 10: Explicit collection folders

**Explicit child selection now corrects a mistaken parent game safely and remembers the collection for future scans.**

## Delivered behavior

- The typed optional promotion intent binds the exact parent, mapping revision and selected direct child. Ordinary scoped scans remain nondestructive.
- Successful child publication, checkpoint, durable classification and parent retirement share the checked SQL transaction. Failed, cancelled, stale or unauthorized attempts cannot retire a parent.
- Catalog removal reuses the existing lifecycle. Parent saves, states and play history remain retained; non-null retirement audit permanently excludes that identity from logical-path and hash reconnect candidates.
- Shared exact-file cleanup preserves source, shared, replaced and unproven files. Durable bounded processing is reused by manual and existing scheduled cleanup.
- One inventory service suppresses explicitly classified parents and discovers new direct child games through normal and scheduled scans. Unclassified folders retain existing behavior.
- Shared sessions and owned-writer lock order avoid worker self-deadlock. Progress counts use the actual shared inventory.
- Frontend requests reuse the existing builder. Setup navigation uses existing 48px buttons. New production modules remain below 500 lines; existing Scan.vue shrank to 1,385 lines. No parallel scan, storage or cleanup implementation was introduced.

## Commits

| Commit | Result |
| --- | --- |
| 4d6253cc3 | Correct mapping-relative selected-child scanning and known nested paths |
| 8c37f41ce | Corrective plan and collection contract |
| 24f21f6a5, e1592ff8c | Strict promotion contract and schema regression/fix |
| 721a8680e, a3ddc0d61 | Shared inventory regression and atomic promotion |
| 179742da6, 38267b007 | Frontend intent regression and shared request builder |
| 43b61df97, 1d42da7fd | Exact cleanup regression and shared durable processor |
| b45f596d9, 3b79f91ef | Canonical delete permission on acceptance and replay |
| 2b856ef1d | Setup touch target correction |
| f4c4fd772, 9067cb5c0 | Real-worker lock/count regression and session fix |
| 06ade31db, aa7ed4cd8 | Prevent retired parent user state reconnecting to children |
| 10e07fd08 | Guarded actual browser/RQ harness and adversarial evidence validation |

## Verification

- Final browser run: f4dd7651eda049868d9483e52118cfcb, all 22 checks passed on exact final production manifest 3326a6533fc597e42198ddcff6b62a3276203540ba007dbe388fdfcfba9d0b9d. Actual HTTP/RQ initial, selected-child, full and registered scheduled scans completed with exact counts 3/1/4/6. The selected game retained two archive parts.
- Parent retirement/audit, exclusive owned-media removal, shared/source preservation, child preservation, later new children and no parent resurrection passed. All disposable resources and snapshots were removed; source manifests matched.
- Both themes, 320px/desktop layout, mouse, keyboard, touch and actual Next/Previous 48px bounds passed. Physical gamepad was unavailable and remains explicitly blocked.
- Frontend receipt frontend-pgdp34-64fa62f2f2a7456b9052eb312559621f: typecheck, 1,102 tests, build and maintainability passed.
- Backend collection suites: MariaDB 97 and PostgreSQL 45 cases; permission suites 45 each; cleanup regression 21 each. Final actual-worker/import/lock/count suite passed 8 cases each. Final retained-state and ordinary reconnect controls passed 9 cases each. Existing worker/checkpoint/fence 35, owned-domain/publication/cleanup 15 and atomic filesystem 2 passed.
- Fresh schema-final-mariadb, schema-final-mysql and schema-final-postgresql receipts prove upgrade, downgrade to 0138, re-upgrade and existing constraint/CRUD parity against exact final models/migration hashes. Historical earlier schema receipts are not used as final-source proof.
- Scoped Trunk and commit hooks passed. Historical legacy test failures and harness failures remain recorded; this summary does not claim the entire backend suite is green.

Evidence is retained under this phase's evidence directory. Read 33-UAT.md, 33-VALIDATION.md, the receipt index and individual per-run manifests for exact commands and limitations.

## Dev activation

The user approved autoscan every 15 minutes. Only pgdp-dev was recreated using the verified host-local override. Actual scheduled function tasks.scheduled.scan_library.scan_library_task.run is registered with cron */15 * * * *. Frontend and heartbeat returned HTTP 200; the new current worker was idle. Database/Redis containers, 33 catalog games, one user and auth identity were preserved. Games remains read-only. Sanitized proof: evidence/live-autoscan-15m/activation-receipt.json.

Schema 0140 was applied with a protected pre-migration SQL backup. No DB/media reset, source game modification, production deployment or push occurred. Existing unrelated dirty files remain untouched.

## Remaining acceptance

Plan 33-10 implementation and technical verification are complete. Plan 33-06 human acceptance of this corrected live flow remains pending; the earlier full-scan approval does not automatically approve the new correction. Physical gamepad UAT and the requested later independent deep review remain open. No subsequent phase was started.
