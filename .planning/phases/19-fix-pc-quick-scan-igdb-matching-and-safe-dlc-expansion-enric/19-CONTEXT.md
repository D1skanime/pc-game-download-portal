# Phase 19: Fix PC quick-scan IGDB matching and safe DLC/expansion enrichment - Context

**Gathered:** 2026-09-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Repair automatic PC library scans so compact filesystem names such as
`EuroTruckSimulator2` resolve through IGDB as reliably as the existing Steam
lookup, preserving classic-ROM behavior. A quick scan and a later metadata
refresh must establish or recover the IGDB parent relation needed for safe,
IGDB-first DLC and expansion component enrichment.

</domain>

<decisions>
## Implementation Decisions

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

### Claude's Discretion

- Select the smallest PC-specific normalizer that reuses established title
  parsing and has focused regression tests for scanning and refreshing.
- Keep the implementation backend-first. No UI redesign is required for this
  bugfix unless an existing exact-title component selection is demonstrably
  inaccessible.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PC scan and provider flow

- `backend/handler/scan_handler.py` — PC scan dispatch, Steam normalization,
  provider application order, and scan-type eligibility.
- `backend/handler/metadata/igdb_handler.py` — automatic IGDB filename search
  and ID-based refresh behavior.
- `backend/handler/metadata/steam_handler.py` — established compact-title
  boundary normalization to mirror only where appropriate.
- `backend/endpoints/sockets/scan.py` — parent IGDB enrichment followed by
  component enrichment during a scan.
- `backend/handler/metadata/pc_match_handler.py` — reviewable PC candidates,
  exact IGDB related-candidate checks, and Steam DLC validation.

### Explicit component metadata selection

- `backend/endpoints/roms/pc_metadata.py` — existing component candidate and
  explicit selection API contract.
- `backend/models/rom.py` — ROM and component metadata persistence boundaries.

### Deferred media and soundtrack follow-up

- `frontend/src/v2/components/GameDetails/MediaTab.vue` — existing Media
  subtab composition.
- `frontend/src/v2/components/GameDetails/SoundtrackPanel.vue` — existing
  soundtrack player and supported audio extensions.
- `backend/endpoints/roms/soundtrack.py` — legacy source-writing upload route
  that a future read-only-safe owned-media solution must not reuse directly.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `SteamHandler.COMPACT_TITLE_BOUNDARY` already turns compact PC names into
  searchable terms for Steam.
- `PcMetadataMatchHandler.collect_component_candidates()` and
  `select_pc_component_metadata_candidate()` already support review then
  explicit component-candidate persistence.
- `_enrich_pc_dlc_from_igdb()` preserves the intended IGDB-first relation
  sequence before optional Steam enrichment.

### Established Patterns

- Metadata provider failures are isolated so one provider cannot abort the
  remaining scan flow.
- Persisted external IDs are refreshed by ID and must never be silently
  replaced by a name search.
- Provider media and user-selected display state are separate concerns.

### Integration Points

- `scan_rom()` calls IGDB and Steam concurrently, then persists provider
  metadata before `endpoints/sockets/scan.py` runs PC parent/component
  enrichment.
- The current automatic IGDB path receives the raw filesystem name, while the
  Steam handler already normalizes a compact title. This is the confirmed gap.

</code_context>

<specifics>
## Specific Ideas

- The UAT fixture `EuroTruckSimulator2` is the regression case: parent IGDB
  ID `3070`, DLC `Euro Truck Simulator 2: Special Transport`, and expansion
  `Euro Truck Simulator 2: Italia`.
- The fixed quick scan must make the parent relation available so both
  components can be identified safely, rather than requiring a separate
  per-ROM scan.

</specifics>

<deferred>
## Deferred Ideas

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

</deferred>

---

_Phase: 19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric_
_Context gathered: 2026-09-28_
