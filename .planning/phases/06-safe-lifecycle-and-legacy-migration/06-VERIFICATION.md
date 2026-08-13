---
phase: 06-safe-lifecycle-and-legacy-migration
verified: 2026-08-13T12:54:39Z
status: gaps_found
score: 21/28 must-haves verified
overrides_applied: 0
overrides: []
re_verification:
  previous_status: gaps_found
  previous_score: 21/28
  gaps_closed:
    - "Migration confirmation now reobserves the canonical source and binds exact source and catalog fingerprints."
  gaps_remaining:
    - "Retained user value is usable while detached, but production reconnection is not crash/retry safe."
    - "Active v2 still exposes a source-file deletion action outside the corrected catalog-removal dialog."
    - "Legacy migration portability, aggregate read bounding, and rollback lineage remain incomplete."
  regressions:
    - "The new STAT-to-HASH fingerprint path can exceed the aggregate byte budget after a file replacement race."
gaps:
  - truth: "External-root mutation actions are absent from the active v2 UI and remain server-blocked."
    status: failed
    reason: "The backend remains fail-closed and DeleteRomDialog is catalog-only, but active v2 FilesTab still calls the exported deleteRomFile client against the source-file deletion endpoint."
    artifacts:
      - path: "frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue"
        issue: "deleteSelectedFiles offers and invokes source-file deletion at lines 494-512."
      - path: "frontend/src/services/api/rom.ts"
        issue: "deleteRomFile remains exported at lines 805-813 and 930."
    missing:
      - "Remove the active-v2 ROM-file deletion controls and deleteRomFile service export, or replace the action with a catalog-only operation."
      - "Add an active-v2-wide regression test, not only a DeleteRomDialog test."
  - truth: "Catalog detachment preserves reliably reconnectable identity and later scans restore retained user value."
    status: partial
    reason: "Detached save/state APIs work, and the handler rebinds strong unique matches atomically, but scan commits the ROM before a separate newly-added-only reconnect. A crash or reconnect failure leaves assets detached, and retry skips reconnection because the ROM is no longer newly added."
    artifacts:
      - path: "backend/endpoints/sockets/scan.py"
        issue: "add_rom commits at line 500; reconnect runs separately only under newly_added at lines 502-510."
      - path: "backend/handler/database/catalog_lifecycle_handler.py"
        issue: "The reconnect transaction is internally atomic but is not durable with ROM creation or retried for an existing exact match."
    missing:
      - "Make ROM persistence and retained reconnection one transaction, or run an idempotent durable reconnect for both newly created and existing exact matches."
      - "Test failure after ROM insertion followed by scan retry."
  - truth: "Legacy migration is portable and every canonical observation remains within its configured budgets."
    status: failed
    reason: "Revision 0112 rejects valid selectable 0111 rows because it adds a NULL fingerprint and immediately requires non-NULL fingerprints for selectable rows. Separately, the detector checks aggregate budget against STAT but gives HASH the full per-file allowance and never rechecks bytes_read against the aggregate remainder."
    artifacts:
      - path: "backend/alembic/versions/0112_phase6_gap_closure.py"
        issue: "Lines 57-71 add the column and selectable constraint without backfill or portable invalidation."
      - path: "backend/handler/storage/legacy_migration.py"
        issue: "Lines 265-305 permit a STAT-to-HASH replacement race to exceed aggregate_byte_budget."
    missing:
      - "Portably invalidate or backfill pre-0112 selectable detections before creating the constraint, with seeded-0111 upgrade coverage on all supported dialects."
      - "Pass min(per-file budget, remaining aggregate allowance) to HASH and reject any returned byte count beyond the remaining aggregate budget."
      - "Add an inode/file replacement test between STAT and HASH."
  - truth: "Migration records sufficient exact lineage and rollback restores only the original affected entities."
    status: partial
    reason: "Rollback now restores only recorded row IDs and preserves unrelated/later rows, but each change record stores only entity kind, entity ID, and prior missing flag. For RomFile, the handler reads the current rom_id and compares the locked row to that same current value, so same-platform reparenting is not detected."
    artifacts:
      - path: "backend/models/storage.py"
        issue: "LegacyMigrationCatalogChange has no migration-time RomFile parent identity or bounded row identity/version."
      - path: "backend/handler/database/legacy_migration_handler.py"
        issue: "Lines 984-1037 derive and validate lineage from current state, making the parent comparison tautological."
    missing:
      - "Persist migration-time RomFile parent identity and any bounded identity/version needed to detect substitution."
      - "Validate persisted lineage under rollback locks and test same-platform reparenting and ROM substitution."
deferred: []
---

# Phase 6: Safe Lifecycle and Legacy Migration Verification Report

**Phase Goal:** Operators can remove catalog state and bridge existing layouts without restructuring or deleting source content.
**Verified:** 2026-08-13T12:54:39Z
**Status:** gaps_found
**Re-verification:** Yes, after Plans 06-10 through 06-17

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                           | Status   | Evidence                                                                                                                                        |
| --- | ----------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Game removal preserves every original source file/directory.                                    | VERIFIED | IDs-only removal, owned cleanup intents, manifest tests, and the independent catalog-removal spot test pass.                                    |
| 2   | Mapping/catalog removal retains source and external mutation actions are absent/server-blocked. | FAILED   | Server denial remains wired, but active v2 FilesTab invokes `deleteRomFile`.                                                                    |
| 3   | Supported layouts become roots/relative mappings without content restructuring.                 | VERIFIED | Detector constructs only the two literal grammars; migration writes DB/config state only.                                                       |
| 4   | Ambiguous layouts require manual mapping; fallback is observable/time-bounded.                  | VERIFIED | Both-candidate, unsafe, empty, conflict, and expiry paths are bounded and no source fallback consumer exists.                                   |
| 5   | Mappings persist with portable, practically reversible migration behavior.                      | FAILED   | 0112 cannot upgrade an 0111 database containing a valid selectable detection row.                                                               |
| 6   | Detachment preserves usable user value and reliably reconnectable identity.                     | FAILED   | Detached assets are usable, but production reconnection can be permanently skipped after a split-commit failure.                                |
| 7   | Remove from catalog accepts IDs only.                                                           | VERIFIED | Request schema and `deleteRoms` serialize only `rom_ids`.                                                                                       |
| 8   | Cleanup targets only RomM-owned assets.                                                         | VERIFIED | Typed resource/screenshot cleanup intents authorize owned storage only.                                                                         |
| 9   | Mapping-removal consequences report retention/cancellation.                                     | VERIFIED | Typed consequence response is wired through the protected storage route.                                                                        |
| 10  | Confirmed mapping removal updates mapping/catalog/audit atomically.                             | VERIFIED | Ordered locked transaction and failure-injection coverage remain present.                                                                       |
| 11  | Old work stops and later mapping/scan reconnects only unique identity.                          | FAILED   | Strong uniqueness is enforced, but scan retry cannot repair a failed post-insert reconnect.                                                     |
| 12  | Only an admin explicitly starts detection.                                                      | VERIFIED | Protected administrator POST/manual task; no startup or scheduled trigger found.                                                                |
| 13  | Only two literal fs_slug grammars are read within budgets.                                      | FAILED   | Grammar is exact, but STAT-to-HASH replacement can exceed the aggregate byte budget.                                                            |
| 14  | Impact preview reports mapping/counts/problems/owned effects.                                   | VERIFIED | Typed bounded response is populated from locked DB state.                                                                                       |
| 15  | Confirmation binds result and current source/catalog state.                                     | VERIFIED | Source SHA-256 and exact catalog fingerprint are recomputed under locks immediately before mutation; targeted drift tests passed.               |
| 16  | Active/overlapping mappings block migration.                                                    | VERIFIED | Equal, ancestor, descendant, active, and lifecycle conflict checks remain wired.                                                                |
| 17  | Mapping/reconnection/audit/sufficient rollback metadata commit atomically.                      | FAILED   | Transaction is atomic, but persisted change metadata omits migration-time RomFile lineage.                                                      |
| 18  | Injected migration failure leaves no partial state.                                             | VERIFIED | Flush-stage transaction tests and independent rollback-failure spot test pass.                                                                  |
| 19  | Ambiguous catalog entries remain visible/unreachable.                                           | VERIFIED | Only unique normalized identities reconnect; ambiguous rows stay missing.                                                                       |
| 20  | Productive consumers mark first use before source open.                                         | VERIFIED | Shared read context retains validate, mark, revalidate, open ordering.                                                                          |
| 21  | First-use CAS is followed by exact revision revalidation.                                       | VERIFIED | Mapping ID/revision are rechecked after durable marking.                                                                                        |
| 22  | Concurrent first-use creates one durable marker.                                                | VERIFIED | Barrier-backed lock/CAS tests remain present and recorded passing.                                                                              |
| 23  | Admin rollback API binds migration/platform/expected version.                                   | VERIFIED | Protected typed GET/POST routes delegate to locked handler checks.                                                                              |
| 24  | Unused rollback restores only exact prior owned state.                                          | FAILED   | Exact row set is restored, but current-parent-derived lineage does not protect against same-platform reparenting/substitution.                  |
| 25  | Used/stale/replayed/expired/cross-platform rollback fails safely.                               | VERIFIED | Bounded handler/API checks remain wired; targeted stale rollback passed.                                                                        |
| 26  | Phase regressions pass writable/read-only fixtures.                                             | VERIFIED | Recorded 291 focused tests and independent 49-test spot run pass; source-manifest assertions cover writable/read-only cases.                    |
| 27  | Closed server inventory denies external mutations before I/O.                                   | VERIFIED | Policy/inventory gates remain server-side and the route rejects source mutation.                                                                |
| 28  | Generated API contract and frontend typecheck pass.                                             | VERIFIED | Recorded controlled generation, typecheck, 632 frontend tests, locale gates, and build passed; screenshot schema overbreadth remains a warning. |

**Score:** 21/28 truths verified

### Required Artifacts

All artifacts declared by Plans 06-01 through 06-17 pass the GSD existence/substance check. Deeper status follows.

| Artifact                                                       | Expected                                | Status   | Details                                                                                                           |
| -------------------------------------------------------------- | --------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| `backend/handler/database/catalog_lifecycle_handler.py`        | Detached ownership and unique reconnect | PARTIAL  | Substantive and transactional, but production caller durability is incomplete.                                    |
| `backend/endpoints/saves.py`, `backend/endpoints/states.py`    | Detached asset lifecycle/auth           | VERIFIED | Live-or-retained platform resolution, 404 masking, owned content operations, and bounded live-ROM-only conflicts. |
| `backend/endpoints/sockets/scan.py`                            | Production reconnect consumer           | PARTIAL  | Wired only after a separately committed new-ROM insert and only for `newly_added`.                                |
| `frontend/src/v2/components/Dialogs/DeleteRomDialog.vue`       | Catalog-only removal                    | VERIFIED | Source-delete controls and language removed from this dialog.                                                     |
| `frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue` | Active v2 source-safe file actions      | FAILED   | Still exposes source deletion.                                                                                    |
| `backend/alembic/versions/0112_phase6_gap_closure.py`          | Portable fingerprint/change schema      | PARTIAL  | Head schema is substantive; upgrade of existing selectable 0111 rows is invalid.                                  |
| `backend/handler/storage/legacy_migration.py`                  | Complete bounded source fingerprint     | PARTIAL  | Content fingerprint works; aggregate budget race remains.                                                         |
| `backend/handler/database/legacy_migration_handler.py`         | Exact confirmation and rollback         | PARTIAL  | Confirmation is fixed; rollback lineage remains underbound.                                                       |
| `backend/tools/verify_phase6_contracts.py`                     | Controlled exact cleanup                | WARNING  | Normal and modeled cleanup pass, but a real cleanup failure permanently disables retry.                           |
| `backend/endpoints/responses/assets.py`                        | Accurate asset contract                 | WARNING  | Shared base advertises nullable/retained screenshot ownership that persistence cannot produce.                    |
| `06-VALIDATION.md`                                             | Current acceptance evidence             | STALE    | Says passed despite the directly observable blockers in this report.                                              |

### Key Link Verification

| From                   | To                         | Via                                    | Status           | Details                                                                             |
| ---------------------- | -------------------------- | -------------------------------------- | ---------------- | ----------------------------------------------------------------------------------- |
| ROM removal route      | catalog lifecycle handler  | IDs-only protected call                | WIRED            | Handler result drives bounded response; post-commit cache failures are best-effort. |
| Save/State routes      | retained platform identity | effective owner/platform authorization | WIRED            | Independent detached lifecycle tests passed.                                        |
| scan ROM insert        | retained reconnect         | post-insert handler call               | PARTIAL          | Call exists, but transaction/retry boundary is unsafe.                              |
| detector               | HASH capability            | LIST/STAT then descriptor hashing      | PARTIAL          | Real data flows, but remaining aggregate allowance is not enforced at HASH.         |
| migration confirmation | current source/catalog     | locked reobservation and fingerprints  | WIRED            | Same-metadata byte and canonical drift tests passed.                                |
| rollback               | catalog change rows        | recorded IDs and prior missing flags   | PARTIAL          | Exact row targeting works; recorded parent lineage does not exist.                  |
| DeleteRomDialog        | catalog removal API        | `deleteRoms`                           | WIRED            | Exact `rom_ids` body.                                                               |
| FilesTab               | source deletion API        | `deleteRomFile`                        | WIRED, FORBIDDEN | This working link violates CAT-04.                                                  |
| backend OpenAPI        | generated frontend         | controlled harness                     | WIRED            | Recorded harness exit 0 and typecheck pass.                                         |

The GSD key-link checker passed Plans 01-11 and 16-17. It reported symbolic `from` labels in Plans 12-15 as source files not found; manual code-level tracing above resolves those links and exposes the partial wiring.

### Data-Flow Trace (Level 4)

| Artifact                     | Data Variable                         | Source                                           | Produces Real Data                        | Status                |
| ---------------------------- | ------------------------------------- | ------------------------------------------------ | ----------------------------------------- | --------------------- |
| Detached save/state response | `rom_id`, `retained_catalog_id`       | committed retained identity and asset rows       | Yes                                       | FLOWING               |
| Retained reconnection        | new ROM ID plus logical/hash identity | scan insert then separate lifecycle transaction  | Sometimes                                 | PARTIAL, RETRY-HOLLOW |
| Legacy confirmation          | source/catalog fingerprints           | fresh descriptor observation plus locked DB rows | Yes                                       | FLOWING               |
| Legacy observation bytes     | `bytes_read`                          | HASH after STAT                                  | Yes, but potentially over aggregate limit | OVER-BUDGET RACE      |
| Rollback restoration         | catalog change rows                   | entity ID and prior missing flag                 | Incomplete lineage                        | HOLLOW LINEAGE        |
| v2 file deletion             | selected RomFile IDs                  | FilesTab selection to DELETE API                 | Yes                                       | FORBIDDEN FLOWING     |

### Behavioral Spot-Checks

| Behavior                                                            | Command/environment                                                                                                                           | Result                                                                    | Status |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ------ |
| Detached assets, drift rejection, exact rollback, harness contracts | Disposable MariaDB 11.4 + Redis 7 + immutable test runner; explicit DB/Redis/auth; read-only checkout; pytest `-p no:env -p no:cacheprovider` | 49 passed, 2 warnings, 6.36s                                              | PASS   |
| Artifact checks                                                     | GSD `verify artifacts` for Plans 01-17                                                                                                        | 17/17 plans all artifacts passed L1/L2                                    | PASS   |
| Active v2 source-delete absence                                     | Static production trace                                                                                                                       | `FilesTab.vue:511` calls `romApi.deleteRomFile`; service exports it       | FAIL   |
| Aggregate hash budget                                               | Static data-flow trace                                                                                                                        | HASH receives per-file max, no remaining aggregate cap or post-read check | FAIL   |
| Upgrade existing selectable 0111 row                                | Migration DDL trace                                                                                                                           | NULL column immediately conflicts with selectable/non-NULL constraint     | FAIL   |

Known completed gates are cross-reference evidence, not independent reruns: final focused backend 291 passed; controlled harness exit 0 and harness contract 26 passed; MariaDB/PostgreSQL 54 handler tests each plus MySQL round trips; frontend 632 tests, typecheck, build, and locale gates; prior-phase regression 699 passed and 7 skipped. The independent rerun for this report is the 49-test row above.

### Probe Execution

SKIPPED. No Phase 6 probe script was declared or found.

### Requirements Coverage

| Requirement | Source Plans         | Description                                               | Status    | Evidence                                                                              |
| ----------- | -------------------- | --------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------- |
| CAT-01      | 02, 09-11, 15-17     | Distinguish catalog removal from source deletion          | BLOCKED   | Catalog dialog/API are correct, but FilesTab still offers source deletion.            |
| CAT-02      | 01-02, 09-10, 14-15  | Preserve source and retained user value                   | BLOCKED   | Source preservation and detached APIs pass; reliable retryable reconnection does not. |
| CAT-03      | 03, 06, 09, 15       | Mapping removal changes owned state only                  | SATISFIED | Locked mapping/catalog/audit transaction retains source and catalog rows.             |
| CAT-04      | 02-03, 09, 11, 15-17 | No external mutation actions in v2; server blocked        | BLOCKED   | Server blocked, active v2 FilesTab action remains.                                    |
| MIG-01      | 04-06, 09, 12, 15    | Represent exact legacy layouts without restructuring      | SATISFIED | Two exact grammars and DB-only migration exist.                                       |
| MIG-02      | 01, 08-09, 12-13, 15 | Portable and practically reversible                       | BLOCKED   | Existing selectable 0111 upgrade fails; rollback lineage is insufficient.             |
| MIG-03      | 04-06, 09, 12, 15    | Manual mapping on unsafe/ambiguous/incomplete observation | BLOCKED   | STAT-to-HASH race can accept observation beyond aggregate budget.                     |
| MIG-04      | 01, 06-15            | Persistence and scanability across restart                | SATISFIED | Durable mapping/migration/first-use state and recorded dialect/restart evidence.      |
| MIG-05      | 04-05, 08-09, 12, 15 | Explicit observable time-bounded fallback                 | SATISFIED | Expiring status only; no legacy read authority or fallback consumer.                  |

All nine Phase 6 requirement IDs appear in plan frontmatter; none is orphaned.

### Final 06-REVIEW Finding Disposition

| Finding                                              | Disposition | Severity | Independent evidence                                                                                                                                            |
| ---------------------------------------------------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CR-01: 0112 rejects existing selectable 0111 rows    | CONFIRMED   | BLOCKER  | Added fingerprint is NULL; new check requires non-NULL when selectable, with no backfill/invalidation.                                                          |
| CR-02: STAT/HASH race bypasses aggregate limit       | CONFIRMED   | BLOCKER  | Aggregate check uses STAT size; HASH gets full per-file cap and returned bytes are not checked against remaining aggregate.                                     |
| CR-03: retained reconnect split commit               | CONFIRMED   | BLOCKER  | `add_rom` completes before separate `newly_added`-only reconnect.                                                                                               |
| CR-04: active v2 source deletion                     | CONFIRMED   | BLOCKER  | FilesTab action and service export are directly wired.                                                                                                          |
| CR-05: rollback lineage check tautological           | CONFIRMED   | BLOCKER  | Current `rom_id` is read into `file_lineage`, then compared to the same locked current value.                                                                   |
| WR-01: cleanup failure disables retry                | CONFIRMED   | WARNING  | `_cleaned=True` is assigned before Docker/volume/env removal; later calls return immediately.                                                                   |
| WR-02: screenshot contract impossible detached state | CONFIRMED   | WARNING  | `Screenshot` persistence has required ROM ownership and no retained column, while shared response/generated models advertise both nullable ROM and retained ID. |

Passing suites do not refute these findings because none exercises the missing seeded-0111 selectable upgrade, STAT-to-HASH replacement, post-insert reconnect retry, active-v2-wide source-action inventory, same-platform file reparenting, real cleanup-failure retry, or screenshot schema specialization.

### Anti-Patterns Found

| File                                                           | Line        | Pattern                                          | Severity | Impact                                                      |
| -------------------------------------------------------------- | ----------- | ------------------------------------------------ | -------- | ----------------------------------------------------------- |
| `frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue` | 494-512     | Forbidden destructive UI and API call            | BLOCKER  | Active v2 offers source deletion.                           |
| `backend/endpoints/sockets/scan.py`                            | 500-510     | Split durable transition                         | BLOCKER  | Crash/retry can strand retained user value.                 |
| `backend/alembic/versions/0112_phase6_gap_closure.py`          | 57-71       | Constraint added over incompatible existing rows | BLOCKER  | Upgrade failure on valid prior state.                       |
| `backend/handler/storage/legacy_migration.py`                  | 265-305     | TOCTOU budget enforcement                        | BLOCKER  | Aggregate observation limit can be exceeded.                |
| `backend/handler/database/legacy_migration_handler.py`         | 984-1037    | Current-state lineage compared with itself       | BLOCKER  | Rollback may modify a reparented entity.                    |
| `backend/tools/verify_phase6_contracts.py`                     | 486-515     | Completion flag set before cleanup               | WARNING  | Cleanup failure cannot be retried.                          |
| `backend/endpoints/responses/assets.py`                        | 11-35       | Overbroad shared response base                   | WARNING  | Generated screenshot contract advertises impossible states. |
| `06-VALIDATION.md`                                             | frontmatter | Stale `status: passed`                           | WARNING  | Planning evidence contradicts live code.                    |

No unreferenced TBD, FIXME, or XXX marker was found in the Phase 6 reviewed file set. Empty-return/placeholder grep hits were initial states, bounded empty results, tests, or locale key names, not user-visible stubs.

### Human Verification Required

None. The failed behaviors and remaining warnings are deterministically observable in code and targeted runtime tests. UI control presence does not require visual judgment.

### Deferred Items

None. Phases 7-9 do not specifically fix current v2 source deletion, reconnect durability, seeded-0111 upgrade compatibility, aggregate HASH bounding, or rollback lineage. These remain Phase 6 gaps.

### Planning Consistency

`06-VALIDATION.md` still claims `status: passed`. ROADMAP top/progress report 17/17 complete, while the Phase 6 detail block still says 9/17 and leaves Plans 10-17 unchecked. These tracking inconsistencies do not change the code verdict but should be corrected with the gap work.

### Gaps Summary

Four root concerns block the goal: active v2 still exposes source deletion; retained reconnection is not crash/retry safe; legacy migration is not fully portable or aggregate-bounded; and rollback lacks persisted migration-time lineage. The prior exact-confirmation gap is closed, and exact row targeting is materially improved, but task completion and passing suites do not make the remaining goal claims true.

### Resource Cleanup

The independent test run used uniquely named task-owned MariaDB, Redis, runner containers, and Docker networks. Both the intercepted first attempt and the valid 49-test rerun were checked afterward; no `romm-p06verify*` or `romm-p06spot*` container/network remains. No deployment, persistent service restart, product edit, database volume, or Node volume was created.

---

_Verified: 2026-08-13T12:54:39Z_
_Verifier: Codex (gsd-verifier)_
