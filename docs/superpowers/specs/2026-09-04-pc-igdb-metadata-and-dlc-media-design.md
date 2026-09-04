# PC IGDB Metadata and DLC Media Design

## Goal

Make scan-time IGDB enrichment provide concise, PC-specific metadata and owned
media for local PC parent games and their unambiguously linked DLC components.

## Scope

The feature applies to a Windows parent ROM and every DLC component that has a
trusted IGDB link. It does not change source-library files or paths.

For each eligible target, persist:

- One main developer, the first IGDB involved company marked as a developer.
- Publisher names from IGDB involved companies marked as publishers.
- IGDB theme names.
- The PC-specific release date, using the Microsoft Windows release record.
- Cover, screenshots, and artworks in RomM-owned storage.

Supporting developers are intentionally ignored. The existing mixed company list
remains available for providers that do not expose role-specific company data.

## Data Model

Parent ROM metadata and `RomComponentMetadata` receive equivalent structured
fields for `main_developer`, `publishers`, `themes`, and `pc_release_date`.
The API exposes these fields in the detailed parent and component response
schemas. Existing generic first-release metadata remains intact for compatibility
but the PC detail UI prefers the PC-specific release date.

The component uses `RomComponentOwnedMedia` for imported cover, screenshot, and
artwork records. Parent media uses the established RomM-owned parent-media flow.
No IGDB URL or downloaded media is written into the scanned game library.

## Scan and Import Flow

1. Resolve the parent game or a trusted DLC component to an IGDB candidate.
2. Request IGDB involved-company roles, themes, Microsoft Windows release dates,
   cover, screenshots, and artworks.
3. Normalize the metadata: retain the first developer, all publishers, all
   non-empty themes, and the Microsoft Windows release date only.
4. Persist normalized metadata to the selected parent or component.
5. Download selected cover, screenshots, and artwork into RomM-owned storage.
6. Record imported component files as component-owned media, never as source
   evidence. Parent imports use the existing parent-owned media mechanism.
7. A failed optional media download is logged without losing already valid
   metadata or source-library scan visibility.

Automatic DLC import occurs only after the DLC is unambiguously linked to its
parent and to its IGDB candidate. Ambiguous or unresolved components remain
unchanged and require explicit user matching.

## UI Contract

The parent and DLC detail pages use the same information hierarchy:

- Cover in the left cover column.
- A top metadata line that displays `PC release: <localized date>` in place of
  the generic Desktop Games plus first-release-date line when PC release data is
  present.
- Overview content below the tab navigation, with summary and technical facts.
- Separate Main developer, Publishers, and Themes groups in Overview.
- A screenshot gallery directly below the Overview description and facts for
  both parent and DLC.
- The complete imported media collection remains accessible through Media.

Themes are stored in a form suitable for future library-filter links. Linking
theme chips to a gallery is optional in this implementation and must not require
a schema migration later.

## Error Handling and Safety

- Missing IGDB fields are omitted from display rather than replaced by invented
  data.
- Only the Microsoft Windows release record is considered for PC release.
- A provider response never grants arbitrary filesystem access.
- Imported files retain trusted provider metadata and stay under RomM-owned
  resource paths.
- Failed component enrichment must not hide an already persisted parent ROM from
  scan events or the library.

## Verification

- Backend tests cover normalization of first developer, publishers, themes, and
  Windows-only release selection for parents and DLC components.
- Endpoint and handler tests prove owned media import never writes to the source
  library and remains target-contained.
- Frontend tests cover PC-release rendering, metadata groups, and screenshot
  galleries for parent and DLC pages.
- OpenAPI generation, frontend typecheck, focused backend/frontend tests, locale
  parity, and scoped Trunk checks pass.
- Manual UAT verifies a parent and linked DLC show their selected metadata and
  media in the specified locations.
