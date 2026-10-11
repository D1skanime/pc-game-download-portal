---
phase: 19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric
verified: 2026-09-28T12:09:05Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run a normal IGDB-and-Steam quick scan on the authorized Windows EuroTruckSimulator2 fixture, then review and explicitly select a component candidate."
    expected: "One existing parent remains with IGDB ID 3070 and unchanged filesystem identity; only unambiguous Special Transport and Italia relations are enriched; an ambiguous or unrelated component remains unchanged; candidate review alone makes no change."
    why_human: "Real provider responses, mounted fixture layout, scan orchestration, and visible no-change behavior cannot be proven without the authorized live environment."
---

# Phase 19: Fix PC quick-scan IGDB matching and safe DLC/expansion enrichment Verification Report

**Phase Goal:** Repair automatic Windows PC scans so compact names resolve with IGDB as reliably as Steam; repair existing Steam-only Windows PC records on IGDB-selected metadata refresh without duplicates; preserve fail-closed IGDB-first DLC/expansion enrichment and explicit manual component selection.
**Verified:** 2026-09-28T12:09:05Z
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                             | Status   | Evidence                                                                                                                                                                                                                                                                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | D-01: A Windows quick scan presents compact `EuroTruckSimulator2` to IGDB as `Euro Truck Simulator 2`.            | VERIFIED | `scan_handler._windows_igdb_lookup_name()` removes tags and applies Steam's established `COMPACT_TITLE_BOUNDARY`; the Windows-only `get_rom()` fallback uses its result at lines 741-750.                                                                                                                          |
| 2   | A Windows name already containing spaces is unchanged before IGDB lookup.                                         | VERIFIED | The helper returns the tag-stripped name unchanged when it contains a space. The focused regression covers `Euro Truck Simulator 2`.                                                                                                                                                                               |
| 3   | A classic-ROM scan keeps its original filename-derived IGDB lookup value.                                         | VERIFIED | The transform is guarded by `platform.slug == UPS.WIN`; the non-Windows regression expects the unmodified compact title.                                                                                                                                                                                           |
| 4   | D-02: Existing IGDB matcher safety and thresholds remain authoritative.                                           | VERIFIED | The phase diff changes only the `scan_handler` fallback argument and narrow admission predicate. `IGDBHandler` and its matching code were not changed.                                                                                                                                                             |
| 5   | D-03: An admitted Steam-only Windows UPDATE with no IGDB ID performs IGDB name lookup, not ID refresh.            | VERIFIED | Matching Windows, positive Steam ID, absent IGDB ID, UPDATE, and selected IGDB predicates are enforced in both `should_scan_rom()` and `fetch_igdb_rom()`. Existing IGDB IDs still call `get_rom_by_id()`.                                                                                                         |
| 6   | D-03: The existing Windows Steam-only record is updated in place without a duplicate.                             | VERIFIED | Scan wiring persists `scan_rom()` through `db_rom_handler.add_rom()` before parent enrichment. The regression creates `EuroTruckSimulator2`, asserts the saved ID equals the persisted ID, and counts exactly one matching row.                                                                                    |
| 7   | D-04: Automatic DLC and expansion enrichment uses only one exact, parent-related IGDB identity.                   | VERIFIED | Parent IGDB metadata is committed before components are reloaded and processed. `fetch_unique_related_igdb_candidate()` accepts one related candidate only, hydrates it by ID, and rejects mismatched or incomplete hydration. Coverage uses the parent ID 3070 with both Special Transport and Italia identities. |
| 8   | D-06: Ambiguous, unrelated, or hydration-failed automatic candidates make no component write and no Steam lookup. | VERIFIED | `_enrich_pc_dlc_from_igdb()` returns before persistence when the hydrated candidate is absent; Steam lookup follows only a successful optimistic IGDB component save. Regression assertions verify both calls are absent for ambiguity and hydration failure.                                                      |
| 9   | D-05: Manual component search is review-only, while application requires a current explicit candidate selection.  | VERIFIED | GET only calls `collect_component_candidates()` and returns candidates plus `expected_version`. POST recomputes candidates, requires the submitted ID to be present, and calls the optimistic persistence API with `expected_version`; tests cover read-only GET and stale-version conflict.                       |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact                                       | Expected                                                                     | Status   | Details                                                                                                        |
| ---------------------------------------------- | ---------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------- |
| `backend/handler/scan_handler.py`              | Windows-only compact-title presentation and inner Steam-only UPDATE recovery | VERIFIED | Exists, substantive, and invoked by the IGDB name-search fallback.                                             |
| `backend/endpoints/sockets/scan.py`            | Narrow scan-loop admission and parent-before-component enrichment order      | VERIFIED | `should_scan_rom()` gates the recovery; `_identify_rom()` saves and enriches parent before loading components. |
| `backend/handler/metadata/pc_match_handler.py` | Exact related IGDB identity hydration and post-IGDB Steam validation         | VERIFIED | Candidate selection is unique, relation-bound, ID-hydrated, and fail-closed.                                   |
| `backend/endpoints/roms/pc_metadata.py`        | Read-only candidate review and explicit optimistic selection                 | VERIFIED | GET has read scope only; POST recomputes candidates and uses write scope plus expected version.                |
| `backend/tests/handler/test_scan_handler.py`   | Windows/classic/provider-dispatch regression coverage                        | VERIFIED | Contains direct compact, spaced, classic, persisted-ID, and Steam-only recovery assertions.                    |
| `backend/tests/endpoints/sockets/test_scan.py` | Eligibility and fail-closed component flow regressions                       | VERIFIED | Covers every recovery predicate plus no-write/no-Steam failure paths and the two 3070 relations.               |

### Key Link Verification

| From              | To                          | Via                                                           | Status | Details                                                                                                        |
| ----------------- | --------------------------- | ------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| `scan_handler.py` | `meta_igdb_handler.get_rom` | Windows-only name-search fallback argument                    | WIRED  | The fallback computes `lookup_name` only for `UPS.WIN` and awaits `get_rom(rom, lookup_name, ...)`.            |
| `sockets/scan.py` | `scan_handler.py`           | Selected-IGDB UPDATE eligibility reaches name-search recovery | WIRED  | `should_scan_rom()` admits only the same Windows/Steam/IGDB/UPDATE predicate that `fetch_igdb_rom()` consumes. |
| `sockets/scan.py` | `pc_match_handler`          | Exact related IGDB candidate before optional Steam            | WIRED  | Candidate fetch, optimistic IGDB save, then `fetch_validated_steam_dlc()` occur in that order.                 |
| `pc_metadata.py`  | `pc_match_handler`          | Candidate review and explicit POST selection                  | WIRED  | GET and POST both call `collect_component_candidates()`; POST only saves a freshly recomputed submitted ID.    |

The automated key-link helper reported false negatives for the first two links because its plan patterns contain escaped literal dots. Manual source inspection above confirms both executable links.

### Data-Flow Trace (Level 4)

| Artifact          | Data Variable                                      | Source                                                                                        | Produces Real Data                                       | Status  |
| ----------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------- |
| `scan_handler.py` | `lookup_name`                                      | `rom_attrs["fs_name"]`, tag removal, compact-title boundary                                   | Yes, passed to live IGDB adapter call                    | FLOWING |
| `sockets/scan.py` | parent IGDB metadata then `scan_target.components` | `scan_rom()` result persisted by `add_rom()`, then `apply_pc_igdb_enrichment()` and DB reload | Yes, persisted parent relation feeds component loop      | FLOWING |
| `pc_metadata.py`  | `results` and selected candidate                   | Provider candidate collection recomputed for the request                                      | Yes, only a returned ID can reach optimistic persistence | FLOWING |

### Behavioral Spot-Checks

| Behavior                    | Command                                                                                                                                 | Result                                                                                                 | Status                    |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------- |
| Phase-focused backend tests | `cd backend && uv run pytest ... -k 'compact or classic or steam_only or recovery or enrichment or component or metadata_selection' -x` | Reached `setup_database` before the first assertion and failed connecting to MariaDB `127.0.0.1:3306`. | SKIP, environment blocked |
| Python syntax               | AST parse of 4 implementation and 5 relevant test modules                                                                               | All 9 files parsed.                                                                                    | PASS                      |
| Targeted static checks      | `trunk check --no-fix` on the 9 phase files                                                                                             | `Checked 9 files`, `No issues`.                                                                        | PASS                      |

### Probe Execution

Step 7c: SKIPPED. Phase plans and summaries declare no probes, and this repository has no `scripts/` probe directory.

### Requirements Coverage

| Requirement | Source Plan  | Description                                                                | Status    | Evidence                                                                    |
| ----------- | ------------ | -------------------------------------------------------------------------- | --------- | --------------------------------------------------------------------------- |
| D-01        | 19-01        | Normalize compact Windows titles only on the PC IGDB scan path.            | SATISFIED | Windows-only helper and call-site preserve non-Windows values.              |
| D-02        | 19-01        | Preserve provider safety and matching thresholds.                          | SATISFIED | No IGDB matcher/threshold modification in phase commits.                    |
| D-03        | 19-01, 19-02 | Repair an existing Steam-only Windows record without duplicate creation.   | SATISFIED | Dual admission guards plus in-place persistence test.                       |
| D-04        | 19-02        | Automatic DLC/expansion enrichment remains unambiguous and relation-bound. | SATISFIED | Unique relation selection, ID hydration, parent-before-component flow.      |
| D-05        | 19-02        | Manual component search requires review then explicit selection.           | SATISFIED | Read-only GET, recomputed POST candidate validation, version check.         |
| D-06        | 19-02        | Steam runs only after authoritative IGDB component identity.               | SATISFIED | Early returns prevent writes/Steam; post-save Steam sequencing is explicit. |

No Phase 19 requirement is orphaned from its plans. There are no later milestone phases to which a gap could be deferred.

### Anti-Patterns Found

| File                              | Line    | Pattern                                                | Severity | Impact                                                                                                     |
| --------------------------------- | ------- | ------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------- |
| `backend/handler/scan_handler.py` | 202-218 | Existing `return {}` defensive provider-data fallbacks | Info     | Outside the phase logic and not connected to user-visible empty output; no phase-added debt markers found. |

No unreferenced `TBD`, `FIXME`, or `XXX` debt marker exists in the Phase 19 modified files. The phase diff introduces no source-library mutation call.

### Human Verification Required

### 1. Authorized Windows fixture quick scan and explicit review flow

**Test:** In an already-authorized test library, keep the existing `EuroTruckSimulator2` parent and local components named `Euro Truck Simulator 2: Special Transport` and `Euro Truck Simulator 2: Italia`. Run a normal quick scan with IGDB and Steam selected. Then search an exact component title in the existing PC Components UI, inspect candidates, and explicitly select one.

**Expected:** The parent resolves to IGDB 3070 with exactly one parent row and unchanged filesystem identity. Special Transport and Italia receive metadata only for unambiguous related IGDB identities. An ambiguous or unrelated component remains unchanged. A candidate search alone persists nothing; the explicit, current-version selection is required.

**Why human:** This depends on live IGDB and Steam provider responses, the mounted fixture, scan lifecycle, and visible end-to-end behavior. The local test database is unavailable before pytest assertions run.

### Gaps Summary

No implementation gaps were found. Automated pytest is environment-blocked before test execution by the unavailable MariaDB endpoint, so it is not classified as a product failure. The phase remains `human_needed` until the required live fixture flow is performed.

---

_Verified: 2026-09-28T12:09:05Z_
_Verifier: the agent (gsd-verifier)_
