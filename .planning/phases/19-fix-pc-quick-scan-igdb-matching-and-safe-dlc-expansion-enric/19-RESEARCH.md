# Phase 19: Fix PC quick-scan IGDB matching and safe DLC/expansion enrichment - Research

**Researched:** 2026-09-28
**Domain:** PC scan orchestration, IGDB metadata matching, and safe PC component enrichment
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

### PC Scan Matching

- **D-01:** Normalize compact titles only on the PC scan path before automatic
  IGDB name lookup. Do not alter classic-ROM scan matching.
- **D-02:** Preserve existing provider safety and matching thresholds. The fix
  must improve title presentation to IGDB, not broaden ambiguous matching.
- **D-03:** A metadata refresh must repair an existing PC record that has a
  persisted Steam ID but no IGDB ID, without creating a duplicate ROM.

### DLC and Expansion Identity

- **D-04:** Automatic DLC and expansion enrichment remains fail-closed. It
  applies only after the parent and the related IGDB entry are unambiguous.
- **D-05:** A user may enter an exact component title, review the provider
  candidates, and explicitly select one. No name-search candidate is applied
  merely because it is the sole returned result.
- **D-06:** Preserve the existing IGDB-first component relation flow and only
  use Steam after the authoritative IGDB component identity is established.

### the agent's Discretion

- Select the smallest PC-specific normalizer that reuses established title
  parsing and has focused regression tests for scanning and refreshing.
- Keep the implementation backend-first. No UI redesign is required for this
  bugfix unless an existing exact-title component selection is demonstrably
  inaccessible.

### Deferred Ideas (OUT OF SCOPE)

- A media-management phase: Media-based screenshot selection for overview,
  permanent provider-media deletion with an explicit full-media refresh,
  provider artwork candidates, owned artwork uploads, and multiple smooth,
  reduced-motion-aware rotating backgrounds.
- A soundtrack phase: RomM-owned manual uploads for MP3, AAC, FLAC, OGG,
  OPUS, M4A, and WAV; per-game inclusion and ordering of playable tracks;
  reuse of the existing player; no SteamGridDB audio crawling. Automatic track
  metadata enrichment remains later work.
- Existing todo `2026-09-03-fix-pc-dlc-notes-soundtrack-and-artwork-uploads.md`
  was reviewed but not folded into Phase 19 because notes and media uploads
  are independent of the scan matching defect.
  </user_constraints>

## Project Constraints (from AGENTS.md)

- Work only in `/home/d1sk/romm` on the Linux checkout, preserve unrelated worktree changes, and do not access or alter Team4s, a NAS mount, or deployment state. [VERIFIED: codebase grep]
- Backend work follows endpoint to handler to database/metadata layers, uses managed sessions and typed project exceptions, and tests must travel with changed logic. [VERIFIED: codebase grep]
- Run backend checks through `uv run pytest` and repository formatting/linting through `trunk fmt && trunk check`; never bypass hooks. [VERIFIED: codebase grep]
- Documentation, comments, and identifiers are English, and comments must be concise with no em dash. [VERIFIED: codebase grep]
- This change has no response-schema or route-contract change, so generated frontend API types are not expected to change. [VERIFIED: codebase grep]

## Summary

The confirmed defect has two gates, not one. On a new Windows quick scan, `scan_rom()` calls IGDB with the raw `fs_name`, while `SteamHandler.get_rom()` first removes tags and inserts spaces at lowercase-to-uppercase and letter-to-digit boundaries. Thus `EuroTruckSimulator2` reaches Steam as `Euro Truck Simulator 2` but reaches IGDB as the compact token. [VERIFIED: codebase grep]

An existing Steam-only Windows ROM is also ineligible for the normal `update` refresh when IGDB is selected: `Rom.is_identified` deliberately ignores `steam_id`, and `should_scan_rom()` requires both `is_identified` and a selected-source ID. If it did reach `scan_rom()`, IGDB's own update guard separately requires an existing `rom.igdb_id`. [VERIFIED: codebase grep]

**Primary recommendation:** add one PC-only IGDB lookup-title helper in `backend/handler/scan_handler.py`, use it only for Windows name-search fallback, and add the matching narrow Steam-only Windows plus selected-IGDB exception to both update eligibility gates. Do not touch `IGDBHandler` matching thresholds, classic scan behavior, or the existing IGDB-first DLC relation code. [VERIFIED: codebase grep]

## Architectural Responsibility Map

| Capability                                              | Primary Tier       | Secondary Tier     | Rationale                                                                                                                                                                             |
| ------------------------------------------------------- | ------------------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Compact PC title presentation for automatic IGDB lookup | API / Backend      | Database / Storage | `scan_rom()` owns provider dispatch and can scope normalization to `UPS.WIN` before calling the IGDB handler. [VERIFIED: codebase grep]                                               |
| Steam-only PC refresh eligibility                       | API / Backend      | Database / Storage | The scan loop decides whether an existing ORM ROM enters `scan_rom()` before any provider request. [VERIFIED: codebase grep]                                                          |
| Parent IGDB persistence                                 | Database / Storage | API / Backend      | `apply_pc_igdb_enrichment()` performs optimistic, parent-row persistence after provider matching. [VERIFIED: codebase grep]                                                           |
| DLC and expansion identity enrichment                   | API / Backend      | Database / Storage | The scan socket flow accepts only one exact cached related IGDB identity, hydrates it by ID, then persists component metadata. [VERIFIED: codebase grep]                              |
| Manual component-candidate review and selection         | Browser / Client   | API / Backend      | The active v2 PC Components tab invokes the existing review and explicit-selection APIs; the backend re-collects candidates and validates the submitted ID. [VERIFIED: codebase grep] |

## Standard Stack

### Core

| Library                                              | Version         | Purpose                                    | Why Standard                                                                                   |
| ---------------------------------------------------- | --------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| Existing Python backend, FastAPI, SQLAlchemy, pytest | Project-managed | Scan orchestration, persistence, and tests | Phase 19 requires no new runtime dependency or package installation. [VERIFIED: codebase grep] |

### Supporting

| Library                                         | Version                 | Purpose                                                           | When to Use                                                                                                                             |
| ----------------------------------------------- | ----------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Existing `re` compact-title boundary expression | Python standard library | Split lower-to-upper and letter-to-digit compact title boundaries | Reuse the behavior already used by Steam and PC candidate collection, only at the Windows IGDB scan boundary. [VERIFIED: codebase grep] |

### Alternatives Considered

| Instead of                                 | Could Use                                             | Tradeoff                                                                                                                                                        |
| ------------------------------------------ | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PC-only scan-boundary normalization        | Change `IGDBHandler.get_rom()` globally               | Globalizing the transform would change classic-ROM and platform-specific filename parsing, violating D-01. [VERIFIED: codebase grep]                            |
| Narrow Steam-only Windows update exception | Treat `steam_id` as general `Rom.is_identified` state | That property deliberately describes established non-Steam metadata identity and changing it affects scan behavior outside the phase. [VERIFIED: codebase grep] |
| Existing automatic related-IGDB resolver   | Auto-apply a sole arbitrary name-search result        | The current manual API and D-05 require review plus explicit selection for name-search candidates. [VERIFIED: codebase grep]                                    |

**Installation:** None. [VERIFIED: codebase grep]

## Architecture Patterns

### System Architecture Diagram

```text
filesystem PC folder: EuroTruckSimulator2
              |
              v
scan loop: should_scan_rom
  quick new ROM OR narrow update exception
              |
              v
scan_rom (Windows only)
  strip known tags, split compact boundaries
  "Euro Truck Simulator 2"
              |
              +-------------------------------+
              |                               |
              v                               v
IGDB name lookup, existing thresholds     Steam lookup, existing behavior
              |                               |
              v                               v
parent IGDB ID and metadata              Steam ID and metadata
              |
              v
apply_pc_igdb_enrichment (optimistic parent persistence)
              |
              v
for each local DLC component
  exact title equals exactly one cached IGDB dlc/expansion relation?
       | yes                                      | no
       v                                          v
hydrate IGDB relation by ID                   leave component unchanged
       |
       v
optional Steam DLC lookup, only after IGDB identity,
then validate DLC type, similarity, and parent relation
```

The diagram reflects the current successful parent-to-component data flow. The repair must make the parent IGDB relation available at its existing entry point, rather than adding a second component-only matcher. [VERIFIED: codebase grep]

### Recommended Project Structure

```text
backend/
├── handler/scan_handler.py                 # PC-only lookup title and IGDB update gate
├── endpoints/sockets/scan.py               # PC-only scan eligibility exception
├── tests/handler/test_scan_handler.py      # lookup-title and provider-dispatch regression tests
├── tests/endpoints/sockets/test_scan.py    # update eligibility regression tests
└── tests/handler/test_fastapi.py            # scan-level persistence/enrichment regression if fixture seam is practical
```

The phase should not require a schema migration, a new endpoint, a generated client update, or a frontend redesign. [VERIFIED: codebase grep]

### Pattern 1: PC-only provider input adaptation

**What:** derive a provider lookup presentation string from the PC filesystem name without changing the persisted filesystem identity or generic IGDB handler behavior. [VERIFIED: codebase grep]

**When to use:** only in `fetch_igdb_rom()` when `platform.slug == UPS.WIN` and the path has reached IGDB's name-search fallback, not an ID-based Hashéous, Playmatch, or persisted-IGDB refresh. [VERIFIED: codebase grep]

**Example:**

```python
# Source: backend/handler/scan_handler.py and backend/handler/metadata/steam_handler.py
def _pc_igdb_lookup_name(fs_name: str) -> str:
    name = fs_rom_handler.get_file_name_with_no_tags(fs_name)
    return COMPACT_TITLE_BOUNDARY.sub(" ", name) if " " not in name else name

# In the Windows-only IGDB name-search fallback:
lookup_name = _pc_igdb_lookup_name(rom_attrs["fs_name"])
return await meta_igdb_handler.get_rom(rom, lookup_name, platform_igdb_id)
```

The final helper name is discretionary. Its contract must preserve ordinary spaced names and make `EuroTruckSimulator2` become `Euro Truck Simulator 2`; it must not split all-caps acronyms or broaden IGDB's similarity policy. [VERIFIED: codebase grep]

### Pattern 2: Narrow recovery eligibility

**What:** treat a Windows ROM with `steam_id` present and `igdb_id` absent as eligible for an IGDB `update` only when IGDB is selected. [VERIFIED: codebase grep]

**When to use:** in both `should_scan_rom()` and the `fetch_igdb_rom()` outer condition, because the former otherwise skips the row and the latter otherwise returns an empty IGDB result. [VERIFIED: codebase grep]

**Example:**

```python
# Source: backend/endpoints/sockets/scan.py and backend/handler/scan_handler.py
is_pc_igdb_recovery = (
    rom.platform_slug == UPS.WIN
    and bool(rom.steam_id)
    and not rom.igdb_id
    and MetadataSource.IGDB in metadata_sources
)

# UPDATE may proceed if the old selected-source-ID rule OR this recovery rule holds.
```

The implementation should use the project’s existing enum/string conventions and avoid a broad `steam_id` inclusion in `Rom.is_identified`. [VERIFIED: codebase grep]

### Anti-Patterns to Avoid

- **Normalize inside `IGDBHandler.get_rom()`:** this handler owns platform-specific classic filename formats, so a global compact-name rewrite crosses D-01’s boundary. [VERIFIED: codebase grep]
- **Use Steam ID to infer IGDB ID:** the current system performs IGDB ID refresh only from explicit identifiers or its normal lookup path; no verified Steam-to-IGDB mapping contract exists in this codebase. [VERIFIED: codebase grep]
- **Let a sole name-search candidate persist automatically:** `select_pc_component_metadata_candidate()` requires a submitted candidate ID from recomputed candidate results, and automatic scan enrichment accepts only one exact related parent IGDB candidate. [VERIFIED: codebase grep]
- **Change component enrichment to search Steam first:** `_enrich_pc_dlc_from_igdb()` hydrates IGDB first, then permits Steam only after validated DLC and parent relation checks. [VERIFIED: codebase grep]

## Don't Hand-Roll

| Problem             | Don't Build                                                  | Use Instead                                                                | Why                                                                                                                                                                |
| ------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Fuzzy game matching | A phase-specific IGDB score or fallback matcher              | Existing `IGDBHandler._search_rom()` and `find_best_match()`               | It already applies game-type passes, prefix/superset ambiguity handling, expanded search, and current thresholds. [VERIFIED: codebase grep]                        |
| Component identity  | New DLC title heuristic or automatic name-search persistence | Existing `PcMetadataMatchHandler` exact related-IGDB candidate flow        | It compares normalized word sequences against the parent’s `dlcs` and `expansions`, requires exactly one candidate, then hydrates by ID. [VERIFIED: codebase grep] |
| Steam DLC trust     | Ad hoc Steam app relation parsing                            | `fetch_validated_steam_dlc()`                                              | It verifies type `dlc`, high title similarity, a valid positive `fullgame.appid` when supplied, and equality with the parent Steam ID. [VERIFIED: codebase grep]   |
| Optimistic writes   | Direct component or ROM session mutation                     | `apply_pc_igdb_enrichment()` and `apply_pc_component_metadata_candidate()` | They enforce expected update timestamps and return `None` on stale state. [VERIFIED: codebase grep]                                                                |

**Key insight:** Phase 19 is a narrow input-presentation and eligibility repair. The established matching, explicit-review, provider-order, and optimistic-persistence safeguards already implement the difficult correctness work. [VERIFIED: codebase grep]

## Common Pitfalls

### Pitfall 1: Fixing only the compact title

**What goes wrong:** a new quick-scanned PC game succeeds, but an existing Steam-only PC record still does not enter an IGDB `update` refresh. [VERIFIED: codebase grep]

**Why it happens:** `should_scan_rom()` rejects it because `is_identified` excludes Steam, and `fetch_igdb_rom()` rejects `UPDATE` without `rom.igdb_id`. [VERIFIED: codebase grep]

**How to avoid:** add and test the same PC, Steam-present, IGDB-absent, IGDB-selected predicate at both gates. [VERIFIED: codebase grep]

**Warning signs:** `meta_igdb_handler.get_rom()` is never awaited in a test that models the persisted Steam-only Windows ROM. [VERIFIED: codebase grep]

### Pitfall 2: Broadening classic scan behavior accidentally

**What goes wrong:** compact filenames for classic platforms receive new spacing before IGDB-specific PS2, PSP, Switch, MAME, or ScummVM parsing. [VERIFIED: codebase grep]

**Why it happens:** placing the transform inside `IGDBHandler.get_rom()` puts it before its platform-specific parsing and every platform’s provider call. [VERIFIED: codebase grep]

**How to avoid:** keep the helper call at the Windows branch in `scan_rom()` and add a non-Windows call-argument regression test. [VERIFIED: codebase grep]

**Warning signs:** an IGDB handler unit test changes solely because a classic filename became spaced. [VERIFIED: codebase grep]

### Pitfall 3: Bypassing fail-closed component enrichment

**What goes wrong:** a component receives metadata from a generic name-search result that happens to be unique. [VERIFIED: codebase grep]

**Why it happens:** unique return count is not identity proof; automatic enrichment is designed around the parent’s explicit IGDB relation and exact normalized title equality. [VERIFIED: codebase grep]

**How to avoid:** do not modify `find_unique_related_igdb_candidate()` or replace it with `collect_component_candidates()` in scan automation. [VERIFIED: codebase grep]

**Warning signs:** an automatic scan calls `get_matched_roms_by_name()` for a DLC component. [VERIFIED: codebase grep]

### Pitfall 4: Confusing available manual selection with auto-selection

**What goes wrong:** implementation adds a UI or API path that applies a lone result automatically. [VERIFIED: codebase grep]

**Why it happens:** `collect_component_candidates()` is intentionally review-only, while the existing `POST` recomputes the exact query and requires `candidate_id` plus optimistic `expected_version`. [VERIFIED: codebase grep]

**How to avoid:** retain the existing PC Components surface and test candidate review followed by an explicit selection only. [VERIFIED: codebase grep]

**Warning signs:** a GET candidates request causes a database write, or POST accepts no candidate ID. [VERIFIED: codebase grep]

## Code Examples

### Existing safe automatic component sequence

```python
# Source: backend/endpoints/sockets/scan.py
candidate = await pc_metadata_match_handler.fetch_unique_related_igdb_candidate(
    rom, component
)
if candidate is None:
    return

saved_component = db_rom_handler.apply_pc_component_metadata_candidate(
    rom.id, component.id, component.updated_at, "igdb", candidate.fields
)
if saved_component is None:
    return

steam_candidate = await pc_metadata_match_handler.fetch_validated_steam_dlc(
    rom, candidate
)
```

This is the required order for D-04 and D-06: one authoritative related IGDB identity, ID hydration, optimistic persistence, then optional Steam enrichment. [VERIFIED: codebase grep]

### Existing explicit component selection contract

```text
GET  /api/roms/{rom_id}/pc-components/{component_id}/metadata-candidates?query=<exact title>
POST /api/roms/{rom_id}/pc-components/{component_id}/metadata-selection
     { candidate_id, query, expected_version, selected_media_ids }
```

The active v2 Game Details PC Components tab renders `PcComponents`, and the frontend API client exposes both search and selection methods. No UI work is required unless an implementation audit finds that the existing component control itself is inaccessible. [VERIFIED: codebase grep]

## State of the Art

| Old Approach                                                           | Current Approach                                                                                                 | When Changed | Impact                                                                                  |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------- |
| Raw compact `fs_name` reaches automatic IGDB name search for Windows   | Steam and reviewable PC candidate collection already split compact title boundaries, but scan IGDB does not      | Present code | Phase 19 should align only the missing Windows scan boundary. [VERIFIED: codebase grep] |
| Generic automatic component title matching would be possible in theory | Automatic enrichment uses exact parent-related IGDB identity and manual lookup is review then explicit selection | Present code | Preserve this fail-closed design. [VERIFIED: codebase grep]                             |

## Assumptions Log

All conclusions are backed by the live codebase and phase context. No external package, provider API, or operational policy claim is needed for this phase. [VERIFIED: codebase grep]

## Resolved Scope Decisions

1. **Recovery platform scope is Windows-only in Phase 19.**
   - Locked outcome: the exception is limited to `UPS.WIN`. Although Steam supports `win`, `linux`, and `mac`, D-01 and D-03 constrain this repair to the demonstrated Windows path, and component reconciliation/enrichment is currently guarded by `UPS.WIN`. Linux/macOS require a separate reproducer and explicit scope decision. [VERIFIED: codebase grep]

2. **Refresh-dialog copy does not change in Phase 19.**
   - Locked outcome: retain the existing user-facing refresh description. The narrow Steam-only Windows name-lookup exception needs no locale or copy update unless separately requested. [VERIFIED: codebase grep]

## Environment Availability

| Dependency                         | Required By                      | Available  | Version        | Fallback                                                                                              |
| ---------------------------------- | -------------------------------- | ---------- | -------------- | ----------------------------------------------------------------------------------------------------- |
| `uv`                               | Backend test execution           | Yes        | 0.12.3         | None needed. [VERIFIED: codebase grep]                                                                |
| Project Python via `uv run python` | Backend implementation and tests | Yes        | 3.13.15        | None needed. [VERIFIED: codebase grep]                                                                |
| pytest via project environment     | Focused regression suite         | Yes        | 9.0.3          | None needed. [VERIFIED: codebase grep]                                                                |
| Live IGDB credentials/network      | Manual UAT against provider      | Not probed | Not applicable | Mock existing provider seams in automated tests; treat live UAT separately. [VERIFIED: codebase grep] |

**Missing dependencies with no fallback:** None for implementation and automated tests. [VERIFIED: codebase grep]

**Missing dependencies with fallback:** Live IGDB access is not required for focused unit and scan orchestration tests because current tests mock handler calls. [VERIFIED: codebase grep]

## Validation Architecture

### Test Framework

| Property                 | Value                                                                                                                                                                                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framework                | pytest 9.0.3, with project-managed pytest-asyncio and pytest-mock support. [VERIFIED: codebase grep]                                                                                                                                                      |
| Config file              | `backend/pyproject.toml`. [VERIFIED: codebase grep]                                                                                                                                                                                                       |
| Quick run command        | `cd backend && uv run pytest tests/handler/test_scan_handler.py tests/endpoints/sockets/test_scan.py tests/handler/metadata/test_pc_match_handler.py -x` [VERIFIED: codebase grep]                                                                        |
| Full phase suite command | `cd backend && uv run pytest tests/handler/test_scan_handler.py tests/handler/test_fastapi.py tests/endpoints/sockets/test_scan.py tests/handler/metadata/test_pc_match_handler.py tests/endpoints/roms/test_pc_metadata.py -x` [VERIFIED: codebase grep] |

### Phase Requirements to Test Map

| Behavior                                                                                                                                    | Test Type                         | Automated Command                                                                                                        | File Exists?                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| New Windows quick scan presents `EuroTruckSimulator2` to IGDB as `Euro Truck Simulator 2` and accepts the handler’s IGDB result             | async scan orchestration          | `uv run pytest tests/handler/test_fastapi.py -k euro_truck -x`                                                           | No, add in Phase 19. [VERIFIED: codebase grep]                                                  |
| Equivalent compact classic ROM still passes its raw filename to IGDB                                                                        | unit/provider-dispatch regression | `uv run pytest tests/handler/test_scan_handler.py -k classic -x`                                                         | No, add in Phase 19. [VERIFIED: codebase grep]                                                  |
| Steam-only Windows ROM is selected for `update` when IGDB is selected, and remains excluded if IGDB is not selected                         | unit scan eligibility             | `uv run pytest tests/endpoints/sockets/test_scan.py -k steam_only -x`                                                    | No, add in Phase 19. [VERIFIED: codebase grep]                                                  |
| Selected Steam-only Windows refresh makes the IGDB name-search call, not an IGDB ID refresh, and preserves the same ROM identity            | async scan orchestration          | `uv run pytest tests/handler/test_fastapi.py -k steam_only -x`                                                           | No, add in Phase 19. [VERIFIED: codebase grep]                                                  |
| Parent IGDB result initiates existing exact-relation DLC and expansion enrichment, while ambiguous or unrelated components remain untouched | scan/socket integration           | `uv run pytest tests/endpoints/sockets/test_scan.py -k enrichment -x`                                                    | Existing partial coverage, extend with UAT fixture relation. [VERIFIED: codebase grep]          |
| Exact-title component candidates remain review-only and persist only after explicit POST selection                                          | endpoint plus handler unit        | `uv run pytest tests/handler/metadata/test_pc_match_handler.py tests/endpoints/roms/test_pc_metadata.py -k component -x` | Yes, preserve and extend only if fixture-specific coverage is needed. [VERIFIED: codebase grep] |

### Required Test Seams

- In `backend/tests/handler/test_scan_handler.py`, test the extracted PC lookup-title helper directly if introduced, and patch `handler.scan_handler.meta_igdb_handler.get_rom` to assert exact call arguments. The file already uses `AsyncMock` and provider-method patches. [VERIFIED: codebase grep]
- In `backend/tests/endpoints/sockets/test_scan.py`, extend `TestShouldScanRom` with a mock Windows ROM whose only external identity is `steam_id`; assert the narrow selected-IGDB positive and non-IGDB or non-Windows negatives. [VERIFIED: codebase grep]
- In `backend/tests/handler/test_fastapi.py`, use the established `scan_rom()` fixture style with mocked provider methods to prove a persisted Steam-only parent receives IGDB name lookup and no duplicate `Rom` is inserted. Keep this focused rather than VCR/live-network dependent. [VERIFIED: codebase grep]
- Keep `backend/tests/handler/metadata/test_pc_match_handler.py` and `backend/tests/endpoints/roms/test_pc_metadata.py` as the contract tests for exact component candidate review, exact-parent relationship behavior, explicit selection, and component-only persistence. [VERIFIED: codebase grep]

### Sampling Rate

- **Per task commit:** run the quick focused command above. [VERIFIED: codebase grep]
- **Per wave merge:** run the full phase suite above. [VERIFIED: codebase grep]
- **Phase gate:** run `trunk fmt && trunk check`, then the full phase suite green before verification. [VERIFIED: codebase grep]

### Wave 0 Gaps

- [ ] Add the Windows compact-name-to-IGDB scan regression fixture.
- [ ] Add narrow Steam-only Windows `update` eligibility positives and negatives.
- [ ] Add a scan-level no-duplicate persistence assertion for the refresh repair.
- [ ] Extend component enrichment coverage with the parent ID `3070`, a uniquely related DLC, and a uniquely related expansion if the existing fixtures cannot express both kinds.

## Security Domain

### Applicable ASVS Categories

| ASVS Category         | Applies        | Standard Control                                                                                                                                                   |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| V2 Authentication     | No new surface | Existing protected scan and metadata routes remain unchanged. [VERIFIED: codebase grep]                                                                            |
| V3 Session Management | No new surface | Existing Socket.IO and route authentication remain unchanged. [VERIFIED: codebase grep]                                                                            |
| V4 Access Control     | Yes            | Preserve existing scope checks on scan and PC metadata review/selection endpoints. [VERIFIED: codebase grep]                                                       |
| V5 Input Validation   | Yes            | Continue passing filesystem names through existing filename-tag handling and use bounded `query` validation for manual candidate review. [VERIFIED: codebase grep] |
| V6 Cryptography       | No             | The phase introduces no cryptographic operation. [VERIFIED: codebase grep]                                                                                         |

### Known Threat Patterns for This Stack

| Pattern                                          | STRIDE                        | Standard Mitigation                                                                                                                                                                    |
| ------------------------------------------------ | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Incorrect external metadata association          | Tampering                     | Preserve IGDB scoring thresholds, require an exact single parent-related candidate for auto component writes, and retain optimistic expected-version checks. [VERIFIED: codebase grep] |
| Unauthorized metadata changes                    | Elevation of privilege        | Keep `ROMS_READ` for review and `ROMS_WRITE` for explicit selection; do not add an unauthenticated route. [VERIFIED: codebase grep]                                                    |
| Race overwrites during scan/selection            | Tampering                     | Use the existing timestamp-checked parent and component persistence methods, which return no update on stale rows. [VERIFIED: codebase grep]                                           |
| Provider failure causing partial unsafe fallback | Denial of service / Tampering | Existing concurrent provider collection isolates exceptions and enrichment stops when IGDB hydration is absent or fails. [VERIFIED: codebase grep]                                     |

## Sources

### Primary (HIGH confidence)

- `backend/handler/scan_handler.py`, inspected current scan metadata gates, provider dispatch, Steam handling, and pre-existing PC auto-link behavior. [VERIFIED: codebase grep]
- `backend/handler/metadata/igdb_handler.py`, inspected ID-tag handling, platform-specific parsing, search flow, and existing match safeguards. [VERIFIED: codebase grep]
- `backend/handler/metadata/steam_handler.py`, inspected the established compact title boundary normalization. [VERIFIED: codebase grep]
- `backend/endpoints/sockets/scan.py`, inspected scan eligibility and parent-to-component enrichment order. [VERIFIED: codebase grep]
- `backend/handler/metadata/pc_match_handler.py` and `backend/endpoints/roms/pc_metadata.py`, inspected exact related-candidate matching, review, and explicit selection semantics. [VERIFIED: codebase grep]
- `backend/tests/handler/test_scan_handler.py`, `backend/tests/handler/test_fastapi.py`, `backend/tests/endpoints/sockets/test_scan.py`, `backend/tests/handler/metadata/test_pc_match_handler.py`, and `backend/tests/endpoints/roms/test_pc_metadata.py`, inspected live regression seams. [VERIFIED: codebase grep]
- `frontend/src/v2/views/GameDetails.vue` and `frontend/src/services/api/rom.ts`, inspected the active UI reachability of PC component candidate review and selection. [VERIFIED: codebase grep]

### Secondary (MEDIUM confidence)

- None. [VERIFIED: codebase grep]

### Tertiary (LOW confidence)

- None. [VERIFIED: codebase grep]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, no dependency change is required and the project-managed test environment was probed. [VERIFIED: codebase grep]
- Architecture: HIGH, all relevant control-flow and persistence paths were inspected in the live checkout. [VERIFIED: codebase grep]
- Pitfalls: HIGH, each pitfall follows from an identified current gate or an existing testable safety boundary. [VERIFIED: codebase grep]

**Research date:** 2026-09-28
**Valid until:** 2026-10-28, unless scan orchestration or PC component matching changes first. [VERIFIED: codebase grep]
