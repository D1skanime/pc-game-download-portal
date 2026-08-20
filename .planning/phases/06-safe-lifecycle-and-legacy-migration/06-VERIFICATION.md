---
phase: 06-safe-lifecycle-and-legacy-migration
verified: 2026-08-20T15:07:27Z
status: gaps_found
score: 23/31 must-haves verified
overrides_applied: 0
overrides: []
requirements: 6/9 satisfied, 1 satisfied_with_warning, 2 blocked
re_verification:
  previous_status: gaps_found
  previous_score: 25/28
  gaps_closed:
    - "Changed fs_name authorization now runs before unmatch, provider, database, cache, collection, resource, or filesystem effects."
    - "Rom and RomFile incarnation tokens are guarded across the supported instance, statement, executemany, and bulk mapping paths."
    - "All bounded legacy observation exits now persist and expose truthful lower-bound metadata."
    - "Owned create/replace now retry short and interrupted writes and reject zero progress."
  gaps_remaining:
    - "Legacy preview and migration reconnect catalog-only identities without proving each source file exists."
    - "Primary manual replacement is destructive before successful staged publication and concurrent uploads race."
    - "Screenshot upload performs owned filesystem and database effects without ROM/platform visibility enforcement."
    - "OwnedCreate publishes its final name before content is complete and durable."
    - "HEAD download preflight consumes direct rollback eligibility without productive content delivery."
    - "The active-v2 mutation inventory omits direct fetch, callable clients, and request(config) calls."
  regressions:
    - "Raw source-derived filenames are interpolated into Content-Disposition without safe encoding."
gaps:
  - truth: "Only source identities actually observed under the detected legacy mapping reconnect; missing catalog entries stay unreachable."
    status: failed
    reason: "Preview and migration derive reconnectability only from unique catalog paths and never intersect those paths with the bounded source observation."
    artifacts:
      - path: "backend/handler/database/legacy_migration_handler.py"
        issue: "_catalog_impact and _reconnectable_catalog_ids use catalog rows only."
      - path: "backend/handler/database/roms_handler.py"
        issue: "reconnect_legacy_catalog clears Rom and every child RomFile missing_from_fs flag for every unique catalog path."
    missing:
      - "Persist or privately bind the exact normalized source identities observed during detection."
      - "Compute preview and migration changes from the source/catalog intersection, including child RomFile identity."
      - "Add an integration regression with one present ROM, one absent unique ROM, and an absent sidecar."
  - truth: "Replacing a primary manual preserves the previous manual until one complete replacement is durably and atomically published."
    status: failed
    reason: "The backend deletes different-extension manuals before receiving the replacement and streams into the final name; the frontend concurrently submits every selected primary manual."
    artifacts:
      - path: "backend/endpoints/roms/manual.py"
        issue: "Lines 97-127 delete the prior extension and write directly to the public destination before request success."
      - path: "frontend/src/services/api/rom.ts"
        issue: "Lines 499-524 launch all manual uploads concurrently with Promise.allSettled."
    missing:
      - "Accept one primary manual per operation, stage and fsync a unique temporary file, atomically publish, commit path_manual, then remove the superseded file."
      - "Serialize or reject multiple/concurrent primary manual uploads and cover disconnect, retry, replacement, and concurrency."
  - truth: "ROM-scoped screenshot upload enforces hidden ROM and platform visibility before every owned filesystem or database effect."
    status: failed
    reason: "add_screenshot looks up the ROM but never calls assert_rom_visible before deriving the path, writing the file, scanning it, and creating/updating the row."
    artifacts:
      - path: "backend/endpoints/screenshots.py"
        issue: "Lines 53-123 perform upload effects without the visibility guard used by download at lines 149-151."
      - path: "backend/tests/endpoints/test_screenshots.py"
        issue: "Hidden download cases exist, but hidden-ROM and hidden-platform upload cases do not."
    missing:
      - "Call assert_rom_visible immediately after ROM lookup and before path derivation or writes."
      - "Add hidden-ROM/platform upload regressions asserting 404 masking, zero filesystem calls, and no row."
  - truth: "OwnedCreate either publishes complete durable content or leaves no final artifact, including across process failure."
    status: failed
    reason: "OwnedCreate creates the final name before writing and does not fsync the file or parent; process death can expose a partial final file."
    artifacts:
      - path: "backend/handler/filesystem/storage_access.py"
        issue: "Lines 422-446 write the public destination directly; Python exception cleanup cannot cover process death and close failure can bypass unlink."
    missing:
      - "Write and fsync a unique descriptor-relative temporary, close safely, atomically publish without replacement, and fsync the parent."
      - "Add subprocess-crash, close-error, and durability-path tests."
  - truth: "Only productive scan, hash, stream, play, or download use consumes direct migration rollback eligibility."
    status: failed
    reason: "GET and HEAD share DOWNLOAD preflight, which marks first use before the HEAD branch closes the descriptor without transferring content."
    artifacts:
      - path: "backend/endpoints/roms/files.py"
        issue: "preflight_mapped_download runs at line 226 before request.method HEAD is handled at lines 248-254."
      - path: "backend/handler/storage/read_context.py"
        issue: "DOWNLOAD maps unconditionally to the first-use marker in lines 45-51 and 125-129."
    missing:
      - "Provide a metadata-only HEAD path that validates and stats without marking first use."
      - "Test that HEAD preserves rollback eligibility while GET/productive delivery consumes it."
  - truth: "The live active-v2 mutation inventory discovers every supported HTTP transport form and fails closed on unresolved calls."
    status: failed
    reason: "extractRawCalls skips call expressions whose callee is not property/element access, so direct fetch and callable clients disappear; request(config) is also not decoded."
    artifacts:
      - path: "frontend/src/v2/sourceMutationInventory.test.ts"
        issue: "Lines 414-421 skip direct calls, and the extractor only treats method-named members as HTTP operations."
      - path: "frontend/src/services/api/play-session.ts"
        issue: "A reachable direct fetch POST at lines 31-40 proves the omission exists in production source."
    missing:
      - "Extract global fetch, callable Axios clients, and request(config), resolving or failing closed on method and route."
      - "Route negative fixtures through the production finalInventorySource path."
deferred: []
---

# Phase 6: Safe Lifecycle and Legacy Migration Verification Report

**Phase Goal:** Operators can remove catalog state and bridge existing layouts without restructuring or deleting source content.
**Verified:** 2026-08-20T15:07:27Z
**Status:** gaps_found
**Re-verification:** Yes, mandatory final gate after Plan 06-32 and code review
**Verified tree:** Linux `/home/d1sk/romm`, branch `codex/pc-module-analysis`, origin `https://github.com/rommapp/romm.git`, HEAD `895b872694bb52e38975c01938ddd10d8855880c`

## Goal Achievement

Catalog-only removal, source immutability, exact legacy path grammar, mapping persistence, portable schema migration, and the previously reported rename/token/lower-bound/short-write defects are implemented. The phase still fails the complete contract. Migration can falsely publish absent catalog rows as reachable, owned manual/create flows can lose or expose partial data, screenshot upload bypasses hidden-resource visibility, HEAD consumes rollback eligibility without productive use, and the advertised v2 mutation inventory silently omits live transport syntax.

### Roadmap Success Criteria

| #   | Roadmap truth                                                                                        | Status   | Evidence                                                                                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Catalog removal leaves every original source file and directory unchanged.                           | VERIFIED | IDs-only request, retained identity transfer, typed owned cleanup, source-manifest regressions, and the independent regression gate pass.                                         |
| 2   | Mapping removal retains indexed games/source; external-root mutations are absent and server-blocked. | VERIFIED | Atomic deactivation/reachability/audit flow and early server denials are wired. The semantic inventory proof remains incomplete, tracked separately below.                        |
| 3   | Supported layouts become roots and relative mappings without source restructuring.                   | VERIFIED | Detection constructs only `roms/{fs_slug}` and `{fs_slug}/roms`; migration writes owned DB/config state only. Its reachability result is incorrect for absent catalog identities. |
| 4   | Ambiguous layouts require explicit manual mapping; fallback is visible and time-bounded.             | VERIFIED | Both-candidate, unsafe, empty, overlap, expiry, lower-bound, and no-fallback paths remain substantive and tested.                                                                 |
| 5   | Mappings survive restart/deployment with portable and practically reversible migration behavior.     | FAILED   | Persistence and dialect portability pass, but a non-productive HEAD request permanently consumes direct rollback eligibility.                                                     |

**Roadmap score:** 4/5 success criteria verified

### Consolidated Must-Haves

| #   | Truth                                                                                      | Status   | Evidence                                                                                                |
| --- | ------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------- |
| 1   | Game removal preserves every original source file/directory.                               | VERIFIED | Catalog-only request and immutable source evidence remain wired.                                        |
| 2   | Mapping/catalog removal retains source and external mutation requests deny before effects. | VERIFIED | Historical late rename authorization gap is closed; current guards run before side effects.             |
| 3   | Supported layouts become roots/relative mappings without restructuring.                    | VERIFIED | Exact two-grammar detector and owned-only migration writes.                                             |
| 4   | Ambiguous layouts require manual mapping; fallback is visible/time-bounded.                | VERIFIED | Unsafe/incomplete outcomes are unselectable and expiring.                                               |
| 5   | Mappings persist with portable, practically reversible migration behavior.                 | FAILED   | HEAD incorrectly marks productive first use.                                                            |
| 6   | Detached saves/states/play sessions remain usable and reconnectable.                       | VERIFIED | Retained ownership and strong-identity scan reconnection are live.                                      |
| 7   | Remove from catalog accepts IDs only.                                                      | VERIFIED | Backend schema and frontend serializer accept `rom_ids` only.                                           |
| 8   | Cleanup targets only RomM-owned assets.                                                    | VERIFIED | Typed cleanup intents cannot address the external descriptor.                                           |
| 9   | Mapping removal reports retention and cancellation consequences.                           | VERIFIED | Protected route returns bounded consequence schema.                                                     |
| 10  | Confirmed mapping removal updates mapping/catalog/audit atomically.                        | VERIFIED | Ordered locks and one handler transaction remain wired.                                                 |
| 11  | Later scans reconnect one unique retained identity and retry safely.                       | VERIFIED | Durable add/update path invokes idempotent retained reconnection.                                       |
| 12  | Only an authorized administrator explicitly starts detection.                              | VERIFIED | Admin route/manual task only; no startup or scheduled trigger.                                          |
| 13  | Only two literal fs_slug grammars are observed within budgets.                             | VERIFIED | Descriptor LIST/STAT/HASH flow and truthful lower bounds remain wired.                                  |
| 14  | Impact preview reports truthful mapping, counts, problems, and owned effects.              | FAILED   | Reconnectable counts come from catalog uniqueness without source-existence intersection.                |
| 15  | Confirmation binds current source and exact catalog state.                                 | VERIFIED | Source/catalog fingerprints are recomputed under lifecycle locks.                                       |
| 16  | Active/equal/ancestor/descendant mappings block migration.                                 | VERIFIED | Ordered active-mapping conflict checks remain wired.                                                    |
| 17  | Mapping/reconnection/audit/change metadata commit atomically.                              | VERIFIED | One transaction commits the set, although CR-01 makes the chosen set wrong.                             |
| 18  | Injected migration failure leaves no partial database state.                               | VERIFIED | Flush seams and rollback tests remain substantive.                                                      |
| 19  | Missing or ambiguous catalog entries stay visible and unreachable.                         | FAILED   | Catalog-only uniqueness reconnects absent rows and all child files.                                     |
| 20  | Only productive consumers mark first use before source open.                               | FAILED   | HEAD uses DOWNLOAD preflight and consumes the marker.                                                   |
| 21  | First-use CAS is followed by exact revision revalidation.                                  | VERIFIED | Mapping ID/revision revalidation remains in shared read context.                                        |
| 22  | Concurrent productive first use creates one marker.                                        | VERIFIED | Stable lock/CAS implementation remains tested.                                                          |
| 23  | Admin rollback binds migration/platform/expected version.                                  | VERIFIED | Typed routes delegate to locked compare-and-set handler.                                                |
| 24  | Rollback restores only exact unchanged original entities.                                  | VERIFIED | Current token guards cover supported ORM bulk paths and exact lineage validation.                       |
| 25  | Used/stale/replayed/expired/cross-platform rollback fails safely.                          | VERIFIED | Handler checks and bounded typed errors remain wired.                                                   |
| 26  | Writable/read-only regressions preserve source manifests.                                  | VERIFIED | Current focused tests pass and no product change followed Plan 32 evidence.                             |
| 27  | Closed server/UI inventory discovers and classifies all external mutation calls.           | FAILED   | Direct fetch/callable/request(config) transports are silently omitted.                                  |
| 28  | Backend OpenAPI and generated frontend contracts are coherent.                             | VERIFIED | Screenshot remains live-ROM-owned; saves/states remain detachable; generated tree has no worktree diff. |
| 29  | Primary manual replacement is staged, serialized, and failure-atomic.                      | FAILED   | Prior manual is deleted before upload completes and frontend uploads concurrently.                      |
| 30  | Screenshot upload enforces ROM/platform visibility before effects.                         | FAILED   | Upload lacks `assert_rom_visible`; download has it.                                                     |
| 31  | OwnedCreate publishes complete durable content or no final artifact.                       | FAILED   | Final filename exists during write and no fsync/atomic publication protects process failure.            |

**Score:** 23/31 must-haves verified

## Required Artifacts

| Artifact                                                | Expected                                      | Status   | Details                                                                                                      |
| ------------------------------------------------------- | --------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| `backend/handler/database/catalog_lifecycle_handler.py` | Catalog detachment and retained identity      | VERIFIED | Substantive, called by removal and scan reconnection, real DB state flows.                                   |
| `backend/handler/database/storage_handler.py`           | Atomic mapping removal                        | VERIFIED | Substantive, endpoint-wired, ordered DB locks and audit data flow.                                           |
| `backend/handler/storage/legacy_migration.py`           | Exact bounded source observation              | VERIFIED | Descriptor-bound real observation, SHA-256 fingerprint, budgets, lower bounds.                               |
| `backend/handler/database/legacy_migration_handler.py`  | Preview/migrate/rollback orchestration        | FAILED   | Wired and substantive, but preview/reconnect selection does not consume observed source identities.          |
| `backend/handler/database/roms_handler.py`              | Catalog reconnection                          | FAILED   | Wired into migration, but clears reachability for catalog-only unique identities and all child files.        |
| `backend/endpoints/roms/manual.py`                      | Safe primary manual upload                    | FAILED   | Wired to resources storage and DB, but destructive ordering and public-name streaming are not atomic.        |
| `backend/endpoints/screenshots.py`                      | Authorized screenshot lifecycle               | FAILED   | Real file/DB flow exists, but upload omits hidden ROM/platform visibility guard.                             |
| `backend/handler/filesystem/storage_access.py`          | Owned create/replace capabilities             | FAILED   | Replace is staged; create writes the final name directly and lacks durability/atomic-publication guarantees. |
| `backend/endpoints/roms/files.py`                       | Mapped GET/HEAD delivery                      | FAILED   | Both methods use productive DOWNLOAD preflight; raw filename also enters Content-Disposition.                |
| `frontend/src/v2/sourceMutationInventory.test.ts`       | Fail-closed live v2 mutation inventory        | FAILED   | Substantive and executed, but direct/callable/config transports never reach classification.                  |
| `frontend/src/v2/sourceMutationControls.test.ts`        | Absence of active-v2 source mutation controls | VERIFIED | Current 10-test control gate passes.                                                                         |
| `backend/tools/verify_storage_migrations.py`            | Three-dialect migration authority             | VERIFIED | Substantive lifecycle/lineage verifier; Plan 32 evidence covers MariaDB, MySQL, PostgreSQL.                  |

## Key Link Verification

| From                       | To                        | Via                              | Status           | Details                                                                                  |
| -------------------------- | ------------------------- | -------------------------------- | ---------------- | ---------------------------------------------------------------------------------------- |
| Catalog removal endpoint   | catalog lifecycle handler | IDs-only protected call          | WIRED            | Retained ownership and owned cleanup response flow to API.                               |
| Mapping removal endpoint   | storage handler           | expected-version transaction     | WIRED            | Consequences, deactivation, reachability, cancellation, and audit are connected.         |
| Detection task             | legacy detector           | explicit admin/manual task       | WIRED            | Real descriptor observations persist bounded results.                                    |
| Migration handler          | source observation        | source fingerprint reobservation | PARTIAL          | Aggregate fingerprint is bound, but exact observed identities do not drive reconnection. |
| Migration handler          | ROM reconnection          | `reconnect_legacy_catalog`       | WIRED BUT WRONG  | Real DB updates flow, but catalog uniqueness substitutes for source existence.           |
| Manual upload UI           | manual endpoint           | concurrent POST calls            | WIRED BUT UNSAFE | Promise fan-out reaches direct final-file writes.                                        |
| Screenshot POST            | visibility boundary       | `assert_rom_visible`             | NOT WIRED        | Guard is imported but absent from upload path.                                           |
| HEAD download              | rollback first-use CAS    | DOWNLOAD read context            | WIRED BUT WRONG  | HEAD reaches CAS before method branch.                                                   |
| Active-v2 modules/services | semantic inventory        | AST extraction/classification    | PARTIAL          | Property/element method calls flow; direct/callable/config calls disappear.              |

## Data-Flow Trace (Level 4)

| Artifact          | Data variable                         | Source                            | Produces real data                         | Status                |
| ----------------- | ------------------------------------- | --------------------------------- | ------------------------------------------ | --------------------- |
| Legacy preview    | reconnectable/unmatched counts        | Live catalog query only           | Yes, but missing source intersection       | HOLLOW SOURCE BINDING |
| Legacy migration  | reconnected ROM/RomFile IDs           | Live locked catalog rows only     | Yes, but absent rows included              | FAILED                |
| Catalog removal   | retained identity and cleanup intents | Live locked ROM/asset rows        | Yes                                        | FLOWING               |
| Mapping removal   | reachability/version/audit            | Live locked mapping/catalog rows  | Yes                                        | FLOWING               |
| Manual upload     | final manual bytes/path               | Request stream to public filename | Yes, but destructive/non-atomic            | FAILED                |
| Screenshot upload | ROM/platform/user ownership           | Live ROM lookup and upload        | Yes, but visibility unchecked              | FAILED                |
| Download HEAD     | mapping first-use state               | Shared DOWNLOAD preflight         | Yes, but non-productive request mutates it | FAILED                |

## Review Reconciliation

| Finding                                                     | Verdict                                | Independent evidence                                                                                                                                        |
| ----------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CR-01 reconnect without source-existence proof              | CONFIRMED, BLOCKER                     | `roms_handler.py:2673-2697` and `legacy_migration_handler.py:350-378,408-419` use catalog identities only; no observed identity set is persisted or passed. |
| CR-02 failed/concurrent manual uploads destroy prior manual | CONFIRMED, BLOCKER                     | `manual.py:97-127` deletes prior extension and streams to final; `rom.ts:499-524` concurrently submits all files.                                           |
| CR-03 screenshot upload lacks visibility guard              | CONFIRMED, BLOCKER                     | `screenshots.py:53-123` has no guard before file/DB effects; download uses the guard at 149-151.                                                            |
| CR-04 OwnedCreate publishes partial final file              | CONFIRMED, BLOCKER                     | `storage_access.py:422-446` opens final with O_EXCL, writes, and closes without temp publication or fsync.                                                  |
| WR-01 HEAD consumes rollback eligibility                    | CONFIRMED, BLOCKER FOR PHASE MUST-HAVE | `files.py:225-254` calls DOWNLOAD preflight before HEAD branch; `read_context.py:45-51,125-129` marks first use.                                            |
| WR-02 inventory ignores direct/callable mutations           | CONFIRMED, BLOCKER FOR PHASE MUST-HAVE | `sourceMutationInventory.test.ts:414-421` skips direct calls; reachable `play-session.ts:31-40` contains direct POST fetch.                                 |
| WR-03 raw filename can break Content-Disposition            | CONFIRMED, WARNING                     | `files.py:241` interpolates the database filename without escaping or RFC 5987 encoding; no quote/control/Unicode tests were found.                         |

No finding is refuted. Product code is byte-identical to reviewed product HEAD `f7420c24e`; the only later code commit changes two tests.

## Behavioral Spot-Checks

| Behavior                           | Command                                                                                                      | Result                                                                    | Status                                 |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------- | -------------------------------------- |
| Prior Phase 1-5 regression         | 29 derived pytest modules, one isolated MariaDB DB/user/basetemp per module, `-p no:env -p no:cacheprovider` | 931 passed, 8 skipped, 0 failed                                           | PASS                                   |
| Review-adjacent backend regression | screenshots, legacy migration, storage access, manual, ROM file modules                                      | 114 passed, 7 skipped, 0 failed                                           | PASS, coverage gaps remain             |
| Active-v2 inventory/control tests  | `npm run test -- sourceMutationInventory.test.ts sourceMutationControls.test.ts`                             | 2 files, 26 tests passed                                                  | PASS, WR-02 is an extractor blind spot |
| Post-review behavior diff          | `git diff --name-status f7420c24e..895b87269`                                                                | Only `test_rom.py`, `test_heartbeat.py`, and review documentation changed | PASS, no product behavior change       |
| Final environment identity         | uname/git top-level/branch/origin/HEAD                                                                       | All exact expected values                                                 | PASS                                   |

The first attempt at the prior-phase gate intentionally disabled `pytest-env` but omitted its `ROMM_BASE_PATH=romm_test` value, causing fixture-path failures in module 12. After restoring that repository test setting explicitly, all 29 deterministic modules produced the required 939 outcomes. The failed attempt's exact DB/user/basetemp was removed before retry.

## Probe Execution

No `scripts/*/tests/probe-*.sh` files or Phase 6 declared probe paths exist. Step 7c is skipped; the checked-in Python verifiers are represented by the recorded Plan 32 evidence and source inspection, not claimed as newly executed probes.

## Requirements Coverage

| Requirement | Source plans                            | Status                 | Evidence                                                                                                                                             |
| ----------- | --------------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| CAT-01      | 02, 09, 11, 15-18, 22-26, 32            | SATISFIED              | API/UI distinguish catalog removal and contain no source-delete option.                                                                              |
| CAT-02      | 01-02, 09-10, 14-15, 19, 22, 31-32      | BLOCKED                | Catalog removal preserves source, but primary manual replacement and OwnedCreate violate the plan-expanded owned-state integrity contract.           |
| CAT-03      | 03, 06, 09, 15, 19, 23, 32              | SATISFIED              | Mapping removal retains indexed games/source and atomically changes owned state.                                                                     |
| CAT-04      | 02-03, 09, 11, 15-18, 24-29, 32         | SATISFIED WITH WARNING | Actual inspected v2 calls remain source-safe and server denials are live, but the required semantic inventory is not fail-closed for all transports. |
| MIG-01      | 04-06, 09, 12, 15, 20-21, 23, 32        | SATISFIED              | Exact layouts become owned roots/mappings without source mutation.                                                                                   |
| MIG-02      | 01, 08-09, 12-13, 15, 20-21, 23, 28, 32 | BLOCKED                | Dialect/schema portability passes, but non-productive HEAD consumes practical direct rollback.                                                       |
| MIG-03      | 04-06, 09, 12, 15, 20, 23, 30, 32       | SATISFIED              | Unsafe/ambiguous detection remains manual and unselectable; CR-01 is catalog reachability after safe layout detection.                               |
| MIG-04      | 01, 06-09, 12-13, 15, 20-21, 23, 28, 32 | SATISFIED              | Mapping and lifecycle state survive restart with portable durable schema.                                                                            |
| MIG-05      | 04-05, 08-09, 12, 15, 20, 23, 30, 32    | SATISFIED              | Compatibility state is explicit, expiring, bounded, and no fallback bypass was found.                                                                |

No Phase 6 requirement is orphaned from all plans. Later Phases 7-9 do not specifically own any reported defect, so no gap is deferred.

## Anti-Patterns Found

| File                              | Line | Pattern                  | Severity | Impact                                                                        |
| --------------------------------- | ---- | ------------------------ | -------- | ----------------------------------------------------------------------------- |
| `backend/models/rom.py`           | 82   | `HACK`                   | INFO     | Enum member `RomFileCategory.HACK`, not a debt marker.                        |
| Phase 6 reviewed code             | n/a  | TBD/FIXME/XXX            | NONE     | No unreferenced blocker debt marker found.                                    |
| `backend/endpoints/roms/files.py` | 241  | Raw header interpolation | WARNING  | Quote/control/Unicode filenames can produce invalid headers or 500 responses. |

## Confirmation-Bias Countercheck

- Partial requirement: CAT-04 behavior appears source-safe, but its claimed exhaustive inventory is not exhaustive.
- Misleading passing test: the 26-test frontend gate passes because the extractor silently omits direct `fetch`, including the live play-session POST.
- Uncovered error path: process termination during `OwnedCreate.create` cannot run Python cleanup and leaves the public final name partial.

## Human Verification Required

None. The blocking behaviors are deterministic in current source and do not require visual, realtime, or external-service judgment.

## Cleanup and Worktree Proof

- No deployment, restart, service mutation, branch operation, product edit, or test edit was performed.
- Every verifier-created `romm_test_p06fv_*` database and `p06fv_*` user is absent; application `SELECT 1` returns 1.
- No `/tmp/romm-p06fv-*` basetemp remains.
- The exact 28 baseline untracked paths remain unchanged.
- After this report, the only new tracked worktree difference is this `06-VERIFICATION.md` file.

## Gaps Summary

Six closure roots block the final gate: source-observed migration matching, atomic primary-manual replacement, screenshot visibility-before-effects, crash-safe OwnedCreate publication, productive-only rollback consumption, and exhaustive fail-closed v2 transport inventory. The raw Content-Disposition handling is a separate warning. All are current code defects; none is clearly assigned to a later milestone phase.

---

_Verified: 2026-08-20T15:07:27Z_
_Verifier: Codex (gsd-verifier)_
