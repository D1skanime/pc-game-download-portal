# Phase 23: Mehrsprachige Steam-Metadaten - Context

**Gathered:** 2026-10-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Persist German, English, and further available Steam text variants per Steam
app and render the variant matching the selected UI language.

</domain>

<decisions>
## Implementation Decisions

### Language fallback

- If a selected UI language is not stored for a game, show the English Steam
  description.

### Metadata scope

- Store multiple available Steam language variants rather than overwriting the
  single display summary.

</decisions>

<specifics>
## Specific Ideas

- Preserve language provenance such as `de` and `en` for each stored variant.

</specifics>

<canonical_refs>

## Canonical References

- `docs/superpowers/specs/2026-10-01-steam-supplemental-metadata-and-dlc-design.md` — Existing Steam metadata and DLC decisions.
- `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md` — Current Steam scan and UAT boundary.

</canonical_refs>
