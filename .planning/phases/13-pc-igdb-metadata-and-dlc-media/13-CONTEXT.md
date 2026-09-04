# Phase 13: PC IGDB Metadata and DLC Media - Context

**Gathered:** 2026-09-04
**Status:** Ready for research and planning
**Source:** Specification express path (`docs/superpowers/specs/2026-09-04-pc-igdb-metadata-and-dlc-media-design.md`)

<domain>
## Phase Boundary

Extend scan-time IGDB enrichment for Windows parent ROMs and unambiguously
linked DLC components. Persist normalized PC-specific metadata and provider
media in RomM-owned storage, expose it through parent and component API
schemas, and render it in their v2 detail overviews. Source-library files and
paths remain immutable.
</domain>

<decisions>
## Implementation Decisions

### Eligible targets and matching

- Scan-time enrichment applies to Windows parent ROMs and DLC components only
  when the DLC has an unambiguous trusted link to both its parent and IGDB
  candidate.
- Ambiguous or unresolved components remain unchanged and require explicit
  user matching.

### IGDB normalization

- Persist the first involved company marked as developer as `main_developer`.
- Persist all involved companies marked as publishers as `publishers`.
- Persist all non-empty IGDB `themes`.
- Persist only the Microsoft Windows release date as `pc_release_date`.
- Preserve generic first-release metadata and the existing mixed-company list
  for backward compatibility.

### Media ownership and failure behavior

- Download selected IGDB cover, screenshots, and artwork only into RomM-owned
  storage.
- Store DLC imports as `RomComponentOwnedMedia`; use the established
  parent-owned media path for parent imports.
- A failed optional media download is logged and does not discard valid
  metadata or hide the ROM from scan results.

### API and v2 presentation

- Detail parent and component response schemas expose equivalent structured
  metadata fields.
- Parent and DLC detail pages prefer localized PC release date when present.
- Overview renders separate Main developer, Publishers, and Themes groups plus
  a screenshot gallery below description and technical facts.
- The complete imported collection remains available through Media.
- Theme persistence must permit future library-filter links without a later
  schema migration; linking chips is out of scope.

### Claude's Discretion

- Exact model, migration, handler, task, endpoint and component names.
- How to reuse existing IGDB adapter and scan orchestration patterns.
- Exact validation limits and retry/logging mechanisms, subject to repository
patterns and the immutable-storage boundary.
</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product specification

- `docs/superpowers/specs/2026-09-04-pc-igdb-metadata-and-dlc-media-design.md` - authoritative Phase 13 scope and acceptance criteria.

### Existing component and media contracts

- `.planning/phases/12-dlc-detail-pages-for-local-pc-components/12-CONTEXT.md` - established component isolation decisions.
- `.planning/phases/12-dlc-detail-pages-for-local-pc-components/12-07-PLAN.md` - owned component media persistence conventions.
- `.planning/phases/12-dlc-detail-pages-for-local-pc-components/12-08-PLAN.md` - target-aware metadata matching and media import safety.
- `.planning/phases/12-dlc-detail-pages-for-local-pc-components/12-11-PLAN.md` - component detail UI and media boundaries.

### Repository rules

- `CLAUDE.md` - backend authority, generated OpenAPI contracts, v2 and verification rules.
- `.claude/skills/backend-development/SKILL.md` - backend layering and migration constraints.
- `.claude/skills/frontend-v2-components/SKILL.md` - v2 component rules.
- `.claude/skills/frontend-v2-input/SKILL.md` - responsive and universal-input rules.
- `.claude/skills/frontend-i18n/SKILL.md` - locale parity requirements.
  </canonical_refs>

<specifics>
## Specific Ideas

- No provider response may grant arbitrary filesystem access.
- No downloaded media or IGDB URL is written into the scanned game library.
- Missing IGDB fields are omitted, never invented.
- Microsoft Windows is the sole platform used for PC release selection.
</specifics>

<deferred>
## Deferred Ideas

- Theme chips linking to a library gallery.
- Any source-library mutation or path rewrite.
</deferred>

---

_Phase: 13-pc-igdb-metadata-and-dlc-media_
_Context gathered: 2026-09-04 via specification express path_
