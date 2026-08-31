# Phase 10: PC Integration Model - Context

**Gathered:** 2026-08-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Model games already present in a read-only PC library as a base game plus explicit
components, build reproducible manifests, and let operators review metadata matches
and eligible media without modifying library sources. This phase does not download,
install, unpack, rename, or otherwise prepare PC games.

</domain>

<decisions>
## Implementation Decisions

### PC library safety and components

- **D-01:** The PC source library is strictly read-only. Scanning, manifesting,
  matching, and media handling must not create, rename, move, delete, extract, or
  edit files beneath a registered source root.
- **D-02:** A logical PC game can contain explicitly classified base, update, DLC,
  hotfix, language-pack, and extra components. Ambiguous layouts remain unclassified
  and are reported clearly rather than guessed.
- **D-03:** Every recognized component records a stable manifest of relative paths,
  byte sizes, and strong digests.

### Metadata selection

- **D-04:** Metadata matching is review-first: RomM presents candidate matches and
  the operator explicitly selects a result before metadata is applied. No candidate
  is silently accepted.
- **D-05:** Reuse existing IGDB, SteamGridDB, MobyGames, and LaunchBox provider
  contracts where possible; unavailable providers must produce a clear non-mutating
  result.

### LaunchBox and media

- **D-06:** LaunchBox is a locally mounted, read-only metadata/media source. A
  direct LaunchBox cloud-account connection is out of scope because no documented
  public third-party API or OAuth flow is available.
- **D-07:** Eligible local LaunchBox descriptions, cover art, fan art, logos,
  screenshots, and videos may be offered with the selected match and shown in v2.
- **D-08:** RiotPixels is an evaluation-only provider in this phase. Automated
  import remains disabled until API, licensing/rights, and operating constraints
  are documented and accepted.

### Claude's Discretion

- Concrete database shape, component-layout heuristics, candidate ranking, and v2
  presentation details must follow established RomM patterns while preserving the
  review-first and read-only decisions above.

### Folded Todos

- **Enforce immutable external game libraries:** Its read-only invariant applies to
  PC source roots and is verified by this phase's manifest and scan tests.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone scope

- `.planning/PROJECT.md` — v1.1 PC integration goal and feature boundary.
- `.planning/REQUIREMENTS.md` — PCMOD, PCMETA, PCLB, PCRP, PCSAFE, and PCTEST
  requirement definitions and explicit exclusions.
- `.planning/ROADMAP.md` — Phase 10 goal, dependency, and success criteria.
- `.planning/STATE.md` — current milestone state and prior Phase 9 acceptance.

### Existing implementation

- `backend/models/rom.py` — existing logical ROM/file models and provider metadata
  fields that the PC model should extend or reuse.
- `backend/handler/scan_handler.py` — metadata-source selection and scan pipeline.
- `backend/handler/metadata/launchbox_handler/` — current LaunchBox local/remote
  source and eligible media handling.
- `frontend/src/v2/views/Scan.vue` — v2 metadata-source and scan workflow.
- `frontend/src/v2/views/Settings/MetadataSources.vue` — v2 provider settings.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `Rom` and `RomFile` already represent a logical library item and its files.
- Existing metadata handlers support IGDB, MobyGames, SteamGridDB, and LaunchBox.
- The LaunchBox handler already distinguishes local sources and collects media.

### Established Patterns

- Metadata source selection flows through `MetadataSource` and scan handlers.
- v2 keeps scan controls in `Scan.vue` and provider configuration in
  `Settings/MetadataSources.vue`.

### Integration Points

- PC component recognition connects to the filesystem scan pipeline and persistent
  ROM/file model.
- Candidate review and selected media connect to the existing v2 scan and metadata
  presentation paths.

</code_context>

<specifics>
## Specific Ideas

- The user wants PC games to feel properly organized in RomM: a game can include
  base content and companion updates/DLC/language/extras, then receive descriptions
  and artwork after an operator chooses the correct metadata match.
- Windows downloading/installing is a separate future phase.

</specifics>

<deferred>
## Deferred Ideas

- A Windows PC-game downloader/installer and any source-changing preparation flow.
- Direct LaunchBox cloud-account linking until an official supported integration
  exists.
- Automated RiotPixels media ingestion until provider rights and API constraints
  have been positively evaluated.

</deferred>

---

_Phase: 10-PC Integration Model_
_Context gathered: 2026-08-31_
