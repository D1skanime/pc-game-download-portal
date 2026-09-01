# Phase 11: Local PC Media and DLC Navigation - Research

**Researched:** 2026-09-01
**Status:** Complete

## Research Question

How can RomM let an operator select direct PC-library images and independently
identify DLC, while preserving the external library's read-only boundary and
making overview navigation land on the matching local files?

## Existing Constraints and Reusable Paths

### Immutable component evidence already exists

`RomComponent` and `RomComponentManifestMember` persist a component-relative
path, byte size, and SHA-256 digest. `FSRomsHandler.get_pc_components()` reads
the external root only through the read/hash capability and `sync_rom_components()`
preserves component identity when its relative path does not change.

This is the correct source of truth for local-art selection validity. A selected
asset must be valid only when a manifest member still has the same relative path
and SHA-256 value after a rescan. No selection may depend on a host path.

### Component grouping has a deliberate ambiguity boundary

The current scanner creates one component for each recognized top-level folder,
such as `dlc` or `extra`. A flat `dlc/` directory with two unrelated installer
sets is not sufficient evidence to infer two DLC identities. The implementation
must retain this conservative rule:

- a direct recognized `dlc` directory is one DLC component;
- a `dlc/<named-package>/` directory is a separately addressable DLC component;
- a flat directory with several indistinguishable packages remains one component
  rather than being silently split by filename heuristics.

The existing Cyberpunk fixture is an unambiguous one-DLC flat directory. It
therefore supports Phantom Liberty review as one component without changing the
meaning of other layouts.

### RomM-owned resource storage is available

`FSResourcesHandler.store_artwork()` copies and validates a cover into
`RESOURCES_BASE_PATH`, never into the external library. It already produces
large and small covers. The resource handler also owns screenshot paths under
the ROM resource directory.

Local PC media must use a dedicated owned-resource method. It must receive bytes
read through the external read capability, validate them as PNG, JPEG, or WebP,
and write only below the ROM resource directory. Existing `file://` handling is
not sufficient for this feature because selected PC media must be resolved via
the mapping-bound external descriptor and verified against a manifest digest.

### The v2 detail view has the required surfaces

- `GameDetails.vue` owns URL-persistent detail tabs and refreshes a ROM after a
  review action.
- `FilesTab.vue` already persists a selected file subtab in the query string.
- `PcComponents.vue` renders component manifests and is the natural component
  filter target.
- `MediaTab.vue` and `ArtworkSubtab.vue` render RomM-owned artwork.
- `useBackgroundArt()` is presentation-only, so a chosen background needs a
  persisted owned-media path in the detailed ROM response.
- `RelatedGameCard.vue` currently falls back to IGDB. DLC and expansion cards
  need an explicit local-component destination and must suppress that fallback
  for this phase.

### API and concurrency patterns are established

PC base-game matching uses a review endpoint plus a POST containing a candidate
identifier and `expected_version`. It returns 409 on stale data and checks
visibility/scopes before all access. The component metadata and local-media APIs
should use the same review-first contract and return schemas from
`endpoints.responses.rom` so the frontend types can be generated.

## Recommended Design

### 1. Persist component metadata and selected local media separately

Add two owned-database relations below `RomComponent`:

- `RomComponentMetadata` stores the independently selected DLC provider IDs,
  title, summary, provider payload, and its own version timestamp.
- `RomComponentLocalMedia` stores the component association, source-relative
  manifest path, source SHA-256, selected role (`cover`, `background`, or
  `gallery`), detected image type, and the owned resource path.

The media rows are selection records, not an imported file inventory. A gallery
can retain multiple rows, while the handler replaces the single cover or
background selection for a ROM transactionally. Cover selection also refreshes
the standard Rom cover paths so gallery cards and the detail cover immediately
use the selected owned image.

### 2. Discover candidates from manifests, copy only after confirmation

For a DLC or extra component, enumerate only direct manifest members whose
suffix is `.png`, `.jpg`, `.jpeg`, or `.webp`. Do not inspect archive members,
PDFs, or other extras. Before a candidate is previewed or accepted, read it via
the mapping descriptor and validate its real MIME type and decodability. A
preview is a read-only, authenticated response from the already-manifested
source. Applying a role copies the validated bytes into the RomM resource root.

At apply time, re-hash the source stream and compare it with the reviewed
manifest SHA-256 before writing owned media. This closes the interval between
candidate review and copy. A failed validation or changed digest returns a
conflict and leaves the current selection unchanged.

### 3. Reconcile selected media on each PC rescan

After `sync_rom_components()`, compare every selected media record against the
fresh manifest. When the exact source path and digest remain, preserve the
selection and its owned copy. When either is absent or changed, delete the
selection and its owned resource. If the invalid row was the cover, clear only
the cover it owns. All cleanup is constrained to the RomM resource directory.

### 4. Review DLC metadata per recognized DLC component

Expose component-scoped candidate and selection endpoints. They must reject a
component that is not `dlc`, reconstruct candidates server-side, and update only
that component's metadata record. The existing base-game endpoint remains the
base-game path, so selecting Phantom Liberty can never overwrite Cyberpunk 2077
metadata.

Component identity in frontend and endpoints should be the persisted component
ID, not a user-supplied filesystem path. Relative paths remain display data and
are URL-encoded only for the Files filter.

### 5. Navigate overview DLC cards internally

Enrich the detailed ROM response with the map of locally identified DLC IGDB IDs
to component relative paths. An expansion or DLC card with a matching component
routes to the current ROM with `?tab=files&component=<path>`. `FilesTab` renders
the component-manifest view for that parameter and keeps the filter URL-persistent.
For expansions and DLC, do not use an IGDB fallback link. Other related-game
categories retain their current behavior.

## Test Strategy

### Backend

- Model and migration tests prove uniqueness, cascade behavior, and portable
  enums/constraints for component metadata and selected local media.
- Scanner tests cover nested DLC grouping, flat-DLC ambiguity preservation, and
  selection reconciliation for unchanged, modified, and removed source images.
- Resource-handler tests prove validated bytes are copied to owned storage,
  invalid images are rejected, source bytes remain unchanged, and cleanup cannot
  leave the ROM resource root.
- Endpoint tests cover authentication, visibility, review-only discovery,
  stale selection, digest change between review and apply, unsupported/PDF/ZIP
  exclusion, independent base and DLC selections, and no source mutation.

### Frontend

- Component tests cover role selection, candidate preview/error states, and the
  refresh after a successful apply.
- Files tests cover the persisted `component` filter and a selected DLC
  manifest.
- Related-card tests cover an internal DLC destination and prove no `window.open`
  IGDB fallback is used for DLC/expansion cards.
- Generated OpenAPI types, typecheck, and targeted browser UAT cover the full
  Cyberpunk flow: select the direct PNG as local artwork, match Phantom Liberty,
  click it from Overview, and land on the filtered local files.

## Risks and Mitigations

| Risk                                             | Mitigation                                                             |
| ------------------------------------------------ | ---------------------------------------------------------------------- |
| A renamed `.png` is not an image                 | Validate actual MIME and decode it before preview or copy.             |
| Source changes after review                      | Re-hash immediately before the owned copy and reject mismatch.         |
| Scan cleanup could touch source data             | Cleanup uses only stored RomM-owned resource paths.                    |
| Flat multi-DLC folders are ambiguous             | Keep them as one unguessed component.                                  |
| A related card leaves the product                | DLC/expansion cards receive local-only behavior with no IGDB fallback. |
| Existing game cover is overwritten automatically | All roles require an explicit operator POST.                           |

## Validation Architecture

### Automated checks

- Focused backend pytest suites for models, filesystem handlers, scan handling,
  and PC metadata/media endpoints.
- Focused Vitest suites for PC component/media review, Files filtering, and
  related-card routing.
- OpenAPI type regeneration followed by frontend typecheck.
- `trunk fmt && trunk check` on modified paths.

### Manual UAT

Use only the isolated test stack and supplied fixtures. Confirm source-tree
digest before and after the flow. Select the Cyberpunk PNG as cover, background,
and gallery in separate explicit actions; rescan unchanged; then modify or
remove only a disposable fixture image and confirm the corresponding selection
is cleared. Match Phantom Liberty, click it from Overview, and confirm the URL
and visible manifest point to the same ROM's DLC component without opening
IGDB.

## Planning Implications

The phase needs three dependency-ordered plans:

1. Persistence, safe candidate discovery/copy, rescan reconciliation, and API
   schemas/endpoints.
2. Generated contract, component-aware metadata/media review, Files filtering,
   and local-only related-card navigation.
3. Regression tests, isolated-stack evidence, and final quality verification.

---

_Phase: 11-local-pc-media-and-dlc-navigation_
_Research completed: 2026-09-01_
