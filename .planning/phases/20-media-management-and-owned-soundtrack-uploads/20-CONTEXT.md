# Phase 20: Media management and owned soundtrack uploads - Context

**Gathered:** 2026-09-28
**Status:** Ready for planning
**Source:** Carried forward from the user-approved Phase 19 discussion and UAT follow-up

<domain>
## Phase Boundary

Turn v2 Media into the place where an operator manages provider-downloaded
screenshots and artwork without ever writing to the read-only source library.
Allow operator-owned artwork and soundtrack assets, and make the selected
display media usable by the game-details overview.

</domain>

<decisions>
## Implementation Decisions

### Provider screenshot management

- Show provider screenshots in Media as candidates for the overview.
- The operator can deselect a provider screenshot from the overview or delete
  it permanently from RomM-owned media storage.
- A normal scan must not restore a deleted provider asset.
- An explicit full-media refresh restores the complete provider candidate set.

### Artwork and backgrounds

- Show provider artwork candidates in Media.
- Permit artwork and screenshot candidates to be selected as backgrounds.
- Permit uploads of operator-owned artwork to RomM-owned storage only.
- Support multiple chosen backgrounds, rotating with smooth transitions that
  respect reduced-motion preferences.

### Soundtrack

- Support only manual uploads to RomM-owned storage in this phase.
- Accept MP3, AAC, FLAC, OGG, OPUS, M4A, and WAV.
- Let the operator include and order playable tracks per game using the
  existing player.
- Do not crawl SteamGridDB or another external audio provider, and do not add
  automatic track metadata enrichment.

### Safety

- Never rename, move, delete, or otherwise write to the external source
  library.
- Keep provider media and the user-selected display state separate.

### Claude's Discretion

- Choose data model, endpoints, component composition, and migration design
  that preserve existing v2 and owned-storage patterns.
- Choose focused UAT fixtures and test coverage for refresh, deletion,
  selection, upload, ordering, and reduced-motion behavior.

</decisions>

<canonical_refs>

## Canonical References

### Prior product decisions

- `.planning/phases/19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric/19-DISCUSSION-LOG.md` — original locked Media and soundtrack choices.
- `.planning/phases/19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric/19-CONTEXT.md` — source-library safety and provider/display-state boundary.

### Existing implementation surfaces

- `frontend/src/v2/components/GameDetails/MediaTab.vue` — v2 Media subtab composition.
- `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue` — shared, personal, and community screenshot UI.
- `frontend/src/v2/components/GameDetails/ArtworkSubtab.vue` — current artwork gallery.
- `frontend/src/v2/components/GameDetails/SoundtrackPanel.vue` — reusable playback UI.
- `frontend/src/v2/views/GameDetails.vue` — overview screenshots and selected background application.
- `backend/models/rom.py` — owned provider media and detailed-ROM representation.
- `backend/endpoints/roms/soundtrack.py` — legacy source-writing route that must not be reused for uploads.

</canonical_refs>

<specifics>
## Specific Ideas

- The scanned Witcher 3 UAT fixture already has provider screenshots in
  RomM-owned storage and is the first Media verification target.
- The Media tab, rather than Overview, is the operator's management surface.

</specifics>

<deferred>
## Deferred Ideas

- Automatic soundtrack metadata and external audio providers.
- The unresolved Steam localized-summary overwrite defect; it is tracked as a
  separate scan/merge bug and is out of this phase.

</deferred>

---

_Phase: 20-media-management-and-owned-soundtrack-uploads_
_Context gathered: 2026-09-28 from approved prior decisions_
