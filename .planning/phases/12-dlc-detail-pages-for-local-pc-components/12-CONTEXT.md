# Phase 12: DLC detail pages for local PC components - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Give each locally present, independently matched PC DLC component its own
RomM detail page that feels like the parent game's detail experience. The
page makes the DLC's identity, artwork, description, local files, owned media,
and notes understandable without changing the source library.

</domain>

<decisions>
## Implementation Decisions

### Dedicated DLC experience

- **D-01:** A local DLC has its own detail page, rather than only an expanded
  row in the PC Components area.
- **D-02:** The page is reachable from both the Overview DLC card and the
  PC Components list, with clear back navigation to the parent game.
- **D-03:** The page follows the parent game's tab language: Overview,
  Files, Media, and Notes. There is no DLC save-data feature in this phase.
- **D-04:** Overview presents a prominent cover, title, description, and
  DLC-only screenshots or other selected media. Files presents only the
  selected DLC's manifest entries and DLC-specific downloadable artwork.
- **D-05:** Media accepts and manages only RomM-owned DLC media: images,
  screenshots, artwork, soundtrack, and videos. It does not write to or
  otherwise mutate the immutable source library.
- **D-06:** Notes are scoped to the individual DLC, not shared with the parent
  game. Save data remains owned by and available from the parent game because
  the DLC runs through it. There is no separate DLC save-data feature.

### Unified metadata matching

- **D-07:** Replace the bespoke, simplified PC metadata-candidate view with
  the existing polished `ROM zuordnen` matching experience for both the
  PC parent game and every PC component, including DLCs.
- **D-08:** PC Components' `Metadaten suchen` and the DLC detail page's
  overflow action `ROM zuordnen` are two entry points to that one shared
  matching flow.
- **D-09:** The shared flow retains its provider filters, result list,
  description preview, and cover-selection UI. When the target is a DLC, its
  explicit selection writes metadata and selected provider media only to that
  DLC, never to the parent game.
- **D-10:** Selected provider images are imported as RomM-owned DLC media only
  after the user explicitly confirms the match. The feature must not mutate
  source files or silently apply artwork.

### DLC actions and information

- **D-11:** The DLC detail page has an overflow action menu with all
  applicable component actions: `ROM zuordnen`, poster/media selection, and
  downloading the DLC's local files.
- **D-12:** Technical component information, such as size, version evidence,
  and checksums, belongs on the DLC detail experience and may reuse existing
  detail patterns.

### Claude's Discretion

- Exact responsive composition, cover fallback, which Media subtab owns each
  supported media kind, and the precise technical metadata fields shown may
  follow existing v2 Game Details conventions.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and safety boundary

- `.planning/PROJECT.md` - Immutable archive boundary and v1.1 PC integration
  goal.
- `.planning/REQUIREMENTS.md` - Existing PC integration requirements and
  source-read-only constraints.
- `.planning/ROADMAP.md` - Phase 12 goal and dependency on Phase 11.
- `.planning/phases/10-pc-integration-model/10-CONTEXT.md` - PC component,
  manifest, and review-first metadata decisions.
- `.planning/phases/11-local-pc-media-and-dlc-navigation/11-CONTEXT.md` -
  Local artwork, independent DLC metadata, and internal navigation decisions.

### Existing implementation

- `backend/models/rom.py` - RomComponent, component metadata, local media,
  and immutable manifest persistence.
- `backend/endpoints/responses/rom.py` - Detailed ROM and PC component API
  response shapes.
- `backend/endpoints/roms/pc_metadata.py` - Review-first DLC metadata
  selection and source safety contract.
- `frontend/src/v2/views/GameDetails.vue` - Parent game detail page and PC
  component integration point.
- `frontend/src/v2/components/GameDetails/PcComponents.vue` - Existing local
  component list and metadata entry point, which must use the shared matcher.
- `frontend/src/v2/components/Dialogs/MatchRomDialog.vue` - Established
  `ROM zuordnen` search, provider filters, result list, description preview,
  and cover-selection flow to reuse for PC parents and components.
- `frontend/src/v2/components/MatchRom/` - Shared grid/list body variants and
  cover-selection UI used by the established matcher.
- `frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue` - Existing
  component-filtered local file presentation.
- `frontend/src/v2/components/GameDetails/MediaTab.vue` and
  `frontend/src/v2/components/GameDetails/NotesTab.vue` - Parent-game tab
  conventions to adapt while keeping DLC records separate.
- `frontend/src/v2/components/GameDetails/RelatedGameCard.vue` - Overview DLC
  card and local-DLC navigation behavior.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `GameDetails.vue` and its feature composites provide the active v2 detail
  page language, tabs, artwork, media, notes, and navigation patterns.
- `MatchRomDialog.vue` and `components/MatchRom/` already provide the desired
  polished metadata matching and cover-selection experience.
- `RomComponent` already carries a component-local immutable file manifest,
  metadata selection, and owned local media records.
- `FilesTab.vue` already filters the parent game's files to one component.

### Established Patterns

- Metadata and provider artwork remain review-first. Explicitly selected data
  is kept in RomM-owned storage outside the immutable source library.
- Backend response schemas are authoritative, with generated frontend types.
- V2 feature UI belongs below `frontend/src/v2/components/GameDetails/` and
  uses established `R*` primitives and co-located tests.

### Integration Points

- A dedicated route must resolve a parent Rom plus one locally present DLC
  component, then reuse or extend component-specific metadata, owned media,
  notes, and manifest APIs without leaking parent data.
- The matcher needs a target abstraction so the same visual flow can update a
  PC parent or one component safely through the appropriate API contract.
- Overview cards, the PC Components list, and the DLC action menu become
  entry points.

</code_context>

<specifics>
## Specific Ideas

- The user chose the full own-detail-page approach rather than an inline
  component card. It should feel like the main game page while making clear
  that it is a locally present DLC belonging to that game.
- The screenshot of the existing `ROM zuordnen` dialog is the visual and
  interaction reference. It already finds `A Woman's Lot` and shows its
  description and cover, so it must be reused for PC parent and component
  metadata search rather than replaced by a second, simpler UI.

</specifics>

<deferred>
## Deferred Ideas

- DLC-specific save data is intentionally not a feature: save data stays with
  the parent game because the DLC depends on it.

</deferred>

---

_Phase: 12-dlc-detail-pages-for-local-pc-components_
_Context gathered: 2026-09-02_
