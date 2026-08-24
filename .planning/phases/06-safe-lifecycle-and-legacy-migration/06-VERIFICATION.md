---
phase: 06-safe-lifecycle-and-legacy-migration
verified: 2026-08-24T08:57:58Z
status: gaps_found
score: 28/31 must-haves verified
overrides_applied: 0
overrides: []
requirements: 8/9 satisfied, 1 blocked
re_verification:
  previous_status: gaps_found
  previous_score: 23/31
  gaps_closed:
    - "OwnedCreate now stages, fsyncs, and atomically publishes complete content instead of writing the public final name directly."
    - "Mapped HEAD now uses metadata-only STAT and preserves direct rollback eligibility."
    - "The active-v2 mutation inventory now covers direct fetch, callable Axios clients, request(config), aliases, and wrappers."
    - "Screenshot upload now applies ROM and platform visibility before owned effects."
  gaps_remaining:
    - "Legacy migration source evidence still cannot select folder or multi-file ROM parents."
    - "Primary manual upload is failure-atomic in isolation, but uploaded manuals are not discoverable or deletable and redownload bypasses the same CAS boundary."
    - "Screenshot update and delete still bypass hidden-ROM and hidden-platform visibility."
  regressions: []
gaps:
  - truth: "Impact preview and migration reconnect every unique supported catalog identity actually observed in the source, including folder and multi-file ROMs."
    status: failed
    reason: "Detection persists membership digests only for regular files, while catalog selection requires the parent ROM's own path/name digest before selecting the ROM or any child. A directory-backed ROM can therefore never qualify."
    artifacts:
      - path: "backend/handler/storage/legacy_migration.py"
        issue: "Directory records contribute to the aggregate fingerprint, but only regular files enter identity_digests."
      - path: "backend/handler/database/legacy_migration_handler.py"
        issue: "_select_catalog requires the ROM digest in the persisted regular-file digest set before considering its RomFiles."
      - path: "backend/tests/integration/test_legacy_migration.py"
        issue: "No migration regression covers a folder or multi-file ROM with present and absent children."
    missing:
      - "Persist typed directory and regular-file identity evidence, or derive a proven exact folder boundary from observed children."
      - "Select a folder ROM from exact directory evidence and each child only from independent file evidence."
      - "Add preview, migration, restart, and rollback regressions for nested folder and multi-file ROMs."
  - truth: "Primary manual replacement remains discoverable, deletable, failure-atomic, and serialized across upload and redownload."
    status: failed
    reason: "Upload publishes a random token path, but discovery and deletion recognize only fixed {rom.id}.pdf/.md names. Redownload writes a fixed name and updates path_manual unconditionally, outside the upload CAS, while the v2 pending state excludes redownload."
    artifacts:
      - path: "backend/endpoints/roms/manual.py"
        issue: "Upload uses a random path and CAS, delete delegates to fixed-name discovery, and redownload bypasses CAS with an unconditional update."
      - path: "backend/handler/filesystem/resources_handler.py"
        issue: "manual_exists and _get_manual_path inspect only fixed ROM-ID filenames rather than the validated path_manual authority."
      - path: "frontend/src/v2/components/GameDetails/ManualSubtab.vue"
        issue: "manualMutationPending excludes redownloadingManual, so replace remains independently startable during redownload."
      - path: "backend/tests/endpoints/roms/test_manual.py"
        issue: "The three endpoint tests cover upload concurrency but not upload-delete, restart discovery, redownload failure, or upload/redownload races."
    missing:
      - "Make validated rom.path_manual authoritative for primary manual discovery and deletion, with bounded legacy fixed-name compatibility if required."
      - "Route redownload through the same staged publication, expected-path CAS, prior-path preservation, and loser cleanup contract as upload."
      - "Include redownload in frontend pending state and add both race orderings plus failure, restart, and orphan checks."
  - truth: "Every screenshot mutation masks hidden ROM and platform targets before owned filesystem or database effects."
    status: failed
    reason: "Upload and download enforce assert_rom_visible, but update and delete accept an owner screenshot ID and mutate public state or delete the owned file and row without checking the screenshot's ROM or platform visibility."
    artifacts:
      - path: "backend/endpoints/screenshots.py"
        issue: "PUT /{id} and DELETE /{id} have owner checks but no assert_rom_visible before database or filesystem effects."
      - path: "backend/tests/endpoints/test_screenshots.py"
        issue: "Hidden target coverage exists for upload and download only, not update or delete."
    missing:
      - "Apply assert_rom_visible with static Screenshot not found masking before update and delete effects."
      - "Add hidden-ROM and hidden-platform update/delete tests proving identical 404 responses and zero filesystem/database mutation."
deferred: []
---

# Phase 6: Safe Lifecycle and Legacy Migration Verification Report

**Phase Goal:** Operators can remove catalog state and bridge existing layouts without restructuring or deleting source content.
**Verified:** 2026-08-24T08:57:58Z
**Status:** gaps_found
**Re-verification:** Yes, after Plans 06-33 through 06-47 and the final Phase 06 code review
**Verified tree:** Linux `/home/d1sk/romm`, branch `codex/pc-module-analysis`, origin `https://github.com/rommapp/romm.git`, HEAD `2d5e19b2f92b28f2eea72a7d742ab6ed806d2d18`

## Goal Achievement

Phase 06 has strong, fresh regression evidence and closes four of the six previously reported implementation gaps. That evidence does not prove the full goal. Static data-flow inspection shows that ordinary folder and multi-file ROMs cannot reconnect through the new private source evidence, primary manuals uploaded through the new safe endpoint cannot be managed through the existing discovery/deletion API and can race redownload, and hidden screenshot targets remain mutable through update and delete.

### Roadmap Success Criteria

| #   | Roadmap truth                                                                                                      | Status   | Evidence                                                                                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Catalog removal leaves every original source file and directory unchanged.                                         | VERIFIED | IDs-only removal, typed owned cleanup, retained identity transfer, and the digest-bound source manifest show no source mutation.                                                                  |
| 2   | Mapping removal retains indexed games and source; external-root mutation actions remain absent and server-blocked. | VERIFIED | Mapping lifecycle retains catalog rows, server denials remain wired, and the repaired semantic inventory covers supported HTTP transport forms.                                                   |
| 3   | Supported layouts become roots and relative mappings without restructuring source content.                         | FAILED   | Mapping creation is source-safe, but directory-backed and multi-file catalog identities cannot be selected from file-only membership evidence, so common supported layouts are not fully bridged. |
| 4   | Ambiguous layouts require explicit manual mapping; fallback is visible and time-bounded.                           | VERIFIED | Detection remains bounded, expiring, unselectable for unsafe or ambiguous outcomes, and has no silent fallback path.                                                                              |
| 5   | Mappings survive restart and deployment with portable, practically reversible migration behavior.                  | VERIFIED | 0114 lifecycle authority is recorded across MariaDB, MySQL, and PostgreSQL; HEAD no longer consumes rollback eligibility.                                                                         |

**Roadmap score:** 4/5 success criteria verified

### Consolidated Must-Haves

| #   | Truth                                                                             | Status                | Evidence                                                                                                                               |
| --- | --------------------------------------------------------------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Game removal preserves every source file and directory.                           | VERIFIED              | Catalog request carries IDs only; source manifests remain identical.                                                                   |
| 2   | Mapping and catalog removal retain source and deny external mutation.             | VERIFIED              | Lifecycle handlers and repaired inventory remain wired.                                                                                |
| 3   | Supported layouts map without source restructuring.                               | VERIFIED              | Detection and mapping writes use owned state only; full bridge behavior is separately failed at item 14.                               |
| 4   | Ambiguous layouts remain manual and time-bounded.                                 | VERIFIED              | Unsafe, incomplete, overlap, and expiry paths remain unselectable.                                                                     |
| 5   | Mapping persistence and rollback are portable and practical.                      | VERIFIED              | Three-dialect 0114 evidence and metadata-only HEAD behavior are present.                                                               |
| 6   | Detached saves, states, and play sessions remain usable and reconnectable.        | VERIFIED              | Retained ownership and exact scan reconnection remain live.                                                                            |
| 7   | Remove from catalog accepts IDs only.                                             | VERIFIED              | Backend and generated frontend request expose `rom_ids` only.                                                                          |
| 8   | Cleanup targets only RomM-owned assets.                                           | VERIFIED              | Typed cleanup intents and owned descriptors remain in use.                                                                             |
| 9   | Mapping removal reports retention and cancellation consequences.                  | VERIFIED              | Bounded consequence response remains endpoint-wired.                                                                                   |
| 10  | Confirmed mapping removal updates mapping, catalog, and audit atomically.         | VERIFIED              | Ordered transaction and optimistic confirmation remain substantive.                                                                    |
| 11  | Later scans reconnect one unique retained identity and retry safely.              | VERIFIED              | Durable idempotent scan reconnection remains wired.                                                                                    |
| 12  | Only an authorized administrator starts detection.                                | VERIFIED              | Admin endpoint and manual task remain the only triggers.                                                                               |
| 13  | Only two literal fs_slug grammars are observed within budgets.                    | VERIFIED              | Bounded descriptor LIST, STAT, and HASH flow remains exact.                                                                            |
| 14  | Impact preview is truthful and source-bound for supported identities.             | FAILED                | File-only digest persistence prevents folder ROM parents from qualifying despite observed contents.                                    |
| 15  | Confirmation binds current source and exact catalog state.                        | VERIFIED              | Source fingerprint, identity tuple, and catalog fingerprint are revalidated under locks.                                               |
| 16  | Active and overlapping mappings block migration.                                  | VERIFIED              | Equal, ancestor, descendant, and active conflicts remain guarded.                                                                      |
| 17  | Mapping, reconnection, audit, and change metadata commit atomically.              | VERIFIED              | One locked migration transaction remains wired.                                                                                        |
| 18  | Injected migration failure leaves no partial database state.                      | VERIFIED              | Failure seams and rollback coverage remain present.                                                                                    |
| 19  | Missing or ambiguous catalog entries remain visible and unreachable.              | VERIFIED              | Selection remains exact and does not falsely reconnect absent rows.                                                                    |
| 20  | Only productive consumers mark first use.                                         | VERIFIED              | HEAD uses STAT; GET retains DOWNLOAD first-use.                                                                                        |
| 21  | First-use CAS is followed by revision revalidation.                               | VERIFIED              | Shared mapped-read context retains the ordering.                                                                                       |
| 22  | Concurrent productive first use creates one marker.                               | VERIFIED              | Lock and CAS implementation remains substantive.                                                                                       |
| 23  | Admin rollback binds migration, platform, and expected version.                   | VERIFIED              | Typed routes delegate to locked compare-and-set handling.                                                                              |
| 24  | Rollback restores only exact unchanged original entities.                         | VERIFIED              | Change lineage and immutable incarnation tokens remain enforced.                                                                       |
| 25  | Used, stale, replayed, expired, and cross-platform rollback fails safely.         | VERIFIED              | Bounded handler checks remain wired.                                                                                                   |
| 26  | Writable and read-only regressions preserve source manifests.                     | VERIFIED              | Bound record reports 2,746 identical before and after entries.                                                                         |
| 27  | Closed server and v2 inventory discovers supported external mutation calls.       | VERIFIED              | Fetch, callable clients, request configs, aliases, wrappers, and live keepalive are handled.                                           |
| 28  | Backend OpenAPI and generated frontend contracts are coherent.                    | VERIFIED              | Bound record reports 257 identical generated files and parser verification passes.                                                     |
| 29  | Primary manual replacement is manageable, staged, serialized, and failure-atomic. | FAILED                | Upload is staged and CAS-protected, but discovery/delete miss random paths and redownload bypasses CAS and pending serialization.      |
| 30  | Screenshot lifecycle enforces ROM and platform visibility before effects.         | FAILED                | Upload/download are guarded; update/delete are not.                                                                                    |
| 31  | OwnedCreate publishes complete durable content or no acknowledged final artifact. | VERIFIED WITH WARNING | Staging, file fsync, no-replace publication, and parent fsync are present; close-error retry can close an unrelated reused descriptor. |

**Score:** 28/31 must-haves verified

## Required Artifacts

| Artifact                                                | Expected                                 | Status                    | Details                                                                                           |
| ------------------------------------------------------- | ---------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------- |
| `backend/handler/database/catalog_lifecycle_handler.py` | Catalog detachment and retained identity | VERIFIED                  | Substantive, endpoint-wired, and backed by real database state.                                   |
| `backend/handler/database/storage_handler.py`           | Atomic mapping removal                   | VERIFIED                  | Consequence confirmation, revision invalidation, catalog retention, and audit remain wired.       |
| `backend/handler/storage/legacy_migration.py`           | Exact bounded source observation         | PARTIAL                   | Observation is substantive, but membership evidence records regular files only.                   |
| `backend/handler/database/legacy_migration_handler.py`  | Source-bound preview and migration       | FAILED                    | Folder ROM selection requires a digest that detection never persists.                             |
| `backend/endpoints/roms/manual.py`                      | Safe primary manual lifecycle            | FAILED                    | Upload is staged and CAS-protected; deletion discovery and redownload use incompatible authority. |
| `backend/handler/filesystem/resources_handler.py`       | Primary manual discovery and deletion    | FAILED                    | Fixed ID filenames conflict with tokenized upload paths.                                          |
| `backend/endpoints/screenshots.py`                      | Visibility-safe screenshot lifecycle     | FAILED                    | PUT and DELETE lack visibility guards.                                                            |
| `backend/handler/filesystem/storage_access.py`          | Durable owned create and replace         | VERIFIED WITH WARNING     | Publication contract is substantive; descriptor close retry is unsafe after close errors.         |
| `backend/endpoints/roms/files.py`                       | Productive GET and metadata-only HEAD    | VERIFIED                  | HEAD uses STAT and safe Content-Disposition handling; GET retains first-use.                      |
| `frontend/src/v2/sourceMutationInventory.test.ts`       | Fail-closed live mutation inventory      | VERIFIED                  | Supported direct, callable, config, alias, and wrapper forms are included.                        |
| `backend/tools/verify_storage_migrations.py`            | Three-dialect lifecycle authority        | VERIFIED                  | Acceptance record binds successful MariaDB, MySQL, and PostgreSQL stages.                         |
| `backend/tools/verify_phase6_acceptance.py`             | Deterministic complete acceptance record | VERIFIED AS EVIDENCE TOOL | The evidence-only verifier passes, but its selected tests do not cover the three current gaps.    |

## Key Link Verification

| From                     | To                           | Via                                | Status    | Details                                                                                 |
| ------------------------ | ---------------------------- | ---------------------------------- | --------- | --------------------------------------------------------------------------------------- |
| Catalog removal endpoint | catalog lifecycle handler    | IDs-only protected route           | WIRED     | Retained ownership and owned cleanup flow to real DB state.                             |
| Mapping removal endpoint | storage handler              | expected-version transaction       | WIRED     | Consequences, deactivation, reachability, cancellation, and audit are connected.        |
| Legacy detector          | private identity rows        | persisted digest tuple             | PARTIAL   | Regular files flow; directory identity does not.                                        |
| Migration handler        | ROM and RomFile reconnection | explicit locked ID sets            | PARTIAL   | Flat identities flow correctly; folder parent gating makes nested children unreachable. |
| Manual upload            | primary manual handler       | staged file plus expected-path CAS | WIRED     | Safe for upload versus upload.                                                          |
| Manual deletion          | uploaded token path          | fixed-name discovery               | NOT WIRED | The uploaded path cannot be found by manual_exists.                                     |
| Manual redownload        | upload CAS boundary          | common staged replacement handler  | NOT WIRED | Redownload uses fixed-name download and unconditional path update.                      |
| Screenshot update/delete | ROM visibility boundary      | assert_rom_visible                 | NOT WIRED | Owner check is present, object visibility check is absent.                              |
| HEAD download            | rollback first-use state     | STAT capability                    | WIRED     | Metadata-only requests no longer mark first use.                                        |
| Active-v2 services       | semantic inventory           | AST extraction and classification  | WIRED     | Previously omitted transport forms now reach classification.                            |

## Data-Flow Trace (Level 4)

| Artifact                  | Data variable                   | Source                                                        | Produces real data                   | Status                 |
| ------------------------- | ------------------------------- | ------------------------------------------------------------- | ------------------------------------ | ---------------------- |
| Legacy preview            | reconnectable ROM IDs/counts    | locked catalog rows intersected with persisted source digests | Real but file-only                   | FAILED FOR FOLDER ROMS |
| Legacy migration          | reconnected ROM and RomFile IDs | explicit selection from the same digest set                   | Real but parent-gated                | FAILED FOR FOLDER ROMS |
| Primary manual upload     | path_manual                     | random owned path plus CAS                                    | Yes                                  | FLOWING                |
| Primary manual delete     | existence and removal path      | fixed `{rom.id}` filename search                              | No for uploaded token paths          | DISCONNECTED           |
| Primary manual redownload | path_manual                     | fixed-name download plus unconditional update                 | Yes, outside CAS                     | UNSAFE                 |
| Screenshot PUT/DELETE     | screenshot ROM visibility       | owner screenshot lookup only                                  | Visibility data exists but is unused | DISCONNECTED GUARD     |

## Review Reconciliation

| Finding                                                    | Verdict            | Independent evidence                                                                                                                                                 |
| ---------------------------------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CR-01 file-only evidence breaks folder and multi-file ROMs | CONFIRMED, BLOCKER | `legacy_migration.py:279-348` persists membership only for regular files; `_select_catalog` at `legacy_migration_handler.py:467-496` requires the parent ROM digest. |
| CR-02 uploaded manuals cannot be found or deleted          | CONFIRMED, BLOCKER | Upload uses a random path at `manual.py:115-119`; `resources_handler.py:499-510,581-600` recognizes fixed ID names only.                                             |
| CR-03 redownload bypasses CAS and races upload             | CONFIRMED, BLOCKER | `manual.py:200-207` downloads and updates unconditionally; `ManualSubtab.vue:108-114,186-190` excludes redownload from the common pending state.                     |
| CR-04 hidden screenshot update/delete remain mutable       | CONFIRMED, BLOCKER | `screenshots.py:178-226` has owner checks but no visibility guard before PUT or DELETE effects.                                                                      |
| WR-01 close-error retry can close a reused descriptor      | CONFIRMED, WARNING | `_close_descriptor` and `abort` retry the same descriptor number at `storage_access.py:447-469`; no reuse-sentinel regression was found.                             |

## Behavioral Spot-Checks

| Behavior                       | Command                                                                               | Result                                                                  | Status |
| ------------------------------ | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------ |
| Acceptance evidence integrity  | `python3 backend/tools/verify_phase6_acceptance.py --verify-evidence ...`             | `[PASS] evidence digest, validation binding, and exact source coverage` | PASS   |
| Product drift after acceptance | `git diff --name-status 02d1a5093..HEAD`                                              | Only `06-REVIEW.md` changed                                             | PASS   |
| Folder identity flow           | Static line trace through detector and `_select_catalog`                              | Directory fingerprint exists, directory membership digest does not      | FAIL   |
| Primary manual lifecycle       | Static line trace through upload, discovery, delete, redownload, and UI pending state | Incompatible path authority and missing serialization                   | FAIL   |
| Screenshot visibility          | Static line trace through POST, GET, PUT, and DELETE                                  | POST/GET guarded; PUT/DELETE unguarded                                  | FAIL   |

No service, deployment, restart, complete acceptance run, database mutation, or destructive test was performed during this verification.

## Probe Execution

No conventional or Phase 06 declared `probe-*.sh` path exists. Probe execution is skipped.

## Requirements Coverage

| Requirement | Source plans                                               | Status    | Evidence                                                                                                               |
| ----------- | ---------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------- |
| CAT-01      | 02, 11, 16-17, 38-41, 45, 47                               | SATISFIED | Catalog-only request and locale/UI language remain explicit.                                                           |
| CAT-02      | 01-02, 10, 14-15, 19, 22, 31, 33-34, 43, 47                | SATISFIED | Catalog removal itself preserves source and retained user value; current manual gaps are separate expanded must-haves. |
| CAT-03      | 03, 09, 15, 19, 23, 32, 47                                 | SATISFIED | Mapping removal retains indexed games and source atomically.                                                           |
| CAT-04      | 02-03, 09, 11, 15, 18, 24-29, 32, 34, 36, 47               | SATISFIED | Active-v2 external mutation controls are absent or classified and server denials remain wired.                         |
| MIG-01      | 04-06, 09, 12, 15, 20-21, 23, 32, 37, 42, 44, 47           | BLOCKED   | Folder and multi-file catalog identities are not bridged by file-only source membership evidence.                      |
| MIG-02      | 01, 08-09, 12-13, 15, 20-21, 23, 28, 32, 35, 42, 44, 46-47 | SATISFIED | Three-dialect lifecycle evidence is bound and HEAD preserves practical rollback.                                       |
| MIG-03      | 04-06, 09, 12, 15, 20, 23, 30, 32, 37, 44, 47              | SATISFIED | Unsafe and ambiguous detection remains manual and unselectable.                                                        |
| MIG-04      | 01, 06-09, 12-13, 15, 20-21, 23, 28, 32, 42, 44, 46-47     | SATISFIED | Mapping and private evidence persist across restart and supported dialects.                                            |
| MIG-05      | 04-05, 08-09, 12, 15, 20, 23, 30, 32, 37, 42, 44, 46-47    | SATISFIED | Compatibility remains explicit, expiring, bounded, and without fallback authority.                                     |

No Phase 06 requirement is orphaned from all plans. Phases 7 through 9 do not specifically own any current gap, so no item is deferred.

## Anti-Patterns Found

| File                                           | Line    | Pattern                            | Severity | Impact                                                                                              |
| ---------------------------------------------- | ------- | ---------------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| Phase 06 reviewed files                        | n/a     | Unreferenced TBD/FIXME/XXX         | NONE     | No blocker debt marker found.                                                                       |
| `backend/handler/filesystem/storage_access.py` | 447-469 | Retry `os.close` after close error | WARNING  | Descriptor reuse can make cleanup close an unrelated file or socket.                                |
| Phase 06 tests/locales                         | various | Placeholder/HACK text matches      | INFO     | Test RED messages, enum/category names, and UI placeholder vocabulary are not implementation stubs. |

## Confirmation-Bias Countercheck

- Partial requirement: MIG-01 safely creates mappings but does not reconnect directory-backed ROMs.
- Misleading passing test: the 403-test Phase 06 acceptance stage includes only three manual endpoint tests and no folder-ROM migration, uploaded-manual deletion, redownload race, or hidden screenshot PUT/DELETE case.
- Uncovered error path: after a successful token-path upload, primary manual deletion returns 404 through fixed-name discovery and leaves the file and database reference intact.

## Human Verification Required

None. The blocking behaviors are directly observable in current data flow and missing test coverage. Visual or external-service judgment cannot change the failed status.

## Gaps Summary

Three closure concerns block Phase 06: exact source evidence does not model directory-backed ROM parents, the primary manual lifecycle uses incompatible path and concurrency authorities, and screenshot update/delete omit hidden-resource visibility. The descriptor close retry is a separate warning. The final acceptance record is internally valid, but its selected tests do not exercise these failures. Later milestone phases do not explicitly own them.

## Verification Audit

- Canonical preflight: Linux, `/home/d1sk/romm`, expected branch, origin, and RomM planning identity all verified.
- Pre-write baseline: 28 untracked entries; exact `git status --short | sha256sum` value `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1`.
- Current product code is byte-identical to acceptance HEAD `02d1a5093`; only the committed review document follows it.
- No production code, test code, deployment, service, database, or source content was modified.
- This report is the only verifier write and is intentionally left uncommitted for the orchestrator.

---

_Verified: 2026-08-24T08:57:58Z_
_Verifier: Codex (gsd-verifier)_
