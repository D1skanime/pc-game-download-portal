---
phase: 06-safe-lifecycle-and-legacy-migration
verified: 2026-08-13T01:43:17Z
status: gaps_found
score: 21/28 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Catalog detachment preserves saves, states, play sessions, and reconnectable identity."
    status: failed
    reason: "Save and State rows are detached with rom_id=NULL, but public schemas and API paths require a live Rom; no production path consumes RetainedCatalogIdentity for reconnection."
    artifacts:
      - path: "backend/handler/database/catalog_lifecycle_handler.py"
        issue: "Nulls active ownership."
      - path: "backend/endpoints/responses/assets.py"
        issue: "BaseAsset.rom_id is a required int."
      - path: "backend/handler/database/roms_handler.py"
        issue: "Reconnection searches only missing Rom rows."
    missing:
      - "Support detached asset lifecycle through retained ownership."
      - "Atomically rebind unique retained identities and their user value."
  - truth: "External-root mutation actions are absent from the v2 UI and remain server-blocked."
    status: failed
    reason: "Server denials pass, but active v2 still offers source-file deletion controls and filesystem-deletion language."
    artifacts:
      - path: "frontend/src/v2/components/Dialogs/DeleteRomDialog.vue"
        issue: "Per-game and select-all source-delete controls remain."
      - path: "frontend/src/services/api/rom.ts"
        issue: "Client throws only after the UI offers the action."
    missing:
      - "Remove external source mutation controls from v2."
      - "Present explicit Remove from catalog language and outcomes."
  - truth: "Confirmation binds migration to current source and exact catalog identities."
    status: failed
    reason: "Confirmation binds aggregate counts but no source or catalog-identity fingerprint; revalidation never reobserves source."
    artifacts:
      - path: "backend/handler/storage/legacy_migration.py"
        issue: "LegacyImpactConfirmation stores counts and versions only."
      - path: "backend/handler/database/legacy_migration_handler.py"
        issue: "Equal-count identity substitution and source drift can pass."
    missing:
      - "Bind and recompute bounded deterministic source and catalog fingerprints immediately before mutation."
  - truth: "Unused rollback restores only prior owned database/configuration state."
    status: failed
    reason: "Migration stores aggregate counts; rollback marks every platform Rom and RomFile missing, including unchanged or later-created rows."
    artifacts:
      - path: "backend/models/storage.py"
        issue: "No exact prior per-row reachability state."
      - path: "backend/handler/database/legacy_migration_handler.py"
        issue: "Lines 853-913 overwrite all platform catalog reachability."
    missing:
      - "Record exact affected rows and prior values transactionally, then restore only that validated set."
---

# Phase 6: Safe Lifecycle and Legacy Migration Verification Report

**Phase Goal:** Operators can remove catalog state and bridge existing layouts without restructuring or deleting source content.
**Verified:** 2026-08-13T01:43:17Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                  | Status   | Evidence                                                                                  |
| --- | -------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------- |
| 1   | Game removal preserves every original source file/directory.                           | VERIFIED | IDs-only route and writable/read-only manifest tests pass.                                |
| 2   | Mapping removal retains catalog/source and mutation actions are absent/server-blocked. | FAILED   | Retention and server denial pass; v2 source-delete controls remain.                       |
| 3   | Supported layouts become roots/relative mappings without content restructuring.        | VERIFIED | Exact two-grammar, DB-only migration.                                                     |
| 4   | Ambiguous layouts require manual mapping; fallback is observable/time-bounded.         | VERIFIED | Bounded manual states and 24-hour results; no read fallback found.                        |
| 5   | Mappings persist with portable, practically reversible migration.                      | FAILED   | Persistence/dialects pass; rollback is not exact.                                         |
| 6   | Detachment preserves usable user value and reconnectable identity.                     | FAILED   | Detached assets break current contracts; retained identity is orphaned from reconnection. |
| 7   | Remove from catalog accepts IDs only.                                                  | VERIFIED | OpenAPI body is rom_ids only.                                                             |
| 8   | Cleanup targets only RomM-owned assets.                                                | VERIFIED | Typed resource/screenshot intents only.                                                   |
| 9   | Mapping-removal consequences report retention/cancellation.                            | VERIFIED | Bounded consequences API is wired.                                                        |
| 10  | Confirmed mapping removal updates mapping/catalog/audit atomically.                    | VERIFIED | Locked transaction verified.                                                              |
| 11  | Old work stops and later mapping reconnects only unique identity.                      | FAILED   | Stale work stops; removed retained identities cannot reconnect.                           |
| 12  | Only an admin explicitly starts detection.                                             | VERIFIED | Protected POST/manual task only.                                                          |
| 13  | Only two literal fs_slug grammars are read within budgets.                             | VERIFIED | Exact constructors and LIST/STAT budgets.                                                 |
| 14  | Impact preview reports mapping/counts/problems/owned effects.                          | VERIFIED | Typed bounded response.                                                                   |
| 15  | Confirmation binds result and current source/catalog state.                            | FAILED   | No current source or exact identity fingerprint.                                          |
| 16  | Active/overlapping mappings block migration.                                           | VERIFIED | Equal/ancestor/descendant/active conflicts are manual.                                    |
| 17  | Mapping/reconnection/audit/sufficient rollback metadata commit atomically.             | FAILED   | Transaction atomic, rollback metadata insufficient.                                       |
| 18  | Injected migration failure leaves no partial state.                                    | VERIFIED | Flush-stage tests pass.                                                                   |
| 19  | Ambiguous catalog entries remain visible/unreachable.                                  | VERIFIED | Only unique normalized identities reconnect.                                              |
| 20  | Productive consumers mark first use before source open.                                | VERIFIED | Shared read boundary and consumer coverage.                                               |
| 21  | First-use CAS is followed by exact revision revalidation.                              | VERIFIED | validate, mark, validate, open.                                                           |
| 22  | Concurrent first-use creates one durable marker.                                       | VERIFIED | Barrier-backed tests pass.                                                                |
| 23  | Admin rollback API binds migration/platform/expected version.                          | VERIFIED | Protected typed GET/POST routes.                                                          |
| 24  | Unused rollback restores only exact prior owned state.                                 | FAILED   | Blanket missing=true update.                                                              |
| 25  | Used/stale/replayed/expired/cross-platform rollback fails safely.                      | VERIFIED | Endpoint/integration/dialect handler tests.                                               |
| 26  | Phase regressions pass writable/read-only fixtures.                                    | VERIFIED | Independent core run: 116 passed; storage API: 58 passed.                                 |
| 27  | Closed server inventory denies external mutations before I/O.                          | VERIFIED | Inventory/policy suites pass.                                                             |
| 28  | Generated API contract and frontend typecheck pass.                                    | VERIFIED | Independent vue-tsc exit 0.                                                               |

**Score:** 21/28 must-haves verified

### Required Artifacts

| Artifact                                                   | Status   | Details                                                  |
| ---------------------------------------------------------- | -------- | -------------------------------------------------------- |
| `backend/models/catalog_lifecycle.py`                      | PARTIAL  | Substantive; retained identity lacks reconnect consumer. |
| `backend/tools/verify_storage_migrations.py`               | VERIFIED | Independent three-dialect gate passed.                   |
| `backend/handler/database/catalog_lifecycle_handler.py`    | PARTIAL  | Source-safe detach creates API-incompatible asset state. |
| `backend/tests/endpoints/roms/test_catalog_removal.py`     | PARTIAL  | Checks retained rows, not later asset use/reconnect.     |
| `backend/handler/database/storage_handler.py`              | VERIFIED | Mapping lifecycle is locked/versioned/audited.           |
| `backend/tests/handler/database/test_storage_lifecycle.py` | PARTIAL  | Missing-ROM reconnection only.                           |
| `backend/handler/storage/legacy_migration.py`              | PARTIAL  | Detector works; confirmation is underbound.              |
| `backend/handler/database/legacy_migration_handler.py`     | PARTIAL  | Wired/atomic; stale confirmation and rollback defects.   |
| `backend/tests/handler/storage/test_legacy_migration.py`   | PARTIAL  | Count-changing drift only.                               |
| `backend/tests/integration/test_legacy_migration.py`       | PARTIAL  | Does not assert exact prior catalog restoration.         |
| `backend/endpoints/storage.py`                             | VERIFIED | Protected typed APIs are wired.                          |
| `06-VALIDATION.md`                                         | STALE    | Claims passed despite observable gaps.                   |

SDK checks found all 18 declared artifacts present/substantive and all 10 declared key links pattern-wired. The table records deeper behavioral status.

### Key Link Verification

| From             | To                 | Status  | Details                                   |
| ---------------- | ------------------ | ------- | ----------------------------------------- |
| assets           | retained lifecycle | PARTIAL | Detach wired; rebind absent.              |
| ROM endpoint     | lifecycle handler  | WIRED   | IDs-only call and bounded result.         |
| storage endpoint | storage handler    | WIRED   | Consequence-confirmed removal.            |
| detector task    | exact detector     | WIRED   | Explicit job reloads authority.           |
| storage endpoint | migration handler  | PARTIAL | Calls wired; data contracts insufficient. |
| read context     | first-use handler  | WIRED   | Pre-open mark/revalidate.                 |
| dialect verifier | Alembic 0111       | WIRED   | MariaDB/MySQL/PostgreSQL passed.          |
| contract harness | generated frontend | WIRED   | Current typecheck passed.                 |

### Data-Flow Trace (Level 4)

| Artifact                 | Source                            | Status           |
| ------------------------ | --------------------------------- | ---------------- |
| Catalog removal response | committed detach transaction      | FLOWING          |
| Mapping consequences     | locked DB count                   | FLOWING          |
| Detection result         | bounded LIST/STAT and durable row | FLOWING          |
| Impact confirmation      | aggregate DB counts/detection row | HOLLOW FOR DRIFT |
| Rollback restoration     | no exact prior-state source       | DISCONNECTED     |
| Detached asset access    | retained row unused by API        | DISCONNECTED     |
| Retained reconnection    | no consumer                       | DISCONNECTED     |

### Behavioral Spot-Checks

| Behavior                                 | Result                                                | Status |
| ---------------------------------------- | ----------------------------------------------------- | ------ |
| Core lifecycle/integration/policy pytest | 116 passed                                            | PASS   |
| Storage endpoint pytest                  | 58 passed                                             | PASS   |
| Detached `BaseAsset` with `rom_id=None`  | Pydantic int_type error                               | FAIL   |
| Three-dialect verifier                   | all dialects passed; 47 handler tests where supported | PASS   |
| Frontend typecheck                       | vue-tsc exit 0                                        | PASS   |

Passing tests omit the failed behaviors: catalog tests stop after checking nullable rows, rollback tests do not seed mixed prior state, and drift tests change counts.

### Probe Execution

SKIPPED. No Phase 6 probe paths were declared or found.

### Requirements Coverage

| Requirement | Status    | Evidence                                                                            |
| ----------- | --------- | ----------------------------------------------------------------------------------- |
| CAT-01      | BLOCKED   | Backend IDs-only; v2 still offers source deletion and database/filesystem language. |
| CAT-02      | BLOCKED   | Source/rows persist, but retained assets and reconnection are not functional.       |
| CAT-03      | SATISFIED | Mapping removal retains catalog/source and changes owned state only.                |
| CAT-04      | BLOCKED   | Server closed; forbidden action remains in active v2 UI.                            |
| MIG-01      | SATISFIED | Exact mappings, no source mutation.                                                 |
| MIG-02      | BLOCKED   | DDL portable, practical rollback incorrect.                                         |
| MIG-03      | SATISFIED | Unsafe/ambiguous/custom/conflict cases are manual.                                  |
| MIG-04      | SATISFIED | Restart persistence and dialect gate pass.                                          |
| MIG-05      | SATISFIED | Explicit expiring status, no fallback authority.                                    |

No Phase 6 requirements are orphaned from plan frontmatter.

### Anti-Patterns Found

| File                                                     | Line | Severity | Impact                                                |
| -------------------------------------------------------- | ---- | -------- | ----------------------------------------------------- |
| `backend/endpoints/responses/assets.py`                  | 15   | BLOCKER  | Nullable detached ownership violates response schema. |
| `backend/handler/database/roms_handler.py`               | 2695 | BLOCKER  | Retained identities never reconnect.                  |
| `backend/handler/database/legacy_migration_handler.py`   | 343  | BLOCKER  | Aggregate-only confirmation.                          |
| same                                                     | 901  | BLOCKER  | Blanket rollback reachability overwrite.              |
| `frontend/src/v2/components/Dialogs/DeleteRomDialog.vue` | 227  | BLOCKER  | Forbidden source-delete UI remains.                   |
| `backend/endpoints/roms/__init__.py`                     | 2074 | WARNING  | Cache failure can return 500 after commit.            |
| `backend/handler/storage/read_context.py`                | 118  | WARNING  | Some resolution errors escape bounded contract.       |
| `backend/tools/verify_phase6_contracts.py`               | 275  | WARNING  | Invalid PID-file path can leak owned Uvicorn process. |

No unreferenced TBD, FIXME, or XXX marker was found in Phase 6 product files.

### Human Verification Required

None. Failures are directly observable in code/runtime.

### Deferred Item Review

None deferred. Phases 7-9 do not specifically implement retained-identity rebind, detached asset APIs, exact rollback state, drift fingerprints, or removal of this v2 game-delete action.

### Planning Consistency

The roadmap top checkbox/progress table say Phase 6 is complete at 9/9, but the Phase 6 detail block and `roadmap get-phase 6` still say 0/9 with all plans unchecked. SDK phase-completeness independently finds 9 plans and 9 summaries. This does not alter the code verdict, but can misroute workflow tracking.

### Gaps Summary

Four root concerns block the goal: retained user value is unusable/unreconnectable; v2 still advertises forbidden source mutation; migration confirmation accepts stale/equal-count changes; rollback cannot restore exact prior state.

---

_Verified: 2026-08-13T01:43:17Z_
_Verifier: Codex (gsd-verifier)_
