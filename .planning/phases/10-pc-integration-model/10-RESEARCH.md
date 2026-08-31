# Phase 10: PC Integration Model - Research

**Date:** 2026-08-31
**Status:** Complete

## Findings

### Existing model and scan path

- `Rom` is already the single logical game aggregate and `RomFile` is its physical
  member model. The scanner already supports a directory ROM with recursive members.
  Phase 10 should extend this relationship instead of adding parallel PC-game tables.
- `RomFileCategory` already includes `GAME`, `DLC`, `PATCH`, `UPDATE`,
  `TRANSLATION`, `MOD`, `MANUAL`, `SOUNDTRACK`, and `SCREENSHOT`. PC-specific
  classification can build on these values, with a new explicit representation for
  extras and language packs where the present categories are insufficient.
- `FSRomsHandler.get_rom_files` and `scan_rom` are the correct boundary for rooted
  enumeration and hashing. They must return an explicit unresolved result for an
  ambiguous component layout rather than infer a classification from weak names.

### Metadata and media

- `scan_handler.MetadataSource` already exposes IGDB, MobyGames, LaunchBox, and
  SteamGridDB, and coordinates provider fetches and provider-priority fields.
- `LaunchboxHandler` already supports local material and produces metadata plus
  images. Preserve that local-source path and make it selectable for PC matches;
  do not build a new online account flow.
- The current scan is automatic. A distinct candidate-search/review contract is
  needed for PC games: persist nothing provider-derived until an operator selects a
  candidate; then reuse the existing metadata application and media rendering seams.

### Provider boundary

- The LaunchBox community's current public feature request explicitly says that no
  official public Games Database API is available. Local XML/media parsing remains
  the safe Phase-10 integration boundary. Source:
  <https://feedback.launchbox-app.com/p/public-api-access-for-the-launchbox-games-database-globewithmeridianswrench>.
- RiotPixels has useful screenshots, artwork, and animated media, but no verified
  official API and redistribution/storage terms were found for this use case.
  Do not scrape or import it. Record a provider-evaluation document stating the
  evidence required before any later enablement: official API/documentation, allowed
  media use/storage, rate limits, attribution, and credentials handling.

## Recommended delivery slices

1. Add read-only PC component discovery, classification, and reproducible file
   manifests with backend migration and unit/integration tests.
2. Add a review-first PC metadata candidate API that adapts existing configured
   providers and applies only a selected candidate.
3. Add v2 PC details and match-review UI using existing v2 primitives; surface local
   LaunchBox media and clear unresolved/provider errors.
4. Deliver RiotPixels as a written no-enable evaluation, not code that contacts it.

## Risks and mitigations

| Risk                                                | Mitigation                                                                                              |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| A scan mutates a library tree.                      | Run all PC tests on a read-only fixture and assert a before/after tree manifest is identical.           |
| Folder names accidentally classify unrelated files. | Use explicit grammar and a per-component unresolved state; no fallback to auto-apply.                   |
| Provider failures leave half-applied metadata.      | Candidate search is read-only; the apply endpoint validates one candidate and performs one transaction. |
| Artwork rights are unclear.                         | Use only configured existing providers/local user-owned LaunchBox files; keep RiotPixels disabled.      |

## Validation Architecture

| Requirement             | Automated proof                                                                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| PCMOD-01 to PCMOD-04    | Backend fixture scans verify component classes, manifest path/size/digest values, ambiguity, and unchanged source-tree digest.                     |
| PCMETA-01 to PCMETA-02  | Endpoint tests verify candidate list/search, no write before selection, selected-candidate apply, provider-error response, and source attribution. |
| PCLB-01 to PCLB-02      | Local LaunchBox fixture tests verify read-only XML/media discovery and eligible media filtering.                                                   |
| PCRP-01                 | Documentation test/assertion verifies provider is evaluation-only and has no registered runtime source.                                            |
| PCSAFE-01 and PCTEST-01 | Mutation sentinel tests plus focused backend, frontend Vitest, and E2E review-flow coverage.                                                       |

## Sources to read during implementation

- `backend/models/rom.py`
- `backend/handler/filesystem/roms_handler.py`
- `backend/handler/scan_handler.py`
- `backend/handler/metadata/launchbox_handler/`
- `frontend/src/v2/views/Scan.vue`
- `frontend/src/v2/components/GameDetails/FilesTab/`
