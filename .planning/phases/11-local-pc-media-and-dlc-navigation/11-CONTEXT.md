# Phase 11: Local PC Media and DLC Navigation - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Let operators select direct local image files as owned game media, review and
apply metadata independently for recognized DLC components, and navigate from
the game overview to the matching local DLC files without modifying any source
library content.

</domain>

<decisions>
## Implementation Decisions

### Local image selection

- **D-01:** Direct PNG, JPEG, and WebP files found recursively in recognized
  PC extra and DLC component directories are offered for explicit selection as
  a cover, background, or gallery image.
- **D-02:** Selection is review-first. Discovering an image never changes an
  existing cover, background, or gallery automatically.
- **D-03:** A selected local image survives a rescan only while its canonical
  relative path and immutable source digest remain unchanged. Changed or
  missing source images require another explicit selection.
- **D-04:** PDFs and archive contents, including ZIP wallpaper bundles, remain
  immutable downloadable extras. They are never extracted or promoted to
  artwork by this phase.

### DLC metadata and navigation

- **D-05:** Each recognized DLC component can be matched and selected against
  metadata providers independently from the base game. Base-game metadata must
  never silently overwrite a DLC selection, or vice versa.
- **D-06:** When a recognized overview expansion corresponds to a locally
  identified DLC component, its primary action opens the same game's Files
  area filtered to that DLC component.
- **D-07:** The overview's DLC primary action is internal only. It does not
  show or redirect to an IGDB link.

### Claude's Discretion

- Exact persistence schema, supported direct-image MIME validation, component
  matching keys, query parameter names, and media presentation should reuse
  established RomM-owned asset and v2 navigation patterns.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and safety boundary

- `.planning/PROJECT.md` — v1.1 PC integration goal and immutable archive
  boundary.
- `.planning/REQUIREMENTS.md` — completed Phase 10 PC model and metadata
  requirements, plus the external-source safety constraints that remain in
  force.
- `.planning/ROADMAP.md` — Phase 11 dependency and milestone placement.
- `.planning/phases/10-pc-integration-model/10-CONTEXT.md` — review-first PC
  metadata and source-read-only decisions that Phase 11 extends.

### Existing implementation

- `backend/models/rom.py` — Rom, RomComponent, media, and component manifest
  persistence model.
- `backend/handler/metadata/pc_match_handler.py` — current provider candidate
  collection boundary.
- `backend/endpoints/roms/pc_metadata.py` — reviewed PC metadata selection
  route and concurrency contract.
- `backend/handler/filesystem/resources_handler.py` — RomM-owned artwork
  download and storage behavior.
- `frontend/src/v2/components/GameDetails/PcMetadataReview.vue` — current
  review-first candidate UI.
- `frontend/src/v2/views/GameDetails.vue` — overview, PC Components, and
  detail-tab integration point.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `RomComponent` already represents classified base, DLC, and extra component
  directories with immutable manifest members.
- The existing resource handler stores selected artwork outside the source
  root.
- PC metadata review already retrieves candidates and applies an explicit
  operator selection.

### Established Patterns

- Backend changes follow endpoint to handler to database or filesystem
  layering, with response schemas driving generated frontend types.
- V2 keeps feature behavior in `frontend/src/v2/`, uses `R*` primitives, and
  reports asynchronous failures through `useSnackbar`.
- Source roots are immutable. All derived artwork must be stored only in
  RomM-owned assets.

### Integration Points

- The scan and component-manifest path discovers direct local image members.
- Reviewed metadata selection persists provider data independently for a DLC
  component and may schedule or perform owned media storage.
- Game overview expansion cards resolve an internal component target and open
  the filtered Files area.

</code_context>

<specifics>
## Specific Ideas

- The Cyberpunk test library contains a direct 4K PNG alongside poster PDFs
  and a wallpaper ZIP. The PNG becomes a reviewable local-art candidate;
  posters and ZIP remain downloadable extras.
- Phantom Liberty should appear as a local DLC destination from Cyberpunk's
  overview, rather than sending the operator away to IGDB.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

_Phase: 11-Local PC Media and DLC Navigation_
_Context gathered: 2026-09-01_
