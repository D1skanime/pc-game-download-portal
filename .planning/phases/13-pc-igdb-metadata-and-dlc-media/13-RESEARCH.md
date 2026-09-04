# Phase 13: PC IGDB Metadata and DLC Media - Research

## Existing integration points

- `backend/handler/metadata/igdb_handler.py` already builds IGDB candidates with
  cover, screenshots, artwork URLs and generic `companies`, but its field
  request omits company roles, themes and release records.
- `backend/endpoints/sockets/scan.py` persists parent metadata and downloads
  parent cover/screenshots after `scan_rom`; it is the correct scan-time seam.
- `RomComponentMetadata` stores provider identity, name and summary; Phase 12
  adds `RomComponentOwnedMedia` and target-contained persistence helpers.
- `PcMetadataMatchHandler.find_unique_related_igdb_candidate()` already models
  the required unambiguous DLC candidate gate.
- `OverviewTab.vue` is the parent overview analog. `PcDlcDetail.vue` is the
  contained DLC overview analog. Both consume backend-owned response data.

## Recommended approach

1. Extend the IGDB typed result and request fields with
   `involved_companies.developer`, `involved_companies.publisher`,
   `themes.name`, `release_dates.date`, and `release_dates.platform.id`.
   Normalize the first developer, all publishers, non-empty themes, and only
   the IGDB Windows platform record.
2. Persist identical structured metadata on `RomMetadata` and
   `RomComponentMetadata`, with a portable Alembic migration. Expose it from
   detailed parent and component schemas before regenerating frontend types.
3. In the scan path, apply the normalized parent metadata through the existing
   parent metadata writer. For a DLC, call the existing unique-related-candidate
   gate and do nothing if it returns no single candidate. Download only trusted
   selected URLs to RomM-owned resources, and isolate component files through
   `RomComponentOwnedMedia`.
4. Keep optional media download failures non-fatal: log context, retain already
   persisted metadata, and continue the scan/socket lifecycle.
5. Adapt existing overview/detail primitives to show PC release, separate
   developer/publisher/theme groups, and an owned screenshot gallery. Omit
   absent fields, use locale keys, and never use provider/source URLs directly.

## Verification architecture

- Unit tests: IGDB role/theme/Windows-date normalization, including missing and
  non-Windows records.
- Database and endpoint tests: parent/component isolation, stale candidate and
  ambiguous DLC no-op behavior, owned-path media import, and optional download
  failure preservation.
- Frontend tests: parent and DLC PC release/fact groups/gallery rendering,
  absent-data omission, and owner-bounded media URLs.
- Contract gate: OpenAPI generation, typecheck, locale parity/sort and Trunk.

## Risks

- Never infer Windows from a generic first release date. Match the IGDB Windows
  platform id from the adapter platform registry.
- Preserve existing generic `companies` and `first_release_date` for all
  non-PC consumers.
- Do not promote ambiguous related games to a component match or import media
  before candidate identity is confirmed.
