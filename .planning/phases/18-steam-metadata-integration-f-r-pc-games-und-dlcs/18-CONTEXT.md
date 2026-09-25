# Phase 18: Steam Metadata Integration for PC Games and DLCs - Context

**Gathered:** 2026-09-25
**Status:** Ready for planning
**Source:** Approved Steam metadata integration specification

<domain>
## Phase Boundary

Port the official RomM Steam Storefront metadata provider into the PC fork.
Steam is a distinct structured metadata source, while SteamGridDB remains an
artwork-only provider. Steam enriches PC games with German-first text and safe
fallback, and enriches DLC components only after existing IGDB relationships
unambiguously establish their identity.
</domain>

<decisions>
## Implementation Decisions

### Provider, configuration, and scope

- Add MetadataSource.STEAM as an independent provider. Retain sgdb for
  SteamGridDB without rename or behavior changes.
- Port upstream Steam service, typed payloads, handler, registration, enable
  flag, heartbeat, priority integration, schemas, and tests. No scraper and no
  API key.
- Use STEAM_API_ENABLED=false by default, preferred de/CH, and configurable
  fallback en/US.
- Automatic name search is limited to win, linux, and mac. dos, win3x, and
  win9x resolve an explicit valid App ID only. Classic ROM platforms never call
  Steam.

### Identity, localization, and persistence

- Persist nullable steam_id and JSON steam_metadata on Rom and
  RomComponentMetadata without global component-App-ID uniqueness.
- Existing steam_id values refresh strictly by ID, including after filename
  changes, never by rematch.
- German details load first. English fallback fetches only the same resolved App
  ID and fills only missing fields. It never performs a second name search.
- Empty, malformed, unavailable, or rate-limited Steam data is non-fatal and
  cannot clear existing data.

### Merge and manual data protection

- Automatic scans and selected Steam candidates use one normalized application
  and field-merge function.
- Steam may provide localized title, summary, developer, publisher, release,
  and media candidates. It does not replace IGDB themes, franchise, related
  games, or DLC relationships.
- Steam media enters existing artwork selection only and cannot replace selected
  or manually overridden artwork.
- Manual title, summary, release date, and selected artwork are independently
  protected.

### DLC safety

- Preserve all existing IGDB expansion/DLC discovery, enrichment, and unique
  related-candidate logic.
- Only one hydrated IGDB-resolved DLC identity may trigger Steam DLC lookup.
- Reject bundles, soundtracks, demos, editions, tools, and unrelated products.
  A Steam parent relation must match the parent App ID. Without a parent
  relation, apply only a unique high-confidence result tied to the resolved
  IGDB identity.
- Ambiguous, invalid, unmatched, or parent-mismatched DLCs preserve IGDB
  metadata and never create components.

### Verification and observability

- Register Steam in provider, priority, heartbeat, scan, serialization, and v2
  display locations without regressing current providers.
- Log provider, platform, query, App ID, language, confidence, and fallback
  outcome without secrets or payloads.
- Test localization, ID refresh, platform gating, failure isolation, manual
protection, non-empty merge, DLC safety, persistence, duplication prevention,
and classic-ROM non-regression.
</decisions>

<canonical_refs>

## Canonical References

- docs/superpowers/specs/2026-09-24-steam-metadata-integration-design.md
- docs/superpowers/plans/2026-09-24-steam-metadata-integration.md
- backend/handler/metadata/pc_match_handler.py
- backend/endpoints/roms/pc_metadata.py
- backend/handler/database/roms_handler.py
- backend/models/rom.py
- backend/alembic/versions/0118_pc_igdb_structured_metadata.py
  </canonical_refs>

<specifics>
## Specific Ideas

- Upstream baseline inspected at RomM commit eaba9c70d1ef462022c7b4a1ab9846ddb214b66c.
- Keep upstream code close; isolate fork behavior in localization, PC merge,
and component/DLC integration.
</specifics>

<deferred>
## Deferred Ideas

- Translation of non-Steam metadata, Steam login, ownership/library sync,
downloads, installations, achievements, cloud, and generic matching framework
work are outside Phase 18.
</deferred>

---

_Phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs_
_Context gathered: 2026-09-25 from approved specification_
