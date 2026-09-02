# Phase 12: DLC detail pages for local PC components - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Give each locally present, independently matched PC DLC component its own
RomM detail page. The page makes the DLC's identity, artwork, description,
and local files understandable without changing the source library.

</domain>

<decisions>
## Implementation Decisions

### Dedicated DLC experience

- **D-01:** A local DLC has its own detail page, rather than only an expanded
  row in the PC Components area.
- **D-02:** The page is reachable from both the Overview DLC card and the
  PC Components list, with clear back navigation to the parent game.
- **D-03:** The page presents a prominent cover, title, description, media,
  and the DLC's own local files.

### Information and artwork

- **D-04:** Existing matched metadata and already selected local artwork are
  reused. The feature must not alter source files or silently fetch and apply
  new artwork.
- **D-05:** Technical component information, such as size, version evidence,
  and checksums, belongs on the detail page. The exact presentation can reuse
  established RomM detail patterns.

### Claude's Discretion

- Exact page layout, responsive breakpoints, tabs versus sections, cover
  fallback, and the precise metadata fields shown may follow existing v2
  Game Details conventions.

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
  component list and metadata entry point.
- `frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue` - Existing
  component-filtered local file presentation.
- `frontend/src/v2/components/GameDetails/RelatedGameCard.vue` - Overview DLC
  card and local-DLC navigation behavior.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `GameDetails.vue` and its feature composites provide the active v2 detail
  page language, tabs, artwork, and navigation patterns.
- `RomComponent` already carries a component-local immutable file manifest,
  metadata selection, and owned local media records.
- `FilesTab.vue` already filters the parent game's files to one component.

### Established Patterns

- Metadata and local artwork remain review-first, and selected data is kept
  outside the immutable source library.
- Backend response schemas are authoritative, with generated frontend types.
- V2 feature UI belongs below `frontend/src/v2/components/GameDetails/` and
  uses established `R*` primitives and co-located tests.

### Integration Points

- A dedicated route must resolve a parent Rom plus one locally present DLC
  component, then reuse its metadata, local media, and manifest members.
- Overview cards and the PC Components list become the two navigational
  entry points.

</code_context>

<specifics>
## Specific Ideas

- The user chose the full own-detail-page approach: a large cover,
  description, media, and files rather than an inline component card.
- The detail page should feel like the main game page while making clear that
  it is a locally present DLC belonging to that game.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within the Phase 12 detail-page scope.

</deferred>

---

_Phase: 12-dlc-detail-pages-for-local-pc-components_
_Context gathered: 2026-09-02_
