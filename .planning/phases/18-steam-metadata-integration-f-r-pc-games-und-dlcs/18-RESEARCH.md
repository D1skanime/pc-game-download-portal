# Phase 18: Steam Metadata Integration for PC Games and DLCs - Research

**Researched:** 2026-09-25  
**Domain:** Steam Storefront metadata in the RomM PC metadata pipeline  
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- Add MetadataSource.STEAM as an independent provider. Retain sgdb for SteamGridDB without rename or behavior changes.
- Port upstream Steam service, typed payloads, handler, registration, enable flag, heartbeat, priority integration, schemas, and tests. No scraper and no API key.
- Use STEAM_API_ENABLED=false by default, preferred de/CH, and configurable fallback en/US.
- Automatic name search is limited to win, linux, and mac. dos, win3x, and win9x resolve an explicit valid App ID only. Classic ROM platforms never call Steam.
- Persist nullable steam_id and JSON steam_metadata on Rom and RomComponentMetadata without global component-App-ID uniqueness.
- Existing steam_id values refresh strictly by ID, including after filename changes, never by rematch.
- German details load first. English fallback fetches only the same resolved App ID and fills only missing fields. It never performs a second name search.
- Empty, malformed, unavailable, or rate-limited Steam data is non-fatal and cannot clear existing data.
- Automatic scans and selected Steam candidates use one normalized application and field-merge function.
- Steam may provide localized title, summary, developer, publisher, release, and media candidates. It does not replace IGDB themes, franchise, related games, or DLC relationships.
- Steam media enters existing artwork selection only and cannot replace selected or manually overridden artwork.
- Manual title, summary, release date, and selected artwork are independently protected.
- Preserve all existing IGDB expansion/DLC discovery, enrichment, and unique related-candidate logic.
- Only one hydrated IGDB-resolved DLC identity may trigger Steam DLC lookup.
- Reject bundles, soundtracks, demos, editions, tools, and unrelated products. A Steam parent relation must match the parent App ID. Without a parent relation, apply only a unique high-confidence result tied to the resolved IGDB identity.
- Ambiguous, invalid, unmatched, or parent-mismatched DLCs preserve IGDB metadata and never create components.
- Register Steam in provider, priority, heartbeat, scan, serialization, and v2 display locations without regressing current providers.
- Log provider, platform, query, App ID, language, confidence, and fallback outcome without secrets or payloads.
- Test localization, ID refresh, platform gating, failure isolation, manual protection, non-empty merge, DLC safety, persistence, duplication prevention, and classic-ROM non-regression.

### the agent's Discretion

- Keep upstream code close; isolate fork behavior in localization, PC merge, and component/DLC integration.

### Deferred Ideas (OUT OF SCOPE)

- Translation of non-Steam metadata, Steam login, ownership/library sync, downloads, installations, achievements, cloud, and generic matching framework work are outside Phase 18.
  </user_constraints>

## Project Constraints (from AGENTS.md)

- Use the canonical Linux checkout at `/home/d1sk/romm`; preserve unrelated worktree changes. [VERIFIED: AGENTS.md, CLAUDE.md]
- Backend changes follow FastAPI endpoint-to-handler layering, SQLAlchemy 2, Alembic portability across MariaDB/MySQL/PostgreSQL, `uv`, pytest, and Trunk. API schema changes require generated frontend types and typecheck. [VERIFIED: `.claude/skills/backend-development/SKILL.md`]
- New visible v2 work belongs below `frontend/src/v2/`, uses canonical shared resources, locale keys for user-visible text, universal input, and token-based theming. [VERIFIED: CLAUDE.md, `.claude/skills/frontend-v2-*/SKILL.md`]
- New logic requires tests; migrations require upgrade and downgrade verification; never bypass hooks. [VERIFIED: CLAUDE.md, `.claude/skills/pre-pr-verification/SKILL.md`]

## Summary

The fork already has an uncommitted localized Steam adapter, typed payloads, handler, configuration, basic migration, provider enum, heartbeat and narrow tests. The central PC paths do not yet consume Steam: `PcMetadataMatchHandler` has no Steam provider, its candidate allowlist omits `steam_id` and `steam_metadata`, scan collection does not fetch it, and the component writer does not persist its fields. [VERIFIED: codebase grep and `backend/adapters/services/steam.py`, `backend/handler/metadata/steam_handler.py`, `backend/handler/metadata/pc_match_handler.py`, `backend/handler/scan_handler.py`, `backend/handler/database/roms_handler.py`]

The safest plan is a four-part sequence: harden and complete the upstream-compatible provider boundary, complete portable persistence and response/schema wiring, add one guarded normalizer for both automatic and manual PC main-game application, then add an IGDB-first DLC-only enrichment adapter. The normalizer must be the sole place that writes Steam-derived display fields, while IGDB remains authoritative for its relationship graph and manual/selected assets remain authoritative. [VERIFIED: `18-CONTEXT.md`, approved Steam design and implementation plan]

**Primary recommendation:** Keep the service and handler close to current upstream, but implement Steam's fork-specific localization, merge, and DLC checks as small explicit helpers with isolated tests before wiring them into scans. [VERIFIED: current upstream `origin/master` Steam provider, `18-CONTEXT.md`]

## Architectural Responsibility Map

| Capability                                                   | Primary Tier       | Secondary Tier            | Rationale                                                                                                                                                                                                                              |
| ------------------------------------------------------------ | ------------------ | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Storefront lookup, locale fallback, rate degradation         | API / Backend      | External Steam service    | Credentials are unnecessary and outbound requests must be bounded and failure-isolated. [VERIFIED: `backend/adapters/services/steam.py`, `backend/handler/metadata/steam_handler.py`]                                                  |
| Provider enablement, priority, heartbeat and scan scheduling | API / Backend      | Frontend settings display | The backend owns provider availability and scan behavior; v2 only shows configured provider state. [VERIFIED: `backend/config/config_manager.py`, `backend/endpoints/heartbeat.py`, `frontend/src/v2/views/Settings/ScanSettings.vue`] |
| Steam ID and provider payload persistence                    | Database / Storage | API / Backend             | IDs and JSON metadata belong on `Rom` and `RomComponentMetadata`; schema changes need Alembic. [VERIFIED: `backend/models/rom.py`, `backend/alembic/versions/0119_add_steam_metadata.py`]                                              |
| Main-game application and manual protection                  | API / Backend      | Database / Storage        | Existing update and selected-candidate paths own writes and optimistic version checks. [VERIFIED: `backend/handler/database/roms_handler.py`, `backend/endpoints/roms/pc_metadata.py`]                                                 |
| DLC identity and Steam enrichment                            | API / Backend      | Database / Storage        | IGDB relationship resolution occurs server-side and components must never be created by metadata results. [VERIFIED: `backend/handler/metadata/pc_match_handler.py`, `backend/endpoints/sockets/scan.py`]                              |
| Provider labels and metadata display                         | Browser / Client   | API / Backend             | Labels and links are v2 presentation data driven by heartbeat/OpenAPI output. [VERIFIED: `frontend/src/v2/components/GameDetails/providers.ts`, `frontend/src/v2/views/Settings/MetadataSources.vue`]                                  |

## Standard Stack

### Core

| Library / facility                        |         Version | Purpose                                                 | Why standard                                                                                                                                             |
| ----------------------------------------- | --------------: | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python, `aiohttp`, existing `RateLimiter` | project-managed | Steam Storefront HTTP transport, timeout and throttling | Existing provider adapters use the context-bound aiohttp session and limiter. [VERIFIED: `backend/adapters/services/steam.py`, `backend/pyproject.toml`] |
| SQLAlchemy 2 + Alembic                    | project-managed | provider ID/JSON persistence and portable migration     | Repository-standard ORM and migration path. [VERIFIED: CLAUDE.md, `.claude/skills/backend-development/SKILL.md`]                                         |
| FastAPI/Pydantic + generated TypeScript   | project-managed | expose persisted Steam fields to v2                     | Backend response schemas are the OpenAPI source of truth. [VERIFIED: CLAUDE.md, `backend/endpoints/responses/rom.py`]                                    |
| pytest + pytest-asyncio                   | 9.0.3 installed | provider, merge, migration and endpoint tests           | Existing backend test infrastructure. [VERIFIED: `uv run pytest --version`, `.claude/skills/backend-development/SKILL.md`]                               |

### Supporting

| Facility                             | Purpose                                 | When to use                                                                                                                                                                       |
| ------------------------------------ | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Existing PC metadata candidate model | reviewable manual provider choices      | Add Steam as a provider without a parallel manual-selection flow. [VERIFIED: `backend/handler/metadata/pc_match_handler.py`, `backend/endpoints/roms/pc_metadata.py`]             |
| Existing owned-media/artwork policy  | artwork candidate storage and selection | Feed Steam media through it, never direct-write selected cover/screenshot fields. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`, `backend/handler/database/roms_handler.py`] |

**Installation:** none. This phase adds no package. [VERIFIED: approved implementation plan and current `backend/pyproject.toml`]

## Package Legitimacy Audit

Not applicable: no external package installation is planned. [VERIFIED: approved implementation plan]

## Architecture Patterns

### System Architecture Diagram

```text
scan / manual PC selection
        |
        v
provider registry + platform gate
        |                 |
        |                 +--> non-PC or excluded PC without ID -> no Steam request
        v
SteamHandler: search once OR stored-ID lookup
        |
        v
SteamService: de/CH details -> missing text? -> en/US details for SAME app ID
        |
        v
normalized Steam application
        |
        +--> main game: guarded field merge -> Rom + artwork candidate policy
        |
        +--> DLC: exactly one hydrated IGDB relationship -> typed/parent/confidence gate
                                                   |                  |
                                                   | reject           +--> guarded component merge
                                                   v
                                             preserve IGDB state
```

### Recommended Project Structure

```text
backend/
├── adapters/services/steam.py, steam_types.py       # upstream-close transport/payloads
├── handler/metadata/steam_handler.py                # lookup and locale normalization
├── handler/metadata/steam_merge.py                  # fork-specific guarded merge helpers
├── handler/metadata/pc_match_handler.py             # manual candidates, IGDB-first DLC identity
├── handler/scan_handler.py                           # registry and ID-refresh scan seam
├── handler/database/roms_handler.py                 # optimistic persistence only
├── endpoints/roms/pc_metadata.py                    # existing review-first selection endpoint
└── tests/...                                        # adapter, handler, model, endpoint coverage
```

### Pattern 1: Stored ID wins over a later filename

**What:** On update, and on incomplete unmatched metadata, call `get_rom_by_id(existing_steam_id)` rather than a name search. [VERIFIED: current upstream `origin/master:backend/handler/scan_handler.py` `resolve_steam_rom`]

**When to use:** Every persisted Steam refresh, including filename rename. Explicit IDs on `dos`, `win3x`, and `win9x` may use the direct lookup; name search remains limited to `win`, `linux`, and `mac`. [VERIFIED: `18-CONTEXT.md`, `backend/handler/metadata/steam_handler.py`]

### Pattern 2: Same-ID locale fallback, field by field

**What:** Fetch preferred `de/CH`; only if text is absent, fetch configured fallback `en/US` using the already resolved App ID. Choose each non-empty field individually, never re-search. [VERIFIED: `backend/handler/metadata/steam_handler.py`, `backend/tests/handler/metadata/test_steam_handler.py`]

**Anti-patterns to avoid**

- **Fallback name search:** can select another product and violates identity preservation. [VERIFIED: `18-CONTEXT.md`]
- **Generic provider-map application:** scan priority merging treats all non-empty provider fields alike and cannot encode manual field protection or IGDB relationship ownership. [VERIFIED: `backend/handler/scan_handler.py`, `18-CONTEXT.md`]
- **DLC lookup from a folder title alone:** a component name is not a sufficient identity proof and can bind unrelated store merchandise. [VERIFIED: `18-CONTEXT.md`, `backend/handler/metadata/pc_match_handler.py`]

## Don't Hand-Roll

| Problem                   | Don't build                                 | Use instead                                              | Why                                                                                                                                                                         |
| ------------------------- | ------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HTTP session lifecycle    | a per-call HTTP client                      | `ctx_aiohttp_session`                                    | Existing adapters share lifecycle and request controls. [VERIFIED: `backend/adapters/services/steam.py`]                                                                    |
| Request pacing/retries    | a second custom limiter                     | existing `RateLimiter` and Steam adapter retry policy    | One provider-specific rate policy is already implemented. [VERIFIED: `backend/adapters/services/steam.py`]                                                                  |
| Manual PC candidate API   | a Steam-only endpoint                       | `PcMetadataMatchHandler` + existing selection route      | Maintains review, authorization and optimistic concurrency conventions. [VERIFIED: `backend/handler/metadata/pc_match_handler.py`, `backend/endpoints/roms/pc_metadata.py`] |
| Asset overwrite semantics | direct writes to `path_cover_*`/screenshots | existing selected/owned-media and artwork priority paths | Direct writes could bypass selected/manual artwork protection. [VERIFIED: `backend/handler/scan_handler.py`, `backend/endpoints/roms/pc_metadata.py`]                       |

## Common Pitfalls

### Pitfall 1: Steam provider registry drift

**What goes wrong:** Steam is added to the enum but absent from watcher, scan fetch map, config allowlist, heartbeat, response schema, candidate UI, or display-provider table. [VERIFIED: `backend/handler/scan_handler.py`, `backend/watcher.py`, `backend/endpoints/heartbeat.py`, `frontend/src/v2/components/GameDetails/providers.ts`]

**How to avoid:** Treat registration as a checklist and test enum equality with `VALID_SCAN_PRIORITY_SOURCES`, heartbeat output and v2 labels. [VERIFIED: `backend/config/config_manager.py`, `backend/tests/config/test_config_loader.py`]

### Pitfall 2: Provider outage destroys a usable match

**What goes wrong:** a Steam exception, `429`, malformed JSON, region miss, or empty response replaces prior IGDB/Moby/LaunchBox data or fails the whole scan. [VERIFIED: `backend/adapters/services/steam.py`, `backend/handler/scan_handler.py`, `18-CONTEXT.md`]

**How to avoid:** convert Steam failure to `SteamRom(steam_id=None)` at the provider seam and apply only non-empty normalized fields. Keep other gather results and existing persisted values intact. [VERIFIED: current provider fallback pattern in `backend/handler/scan_handler.py`, `18-CONTEXT.md`]

### Pitfall 3: component merge drops Steam data or IGDB structure

**What goes wrong:** current component persistence only copies IGDB/Moby/SGDB/LaunchBox IDs and stores provider metadata wholesale, while IGDB-specific structured fields overwrite component fields. [VERIFIED: `backend/handler/database/roms_handler.py`]

**How to avoid:** add Steam fields deliberately, preserve existing values when Steam has no non-empty replacement, and never write themes or relationships from Steam. [VERIFIED: `18-CONTEXT.md`]

### Pitfall 4: migration/facet mismatch

**What goes wrong:** adding `Rom.steam_id` without its `RomFacets` mirror and response/serialization path produces stale provider coverage or invisible metadata. [VERIFIED: `backend/models/rom.py`, `backend/alembic/versions/0119_add_steam_metadata.py`]

**How to avoid:** model, migration, facet mirror, source maps, schemas and generated frontend types move together; verify upgrade and downgrade on supported dialects. [VERIFIED: `.claude/skills/backend-development/SKILL.md`]

## State of the Art

| Old approach                                                  | Current approach                                                            | Impact                                                                                                                                                |
| ------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Upstream Steam handler uses one locale and generic scan merge | Fork requires German-first, same-App-ID fallback and field-guarded PC merge | Port transport concepts, isolate fork policy. [VERIFIED: current upstream `origin/master:backend/handler/metadata/steam_handler.py`, `18-CONTEXT.md`] |
| Existing automatic DLC import is IGDB-only                    | Steam can enrich only after unique hydrated IGDB identity                   | Retain IGDB discovery and add a narrow Steam enrichment stage. [VERIFIED: `backend/endpoints/sockets/scan.py`, `18-CONTEXT.md`]                       |

## Assumptions Log

| #   | Claim                                                                                                                                   | Section        | Risk if Wrong                                                                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------- |
| A1  | Steam Storefront parent relation will be available in a stable typed field for enough DLC results to enforce it when present. [ASSUMED] | DLC enrichment | The parser may need to tolerate alternate/missing Storefront shapes; tests must cover absent-parent fallback. |
| A2  | No new locale key is required if Steam is only surfaced via provider labels and existing settings components. [ASSUMED]                 | v2 display     | New provider copy may require all locale files and i18n checks.                                               |

## Open Questions

1. **Which exact Storefront details field encodes a DLC's parent App ID?**
   - What we know: the approved scope requires parent equality when Storefront exposes it, and current local typed payload has `fullgame`. [VERIFIED: `18-CONTEXT.md`, `backend/adapters/services/steam_types.py`]
   - What's unclear: the response shape for every DLC/region. [ASSUMED]
   - Recommendation: parse defensively into an optional typed parent ID; fixture tests must include present, absent and malformed parent data. [VERIFIED: `18-CONTEXT.md`]

2. **What is the established manual-field provenance representation?**
   - What we know: ordinary scan update preservation uses existing model values and selected cover paths, but there is no general `manual_fields` abstraction in the inspected PC writer. [VERIFIED: `backend/handler/scan_handler.py`, `backend/handler/database/roms_handler.py`]
   - Recommendation: planner must identify the live manual metadata/source semantics before implementing a normalizer, then test title, summary, release and artwork independently. [VERIFIED: `18-CONTEXT.md`]

## Environment Availability

| Dependency       | Required By                      |                                                   Available | Version                   | Fallback                                                                                                  |
| ---------------- | -------------------------------- | ----------------------------------------------------------: | ------------------------- | --------------------------------------------------------------------------------------------------------- |
| `uv`             | backend tests/migrations         |                                                         yes | 0.12.3                    | none needed. [VERIFIED: local command]                                                                    |
| pytest           | backend validation               |                                                         yes | 9.0.3                     | none needed. [VERIFIED: `uv run pytest --version`]                                                        |
| Node/npm         | generated types and v2 typecheck |                                                         yes | Node 24.19.0, npm 11.17.0 | none needed. [VERIFIED: local command]                                                                    |
| Trunk            | formatting/static validation     |                                                         yes | 1.25.0                    | none needed. [VERIFIED: local command]                                                                    |
| Docker           | DB-backed migration checks       |                                                         yes | 29.6.2                    | use project test environment. [VERIFIED: local command]                                                   |
| Steam Storefront | live metadata                    | externally available, not required for automated unit tests | undocumented interface    | mocked responses and failure degradation. [VERIFIED: `backend/adapters/services/steam.py`, approved plan] |

## Validation Architecture

### Test Framework

| Property             | Value                                                                                                                                                                                                                                                                                         |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framework            | pytest 9.0.3, pytest-asyncio, mocked aiohttp; Vitest 5.9.3 for any v2 change. [VERIFIED: local commands, repository tests]                                                                                                                                                                    |
| Config               | `backend/pyproject.toml`, `frontend/package.json`. [VERIFIED: repository files]                                                                                                                                                                                                               |
| Quick run            | `cd backend && uv run pytest tests/adapters/services/test_steam.py tests/handler/metadata/test_steam_handler.py tests/models/test_pc_igdb_metadata.py tests/endpoints/roms/test_pc_metadata.py tests/endpoints/sockets/test_scan.py -q`                                                       |
| Full relevant checks | backend subset, `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`, `trunk fmt && trunk check`; then `cd frontend && npm run generate && npm run typecheck` if OpenAPI changed. [VERIFIED: CLAUDE.md, `.claude/skills/pre-pr-verification/SKILL.md`] |

### Phase Behaviors -> Test Map

| Behavior                                                                       | Test type                      | Automated command / location                                                            | Status                                                                      |
| ------------------------------------------------------------------------------ | ------------------------------ | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| de/CH query and same-ID fallback                                               | adapter/handler unit           | `tests/adapters/services/test_steam.py`, `tests/handler/metadata/test_steam_handler.py` | Partial, existing. [VERIFIED: files]                                        |
| timeout, 429, malformed and unavailable isolation                              | adapter + scan unit            | extend Steam tests and scan resolver tests                                              | Gap. [VERIFIED: approved plan, existing sparse Steam tests]                 |
| platform gate plus ID refresh after rename                                     | scan/handler unit              | new `test_resolve_steam_rom.py`                                                         | Gap. [VERIFIED: current upstream resolver, `18-CONTEXT.md`]                 |
| provider registry, priority, watcher, heartbeat                                | config/endpoint unit           | `test_config_loader.py`, `test_heartbeat.py`, scan-priority tests                       | Gap. [VERIFIED: codebase registry paths]                                    |
| persistence, no component App-ID uniqueness and reversible migration           | model/migration                | `test_pc_igdb_metadata.py`, Alembic commands                                            | Partial. [VERIFIED: existing model assertion, `0119` migration]             |
| manual-safe non-empty main merge and artwork preservation                      | focused merge unit             | new `test_steam_merge.py`                                                               | Gap. [VERIFIED: approved plan]                                              |
| unique IGDB identity, invalid types, parent mismatch and no component creation | DLC handler/scan unit          | extend PC matcher and socket scan tests                                                 | Gap. [VERIFIED: `backend/endpoints/sockets/test_scan.py`, `18-CONTEXT.md`]  |
| Steam manual candidate and provider label/display                              | endpoint/v2 test and typecheck | PC metadata endpoint tests, v2 relevant component tests                                 | Gap. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`, v2 provider files] |

### Wave 0 Gaps

- [ ] Add test fixtures covering localized normal and partial payloads, malformed payload, `429`, region miss, game, DLC, bundle, soundtrack, demo, edition and tool.
- [ ] Add a test seam around `resolve_steam_rom` and normalized merge, rather than relying on broad scan tests.
- [ ] Add DLC parent relation and confidence fixtures, including absent parent and ambiguous candidates.
- [ ] Add frontend provider-label/display test only if the v2 surfaces change, and regenerate OpenAPI types when response schemas change.

## Security Domain

### Applicable ASVS Categories

| ASVS Category       | Applies | Standard control                                                                                                                                             |
| ------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| V2 Authentication   | yes     | existing protected PC metadata routes and scopes. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`]                                                        |
| V4 Access Control   | yes     | `assert_rom_visible` plus `ROMS_READ`/`ROMS_WRITE`. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`]                                                      |
| V5 Input Validation | yes     | typed App IDs, bounded query parameters and response shape guards. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`, `backend/adapters/services/steam.py`] |
| V6 Cryptography     | no      | no new secrets, credentials or custom cryptography. [VERIFIED: `18-CONTEXT.md`]                                                                              |

### Known Threat Patterns

| Pattern                                           | STRIDE                 | Standard mitigation                                                                                                   |
| ------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Untrusted remote payload overwrites catalog state | Tampering              | normalize allowlisted non-empty fields; retain IGDB/manual/selected state. [VERIFIED: `18-CONTEXT.md`]                |
| Storefront disruption causes availability failure | Denial of service      | rate limiter, retries, response guards and empty-result degradation. [VERIFIED: `backend/adapters/services/steam.py`] |
| Log contains payload or sensitive material        | Information disclosure | structured event context only, no payload or secrets. [VERIFIED: `18-CONTEXT.md`]                                     |
| Maliciously ambiguous DLC binds wrong component   | Tampering              | unique hydrated IGDB identity, type/parent/confidence gates and no component creation. [VERIFIED: `18-CONTEXT.md`]    |

## Sources

### Primary (HIGH confidence)

- `18-CONTEXT.md` and `docs/superpowers/specs/2026-09-24-steam-metadata-integration-design.md`, locked scope and acceptance rules.
- Current fork code, especially `backend/adapters/services/steam.py`, `backend/handler/metadata/steam_handler.py`, `backend/handler/metadata/pc_match_handler.py`, `backend/handler/scan_handler.py`, `backend/endpoints/roms/pc_metadata.py`, and `backend/handler/database/roms_handler.py`.
- Current upstream RomM `origin/master`, `backend/handler/metadata/steam_handler.py` and `backend/handler/scan_handler.py`, port baseline and stored-ID resolver pattern.
- `.claude/skills/backend-development/SKILL.md` and `.claude/skills/pre-pr-verification/SKILL.md`, repository architecture and validation conventions.

### Secondary (MEDIUM confidence)

- `docs/superpowers/plans/2026-09-24-steam-metadata-integration.md`, approved proposed task decomposition.

### Tertiary (LOW confidence)

- Steam DLC parent-response consistency, explicitly recorded in the assumptions log.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, it uses existing repository facilities and no new dependency.
- Architecture: HIGH, fork and current upstream seams were inspected directly.
- Pitfalls: HIGH for integration/persistence risks; MEDIUM for real-world Storefront parent response variation.

**Research date:** 2026-09-25  
**Valid until:** 2026-10-02, because the upstream provider and undocumented Storefront behavior can change.
