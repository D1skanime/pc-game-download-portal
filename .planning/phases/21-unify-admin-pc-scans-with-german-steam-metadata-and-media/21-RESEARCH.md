# Phase 21: Unify admin PC scans with German Steam metadata and media - Research

**Researched:** 2026-09-30
**Domain:** Backend PC scan enrichment, Steam Storefront localization, owned provider media
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

### Shared enrichment and localization

- **D-01:** Both administrator and targeted-ROM PC scans call one shared enrichment boundary. It receives scan type, current ROM state, platform, filesystem name, selected providers, and scan context; it returns a normalized patch and never mutates ORM state directly.
- **D-02:** For an eligible Steam-enabled PC scan, use a persisted valid Steam App ID when present; otherwise allow one normalized-name resolution. Resolve German details first and fetch English only for fields missing from the German payload of that same App ID. Never perform a second broad name search after an App ID is selected.
- **D-03:** Apply the same behavior to newly discovered games and to existing games processed by `update` or `complete`. Keep quick, hash-only, classic-ROM, and excluded-platform behavior unchanged unless it already enters the eligible shared PC path.

### Provenance, manual fields, and provider authority

- **D-04:** Existing Steam provenance decides which earlier Steam-owned display fields may refresh. Manually entered title, summary, developer, publisher, release date, and selected artwork remain authoritative and unchanged.
- **D-05:** Steam may enrich localized title, summary, developer, publisher, release data, cover candidates, and screenshot candidates. IGDB remains authoritative for themes, franchises, related-game relationships, and DLC discovery; this phase does not change Steam DLC identity rules.
- **D-06:** Unavailable, malformed, ambiguous, invalid, or rate-limited Steam responses produce an empty patch and must not erase text, media, placement, or metadata from Steam or another provider.

### Steam media reconciliation and placement

- **D-07:** Treat Steam cover and screenshot URLs as provider candidates. Reconcile them idempotently by trusted provider origin and canonical source URL; a refresh may tombstone vanished provider candidates but never deletes RomM-owned uploads.
- **D-08:** Automatic placement is allowed only on unclaimed surfaces: a preferred Steam cover may fill overview and Steam screenshots may fill background using the existing ordering rules. Manual overview/background placement, user uploads, and explicit provider selections are never replaced, removed, or reordered by scans.
- **D-09:** Reconciled Steam candidates remain visible and editable through the Phase 20 Media interface.

### Verification and operational boundary

- **D-10:** Focused tests must prove scan-path parity, German-first fallback, new/update/complete coverage, manual protection, automatic placement only for unclaimed surfaces, failure isolation, platform gating, and idempotent provider-media reconciliation that leaves uploads untouched.
- **D-11:** Browser UAT uses only the isolated Witcher-style fixture and covers a new game, existing refresh, German Steam text, automatic media, manual override protection, and absence of source-library mutation.
- **D-12:** Do not access a NAS mount, alter Team4s, use Docker Compose, or write to external source-library paths as part of this phase.

### the agent's Discretion

- Choose the smallest seam-compatible API and helper decomposition that reuses `SteamHandler`, `normalize_steam`, the existing PC matching path, and Phase 20 owned-media reconciliation.
- Select focused fixtures and assertions that distinguish the scan policy from the unrelated dev/UAT deployment differences.

### Deferred Ideas (OUT OF SCOPE)

- Steam login, ownership, installation, or library synchronization.
- Translation changes for non-Steam providers and changes to Steam DLC identity/relationship rules.
- Any NAS, Team4s, Docker Compose, or external source-library operation.
  </user_constraints>

## Summary

The scan path already contains a partial Steam seam: `resolve_steam_scan_metadata()` in `backend/handler/scan_handler.py` selects a stored App ID before name search, delegates locale handling to `SteamHandler.get_rom_by_id()`, and feeds the result to `normalize_steam()`. [VERIFIED: codebase, `backend/handler/scan_handler.py`, `backend/handler/metadata/steam_handler.py`, `backend/handler/metadata/steam_merge.py`] It is used only as one provider fetch inside `scan_rom()`, while the explicit PC metadata-selection endpoint has a second, similar `normalize_steam()` construction. [VERIFIED: codebase, `backend/handler/scan_handler.py`, `backend/endpoints/roms/pc_metadata.py`]

The missing Phase 21 behavior is the persistence seam after normalization. The current scan projects Steam media back into `url_cover` and `url_screenshots` through `_steam_artwork_handler()`, whereas Phase 20's catalog requires downloaded, owned provider-media rows with canonical HTTPS identity and placements. [VERIFIED: codebase, `backend/handler/scan_handler.py`, `backend/endpoints/roms/media.py`, `backend/handler/metadata/rom_media.py`, `backend/handler/database/roms_handler.py`] The existing media refresh endpoint is an operator endpoint and derives candidates from the ROM's currently selected legacy URLs, so it is not a suitable scan-policy boundary. [VERIFIED: codebase, `backend/endpoints/roms/media.py`]

**Primary recommendation:** Extract a pure shared PC Steam enrichment function in the metadata layer, then add a scan-only owned-media reconciliation service that consumes its candidate URLs after the ROM patch is persisted, preserves manual state, and performs narrow automatic placement only when the compatible surface has no existing placement. [VERIFIED: codebase patterns, `backend/handler/scan_handler.py`, `backend/handler/metadata/steam_merge.py`, `backend/handler/database/roms_handler.py`]

## Architectural Responsibility Map

| Capability                                                | Primary Tier       | Secondary Tier            | Rationale                                                                                                                                                                                                                                                           |
| --------------------------------------------------------- | ------------------ | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Steam App-ID resolution and German-first normalized patch | API / Backend      | External provider adapter | `SteamHandler` owns Storefront calls and `normalize_steam()` is already pure patch construction. [VERIFIED: codebase, `backend/handler/metadata/steam_handler.py`, `backend/handler/metadata/steam_merge.py`]                                                       |
| Admin and targeted-PC entry-point parity                  | API / Backend      | Database / Storage        | Scan orchestration and explicit candidate selection are backend entry points that must share policy before persistence. [VERIFIED: codebase, `backend/handler/scan_handler.py`, `backend/endpoints/roms/pc_metadata.py`]                                            |
| Provider candidate identity and catalog reconciliation    | Database / Storage | API / Backend             | `RomOwnedMedia` has provider identity, origin, state, and placement persistence, while handlers decide when it may be updated. [VERIFIED: codebase, `backend/models/rom.py`, `backend/handler/database/roms_handler.py`]                                            |
| Downloading provider image bytes                          | API / Backend      | Database / Storage        | The current Phase 20 flow bounds HTTP bytes then stores them through `fs_resource_handler.store_owned_media_image()`. [VERIFIED: codebase, `backend/endpoints/roms/media.py`]                                                                                       |
| Operator inspection and manual selection                  | Browser / Client   | API / Backend             | Existing Media API and v2 Media components consume owned-media catalog and placements; no new UI transport is required. [VERIFIED: context and codebase, `21-CONTEXT.md`, `backend/endpoints/roms/media.py`, `frontend/src/v2/components/GameDetails/MediaTab.vue`] |

## Project Constraints (from AGENTS.md)

- Work in `/home/d1sk/romm`, preserve unrelated dirty worktree changes, and do not access NAS mounts, alter Team4s, use Docker Compose, or write to external source-library paths for this phase. [VERIFIED: repository instructions, `AGENTS.md`, `CLAUDE.md`, `21-CONTEXT.md`]
- Keep backend behavior in handlers, keep endpoints thin, use managed async clients, and use `@begin_session` database handlers rather than ad hoc sessions. [VERIFIED: project skill, `.claude/skills/backend-development/SKILL.md`]
- New backend logic needs focused pytest coverage; use `uv run pytest` and the repository Trunk quality gate, without bypassing hooks. [VERIFIED: repository instructions, `CLAUDE.md`, `.claude/skills/backend-development/SKILL.md`]
- Do not change generated frontend types unless an API schema changes. [VERIFIED: repository instructions, `CLAUDE.md`, `.claude/skills/backend-development/SKILL.md`]

## Standard Stack

### Core

| Library / component                            |                     Version | Purpose                                                 | Why standard                                                                                                                                                                                           |
| ---------------------------------------------- | --------------------------: | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Existing Python handlers and SQLAlchemy models | Python 3.13, SQLAlchemy 2.x | Scan policy, persistence, transaction ownership         | The repository already places scan orchestration in handlers and owned-media state in SQLAlchemy models. [VERIFIED: codebase, `CLAUDE.md`, `backend/handler/scan_handler.py`, `backend/models/rom.py`] |
| Existing Steam Storefront adapter and handler  |   repository implementation | App search, App-ID details, German-first fallback       | `SteamHandler` already gates supported platforms and fetches preferred then fallback details for one App ID. [VERIFIED: codebase, `backend/handler/metadata/steam_handler.py`]                         |
| Existing owned-media catalog                   |   repository implementation | Provider-media identity, state, owned bytes, placements | `RomOwnedMedia` distinguishes provider candidates from uploads and has relational placement state. [VERIFIED: codebase, `backend/models/rom.py`, `backend/handler/database/roms_handler.py`]           |

### Supporting

| Component                                         | Purpose                                                                                                                                                                       | When to use                                                             |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `normalize_steam()`                               | Builds non-empty text/provenance/media patch while respecting manual and Steam-owned display fields. [VERIFIED: codebase, `backend/handler/metadata/steam_merge.py`]          | Every eligible shared Steam enrichment result, before any ORM mutation. |
| `discover_provider_media()`                       | Validates HTTPS URLs and derives canonical provider candidate identity from URL when no native ID exists. [VERIFIED: codebase, `backend/handler/metadata/rom_media.py`]       | Transform Steam cover and screenshots into catalog candidates.          |
| `db_rom_handler.reconcile_provider_owned_media()` | Upserts one provider-owned media row using `(rom_id, provider, provider_media_id)`. [VERIFIED: codebase, `backend/handler/database/roms_handler.py`, `backend/models/rom.py`] | Reuse or extend for scan-driven atomic inventory reconciliation.        |

### Alternatives Considered

| Instead of                                        | Could Use                                                               | Tradeoff                                                                                                                                                                                                                     |
| ------------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shared metadata handler function                  | Duplicate scan and explicit-selection Steam branches                    | Duplication would reintroduce divergent manual/provenance and fallback behavior. [VERIFIED: codebase, `backend/handler/scan_handler.py`, `backend/endpoints/roms/pc_metadata.py`]                                            |
| Owned-media catalog                               | Continue writing Steam URLs to legacy `url_cover` and `url_screenshots` | Legacy URL fields cannot record provider origin, tombstones, owned bytes, or manual placement ownership. [VERIFIED: codebase, `backend/handler/scan_handler.py`, `backend/models/rom.py`, `backend/endpoints/roms/media.py`] |
| Existing managed HTTP client and resource handler | New downloader or source-library writer                                 | Existing code bounds provider image downloads and writes owned resources only. [VERIFIED: codebase, `backend/endpoints/roms/media.py`]                                                                                       |

**Installation:** No external package is required. [VERIFIED: codebase scope, `pyproject.toml`, `21-CONTEXT.md`]

## Architecture Patterns

### System Architecture Diagram

```text
Admin scan                 Targeted PC selection
    |                              |
    +--------- shared pure Steam PC enrichment --------+
                        |                               |
                stored App ID or                    selected App ID
                one eligible name lookup                  |
                        |                               |
                        +---- SteamHandler (de/CH) ------+
                                      |
                         same App ID fallback (en/US)
                                      |
                              normalize_steam()
                                      |
                       normalized text/provenance/media patch
                                      |
             guarded ROM persistence, then candidate reconciliation
                                      |
          owned provider media catalog and unclaimed-surface placement
                                      |
                        existing v2 Media review UI
```

The diagram preserves the established endpoint-to-handler-to-database/filesystem layering and keeps the pure enrichment result separate from persistence. [VERIFIED: codebase, `.planning/codebase/ARCHITECTURE.md`, `backend/handler/scan_handler.py`, `backend/endpoints/roms/pc_metadata.py`]

### Recommended Project Structure

```text
backend/handler/metadata/
  steam_handler.py        # existing locale-aware provider acquisition
  steam_merge.py          # extend only with pure shared PC patch input/output helpers
  rom_media.py            # canonical provider candidate discovery, possibly batch inventory helper
backend/handler/
  scan_handler.py         # invokes shared enrichment, persists scan patch, invokes scan reconciliation
backend/handler/database/
  roms_handler.py         # atomic catalog reconciliation and safe automatic placement
backend/tests/handler/
  test_scan_handler.py    # scan eligibility and text/media patch parity
  database/test_rom_media.py # candidate inventory, tombstone, placement, upload protection
backend/tests/endpoints/
  roms/test_pc_metadata.py # targeted path shares the same policy
```

### Pattern 1: Pure shared enrichment, effectful persistence afterward

**What:** Create a dataclass or TypedDict request containing scan type, ROM snapshot, platform slug, filesystem name, selected sources, and context; return an empty patch on ineligible or failed Steam work. [VERIFIED: context, `21-CONTEXT.md`]

**When to use:** Both automatic `scan_rom()` and the targeted Steam candidate application must call it, but neither helper may write a model directly. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/handler/scan_handler.py`, `backend/endpoints/roms/pc_metadata.py`]

**Implementation shape:**

```python
# Source: repository pattern, backend/handler/scan_handler.py and steam_merge.py
async def resolve_shared_pc_steam_patch(request: SteamScanRequest) -> dict[str, Any]:
    if not request.is_eligible_steam_scan:
        return {}
    details = await resolve_by_persisted_id_or_one_name_lookup(request)
    return normalize_steam(details, request.current) if details else {}
```

The helper should preserve the current stored-ID identity check, exception-to-empty-patch behavior, and `STEAM_PLATFORMS` gating. [VERIFIED: codebase, `backend/handler/scan_handler.py`, `backend/handler/metadata/steam_handler.py`]

### Pattern 2: Complete provider inventory reconciliation after a successful patch

**What:** Convert only validated Steam media URLs into `ProviderMediaCandidate` values, download them to owned storage, then atomically upsert current candidates and tombstone prior Steam candidates absent from that successful inventory. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/handler/metadata/rom_media.py`, `backend/handler/database/roms_handler.py`]

**When to use:** Run only after a valid Steam patch exists and the parent ROM has a durable ID. A failed, malformed, empty, ambiguous, or rate-limited lookup must not invoke the inventory mutation. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/handler/scan_handler.py`]

**Implementation shape:**

```python
# Source: repository pattern, rom_media.py and roms_handler.py
candidates = discover_provider_media("steam", {
    "url_artworks": patch["media"].get("cover", []),
    "url_screenshots": patch["media"].get("screenshots", []),
})
# download each bounded candidate into owned storage, then reconcile complete inventory
```

The current one-item `reconcile_provider_owned_media()` neither receives a complete candidate set nor tombstones disappeared rows, so Phase 21 needs a batch/transactional variant or an explicitly named companion method. [VERIFIED: codebase, `backend/handler/database/roms_handler.py`]

### Pattern 3: Placement is opt-in only for unclaimed compatible surfaces

**What:** In the same locked ROM transaction, inspect `owned_media_placements`; add a preferred Steam artwork to `OVERVIEW` only when no overview placement exists, and add Steam screenshots to `BACKGROUND` only when no background placement exists. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/models/rom.py`, `backend/handler/database/roms_handler.py`]

**When to use:** Only for newly reconciled active Steam candidates. Never call `replace_owned_media_placements()` for an existing surface during a scan because that method replaces ordering. [VERIFIED: codebase, `backend/handler/database/roms_handler.py`]

### Anti-Patterns to Avoid

- **Reusing `_steam_artwork_handler()` as the media persistence contract:** It maps candidate URLs to legacy display fields and loses catalog-level provider identity. [VERIFIED: codebase, `backend/handler/scan_handler.py`]
- **Calling the HTTP route helper from scan orchestration:** `_download_provider_image()` is endpoint-private and scan behavior belongs in handlers. [VERIFIED: codebase, `backend/endpoints/roms/media.py`, `.claude/skills/backend-development/SKILL.md`]
- **Clearing Steam media on an empty patch:** Empty output is the failure-isolation signal, not a declaration of an empty remote inventory. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/handler/scan_handler.py`]
- **Using `replace_owned_media_placements()` for automatic scan placement:** It requires membership equality and deletes/rebuilds a surface ordering. [VERIFIED: codebase, `backend/handler/database/roms_handler.py`]
- **Touching IGDB component/DLC enrichment:** That path is intentionally IGDB-first and must remain outside parent Steam scan parity. [VERIFIED: context, `18-CONTEXT.md`, `19-CONTEXT.md`, `backend/endpoints/sockets/scan.py`]

## Don't Hand-Roll

| Problem                     | Don't Build                                        | Use Instead                                                | Why                                                                                                                                                                                       |
| --------------------------- | -------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Steam locale fallback       | A second title search or manual localization merge | `SteamHandler.get_rom_by_id()` and `normalize_steam()`     | The handler already requests German first and only fetches English details for the same App ID when fields are missing. [VERIFIED: codebase, `backend/handler/metadata/steam_handler.py`] |
| Provider URL identity       | Ad hoc URL comparison                              | `normalize_provider_url()` and `discover_provider_media()` | The existing code normalizes HTTPS origin/path/query and hashes a canonical URL when the provider has no native ID. [VERIFIED: codebase, `backend/handler/metadata/rom_media.py`]         |
| Owned-media storage         | Direct filesystem writes or source-library paths   | `fs_resource_handler.store_owned_media_image()`            | Existing media refresh writes bounded downloaded bytes to owned storage. [VERIFIED: codebase, `backend/endpoints/roms/media.py`]                                                          |
| Optimistic catalog mutation | New raw SQL                                        | `DBRomsHandler` locked media methods                       | The existing methods lock the ROM and use `expected_updated_at` for state consistency. [VERIFIED: codebase, `backend/handler/database/roms_handler.py`]                                   |

## Common Pitfalls

### Pitfall 1: Complete scans erase legacy media before Phase 21 reconciliation

**What goes wrong:** `_identify_rom()` removes legacy resource files for a complete rescan, and `scan_rom()` resets legacy URL/path fields before provider priority is applied. [VERIFIED: codebase, `backend/endpoints/sockets/scan.py`, `backend/handler/scan_handler.py`]

**How to avoid:** Keep Phase 21 owned-media catalog reconciliation independent of legacy resource cleanup, and verify that no owned upload or manual placement is touched by `complete`. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/models/rom.py`]

### Pitfall 2: Existing scan selection prevents Steam update from running

**What goes wrong:** `should_scan_rom()` admits `UPDATE` based on selected metadata-source IDs, with a special IGDB-recovery condition, so Steam-only existing records need an explicit parity eligibility test. [VERIFIED: codebase, `backend/endpoints/sockets/scan.py`]

**How to avoid:** Add tests for an existing Steam-identified Windows, Linux, and macOS record under `UPDATE` and `COMPLETE`, and adjust selection only as narrowly as necessary. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/endpoints/sockets/scan.py`]

### Pitfall 3: Manual protection is broader than the initial merge constants

**What goes wrong:** `normalize_steam()` currently declares only name, summary, and release date as `MANUAL_FIELDS`, while the Phase 21 decision also protects manual developer and publisher values. [VERIFIED: codebase, `backend/handler/metadata/steam_merge.py`; context, `21-CONTEXT.md`]

**How to avoid:** Audit the actual `manual_metadata` representation and extend the pure merge contract plus tests for developer and publisher before wiring persistence. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/handler/metadata/steam_merge.py`]

### Pitfall 4: Tombstoning can accidentally mean deletion

**What goes wrong:** The catalog supports `ACTIVE` and `TOMBSTONED`, but current explicit refresh reactivates a previously deleted provider row. [VERIFIED: codebase, `backend/models/rom.py`, `backend/handler/database/roms_handler.py`, `backend/tests/handler/database/test_rom_media.py`]

**How to avoid:** Define the scan batch operation to tombstone only stale Steam-origin provider rows, never upload-origin rows, and never restore an operator-deleted candidate on an ordinary scan if Phase 20's normal-refresh rule applies. [VERIFIED: context, `20-CONTEXT.md`, `21-CONTEXT.md`]

### Pitfall 5: Text patch success and media download failure have different blast radii

**What goes wrong:** A valid Steam text patch may be available even when a candidate image cannot be downloaded. [VERIFIED: codebase, `backend/handler/metadata/steam_merge.py`, `backend/endpoints/roms/media.py`]

**How to avoid:** Persist guarded text/provenance independently, catch candidate-level media failures, and do not tombstone an existing inventory unless the corresponding complete Steam inventory was successfully acquired and reconciled. [VERIFIED: context, `21-CONTEXT.md`]

## Code Examples

### Existing same-App-ID locale fallback

```python
# Source: backend/handler/metadata/steam_handler.py
preferred = await self.steam_service.get_app_details(
    steam_id, country=STEAM_API_COUNTRY, language=STEAM_API_LANGUAGE
)
if self._needs_fallback(preferred):
    fallback = await self.steam_service.get_app_details(
        steam_id,
        country=STEAM_API_FALLBACK_COUNTRY,
        language=STEAM_API_FALLBACK_LANGUAGE,
    )
```

This is the required localization primitive. [VERIFIED: codebase, `backend/handler/metadata/steam_handler.py`]

### Existing guarded scan lookup

```python
# Source: backend/handler/scan_handler.py
if isinstance(rom.steam_id, int) and not isinstance(rom.steam_id, bool):
    result = await meta_steam_handler.get_rom_by_id(rom.steam_id, platform.slug)
    if result.get("steam_id") != rom.steam_id:
        return {}
elif platform.slug in STEAM_PLATFORMS:
    result = await meta_steam_handler.get_rom(fs_name, platform.slug)
else:
    return {}
```

Keep this persisted-ID-first rule in the new shared boundary. [VERIFIED: codebase, `backend/handler/scan_handler.py`]

## Assumptions Log

| #    | Claim                                                                                       | Section | Risk if Wrong                                                                                    |
| ---- | ------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------ |
| None | All recommendations are derived from Phase 21 locked decisions and the checked-in codebase. | All     | No unverified package or external-service assumption is needed. [VERIFIED: codebase and context] |

## Open Questions

1. **What exact database state distinguishes an operator-deleted provider candidate from a scan-tombstoned candidate?**
   - What we know: the model exposes only `active` and `tombstoned`, and current explicit refresh reactivates a deleted candidate. [VERIFIED: codebase, `backend/models/rom.py`, `backend/handler/database/roms_handler.py`]
   - What's unclear: whether Phase 20 introduced a separate deletion-intent marker outside this model. [VERIFIED: codebase search, `backend/models/rom.py`, `backend/handler/database/roms_handler.py`]
   - Recommendation: planner must make the expected ordinary-scan behavior explicit and add a regression test before implementing batch tombstoning. [VERIFIED: context, `20-CONTEXT.md`, `21-CONTEXT.md`]

2. **Which concrete targeted-ROM action is the parity counterpart?**
   - What we know: `select_pc_metadata_candidate()` rehydrates a selected Steam candidate and separately invokes `normalize_steam()`. [VERIFIED: codebase, `backend/endpoints/roms/pc_metadata.py`]
   - What's unclear: whether D-01 expects that endpoint or a different targeted scan command to adopt the extracted shared request object. [VERIFIED: context, `21-CONTEXT.md`]
   - Recommendation: planner should identify that call site in its first implementation task and retain its public API behavior. [VERIFIED: codebase, `backend/endpoints/roms/pc_metadata.py`]

## Environment Availability

| Dependency            | Required By                     | Available   | Version                                                                                                                  | Fallback                                                                                    |
| --------------------- | ------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Python / uv           | Focused backend tests           | ✓           | Installed in canonical checkout environment. [VERIFIED: codebase environment inspection]                                 | None                                                                                        |
| MariaDB test database | ORM-backed media and scan tests | ✗           | No reachable test database was available during prior integration verification. [VERIFIED: prior execution evidence]     | Unit tests with mocks, then CI or authorized test environment for database-backed coverage. |
| Steam Storefront      | Runtime metadata acquisition    | Not invoked | External calls are mocked in focused tests. [VERIFIED: codebase, `backend/tests/handler/metadata/test_steam_handler.py`] | Empty patch on provider failure.                                                            |

## Validation Architecture

### Test Framework

| Property             | Value                                                                                                                                                                                                                                                                        |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framework            | pytest 9.x with pytest-asyncio. [VERIFIED: codebase, `pyproject.toml`, `backend/pytest.ini`]                                                                                                                                                                                 |
| Config file          | `backend/pytest.ini`, async mode is automatic and test root is `backend/tests`. [VERIFIED: codebase, `backend/pytest.ini`]                                                                                                                                                   |
| Quick run command    | `cd backend && uv run pytest tests/handler/test_scan_handler.py tests/handler/metadata/test_steam_handler.py tests/handler/metadata/test_steam_merge.py -x`                                                                                                                  |
| Full focused command | `cd backend && uv run pytest tests/handler/test_scan_handler.py tests/handler/metadata/test_steam_handler.py tests/handler/metadata/test_steam_merge.py tests/handler/database/test_rom_media.py tests/endpoints/roms/test_media.py tests/endpoints/sockets/test_scan.py -x` |

### Phase Requirements to Test Map

| Locked behavior                                                                    | Test type                 | Automated command / location                                                         | File exists?                                                                                                   |
| ---------------------------------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Stored ID first, German-first same-ID fallback, platform gate, empty failure patch | async unit                | `tests/handler/test_scan_handler.py`, `tests/handler/metadata/test_steam_handler.py` | Existing, expand for shared boundary. [VERIFIED: codebase]                                                     |
| Manual text and Steam provenance refresh                                           | unit                      | `tests/handler/metadata/test_steam_merge.py`                                         | Existing, expand developer/publisher protection. [VERIFIED: codebase]                                          |
| New, update, complete scan-path parity                                             | async handler/integration | `tests/handler/test_scan_handler.py`                                                 | Existing scan fixture helper, new cases required. [VERIFIED: codebase]                                         |
| Provider inventory idempotency, tombstone, upload protection, automatic placement  | database handler          | `tests/handler/database/test_rom_media.py`                                           | Existing catalog tests, new batch and placement cases required. [VERIFIED: codebase]                           |
| Targeted selection shares normalized patch                                         | endpoint unit             | `tests/endpoints/roms/test_pc_metadata.py`                                           | Verify file and add focused cases in Wave 0. [VERIFIED: codebase path inspection]                              |
| Browser UAT with isolated Witcher fixture and no source mutation                   | manual                    | Existing v2 Media surface plus `tests/integration/test_scan_source_immutability.py`  | Automated source-boundary test exists; browser scenario is required manually. [VERIFIED: context and codebase] |

### Sampling Rate

- **Per task commit:** Run the smallest changed pytest module with `-x`. [VERIFIED: project convention, `.claude/skills/backend-development/SKILL.md`]
- **Per wave merge:** Run the full focused command above. [VERIFIED: research recommendation based on existing tests]
- **Phase gate:** Run `trunk check` and the focused backend suite; complete database-backed coverage only in an authorized environment with MariaDB. [VERIFIED: repository instructions, `CLAUDE.md`; prior execution evidence]

### Wave 0 Gaps

- [ ] `backend/tests/handler/test_scan_handler.py`: add a single shared-boundary parity fixture for new, update, complete, and targeted routes.
- [ ] `backend/tests/handler/metadata/test_steam_merge.py`: cover manual developer and publisher metadata fields.
- [ ] `backend/tests/handler/database/test_rom_media.py`: cover successful inventory diff/tombstone, ordinary failure no-op, uploads untouched, and unclaimed-only placements.
- [ ] `backend/tests/endpoints/roms/test_pc_metadata.py`: establish the targeted selection parity assertion if no equivalent exists.

## Security Domain

### Applicable ASVS Categories

| ASVS Category       | Applies               | Standard Control                                                                                                                                                                                                                                        |
| ------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| V4 Access Control   | No new route expected | Preserve existing protected Media and PC metadata endpoints. [VERIFIED: codebase, `backend/endpoints/roms/media.py`, `backend/endpoints/roms/pc_metadata.py`]                                                                                           |
| V5 Input Validation | Yes                   | Accept only provider-origin HTTPS URLs through `normalize_provider_url()`, validate media limits, and retain ORM constraints. [VERIFIED: codebase, `backend/handler/metadata/rom_media.py`, `backend/endpoints/roms/media.py`, `backend/models/rom.py`] |
| V6 Cryptography     | No new cryptography   | Use existing SHA-256 URL identity helper, not new cryptographic protocol logic. [VERIFIED: codebase, `backend/handler/metadata/rom_media.py`]                                                                                                           |

### Known Threat Patterns

| Pattern                             | STRIDE    | Standard Mitigation                                                                                                                                                                                  |
| ----------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Provider URL SSRF or unsafe scheme  | Tampering | Restrict candidates to canonical HTTPS URLs and use existing managed client/resource storage flow. [VERIFIED: codebase, `backend/handler/metadata/rom_media.py`, `backend/endpoints/roms/media.py`]  |
| Source-library mutation during scan | Tampering | Keep all downloaded media in owned storage and retain storage-operation boundary tests. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/tests/integration/test_scan_source_immutability.py`] |
| Manual media override loss          | Tampering | Add only to empty placement surfaces and do not call replacement/reordering APIs from scans. [VERIFIED: context, `21-CONTEXT.md`; codebase, `backend/handler/database/roms_handler.py`]              |

## Sources

### Primary (HIGH confidence)

- [Phase 21 context](21-CONTEXT.md) and [approved design](../../../../docs/superpowers/specs/2026-09-29-admin-pc-scan-steam-parity-design.md), locked behavior and exclusions.
- `backend/handler/scan_handler.py`, current automatic PC scan, Steam resolution, provider application, and complete-scan behavior.
- `backend/handler/metadata/steam_handler.py` and `backend/handler/metadata/steam_merge.py`, localized Steam details and guarded patch semantics.
- `backend/handler/metadata/rom_media.py`, `backend/models/rom.py`, and `backend/handler/database/roms_handler.py`, provider candidate identity, owned-media model, catalog mutation, and placements.
- `backend/endpoints/roms/media.py` and `backend/endpoints/roms/pc_metadata.py`, existing operator and targeted-PC persistence seams.
- `backend/tests/handler/test_scan_handler.py`, `backend/tests/handler/metadata/test_steam_handler.py`, `backend/tests/handler/metadata/test_steam_merge.py`, and `backend/tests/handler/database/test_rom_media.py`, existing regression patterns.

### Secondary (MEDIUM confidence)

- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/INTEGRATIONS.md`, and `.planning/codebase/STACK.md`, repository architectural and tooling summaries.
- `.claude/skills/backend-development/SKILL.md`, backend layering and validation conventions.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, all required components already exist in the checked-in repository.
- Architecture: HIGH, the automatic scan, targeted selection, and media catalog seams were inspected directly.
- Pitfalls: HIGH, they follow direct mismatches between the locked Phase 21 design and current code paths.

**Research date:** 2026-09-30
**Valid until:** 2026-10-30, unless the scan or owned-media seams change.
