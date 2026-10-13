# Phase 29: Rollenbewusste Metadaten, klickbare Themes und mehrsprachige Übersichtsansicht - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 29 improves the PC game detail overview and related search navigation. It separates developer, publisher, and other participating companies where the existing provider contract supports that distinction; makes themes and genres actionable filters; removes duplicate PC release-date presentation; and provides translated labels and locale-aware date formatting across all 18 supported frontend locales.
</domain>

<decisions>
## Implementation Decisions

### Metadata roles

- Keep provider/source data intact; do not invent publisher regions or roles when the source does not provide them.
- Present the main developer separately from publisher data.
- Present additional companies as “participating companies” or equivalent localized wording.

### Themes and navigation

- Render themes and genres as clickable chips/links, consistent with existing genre and company navigation.
- Filters use stable provider IDs or existing canonical query values internally, never localized display strings.
- A theme/genre filter from a PC game keeps the PC platform constraint.

### Overview layout

- Show the PC release date exactly once in the overview core metadata.
- Keep complete IDs, provider provenance, and raw source details in the metadata tab.

### Localization

- Support all current locales: bg_BG, cs_CZ, de_DE, en_GB, en_US, es_ES, fr_FR, hu_HU, it_IT, ja_JP, ko_KR, pl_PL, pt_BR, ro_RO, ru_RU, tr_TR, zh_CN, zh_TW.
- Translate labels and format dates with the active locale.
- Preserve source names when reliable localized provider values are unavailable.

### Claude's Discretion

- Exact chip component and placement within the existing v2 design system.
- Exact existing search query parameter, provided stable IDs and PC scope are preserved.

### Deferred Ideas

- New provider data model for regional publisher history.
- Manual role editing in the ROM edit dialog.
</decisions>

<canonical_refs>

## Canonical References

- .planning/ROADMAP.md — Phase 29 goal and dependency on Phase 28.
- frontend/src/v2/components/GameDetails/OverviewTab.vue — current overview fields.
- frontend/src/locales/index.ts and frontend/src/stores/language.ts — locale loading and fallback.
