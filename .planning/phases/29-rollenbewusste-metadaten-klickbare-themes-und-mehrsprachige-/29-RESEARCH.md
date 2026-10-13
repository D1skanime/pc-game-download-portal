# Phase 29: Rollenbewusste Metadaten, klickbare Themes und mehrsprachige Übersichtsansicht - Research

**Researched:** 2026-10-13
**Domain:** RomM v2 metadata contracts, gallery filters, localized detail UI
**Confidence:** HIGH for existing codebase boundaries, MEDIUM for the new stable-ID contract

## User Constraints

- Arbeite ausschließlich im kanonischen Linux-Checkout \`/home/d1sk/pc-game-download-portal\`. [VERIFIED: user request]
- Keine Codeänderungen außer dieser Research-Datei. [VERIFIED: user request]
- Keine neuen externen Pakete. [VERIFIED: user request]
- Ziel sind alle 18 vorhandenen Frontend-Locales: \`bg_BG\`, \`cs_CZ\`, \`de_DE\`, \`en_GB\`, \`en_US\`, \`es_ES\`, \`fr_FR\`, \`hu_HU\`, \`it_IT\`, \`ja_JP\`, \`ko_KR\`, \`pl_PL\`, \`pt_BR\`, \`ro_RO\`, \`ru_RU\`, \`tr_TR\`, \`zh_CN\`, \`zh_TW\`. [VERIFIED: user request; codebase frontend/src/locales]
- Release-Daten lokal formatieren. Providerwerte nur lokalisieren, wenn belastbar möglich, sonst stabile Rohwerte behalten. [VERIFIED: user request]
- Die Plattform PC muss bei klickbaren Theme-/Genre-Filtern erhalten bleiben. [VERIFIED: user request]

## Phase Requirements

| ID            | Description                                                                                                                                      | Research Support                                                                                                                                                                                                                                                                                                     |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PH29-ROLE     | Developer, publisher, porting, and other company roles must be displayed from provider data without guessing roles from merged company names.    | IGDB already provides expanded \`involved_companies\` records with role booleans; the current normalizer only persists developer and publisher names. [VERIFIED: backend/handler/metadata/igdb_handler.py; CITED: https://api-docs.igdb.com/]                                                                        |
| PH29-FILTER   | Theme and genre chips must be localized for display, clickable, and represented internally by stable IDs while preserving the PC platform scope. | Existing chips navigate with display strings, the backend filter contract accepts string arrays, and IGDB exposes stable entity IDs for genres/themes. [VERIFIED: frontend/src/v2/components/GameDetails/InfoGrid.vue; backend/endpoints/roms/**init**.py; CITED: https://api-docs.igdb.com/]                        |
| PH29-OVERVIEW | Release and core metadata must have one consistent overview location, with no duplicate PC release display.                                      | \`GameHeader\` renders the first release date and \`OverviewTab\` renders the PC release date, so release information is split across two surfaces. [VERIFIED: frontend/src/v2/components/GameDetails/GameHeader.vue; frontend/src/v2/views/GameDetails.vue; frontend/src/v2/components/GameDetails/OverviewTab.vue] |
| PH29-I18N     | All new and affected UI strings must have parity across all 18 locales, and dates must follow the selected locale.                               | The i18n skill requires every \`en_US\` key in all locale directories; current parity and sorted checks already report baseline failures. [VERIFIED: .claude/skills/frontend-i18n/SKILL.md; verified command output 2026-10-13]                                                                                      |

## Summary

The phase is a contract-alignment change across the backend metadata normalizer, response schemas/generated types, v2 detail components, and gallery URL/filter state. The existing backend receives expanded IGDB company, genre, theme, and release-date objects, but collapses company roles to \`main_developer\`, \`publishers\`, and a merged \`companies\` list. The frontend renders that merged list generically and renders PC fields as plain text. [VERIFIED: backend/handler/metadata/igdb_handler.py; backend/endpoints/responses/rom.py; frontend/src/v2/views/GameDetails.vue]

Use provider-owned stable identities for genres and themes in the API/filter contract, with localized labels as presentation data. The chip URL must carry stable filter IDs and the current RomM platform ID, not the translated label. The current URL composable and backend query handler are string-based, so this requires coordinated API/schema, query, generated-type, store, URL, and component work. Do not derive roles or IDs from display text, and do not translate arbitrary provider strings without a provider-backed locale mapping. [VERIFIED: frontend/src/v2/composables/useGalleryFilterUrl/index.ts; frontend/src/stores/galleryFilter.ts; backend/endpoints/roms/**init**.py; backend/handler/database/roms_handler.py]

Keep release/core metadata in the Overview surface as the canonical block. The detail header should retain title, platform, verification, and personal/action context, but must not repeat the release date once Overview owns it. Use the existing locale utility and browser \`Intl.DateTimeFormat\` behavior, or the established vue-i18n date formatter if the planner centralizes formats. [VERIFIED: frontend/src/v2/views/GameDetails.vue; frontend/src/v2/components/GameDetails/GameHeader.vue; frontend/src/v2/components/GameDetails/OverviewTab.vue; CITED: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat]

**Primary recommendation:** Extend the canonical provider-normalized metadata contract with role-aware company records and stable ID/value records for IGDB genres/themes, then make Overview chips route through the existing URL-backed gallery filter while preserving \`platforms=<rom.platform_id>\`, and finish affected UI copy/date paths across all 18 locales without adding dependencies.

## Architectural Responsibility Map

| Capability                                       | Primary Tier       | Secondary Tier | Rationale                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------ | ------------------ | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Provider company-role extraction                 | API / Backend      | -              | Provider payloads and normalization belong in \`handler/metadata\`; endpoints expose normalized results. [VERIFIED: .claude/skills/backend-development/SKILL.md; backend/handler/metadata/igdb_handler.py]                                                                                           |
| Stable genre/theme identity and filter semantics | Database / Storage | API / Backend  | The filter query must compare persisted canonical identities; API serializes them and frontend only carries them. [VERIFIED: backend/models/rom.py; backend/handler/database/roms_handler.py; backend/endpoints/roms/**init**.py]                                                                    |
| Chip label localization and click target         | Browser / Client   | -              | Vue components choose the active locale and create a RouterLink/query location; this project has no SSR tier. [VERIFIED: frontend/src/v2/components/GameDetails/InfoGrid.vue; frontend/src/v2/composables/useGalleryFilterUrl/index.ts; CITED: https://router.vuejs.org/guide/essentials/navigation] |
| PC-platform-preserving filter navigation         | Browser / Client   | API / Backend  | Browser includes the stable RomM platform ID in URL; backend already applies platform IDs. [VERIFIED: frontend/src/v2/composables/useGalleryFilterUrl/index.ts; backend/handler/database/roms_handler.py]                                                                                            |
| Release/core metadata ownership                  | Browser / Client   | API / Backend  | Backend supplies canonical fields; Overview owns presentation and header stops duplicating release. [VERIFIED: frontend/src/v2/views/GameDetails.vue; frontend/src/v2/components/GameDetails/GameHeader.vue; frontend/src/v2/components/GameDetails/OverviewTab.vue]                                 |
| Locale parity and translated labels              | Browser / Client   | -              | Locale JSON files are loaded by frontend and checked by repository scripts. [VERIFIED: .claude/skills/frontend-i18n/SKILL.md; frontend/src/locales/check_i18n_locales.py]                                                                                                                            |

## Project Constraints (from AGENTS.md)

- Windows checkout is coordination/test-only. GSD planning, implementation, commits, and deployment run in the verified Linux checkout. [VERIFIED: AGENTS.md]
- Before the first write or deployment, verify Linux host, canonical path, Git root/branch/remote, and RomM planning state. The preflight passed for \`/home/d1sk/pc-game-download-portal\`; no Windows project write was used. [VERIFIED: AGENTS.md; remote preflight 2026-10-13]
- Read and follow \`CLAUDE.md\`. [VERIFIED: AGENTS.md]
- v2 is the active frontend; v1 is frozen and must not be refactored. [VERIFIED: CLAUDE.md]
- New frontend work belongs under \`frontend/src/v2/\`; shared stores/services/generated types/locales are canonical. [VERIFIED: CLAUDE.md; .claude/skills/frontend-v2-components/SKILL.md]
- Backend owns the API contract. Response/schema or route changes require OpenAPI type regeneration and frontend typecheck. [VERIFIED: CLAUDE.md; .claude/skills/backend-development/SKILL.md]
- New logic requires tests, and locale changes require parity and sorted checks. [VERIFIED: CLAUDE.md; .claude/skills/frontend-i18n/SKILL.md]
- Code, comments, identifiers, Markdown, commits, and PR text are English, and em-dashes are forbidden. [VERIFIED: CLAUDE.md]
- No external package is planned for this phase. [VERIFIED: user request]

## Standard Stack

### Core

| Library    | Version                              | Purpose                                    | Why Standard                                                                                                                                                                                                 |
| ---------- | ------------------------------------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FastAPI    | 0.121.1 (documented project version) | API routes and OpenAPI contract            | Existing backend endpoint layer and generated contract. [VERIFIED: docs/BACKEND_ARCHITECTURE.md]                                                                                                             |
| SQLAlchemy | 2.0 (project family)                 | ORM, metadata view/query ownership         | Existing Rom/RomMetadata/RomFacets models and portable database layer. [VERIFIED: CLAUDE.md; docs/BACKEND_ARCHITECTURE.md; backend/models/rom.py]                                                            |
| Vue        | \`^3.4.27\`                          | v2 detail and gallery UI                   | Existing frontend dependency and \`<script setup>\` convention. [VERIFIED: frontend/package.json]                                                                                                            |
| TypeScript | \`^5.7.3\`                           | Typed frontend contracts and filter IDs    | Existing strict v2 frontend. [VERIFIED: frontend/package.json; docs/FRONTEND_ARCHITECTURE.md]                                                                                                                |
| vue-i18n   | \`^11.1.10\`                         | UI translations and active locale          | Existing locale loading and \`useI18n()\` pattern. [VERIFIED: frontend/package.json; frontend/src/v2/components/GameDetails/OverviewTab.vue; CITED: https://vue-i18n.intlify.dev/guide/advanced/composition] |
| Vue Router | \`^4.3.2\`                           | Bookmarkable filter links/query navigation | Existing \`RouterLink\` and URL filter composable. [VERIFIED: frontend/package.json; frontend/src/v2/components/GameDetails/InfoGrid.vue; CITED: https://router.vuejs.org/guide/essentials/navigation]       |
| Pinia      | \`^3.0.1\`                           | Gallery filter state                       | Existing \`galleryFilter\` store and v2 gallery store. [VERIFIED: frontend/package.json; frontend/src/stores/galleryFilter.ts; frontend/src/v2/stores/galleryRoms.ts]                                        |
| Vuetify    | \`^3.9.2\`                           | Existing wrapped UI foundation             | v2 uses project \`R*\` wrappers rather than a second UI stack. [VERIFIED: frontend/package.json; .claude/skills/frontend-v2-components/SKILL.md]                                                             |

### Supporting

| Library                 | Version                    | Purpose                                | When to Use                                                                                                                                                                               |
| ----------------------- | -------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vitest                  | \`^4.1.5\`                 | Focused frontend component/store tests | Test Overview, InfoGrid, filter URL round-trips, and localization behavior. [VERIFIED: frontend/package.json]                                                                             |
| pytest                  | Project-managed via \`uv\` | Backend normalizer/query/schema tests  | Test role extraction, stable-ID normalization, filter preservation, and provider fallbacks. [VERIFIED: CLAUDE.md; .claude/skills/backend-development/SKILL.md]                            |
| \`Intl.DateTimeFormat\` | Runtime API                | Locale-sensitive release formatting    | Use for release dates after converting the stored Unix timestamp correctly. [CITED: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat] |

### Alternatives Considered

| Instead of                              | Could Use                        | Tradeoff                                                                                                                                                                                              |
| --------------------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Existing URL-backed Pinia filter state  | Local component-only chip state  | Reject. It loses bookmarkability and bypasses existing gallery fetch/invalidation. [VERIFIED: .claude/skills/frontend-v2-patterns/SKILL.md; frontend/src/v2/composables/useGalleryFilterUrl/index.ts] |
| Provider stable IDs with display labels | Display strings as filter values | Reject. Translated labels and provider spelling changes are not stable identities. [VERIFIED: frontend/src/v2/components/GameDetails/InfoGrid.vue; user request]                                      |
| Existing locale files and \`useI18n\`   | New translation package          | Reject. It violates the no-new-package constraint and duplicates current i18n. [VERIFIED: user request; .claude/skills/frontend-i18n/SKILL.md]                                                        |
| Existing normalized provider contract   | Browser requests to providers    | Reject. Provider access is backend-owned and IGDB documents browser CORS restrictions. [VERIFIED: docs/BACKEND_ARCHITECTURE.md; CITED: https://api-docs.igdb.com/]                                    |

**Installation:** None. Use existing lockfile, installed container dependencies, and project scripts. [VERIFIED: user request; frontend/package.json]

**Version verification:** The canonical host has no host \`node\`/\`npm\`; frontend tools are available in \`romm-dev\` (\`node v24.16.0\`, \`npm 11.13.0\`). Registry \`npm view\` returned an unusable \`0.1.0\` response for all queried packages, so manifest versions are the reliable project-version evidence in this session. [VERIFIED: remote environment audit 2026-10-13]

## Architecture Patterns

### System Architecture Diagram

\`\`\`text
IGDB/provider payloads
|
v
backend metadata normalizer

- role-aware companies
- stable genre/theme identity + provider label
- PC release date from Windows release record
  |
  v
  Rom/RomMetadata/RomFacets + detailed/list response schemas
  |
  +--> generated TypeScript models
  | |
  | v
  | GameDetails -> Overview -> localized roles/dates/chips
  |
  +--> gallery filter-values and filter query
  |
  v
  URL: stable genre/theme IDs + platforms=[Rom platform ID]
  |
  v
  Pinia galleryFilter -> backend /roms -> PC-scoped results
  \`\`\`

The diagram separates provider normalization from UI localization and query execution. Display labels must never be the only identity crossing the URL/API boundary. [VERIFIED: existing layered architecture; user request; CITED: https://api-docs.igdb.com/]

### Recommended Project Structure

\`\`\`text
backend/
├── handler/metadata/igdb_handler.py # provider role/ID normalization
├── models/rom.py # canonical metadata/facet ownership
├── handler/database/roms_handler.py # filter query and sidecars
├── endpoints/responses/rom.py # response/OpenAPI contract
└── tests/ # normalizer, schema, query regressions

frontend/src/
├── v2/views/GameDetails.vue # platform context and overview inputs
├── v2/components/GameDetails/OverviewTab.vue
├── v2/components/GameDetails/InfoGrid.vue # localized clickable chips
├── v2/components/GameDetails/GameHeader.vue# no duplicate release display
├── v2/composables/useGalleryFilterUrl/ # stable URL round-trip
├── stores/galleryFilter.ts # typed selected identity
├── v2/stores/galleryRoms.ts # API fetch/invalidation
├── **generated**/ # regenerated OpenAPI types
└── locales/*/rom.json # all 18 locale values
\`\`\`

The structure follows the existing endpoint -> handler -> model and v2 component -> canonical store/service patterns. [VERIFIED: .claude/skills/backend-development/SKILL.md; .claude/skills/frontend-v2-components/SKILL.md; docs/BACKEND_ARCHITECTURE.md]

### Pattern 1: Role-aware normalization

**What:** Read \`involved_companies\` role booleans, preserve company identity/name together, and map only explicit roles. \`developer\` can feed the existing primary field; \`publisher\`, \`porting\`, and \`supporting\` remain separate canonical lists. [VERIFIED: backend/handler/metadata/igdb_handler.py; CITED: https://api-docs.igdb.com/]

**When to use:** For provider payloads with explicit roles. Providers exposing only merged company strings must keep the raw list and not invent roles. [VERIFIED: backend/handler/metadata/igdb_handler.py; backend/handler/metadata/gamelist_handler.py; backend/handler/metadata/flashpoint_handler.py]

\`\`\`python
def role_companies(records, role):
values = []
for record in records:
if record.get(role) is not True:
continue
company = record.get("company")
if not isinstance(company, dict):
continue
company_id, name = company.get("id"), company.get("name")
if isinstance(company_id, int) and isinstance(name, str) and name.strip():
values.append({"id": company_id, "label": name.strip()})
return dedupe_by_id(values)
\`\`\`

This is an implementation shape, not a claim that the exact helper/type already exists. [CITED: https://api-docs.igdb.com/; ASSUMED]

### Pattern 2: Stable filter identity with localized presentation

**What:** Model a filter option as \`{ id, label }\` or an equivalent typed shape, keep \`id\` in Pinia and the URL, and resolve \`label\` at render time. Backend queries must accept/resolve IDs, not translated labels. [VERIFIED: user request; CITED: https://api-docs.igdb.com/; ASSUMED for exact response shape]

**When to use:** Theme and genre chips with stable provider IDs. If no trustworthy ID exists, do not synthesize one from a translated label; retain the raw provider value and mark it non-localizable. [VERIFIED: user request; current schemas; ASSUMED fallback shape]

\`\`\`ts
type MetadataFilterOption = { id: number | string; label: string };

const searchLocation = (kind: "genres" | "themes", option: MetadataFilterOption, platformId: number) => ({
name: ROUTES.SEARCH,
query: { [kind]: String(option.id), platforms: String(platformId) },
});
\`\`\`

Use \`RouterLink\` so navigation and keyboard activation remain native. [VERIFIED: frontend/src/v2/components/GameDetails/InfoGrid.vue; frontend/src/v2/composables/useGalleryFilterUrl/index.ts; CITED: https://router.vuejs.org/guide/essentials/navigation]

### Pattern 3: One canonical release/core metadata block

**What:** Pass one locale-formatted release value and core metadata into Overview. Remove the release date from the header render/data path while keeping platform, verification, tags, and actions. Apply the same ownership decision to \`PcDlcDetail.vue\`, which currently repeats PC release, developer, publishers, and themes. [VERIFIED: frontend/src/v2/components/GameDetails/GameHeader.vue; frontend/src/v2/views/GameDetails.vue; frontend/src/v2/components/GameDetails/OverviewTab.vue; frontend/src/v2/components/GameDetails/PcDlcDetail.vue]

\`\`\`ts
const formatReleaseDate = (timestampSeconds: number | null, locale: string) =>
timestampSeconds
? new Intl.DateTimeFormat(toBrowserLocale(locale), {
day: "2-digit", month: "short", year: "numeric",
}).format(new Date(timestampSeconds * 1000))
: null;
\`\`\`

The seconds-to-milliseconds conversion must be explicit. Existing parent and PC component paths use mixed units, so tests must cover both. [VERIFIED: frontend/src/v2/views/GameDetails.vue; frontend/src/v2/components/GameDetails/OverviewTab.vue; backend/handler/metadata/igdb_handler.py; CITED: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat]

### Anti-Patterns to Avoid

- **Filtering by translated label:** It breaks when locale changes. Send stable IDs. [VERIFIED: user request; current InfoGrid]
- **Inferring publisher/porting/supporting from \`companies\`:** The merged field is roleless for many providers. [VERIFIED: frontend/src/v2/views/GameDetails.vue; backend/handler/metadata/*.py]
- **Keeping release in header and Overview:** It recreates the duplicate PC-release problem. [VERIFIED: current files]
- **Calling providers from browser:** Provider access belongs to backend adapters/handlers. [VERIFIED: docs/BACKEND_ARCHITECTURE.md; CITED: https://api-docs.igdb.com/]
- **Translation map keyed by English text:** It cannot reliably distinguish provider values or survive updates. Key trusted localization by provider ID and locale, with raw fallback. [ASSUMED]

## Don't Hand-Roll

| Problem                        | Don't Build                                       | Use Instead                                                    | Why                                                                                                                                                                                                                      |
| ------------------------------ | ------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Locale-sensitive dates         | Per-locale month tables or string concatenation   | \`Intl.DateTimeFormat\` or existing vue-i18n date formatting   | Runtime locale rules are standardized and the project supports 18 locales. [CITED: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat; VERIFIED: frontend/src/locales] |
| Bookmarkable filter navigation | Component-local state plus duplicate router logic | \`useGalleryFilterUrl\`, \`galleryFilter\`, and \`RouterLink\` | Existing synchronization handles hydration, back/forward, debounce, and API invalidation. [VERIFIED: frontend/src/v2/composables/useGalleryFilterUrl/index.ts; frontend/src/v2/components/Gallery/GalleryShell.vue]      |
| Provider role parsing          | Regex/string heuristics over company names        | Explicit provider role fields                                  | IGDB supplies boolean role fields; name heuristics are not authoritative. [CITED: https://api-docs.igdb.com/; VERIFIED: backend/handler/metadata/igdb_handler.py]                                                        |
| Stable provider identities     | Hashing translated labels in browser              | Provider IDs carried from backend normalization                | IGDB entities expose IDs, names, and slugs; browser is not the identity authority. [CITED: https://api-docs.igdb.com/; VERIFIED: backend/adapters/services/igdb_types.py]                                                |
| Locale parity                  | Manual spot-check of 18 files                     | \`check_i18n_locales.py\` and \`check_i18n_sorted.py\`         | Repository has canonical parity/sort gates. [VERIFIED: .claude/skills/frontend-i18n/SKILL.md]                                                                                                                            |

**Key insight:** The hard part is preserving one identity across provider normalization, portable persistence/querying, generated API types, URL state, and localized presentation. [VERIFIED: existing architecture; user request]

## Common Pitfalls

### Pitfall 1: Losing PC scope when a chip opens Search

**What goes wrong:** Current \`InfoGrid\` creates a query containing only the selected filter, so navigation from a PC detail can become cross-platform. [VERIFIED: frontend/src/v2/components/GameDetails/InfoGrid.vue]

**Why it happens:** Platform context is held by the detail ROM, while the reusable chip component has no platform ID input. [VERIFIED: frontend/src/v2/components/GameDetails/InfoGrid.vue; frontend/src/v2/views/GameDetails.vue]

**How to avoid:** Include \`platforms=<rom.platform_id>\` in the location, or provide a platform-preserving location builder from Overview. Test PC and non-PC navigation. [VERIFIED: user request; frontend/src/v2/composables/useGalleryFilterUrl/index.ts]

**Warning signs:** A generated URL has \`genres\`/\`themes\` but no \`platforms\`, or results include non-PC platforms after clicking a PC detail chip. [ASSUMED test oracle]

### Pitfall 2: Stable IDs discarded by normalization

**What goes wrong:** Current IGDB normalization stores only names for \`genres\` and \`themes\`, and only names for companies. [VERIFIED: backend/handler/metadata/igdb_handler.py]

**Why it happens:** \`RomMetadataSchema\`, \`PcComponentMetadataSchema\`, \`RomFiltersDict\`, and generated frontend models define these values as string arrays. [VERIFIED: backend/endpoints/responses/rom.py; frontend/src/**generated**/models/RomMetadataSchema.ts]

**How to avoid:** Change the contract in one backend-owned path, update persistence/view/facet/query behavior, regenerate OpenAPI types, and typecheck. Do not add a frontend-only cast. [VERIFIED: CLAUDE.md; .claude/skills/backend-development/SKILL.md]

**Warning signs:** \`as unknown as\`, URL labels instead of IDs, or IDs in details but absent from filter sidecars. [VERIFIED: .claude/skills/frontend-v2-components/SKILL.md; inferred verification rule]

### Pitfall 3: Overclaiming roles for providers without roles

**What goes wrong:** A merged \`companies\` list is displayed under Publisher or Porting without source evidence. [VERIFIED: backend/handler/metadata/gamelist_handler.py; backend/handler/metadata/flashpoint_handler.py]

**Why it happens:** Providers normalize to a common string-only shape, while IGDB has richer role records. [VERIFIED: backend/handler/metadata/*.py; backend/handler/metadata/igdb_handler.py]

**How to avoid:** Render role sections only when explicit role data exists. Keep generic fallback clearly labeled and retain raw provider values. [VERIFIED: user request; existing provider contracts]

**Warning signs:** A fixture with only \`companies=["Acme"]\` causes \`publishers=["Acme"]\`, or a refresh changes a role without explicit source evidence. [ASSUMED test oracle]

### Pitfall 4: Seconds/milliseconds mismatch

**What goes wrong:** A valid PC release timestamp renders in 1970 or far in the future. [VERIFIED: current mixed date conversions]

**Why it happens:** \`first_release_date\` and \`pc_release_date\` have different current conversion paths. [VERIFIED: frontend/src/v2/views/GameDetails.vue; frontend/src/v2/components/GameDetails/OverviewTab.vue; backend/handler/metadata/igdb_handler.py]

**How to avoid:** Define and test the unit at the API boundary, convert exactly once, and use a shared formatter. [VERIFIED: user request; current code inspection]

**Warning signs:** Locale snapshots pass but the displayed year is incorrect. [ASSUMED test oracle]

### Pitfall 5: Locale baseline obscures regressions

**What goes wrong:** Current locale check fails because 17 locales lack \`refreshing-media\`, \`account-exists\`, and three scan keys; sorted check reports existing unsorted files. [VERIFIED: command output 2026-10-13]

**Why it happens:** Phase 28 left baseline parity/sort debt. [VERIFIED: .planning/phases/28-youtube-vorschau-steam-app-id-und-pc-save-medienverwaltung/28-UAT.md]

**How to avoid:** Capture the baseline, add every Phase 29 key to all 18 locales, run both gates, and distinguish pre-existing from new failures. Planner must decide whether to close baseline debt here. [VERIFIED: .claude/skills/frontend-i18n/SKILL.md; phase 28 UAT]

## Code Examples

### Existing clickable metadata chip

\`\`\`vue
<router-link
:to="searchLocation(section.filter, item)"
class="r-v2-det-infogrid__chip r-v2-det-infogrid__chip--link"

>

{{ item }}
</router-link>
\`\`\`

This existing pattern supplies native link semantics and is the correct place to inject stable IDs and the preserved platform query. [VERIFIED: frontend/src/v2/components/GameDetails/InfoGrid.vue; CITED: https://router.vuejs.org/guide/essentials/navigation]

### Existing locale-aware date pattern

\`\`\`ts
new Date(Number(timestamp)).toLocaleDateString(toBrowserLocale(locale.value), {
day: "2-digit",
month: "short",
year: "numeric",
});
\`\`\`

The project already uses this in \`GameDetails.vue\` and \`GameListRow.vue\`. Standardize timestamp units before reuse. [VERIFIED: frontend/src/v2/views/GameDetails.vue; frontend/src/v2/components/Gallery/GameListRow.vue; CITED: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat]

### Existing stable platform URL encoding

\`\`\`ts
setList("platforms", selectedPlatforms.value.map((p) => String(p.id)));
\`\`\`

The platform filter already serializes database IDs rather than labels. Genre/theme filters should follow the same identity principle. [VERIFIED: frontend/src/v2/composables/useGalleryFilterUrl/index.ts]

## State of the Art

| Old Approach                                      | Current Approach                                                                      | When Changed          | Impact                                                                                               |
| ------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------- |
| Display-string genre/theme query values           | Stable provider identity plus localized display label                                 | Phase 29 target       | URL/filter state survives locale changes and label updates. [VERIFIED: user request; ASSUMED impact] |
| Merged roleless company display                   | Explicit developer/publisher/porting/supporting sections where source evidence exists | Phase 29 target       | Prevents unsupported role claims. [VERIFIED: user request; CITED: https://api-docs.igdb.com/]        |
| Release date in header and PC release in Overview | One Overview/core metadata block                                                      | Phase 29 target       | Removes duplicate PC release presentation. [VERIFIED: current files; user request]                   |
| New UI keys only in English/subset                | All 18 locale directories plus parity/sort gates                                      | Existing project rule | Prevents missing-key UI. [VERIFIED: .claude/skills/frontend-i18n/SKILL.md]                           |

**Deprecated/outdated:**

- Passing translated or raw display strings as the only filter identity. [VERIFIED: user request; current InfoGrid]
- Treating merged \`companies\` as a developer/publisher role contract. [VERIFIED: frontend/src/v2/views/GameDetails.vue]

## Assumptions Log

| #   | Claim                                                                                                     | Section               | Risk if Wrong                                                                                               |
| --- | --------------------------------------------------------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------- |
| A1  | Stable genre/theme options should use an \`{id, label}\`-like object and carry IDs through URL/API.       | Architecture Patterns | Exact contract could instead require provider-specific ID arrays, affecting migrations and generated types. |
| A2  | Providers without explicit company roles should not populate role-specific UI from generic company lists. | Pattern 1, Pitfalls   | Product owners may want a deliberate fallback policy that must be specified.                                |
| A3  | Canonical release/core metadata should be Overview for parent and PC component detail.                    | Pattern 3             | Product could instead make header authoritative, but duplicate still must be removed.                       |
| A4  | Current PC timestamps are Unix seconds while parent \`first_release_date\` path receives milliseconds.    | Pattern 3, Pitfall 4  | Wrong unit assumption would create date regressions; verify with fixtures/API examples.                     |
| A5  | Baseline locale debt needs an explicit planner decision.                                                  | Pitfall 5             | If out of scope, phase gate must document exact baseline and new-key evidence.                              |

## Open Questions (RESOLVED)

1. **What is the canonical stable-ID schema for mixed providers?**
   - **Decision:** Canonical facet IDs are provider-qualified strings in the form provider:<numeric>, for example igdb:31. Store and transmit this ID separately from the display label and raw provider value. Numeric IDs without a provider prefix are not canonical because providers can collide.
   - **Plan impact:** Backend normalization, API schemas, query parsing, generated types, Pinia state, and URLs must all preserve the exact provider-qualified string.

2. **Should only IGDB genres/themes be localized?**
   - **Decision:** Provider names and raw labels are not translated unless a verified provider mapping exists for the active locale. Application-owned labels are translated through the locale files. Without verified mapping, render the source label and retain its provider identity.
   - **Plan impact:** Locale work must not invent translations for provider values or use translated text as filter identity.

3. **Does the phase close existing locale parity/sorted failures?**
   - **Decision:** Capture the exact parity and sort baseline before locale edits, then rerun each gate independently and verify that Phase 29 introduces no new parity or sort debt. The phase must not claim baseline closure unless a task explicitly plans and verifies cleanup of the pre-existing failures.
   - **Plan impact:** Final gates use separate baseline capture, per-gate commands, and a baseline-delta classification for pre-existing failures, unavailable tools, and new failures.

4. **Which company roles belong in “other companies”?**
   - **Decision:** Preserve and present explicit developer, publisher, porting, and supporting roles independently when the provider supplies them. A company with no verified role remains generic/neutral and is not assigned to a role by name, ordering, or UI grouping.
   - **Plan impact:** Backend records must retain role evidence, and frontend labels must not merge or infer roles from generic company data.

## Environment Availability

| Dependency               | Required By                    | Available              | Version                                 | Fallback                                           |
| ------------------------ | ------------------------------ | ---------------------- | --------------------------------------- | -------------------------------------------------- |
| Linux canonical checkout | All GSD/research writes        | yes                    | \`/home/d1sk/pc-game-download-portal\`  | -                                                  |
| Docker                   | Dev stack and frontend tooling | yes                    | \`romm-dev\` running                    | -                                                  |
| Node.js                  | Frontend tests/typecheck/build | host no, container yes | \`v24.16.0\` in \`romm-dev\`            | Run frontend commands via \`docker exec romm-dev\` |
| npm                      | Frontend scripts               | host no, container yes | \`11.13.0\` in \`romm-dev\`             | Use container npm, no package install              |
| Python 3                 | Locale/backend checks          | yes                    | host \`3.10.12\`, container \`3.13.12\` | Prefer project container runtime                   |
| uv                       | Backend workflow               | host no                | -                                       | Use project backend container/venv                 |
| trunk                    | Format/lint                    | host no                | -                                       | Locate project binary or document blocker          |
| MariaDB/Valkey           | Integration/API tests          | yes                    | MariaDB 11.3.2, Valkey 8 images         | -                                                  |

Missing dependencies with fallback:

- Host Node/npm/uv/trunk are unavailable, but frontend tools and Python 3.13 are available in \`romm-dev\`. [VERIFIED: remote environment audit 2026-10-13]

Missing dependencies with no fallback:

- None identified for code-level planning. Full lint verification may still require locating the project Trunk binary. [VERIFIED: remote environment audit 2026-10-13]

## Validation Architecture

### Test Framework

| Property           | Value                                                                                                                                                             |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framework          | Frontend Vitest \`^4.1.5\`; backend pytest via project \`uv\` workflow. [VERIFIED: frontend/package.json; CLAUDE.md]                                              |
| Config file        | Frontend Vitest config under \`frontend/\`; backend \`backend/pytest.ini\`. [VERIFIED: codebase inventory]                                                        |
| Quick run command  | \`docker exec romm-dev sh -lc 'cd /app/frontend && npm run test -- OverviewTab InfoGrid useGalleryFilterUrl'\` [VERIFIED: package script; container availability] |
| Full suite command | Frontend test/typecheck/build plus locale checks, affected backend pytest, and Trunk gates. [VERIFIED: frontend/package.json; CLAUDE.md; project skills]          |

### Phase Requirements -> Test Map

| Req ID        | Behavior                                                                                                       | Test Type             | Automated Command                                                                                                                  | File Exists?                                                               |
| ------------- | -------------------------------------------------------------------------------------------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| PH29-ROLE     | Explicit provider company roles map to developer/publisher/porting/supporting without populating absent roles. | unit                  | \`backend/.venv/bin/pytest -q tests/handler/metadata tests/models/test_pc_igdb_metadata.py -k 'company or metadata'\`              | Existing PC metadata tests; add role tests in Wave 0. [VERIFIED: codebase] |
| PH29-FILTER   | Stable IDs survive detail chip -> URL -> Pinia -> backend query round trip and retain PC platform.             | component/integration | Frontend \`InfoGrid\`/URL tests plus affected backend rom query tests.                                                             | Add stable-ID/platform-preservation tests. [VERIFIED: codebase search]     |
| PH29-OVERVIEW | Release/core metadata renders once in Overview and is absent from duplicate header/component facts.            | component             | \`docker exec romm-dev sh -lc 'cd /app/frontend && npm run test -- OverviewTab GameHeader PcDlcDetail'\`                           | Existing tests; add duplicate-absence assertions. [VERIFIED: codebase]     |
| PH29-I18N     | New labels exist in all 18 locales and release dates follow active locale.                                     | script/component      | \`python3 frontend/src/locales/check_i18n_locales.py && python3 frontend/src/locales/check_i18n_sorted.py\` plus date/label tests. | Scripts exist; add targeted tests. [VERIFIED: codebase]                    |

### Sampling Rate

- **Per task commit:** affected Vitest/backend subset and locale checks when locale files change. [VERIFIED: project testing rules]
- **Per wave merge:** frontend typecheck, focused backend tests, and generated-type consistency. [VERIFIED: CLAUDE.md; .claude/skills/pre-pr-verification/SKILL.md]
- **Phase gate:** full frontend suite, typecheck/build, affected backend suite, locale parity/sort, \`trunk fmt && trunk check\`, and browser UAT in both themes plus mouse/touch/keyboard/gamepad paths. [VERIFIED: .claude/skills/pre-pr-verification/SKILL.md]

### Wave 0 Gaps

- [ ] Backend fixtures for each explicit company role, including absent publisher/porting/supporting flags. [VERIFIED: current test inventory]
- [ ] API/schema tests for provider-qualified stable genre/theme identities and raw-label fallback. [VERIFIED: current schemas are string-only]
- [ ] Frontend \`InfoGrid\` test for localized label, stable URL ID, and preserved PC platform ID. [VERIFIED: current test gap]
- [ ] \`useGalleryFilterUrl\` round-trip test for stable IDs and platform query preservation. [VERIFIED: current test gap]
- [ ] Overview/GameHeader/PcDlcDetail tests asserting one release/core metadata owner. [VERIFIED: current files/tests]
- [ ] Locale fixture proving two locales format the same timestamp differently while raw provider values remain unchanged. [ASSUMED gap]
- [ ] Decide whether baseline missing locale keys and unsorted files are in scope before final gate. [VERIFIED: current gate output; ASSUMED planning decision]

## Security Domain

### Applicable ASVS Categories

| ASVS Category         | Applies | Standard Control                                                                                                                                                         |
| --------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| V2 Authentication     | yes     | Preserve existing protected routes and read scopes; add no anonymous metadata endpoint. [VERIFIED: backend endpoint patterns]                                            |
| V3 Session Management | yes     | Reuse authenticated Axios/API session; do not put provider credentials in browser. [VERIFIED: docs/BACKEND_ARCHITECTURE.md]                                              |
| V4 Access Control     | yes     | Enforce ROM visibility and platform scope server-side; URL IDs are untrusted. [VERIFIED: backend/handler/auth/dependencies.py; backend/handler/database/roms_handler.py] |
| V5 Input Validation   | yes     | Validate provider-qualified IDs, filter kind, logic operator, and platform IDs at API boundary. [VERIFIED: backend/endpoints/roms/**init**.py; backend skill]            |
| V6 Cryptography       | no      | No cryptographic feature is introduced. [VERIFIED: phase scope]                                                                                                          |

### Known Threat Patterns for FastAPI + Vue

| Pattern                                 | STRIDE                 | Standard Mitigation                                                                                                           |
| --------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Query-string filter tampering           | Tampering / Elevation  | Revalidate IDs and platform scope in backend. [VERIFIED: backend architecture]                                                |
| Provider value rendered as markup       | Tampering              | Render labels as Vue text, never \`v-html\`. [VERIFIED: frontend v2 rules]                                                    |
| Browser-to-provider credential leakage  | Information disclosure | Keep provider calls in backend adapters/handlers. [VERIFIED: docs/BACKEND_ARCHITECTURE.md; CITED: https://api-docs.igdb.com/] |
| Locale fallback changes filter identity | Tampering              | Keep identity separate from localized label and raw fallback. [ASSUMED threat assessment]                                     |

## Sources

### Primary (HIGH confidence)

- \`AGENTS.md\`, \`CLAUDE.md\` - Linux boundary, v1/v2 rules, API ownership, tests, language constraints. [VERIFIED: file read]
- \`frontend/src/v2/components/GameDetails/OverviewTab.vue\`, \`GameHeader.vue\`, \`InfoGrid.vue\`, \`PcDlcDetail.vue\`, \`frontend/src/v2/views/GameDetails.vue\` - current overview, duplicate release, role/theme rendering, chip navigation. [VERIFIED: codebase]
- \`backend/handler/metadata/igdb_handler.py\`, \`backend/adapters/services/igdb_types.py\`, \`backend/models/rom.py\`, \`backend/endpoints/responses/rom.py\`, \`backend/handler/database/roms_handler.py\` - provider roles, normalization, persistence, response, and filter contracts. [VERIFIED: codebase]
- \`frontend/src/v2/composables/useGalleryFilterUrl/index.ts\`, \`frontend/src/stores/galleryFilter.ts\`, \`frontend/src/v2/stores/galleryRoms.ts\` - URL/store/API filter behavior. [VERIFIED: codebase]
- \`frontend/src/locales/check_i18n_locales.py\`, \`check_i18n_sorted.py\`, \`.claude/skills/frontend-i18n/SKILL.md\` - 18-locale parity/sort rules and current baseline failures. [VERIFIED: codebase and command output]
- [IGDB API documentation](https://api-docs.igdb.com/) - entity IDs, expanded genre/theme records, involved-company role booleans, release dates, and browser CORS limitation. [CITED: https://api-docs.igdb.com/]
- [Vue I18n Composition API](https://vue-i18n.intlify.dev/guide/advanced/composition) - \`useI18n\`, \`t\`, locale, and fallback behavior. [CITED: https://vue-i18n.intlify.dev/guide/advanced/composition]
- [Vue Router navigation](https://router.vuejs.org/guide/essentials/navigation) - RouterLink/query navigation and URL behavior. [CITED: https://router.vuejs.org/guide/essentials/navigation]
- [MDN Intl.DateTimeFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat) - locale-sensitive date formatting. [CITED: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat]

### Secondary (MEDIUM confidence)

- \`.planning/phases/28-youtube-vorschau-steam-app-id-und-pc-save-medienverwaltung/RESEARCH.md\` and \`28-UAT.md\` - phase 28 patterns and current Linux Dev/container evidence. [VERIFIED: phase artifacts]
- \`docs/FRONTEND_ARCHITECTURE.md\`, \`docs/BACKEND_ARCHITECTURE.md\` - project architecture summaries. [VERIFIED: codebase docs]

### Tertiary (LOW confidence)

- None used for implementation claims. The exact provider-qualified stable-ID schema remains an open decision, not a verified existing capability. [VERIFIED: research scope]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - manifest, project docs, and code usage agree; npm registry verification was unavailable/unreliable. [VERIFIED: frontend/package.json; docs; environment audit]
- Architecture: HIGH - current files and project skills show ownership boundaries; exact stable-ID shape is MEDIUM. [VERIFIED: codebase]
- Pitfalls: HIGH for duplicate release, string filters, role collapse, timestamp units, and locale baseline; MEDIUM for mixed-provider fallback policy. [VERIFIED: codebase and command output; ASSUMED where noted]

**Research date:** 2026-10-13
**Valid until:** 2026-11-12 for stable project architecture; 2026-10-20 for package/provider documentation and registry availability.
