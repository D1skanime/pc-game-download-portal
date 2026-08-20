---
phase: 06-safe-lifecycle-and-legacy-migration
verified: 2026-08-20T06:59:28Z
status: gaps_found
score: 25/28 must-haves verified
overrides_applied: 0
overrides: []
requirements: 7/9 requirements satisfied
re_verification:
  previous_status: gaps_found
  previous_score: 21/28
  gaps_closed:
    - "The active-v2 generic, sidecar, firmware, upload, setup, patch-persistence, and rename controls/services identified previously are removed."
    - "Retained identity reconnection now runs after every durable scan result and retries safely for an existing ROM."
    - "Seeded 0111/0112 migration lifecycle and aggregate HASH call/return budgets are repaired across the declared dialect verifier."
    - "Rollback now records and validates entity and parent incarnation lineage under deterministic locks."
    - "Screenshot response/generated contracts now require live ROM ownership while saves and states remain detachable."
  gaps_remaining:
    - "External rename authorization still occurs after an unmatch return path and after possible owned screenshot effects."
    - "Rollback incarnation tokens remain mutable through a supported bulk mapping update path."
  regressions:
    - "The final semantic v2 inventory silently omits element-access clients and dynamic/concatenated routes."
    - "Budget-limited legacy observations incorrectly advertise prefix counts as exact."
    - "Inherited owned create/replace capabilities can publish short writes."
gaps:
  - truth: "External-root mutation requests fail closed before database, RomM-owned resource, or filesystem effects, and the final v2 inventory enforces that contract."
    status: failed
    reason: "A changed fs_name combined with unmatch_metadata commits database/cache/collection effects without any RENAME authorization, and the semantic inventory silently drops dynamic client syntax."
    artifacts:
      - path: "backend/endpoints/roms/__init__.py"
        issue: "update_rom returns from the unmatch branch at lines 1539-1583, while changed-fs_name authorization is delayed until lines 1767-1773; screenshot downloads can also occur at lines 1730-1741 first."
      - path: "frontend/src/v2/sourceMutationInventory.test.ts"
        issue: "routeText accepts only literals/templates and extraction accepts only identifier property access, so element access, concatenated routes, variable routes, and namespace clients disappear instead of failing closed."
    missing:
      - "Sanitize/compare fs_name and authorize external RENAME immediately after ROM visibility, before every branch, provider, database, cache, or resource effect."
      - "Exercise changed fs_name with unmatch_metadata and provider screenshot URLs, asserting 403 and zero effects."
      - "Make unknown client syntax fail closed and route negative fixtures through the live extractor/inventory entry point."
  - truth: "Rollback lineage is bound to private immutable Rom and RomFile incarnation tokens."
    status: failed
    reason: "Instance updates and statement .values() updates are rejected, but Session.bulk_update_mappings rewrites incarnation_token and bypasses both installed listeners."
    artifacts:
      - path: "backend/models/rom.py"
        issue: "The mapper listener covers instance history and do_orm_execute inspects statement._values only; legacy bulk mappings do not traverse either invariant guard."
      - path: "backend/tests/handler/database/test_storage_lifecycle.py"
        issue: "The current test covers instance assignment and update(...).values(...), but no bulk mapping or database-boundary rewrite."
    missing:
      - "Reject every supported ORM bulk parameter/mapping update form, or enforce immutable incarnation tokens at the database boundary on all supported dialects."
      - "Add ORM executemany, bulk_update_mappings, restart, and dialect tests."
  - truth: "Budget-limited legacy detection summaries identify prefix counts as lower bounds."
    status: partial
    reason: "Entry, time, file-byte, aggregate-byte, and descriptor budget exits return lower_bound=False even though observation stopped early."
    artifacts:
      - path: "backend/handler/storage/legacy_migration.py"
        issue: "Budget exits at lines 151-169, 216-227, and 267-350 mark partial observations exact."
      - path: "backend/tests/handler/storage/test_legacy_migration.py"
        issue: "test_entry_budget_reports_observed_lower_bound explicitly asserts the incorrect false value."
    missing:
      - "Set lower_bound=true for every partial budget exit and cover each budget reason through persistence/API serialization."
  - truth: "RomM-owned create and replace operations either write complete content or leave no published partial artifact."
    status: partial
    reason: "OwnedCreate.create and OwnedReplace.replace each call os.write once and ignore its returned count. A fresh probe installed 2-byte outputs from a 6-byte payload; the code predates Phase 6 and does not mutate external source content, so it is a serious inherited data-integrity warning rather than a Phase 6 source-immutability blocker."
    artifacts:
      - path: "backend/handler/filesystem/storage_access.py"
        issue: "Single os.write calls at lines 422 and 467 can publish truncated created/replaced files; failed create also lacks destination cleanup."
    missing:
      - "Use a retrying write-all helper with zero-write and InterruptedError handling, unlink failed creates, and replace only after complete write plus fsync."
deferred: []
---

# Phase 6: Safe Lifecycle and Legacy Migration Verification Report

**Phase Goal:** Operators can remove catalog state and bridge existing layouts without restructuring or deleting source content.
**Verified:** 2026-08-20T06:59:28Z
**Status:** gaps_found
**Re-verification:** Yes, after all 26 plans and final review
**Verified tree:** Linux `/home/d1sk/romm`, branch `codex/pc-module-analysis`, origin `https://github.com/rommapp/romm.git`, HEAD `1da8069a4`

## Goal Achievement

The original four root gaps are materially closed in the live implementation: active-v2 mutation affordances are removed, retained reconnection is retry-safe, seeded predecessor migrations and HASH budgets are repaired, and rollback records exact lineage. The phase still fails its final contract because a crafted rename request can perform durable non-source side effects before the server denial, and the rollback identity claimed to be immutable is writable through a supported bulk mapping API. Source content remained unchanged in all inspected and executed paths, but task completion does not satisfy CAT-04 or the rollback-lineage must-have.

### Observable Truths

| #   | Truth                                                                                            | Status                | Evidence                                                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------ | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Game removal preserves every original source file/directory.                                     | VERIFIED              | IDs-only catalog request, retained identity transfer, typed owned cleanup intents, and existing immutable-manifest tests are wired.          |
| 2   | Mapping/catalog removal retains source and every external mutation request fails before effects. | FAILED                | UI/service removal is real, but `update_rom` authorizes changed `fs_name` only after an early unmatch return and possible screenshot writes. |
| 3   | Supported layouts become roots/relative mappings without content restructuring.                  | VERIFIED              | Detector constructs only `roms/{fs_slug}` and `{fs_slug}/roms`; migration writes DB/config/audit state only.                                 |
| 4   | Ambiguous layouts require manual mapping; fallback is visible/time-bounded.                      | VERIFIED              | Both-candidate, unsafe, empty, overlap, expiry, and no-fallback paths are substantive and wired. Budget prefix labelling remains a warning.  |
| 5   | Mappings persist with portable, practically reversible migration behavior.                       | VERIFIED              | 0111/0112/0113 upgrade, guarded downgrade, restart, and re-upgrade implementation exists for all three dialects.                             |
| 6   | Detached saves/states/play sessions remain usable and reconnectable.                             | VERIFIED              | Effective retained ownership is used by endpoints and one strong identity is rebound atomically.                                             |
| 7   | Remove from catalog accepts IDs only.                                                            | VERIFIED              | `CatalogRemovalRequest` and frontend `deleteRoms` serialize only `rom_ids`.                                                                  |
| 8   | Cleanup targets only RomM-owned assets.                                                          | VERIFIED              | Cleanup intents are typed to managed resources/screenshots; external descriptors are never accepted.                                         |
| 9   | Mapping removal reports retention and cancellation consequences.                                 | VERIFIED              | Protected storage route returns the bounded consequence schema.                                                                              |
| 10  | Confirmed mapping removal updates mapping/catalog/audit atomically.                              | VERIFIED              | Ordered row locks and one handler transaction update revision, reachability, cancellation, and audit.                                        |
| 11  | Later scans reconnect only one unique retained identity and retry after failure.                 | VERIFIED              | `scan.py:505-514` invokes reconnection for every durable add/update; retry and ambiguity tests pass.                                         |
| 12  | Only an authorized administrator explicitly starts detection.                                    | VERIFIED              | Protected admin route/manual task; no startup or scheduled trigger was found.                                                                |
| 13  | Only two literal fs_slug grammars are observed within byte/time/entry budgets.                   | VERIFIED              | Descriptor LIST/STAT/HASH path, remaining aggregate cap, and returned-byte rejection are wired; fresh race tests passed.                     |
| 14  | Impact preview reports proposed mapping, counts, problems, and owned effects.                    | VERIFIED WITH WARNING | Real locked DB data flows, but partial observations incorrectly expose `lower_bound=false`.                                                  |
| 15  | Confirmation binds current source and exact catalog state.                                       | VERIFIED              | Source/catalog fingerprints are recomputed under lifecycle locks before mutation.                                                            |
| 16  | Active/equal/ancestor/descendant mappings block migration.                                       | VERIFIED              | Ordered active-mapping conflict checks are present and tested.                                                                               |
| 17  | Mapping/reconnection/audit/change metadata commit atomically.                                    | VERIFIED              | One session transaction creates mapping, reconnects exact rows, audits, versions detection, and records rollback changes.                    |
| 18  | Injected migration failure leaves no partial state.                                              | VERIFIED              | Flush seams and transaction rollback tests cover mapping, catalog, audit, and rollback stages.                                               |
| 19  | Ambiguous catalog entries remain visible and unreachable.                                        | VERIFIED              | Only unique normalized logical identities reconnect.                                                                                         |
| 20  | Productive consumers mark first use before source open.                                          | VERIFIED              | Shared read context performs validation, CAS mark, revision revalidation, then descriptor open.                                              |
| 21  | First-use CAS is followed by exact revision revalidation.                                        | VERIFIED              | Mapping ID/revision are checked after durable first-use marking.                                                                             |
| 22  | Concurrent first use creates one durable marker.                                                 | VERIFIED              | Stable lock/CAS implementation and concurrency regression exist.                                                                             |
| 23  | Admin rollback binds migration/platform/expected version.                                        | VERIFIED              | Protected typed GET/POST routes delegate to locked compare-and-set handler.                                                                  |
| 24  | Rollback restores only exact unchanged original entities.                                        | FAILED                | Persisted entity/parent lineage validation is correct under locks, but its incarnation authority is mutable via `bulk_update_mappings`.      |
| 25  | Used/stale/replayed/expired/cross-platform rollback fails safely.                                | VERIFIED              | Handler checks and bounded typed errors are wired.                                                                                           |
| 26  | Writable/read-only phase regressions preserve source manifests.                                  | VERIFIED              | Existing 315-test evidence matches HEAD; targeted current-HEAD reruns passed.                                                                |
| 27  | Closed server/UI inventory denies external mutation before I/O.                                  | FAILED                | Rename preflight ordering is wrong and the semantic inventory silently omits dynamic syntax.                                                 |
| 28  | Backend OpenAPI and generated frontend contracts are coherent.                                   | VERIFIED              | Screenshot models require `rom_id`, omit retained ownership, and save/state models remain nullable/retained.                                 |

**Score:** 25/28 observable truths verified

All 90 PLAN-level truths were traced into these consolidated observable truths. The three failed consolidated truths correspond to the late rename guard, mutable rollback identity authority, and incomplete semantic inventory/pre-I/O gate.

## Required Artifacts

The 73 artifact declarations across Plans 01-26 exist and are substantive. GSD existence/substance checks passed all file artifacts; Plan 23's generated directory was inspected manually. Representative Level 3/4 results follow.

| Artifact                                                                 | Expected                                  | Status   | Details                                                                                                              |
| ------------------------------------------------------------------------ | ----------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------- |
| `backend/handler/database/catalog_lifecycle_handler.py`                  | Catalog removal and retained reconnection | VERIFIED | Locked strong-identity claim moves saves/states/sessions and versions the retained row in one transaction.           |
| `backend/endpoints/sockets/scan.py`                                      | Retry-safe production reconnection        | VERIFIED | Every durable add/update result invokes reconnect, including existing-ROM retry.                                     |
| `backend/handler/storage/legacy_migration.py`                            | Exact bounded detector/fingerprint        | PARTIAL  | HASH budget race is fixed; budget-exhaustion `lower_bound` metadata is wrong.                                        |
| `backend/alembic/versions/0112_phase6_gap_closure.py`                    | Seeded predecessor normalization          | VERIFIED | Selectable fingerprintless 0111 rows are invalidated before constraints and narrowly restored on safe downgrade.     |
| `backend/alembic/versions/0113_legacy_change_lineage.py`                 | Portable incarnation/lineage schema       | VERIFIED | Bounded token columns, backfill, indexes, lineage shape, predecessor invalidation, and guarded downgrade exist.      |
| `backend/handler/database/legacy_migration_handler.py`                   | Exact confirmation/rollback               | VERIFIED | Fresh fingerprints, exact change capture, deterministic locks, and entity/parent lineage comparison are substantive. |
| `backend/models/rom.py`                                                  | Immutable incarnation authority           | FAILED   | Insert freshness works; `bulk_update_mappings` changes the token.                                                    |
| `backend/endpoints/roms/__init__.py`                                     | Pre-effect source rename denial           | FAILED   | Authorization is below early DB-return and provider/resource paths.                                                  |
| `frontend/src/services/api/rom.ts` and active-v2 controls                | No external mutation authority            | VERIFIED | Forbidden source mutation exports/controls are absent; update serializer omits `fs_name`.                            |
| `frontend/src/v2/sourceMutationInventory.test.ts`                        | Fail-closed semantic inventory            | PARTIAL  | Live literal/property-access graph passes, but unclassifiable dynamic client syntax is dropped.                      |
| `backend/endpoints/responses/assets.py` plus generated screenshot models | Lifecycle-coherent contract               | VERIFIED | Screenshots require live ROM ID; save/state retain nullable live and retained ownership.                             |
| `backend/tools/verify_phase6_contracts.py`                               | Exact retry-safe cleanup                  | VERIFIED | Production `_unlink` uses `Path.unlink(missing_ok=True)` and Docker absence is explicitly classified.                |
| `backend/handler/filesystem/storage_access.py`                           | Typed owned capabilities                  | WARNING  | Authority boundary is correct, but create/replace single writes can publish truncation.                              |

## Key Link Verification

| From                  | To                                | Via                                             | Status                 | Details                                                                             |
| --------------------- | --------------------------------- | ----------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------- |
| Catalog removal route | Lifecycle handler                 | Protected IDs-only call                         | WIRED                  | Response follows committed handler outcome; source paths are not request authority. |
| Scan persistence      | Retained reconnect                | Unconditional post-persistence call             | WIRED                  | Existing-ROM retry closes the prior crash gap.                                      |
| Detector              | External descriptor HASH          | Remaining call cap and returned-byte validation | WIRED                  | Fresh race tests passed.                                                            |
| Confirmation          | Current source/catalog            | Locked reobservation plus exact fingerprints    | WIRED                  | Drift writes nothing.                                                               |
| Migration             | Mapping/catalog/audit/change rows | One DB transaction                              | WIRED                  | Real database state flows through one session.                                      |
| Rollback              | Recorded entity/parent lineage    | Deterministic row locks                         | PARTIAL                | Comparison is wired, but token immutability can be bypassed.                        |
| Active v2             | Shared services/backend routes    | Semantic inventory                              | PARTIAL                | Live known calls classify cleanly; unknown dynamic syntax is not fail-closed.       |
| Changed ROM filename  | External storage policy           | `StorageOperation.RENAME`                       | NOT WIRED EARLY ENOUGH | Guard runs after early and owned-resource effects.                                  |
| Backend schemas       | Generated frontend                | Controlled OpenAPI generation                   | WIRED                  | Live and generated screenshot/save/state ownership shapes agree.                    |

## Data-Flow Trace (Level 4)

| Artifact                      | Data                                                   | Source                                                       | Produces real data | Status                        |
| ----------------------------- | ------------------------------------------------------ | ------------------------------------------------------------ | ------------------ | ----------------------------- |
| Catalog removal               | ROM IDs, retained identity, cleanup intents            | Locked ORM rows                                              | Yes                | FLOWING                       |
| Retained reconnect            | Logical path/hash triple and retained assets           | Durable scanned ROM plus locked retained rows                | Yes                | FLOWING                       |
| Detection/preview             | Candidate entries, hashes, counts, problems            | Descriptor-only source observations plus locked catalog rows | Yes                | FLOWING WITH METADATA WARNING |
| Migration                     | Mapping, catalog reachability, audit, rollback changes | Fresh confirmation and locked DB state                       | Yes                | FLOWING                       |
| Rollback                      | Recorded row IDs/tokens/parents/prior state            | Persisted 0113 lineage and locked live rows                  | Yes                | FLOWING, AUTHORITY PARTIAL    |
| Screenshot generated contract | Pydantic OpenAPI schema                                | Backend response models                                      | Yes                | FLOWING                       |

## Review Finding Reconciliation

| Finding                             | Independent verdict                 | Exact evidence                                                                                                                                                                                                                                             | Phase severity                                              |
| ----------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| CR-01 late rename authorization     | CONFIRMED                           | Direct probe with changed `fs_name` plus `unmatch_metadata=true` returned normally, recorded `database,cache,collections`, and made zero rename authorization calls.                                                                                       | BLOCKER                                                     |
| CR-02 short owned writes            | CONFIRMED                           | Direct monkeypatch probe wrote 2 bytes from a 6-byte payload for both create and atomic replace. `git blame` places the affected lines in Phase 2 commit `b87109531`.                                                                                      | WARNING for this phase, critical owned-data defect globally |
| WR-01 exact label on budget prefix  | CONFIRMED                           | All partial budget exits pass `lower_bound=False`; the named test asserts false after observing only one of two entries.                                                                                                                                   | WARNING                                                     |
| WR-02 executemany token bypass      | CONFIRMED WITH MECHANISM CORRECTION | The exact `Session.execute(update(Model), [params])` example raises `TypeError` before SQL because `_values` is `None`, so that form does not mutate. `Session.bulk_update_mappings`, however, changed the token successfully and bypassed both listeners. | BLOCKER because a PLAN must-have says immutable             |
| WR-03 inventory drops dynamic calls | CONFIRMED                           | AST extraction supports only string/template routes, named imports, identifier receivers, and property access. The negative fixture calls `finalAuthority` directly and never tests extraction.                                                            | WARNING and CAT-04 gate gap                                 |
| WR-04 absent env file loops forever | REFUTED                             | Production `_unlink` is `path.unlink(missing_ok=True)`, so an absent environment file succeeds and clears ownership. The broad catch is not reached for production `FileNotFoundError`.                                                                    | No finding                                                  |

**Reconciliation totals:** 5 confirmed (one with corrected mechanism), 1 refuted, 0 resolved in the reviewed tree.

## Behavioral Spot-Checks

| Behavior                                                                      | Command/result                                                                                                   | Status                                       |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Active-v2 inventory/rendered controls                                         | `npm run test -- sourceMutationInventory sourceMutationControls`: 2 files, 20 tests passed in 3.68s              | PASS                                         |
| Rename, HASH race, cleanup retry, screenshot schema                           | Isolated task DB/user, `pytest -p no:env`: 10 passed in 1.78s                                                    | PASS, but rename test coverage is incomplete |
| Reconnect retry, instance/token guard, reparent rollback, seeded-0111 fixture | Same isolation: 4 passed, 141 deselected in 0.26s                                                                | PASS                                         |
| Changed filename plus unmatch branch                                          | Direct current-HEAD endpoint probe: normal return, durable DB/cache/collection effects, zero authorization calls | FAIL                                         |
| ORM incarnation immutability                                                  | ORM executemany raised TypeError before mutation; `bulk_update_mappings` changed token                           | FAIL                                         |
| Owned short-write handling                                                    | 6-byte content produced 2-byte created and replacement files                                                     | FAIL                                         |
| Cleanup absence semantics                                                     | Code-level production wrapper inspection: `Path.unlink(missing_ok=True)`                                         | PASS                                         |

The first backend setup attempt collected no tests because the normal application DB user correctly lacked authority to create the unique test database. A task-only database/user was then created explicitly, used with `-p no:env` and a test-only auth secret, and removed exactly. It is not counted as behavioral evidence.

## Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` file or Phase 06 probe declaration exists.

## Requirements Coverage

| Requirement | Description                                                                                        | Status                 | Evidence                                                                                                                          |
| ----------- | -------------------------------------------------------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| CAT-01      | Catalog removal is distinct from source deletion in API/UI.                                        | SATISFIED              | IDs-only request/client and catalog-only localized v2 confirmation.                                                               |
| CAT-02      | Catalog removal deletes only defined owned state/assets and preserves source.                      | SATISFIED              | Retained identity transfer, typed cleanup intents, immutable manifests.                                                           |
| CAT-03      | Mapping removal retains indexed games/source and changes owned state only.                         | SATISFIED              | Atomic deactivation/reachability/audit transaction.                                                                               |
| CAT-04      | External delete/rename/move/upload/extract/patch actions are absent in v2 and blocked server-side. | BLOCKED                | Live v2 affordances are absent, but changed filename denial is not pre-effect and the final inventory is not fail-closed.         |
| MIG-01      | Supported layouts become roots/mappings without content mutation.                                  | SATISFIED              | Exact two-grammar detector and DB/config-only migration.                                                                          |
| MIG-02      | Portable, practically reversible migration behavior.                                               | BLOCKED                | Dialect lifecycle passes, but rollback's declared immutable row-incarnation authority can be rewritten by supported bulk mapping. |
| MIG-03      | Unsafe layouts require explicit manual mapping.                                                    | SATISFIED WITH WARNING | Unsafe/incomplete results are unselectable and fallback-free; partial count metadata is mislabeled exact.                         |
| MIG-04      | Mappings and scanability survive restart/deployment.                                               | SATISFIED              | Durable mapping/revision/first-use/lineage schema and restart verifier.                                                           |
| MIG-05      | Compatibility state is explicit, expiring, and cannot bypass policy.                               | SATISFIED              | Detection results expire, are version-bound, unselectable on uncertainty, and have no source fallback consumer.                   |

**Requirements:** 7/9 satisfied, CAT-04 and MIG-02 blocked. No Phase 6 requirement is orphaned from all plans.

## Security, Privacy, and Resource Bounds

- Authorization remains route-scoped and backend authoritative. The confirmed rename defect is ordering, not missing authentication.
- External storage authority remains descriptor-bound and fail-closed for delete/upload/write/mkdir/move/copy/extract families. No live active-v2 forbidden literal call was found.
- Source observations use no-follow descriptor access, source/catalog fingerprints, symlink/path replacement rejection, and call/return HASH budgets.
- Public errors and inventory diagnostics expose stable operations/storage IDs/routes, not host paths, tokens, DB credentials, or file inventories.
- Phase-range high-signal diff sweep found only `example.invalid` and loopback `127.0.0.1` destinations, list-form `subprocess.run`, no new dependency/CI file, and no added executable/binary blob.
- No unreferenced TBD/FIXME/XXX marker exists in the reviewed Phase 06 set. `HACK` at `models/rom.py:81` is an enum value, not a debt marker.
- No human verification is needed to decide the current gaps.

## Cleanup and Repository Integrity

- Task database `romm_test_p06vf_0820`: absent after cleanup.
- Task DB user `p06vf_0820`: absent after cleanup.
- Task containers/volumes/temp directories: none remain.
- Normal application `SELECT 1`: returned 1 before and after cleanup.
- No service restart, deployment, branch/worktree operation, source mutation, or product/test edit occurred.
- Before this report, the only tracked diff was the submitted `06-REVIEW.md`; all 28 pre-existing untracked status entries were preserved.

## Human Verification Required

None. The blocking and warning behaviors are deterministic in code and were directly exercised where useful.

## Deferred Items

None. Later phases do not explicitly own these Phase 06 contract failures.

## Gaps Summary

The phase is not ready to pass. The blocking root concerns are the late external rename guard and mutable rollback-incarnation authority. The semantic inventory and lower-bound metadata need closure to make the advertised regression and bounded-result contracts truthful. The owned short-write defect is real but inherited from Phase 2 and does not grant or perform external source mutation, so it is recorded as a serious non-goal warning rather than used to inflate the Phase 06 blocker count. The cleanup finding is refuted by the production `missing_ok=True` wrapper.

---

_Verified: 2026-08-20T06:59:28Z_
_Verifier: Codex (gsd-verifier)_
