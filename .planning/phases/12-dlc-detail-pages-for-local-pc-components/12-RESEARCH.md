# Phase 12: DLC detail pages for local PC components - Research

**Researched:** 2026-09-02
**Domain:** Vue 3 v2 route and detail presentation for persisted PC DLC components
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### the agent's Discretion

- Exact page layout, responsive breakpoints, tabs versus sections, cover
  fallback, and the precise metadata fields shown may follow existing v2
  Game Details conventions.

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within the Phase 12 detail-page scope.
</user_constraints>

## Project Constraints (from AGENTS.md)

- Perform work in `/home/d1sk/romm` on the Linux host and preserve unrelated worktree changes. [VERIFIED: codebase instructions]
- New frontend work belongs in `frontend/src/v2/`; frozen v1 surfaces must not be refactored. [VERIFIED: CLAUDE.md]
- Backend response schemas are the API authority, and any changed response schema or route requires regenerated frontend types and a frontend typecheck. [VERIFIED: CLAUDE.md]
- V2 feature UI uses feature composites, `R*` primitives, strict TypeScript, semantic accessible markup, token-only colors, and mouse, touch, keyboard, and gamepad support. [VERIFIED: .claude/skills/frontend-v2-components/SKILL.md, .claude/skills/frontend-v2-input/SKILL.md, .claude/skills/frontend-v2-theming/SKILL.md]
- User-facing copy must use vue-i18n. Any locale key change must be translated in every locale and pass both locale checks. [VERIFIED: .claude/skills/frontend-i18n/SKILL.md]
- Tests travel with changed code. Frontend typecheck, tests, build, and relevant manual v2 UI checks are required before handoff. [VERIFIED: CLAUDE.md, .claude/skills/pre-pr-verification/SKILL.md]
- The external PC source library is read-only. The feature must not create, rename, move, delete, extract, edit, download into, or silently alter source-library content. [VERIFIED: 10-CONTEXT.md, 11-CONTEXT.md]

## Summary

Phase 12 can be implemented as a dedicated v2 route that loads the already-authorized parent `DetailedRomSchema`, resolves exactly one owned `PcComponentSchema` of kind `dlc`, and renders a component-focused detail page. The existing `GET /api/roms/{id}` contract already includes every needed persistent field: component identity, sorted immutable manifest members, independently selected component metadata, and selected RomM-owned local media. No new provider call, persistence shape, migration, or package is required. [VERIFIED: backend/endpoints/roms/**init**.py, backend/endpoints/responses/rom.py, backend/models/rom.py]

The page should be visually composed from the established Game Details language, but must not pretend the DLC is an independent `Rom`. Its parent remains the authorization, routing, and file-delivery identity. A component-specific view model should select the DLC title and summary from `component_metadata`, select only that component's owned cover, background, and gallery media, and render only that component's immutable manifest. Use an explicit placeholder when no selected local cover exists rather than falling back to the parent game's cover or fetching provider artwork. That keeps the identity truthful and honors D-04. [VERIFIED: frontend/src/v2/views/GameDetails.vue, frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue, backend/models/rom.py]

**Primary recommendation:** Add a named nested DLC-detail route under the existing parent ROM URL, backed by the existing parent-ROM read endpoint, and build a `GameDetails` feature composite/view that accepts the parent ROM plus resolved DLC component without mutating or enriching either source.

## Architectural Responsibility Map

| Capability                                                         | Primary Tier     | Secondary Tier     | Rationale                                                                                                                                                                                                                      |
| ------------------------------------------------------------------ | ---------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Parent visibility and component data                               | API / Backend    | Database / Storage | `GET /roms/{id}` applies ROM visibility and serializes persisted component relations. [VERIFIED: backend/endpoints/roms/**init**.py, backend/handler/database/roms_handler.py]                                                 |
| DLC URL parsing and valid-DLC resolution                           | Browser / Client | API / Backend      | Vue Router owns route parameters, while the parent API response remains the trusted component source. [VERIFIED: frontend/src/plugins/router.ts, backend/endpoints/responses/rom.py]                                           |
| DLC identity, cover, description, media, and manifest presentation | Browser / Client | CDN / Static       | The v2 view renders persisted metadata and resolves owned artwork through `FRONTEND_RESOURCES_PATH`. [VERIFIED: frontend/src/v2/views/GameDetails.vue, frontend/src/v2/utils/romArtwork.ts]                                    |
| File download/stream authorization                                 | API / Backend    | Database / Storage | Existing Files UI delegates delivery to existing ROM-file endpoints, which remain governed by the storage policy. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue, backend/endpoints/roms/**init**.py] |

## Standard Stack

### Core

| Library                            | Version            | Purpose                                                            | Why Standard                                                                                                                                                             |
| ---------------------------------- | ------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Vue 3, Vue Router, Pinia, vue-i18n | Repository-managed | Route, reactive parent-ROM state, detail rendering, localized copy | These are the active v2 application stack and current Game Details pattern. [VERIFIED: CLAUDE.md, frontend/src/plugins/router.ts, frontend/src/v2/views/GameDetails.vue] |
| Existing `R*` v2 primitives        | Repository-managed | Navigation, actions, tags, collapsibles, empty and error states    | V2 constitution requires primitives when an applicable primitive exists. [VERIFIED: .claude/skills/frontend-v2-components/SKILL.md]                                      |

### Supporting

| Library                          | Version            | Purpose                                            | When to Use                                                                                                                                                                                      |
| -------------------------------- | ------------------ | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Existing generated OpenAPI types | Repository-managed | `DetailedRomSchema` and `PcComponentSchema` typing | Use directly for the parent ROM and resolved DLC, without hand-written duplicate API types. [VERIFIED: frontend/src/**generated**/models/PcComponentSchema.ts, frontend/src/services/api/rom.ts] |

### Alternatives Considered

| Instead of                                              | Could Use                                 | Tradeoff                                                                                                                                                                                                                                   |
| ------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Dedicated nested client route backed by parent-ROM read | New component-detail backend endpoint     | A new endpoint duplicates a fully sufficient schema and authorization relationship, and increases API, OpenAPI, and test scope with no identified need. [VERIFIED: backend/endpoints/responses/rom.py, backend/endpoints/roms/**init**.py] |
| Selected owned cover or a neutral placeholder           | Parent cover or a live provider-art fetch | Parent artwork obscures DLC identity, and a live fetch violates the review-first, no-silent-fetch decision. [VERIFIED: 12-CONTEXT.md, 11-CONTEXT.md]                                                                                       |

**Installation:** None. This phase requires no external package installation. [VERIFIED: codebase inspection]

## Package Legitimacy Audit

No packages are introduced, so no package legitimacy audit is required. [VERIFIED: codebase inspection]

## Architecture Patterns

### System Architecture Diagram

```text
Overview DLC card or PC Components DLC link
                 |
                 v
  /rom/:rom/dlc/:component route
                 |
                 v
 Vue route guard/view loads GET /api/roms/:rom
                 |
       +---------+----------+
       |                    |
       v                    v
 assert parent visible    resolve component by id + kind === "dlc"
       |                    |
       +---------+----------+
                 |
          valid local DLC?
           /           \
          yes           no
          |             |
          v             v
 component detail     bounded unavailable/not-found state
          |
   +------+------+------+
   |             |      |
   v             v      v
 owned local   component immutable manifest  parent-detail back link
 media URLs    metadata  -> existing file rows
   |
 FRONTEND_RESOURCES_PATH only
```

The decision point must reject a route component that is absent or not `kind === "dlc"`. Do not trust a numeric URL parameter to select arbitrary parent component data. The response already limits component data to a parent ROM that has passed `assert_rom_visible`. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue, backend/endpoints/roms/**init**.py]

### Recommended Project Structure

```text
frontend/src/v2/
├── views/
│   └── PcDlcDetails.vue                 # route-level parent fetch and invalid-DLC state
├── components/GameDetails/
│   ├── PcDlcDetail.vue                  # component-focused detail composite
│   ├── PcDlcFiles.vue                   # manifest presentation or narrow FilesTab reuse
│   ├── PcComponents.vue                 # add explicit DLC link
│   └── RelatedGameCard.vue              # change local DLC destination
└── router/
    ├── routes.ts                         # lazy v2 route registration
    └── routeInventory.ts                 # supported-route inventory
```

Exact component splitting remains discretionary. Keep every new UI composite feature-specific below `components/GameDetails/`; do not add a new primitive unless it is domain-free and independently reusable. [VERIFIED: .claude/skills/frontend-v2-components/SKILL.md]

### Pattern 1: Parent-owned route with a narrow local view model

**What:** Fetch the detailed parent ROM through `romApi.getRom`, then derive the DLC by strict numeric route parameter and `component.kind === "dlc"`. Give presentation components a parent `DetailedRomSchema` and a `PcComponentSchema`, not a forged standalone ROM object. [VERIFIED: frontend/src/services/api/rom.ts, frontend/src/v2/views/GameDetails.vue, frontend/src/**generated**/models/PcComponentSchema.ts]

**When to use:** Every direct visit, refresh, and in-app navigation to the DLC route. This mirrors the initial-entry and parameter-update fetch behavior in `GameDetails.vue`. [VERIFIED: frontend/src/plugins/router.ts, frontend/src/v2/views/GameDetails.vue]

**Example:**

```typescript
// Source: established parent-detail and component-filter patterns
const component = computed(() => {
  const id = Number.parseInt(String(route.params.component), 10);
  if (!Number.isSafeInteger(id)) return null;
  return (
    parentRom.value?.components?.find(
      (item) => item.id === id && item.kind === "dlc",
    ) ?? null
  );
});
```

### Pattern 2: Selected-owned-media-only resolution

**What:** Resolve each media role from `component.local_media`, constructing display URLs only from `owned_path` below `FRONTEND_RESOURCES_PATH`; cache-bust from the parent response timestamp as existing Game Details does. [VERIFIED: frontend/src/v2/views/GameDetails.vue, frontend/src/v2/utils/romArtwork.ts]

**When to use:** Cover, backdrop, and gallery only. A local media selection is durable only while source path and digest agree, and persisted `owned_path` is the display artifact. [VERIFIED: 11-CONTEXT.md, backend/models/rom.py]

**Example:**

```typescript
// Source: GameDetails.vue selected-background convention
const localCover = computed(
  () =>
    component.value?.local_media?.find((entry) => entry.role === "cover") ??
    null,
);
const coverUrl = computed(() =>
  localCover.value
    ? `${FRONTEND_RESOURCES_PATH}/${localCover.value.owned_path}?v=${parentRom.value?.updated_at}`
    : null,
);
```

### Pattern 3: Stable explicit navigation and back context

**What:** Route both local DLC entry points by route name and `rom` plus `component` params. The DLC page back action goes to the exact parent ROM route, preferably retaining its overview context. [VERIFIED: frontend/src/plugins/router.ts, frontend/src/v2/components/GameDetails/RelatedGameCard.vue]

**When to use:** The Overview DLC card and the PC Components list must both link to the same canonical page. Replace the current `?tab=files&component=` local-DLC card target rather than adding a competing destination. [VERIFIED: 12-CONTEXT.md, frontend/src/v2/components/GameDetails/RelatedGameCard.vue]

### Anti-Patterns to Avoid

- **Synthetic standalone DLC `DetailedRom`:** It would invent ROM-level fields and could accidentally expose parent cover, game actions, player state, or unrelated files. Pass parent plus component separately. [VERIFIED: frontend/src/v2/components/GameDetails/RelatedGameCard.vue, frontend/src/v2/views/GameDetails.vue]
- **Use source-relative path as a URL or image source:** Treat it only as displayed metadata or a manifest key. Render artwork from owned paths and use existing file APIs for file content. [VERIFIED: backend/models/rom.py, frontend/src/v2/utils/romArtwork.ts]
- **Reuse all parent media:** Filter strictly by `component.id`; parent `resolveRomArtwork` intentionally aggregates gallery media from every component and therefore is not suitable unchanged for a single-DLC page. [VERIFIED: frontend/src/v2/utils/romArtwork.ts]
- **Leave the current Overview card behavior in place:** It violates D-01 and D-02 by opening the parent Files tab, not an own detail page. [VERIFIED: 12-CONTEXT.md, frontend/src/v2/components/GameDetails/RelatedGameCard.vue]

## Don't Hand-Roll

| Problem                                | Don't Build                                           | Use Instead                                                         | Why                                                                                                                                                                                  |
| -------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Parent visibility and response shaping | New client-side access-control or raw component query | Existing `GET /api/roms/{id}` plus `assert_rom_visible`             | Backend is the authority for visibility and has already loaded component relations. [VERIFIED: backend/endpoints/roms/**init**.py, backend/handler/database/roms_handler.py]         |
| Component file filtering               | New filesystem traversal or browser path matcher      | Existing immutable manifest and `FilesTab` component-filter pattern | Manifest members supply the exact relative members and avoid a new source traversal. [VERIFIED: backend/models/rom.py, frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue] |
| Artwork storage and content reads      | Direct source-image path serving or artwork copying   | Persisted owned media paths under `FRONTEND_RESOURCES_PATH`         | Existing selection stores derived media outside the source root. [VERIFIED: backend/handler/filesystem/resources_handler.py, frontend/src/v2/views/GameDetails.vue]                  |
| Routing state                          | Ad hoc `window.location` paths                        | Named Vue Router route and existing parent route patterns           | Preserves SPA navigation and makes both entry points testable. [VERIFIED: frontend/src/plugins/router.ts, frontend/src/v2/components/GameDetails/RelatedGameCard.vue]                |

**Key insight:** Component identity is a subordinate resource of the parent ROM, not a new ROM. The plan should reuse existing persisted data and delivery paths rather than introducing an alternate data or filesystem path. [VERIFIED: backend/models/rom.py]

## Common Pitfalls

### Pitfall 1: Showing the parent game as the DLC

**What goes wrong:** A generic `GameDetails` reuse can show the base title, parent cover, parent background, and all component gallery images. [VERIFIED: frontend/src/v2/views/GameDetails.vue, frontend/src/v2/utils/romArtwork.ts]

**Why it happens:** Existing `GameDetails.vue` is correctly ROM-centric and its selected background scans all components. [VERIFIED: frontend/src/v2/views/GameDetails.vue]

**How to avoid:** Build a narrow component view model. Use `component.component_metadata?.name` and `.summary`, filter `local_media` to the resolved DLC, and show a neutral selected-media fallback when no DLC cover exists. [VERIFIED: backend/endpoints/responses/rom.py, backend/models/rom.py]

**Warning signs:** A DLC page title equals the parent name despite matched DLC metadata, or its gallery shows images owned by another component. [VERIFIED: codebase inference from frontend/src/v2/views/GameDetails.vue and frontend/src/v2/utils/romArtwork.ts]

### Pitfall 2: Turning a route parameter into authority

**What goes wrong:** A valid parent URL combined with a non-DLC or nonexistent component id yields unrelated component data or a misleading blank page. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue]

**Why it happens:** Existing FilesTab accepts any resolved component filter because that is appropriate for a parent file view. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue]

**How to avoid:** Parse integer safely, resolve only from the returned parent components, require `kind === "dlc"`, and show a bounded unavailable state that links back to the parent. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue, backend/models/rom.py]

**Warning signs:** `/rom/1/dlc/2` renders an update, base, extra, or stale component. [VERIFIED: backend/models/rom.py]

### Pitfall 3: Violating review-first media behavior

**What goes wrong:** The page fetches a fresh provider cover, writes an asset, or uses a source-library image directly merely because the page needs artwork. [VERIFIED: 11-CONTEXT.md, 12-CONTEXT.md]

**Why it happens:** Generic media pages often resolve remote artwork opportunistically, while this milestone explicitly disallows silent selection or source modification. [VERIFIED: 11-CONTEXT.md]

**How to avoid:** Render only already-persisted `local_media.owned_path` and selected component metadata. If no cover is selected, render a normal v2 placeholder. Do not invoke metadata candidate or local-media selection endpoints from page mount. [VERIFIED: backend/endpoints/roms/pc_metadata.py, frontend/src/v2/views/GameDetails.vue]

**Warning signs:** Page load produces a POST, opens provider URLs, or changes `rom_component_local_media` without an explicit review action. [VERIFIED: backend/endpoints/roms/pc_metadata.py, backend/models/rom.py]

### Pitfall 4: Losing file membership semantics

**What goes wrong:** The detail page lists every file from the parent ROM or derives paths by string-prefix matching. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue]

**Why it happens:** Parent `rom.files` is broader than a component, while overlapping textual prefixes can be unsafe or inaccurate. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue]

**How to avoid:** Use the component's manifest-members as exact membership evidence, with each relative path, size, and SHA-256. Reuse the existing component-filter logic only after validating the component is the DLC being displayed. [VERIFIED: backend/models/rom.py, frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue]

**Warning signs:** File count differs from `manifest_members.length`, or a parent base file appears on the DLC page. [VERIFIED: backend/models/rom.py]

## Code Examples

### Canonical local-DLC navigation

```typescript
// Source: adapt RelatedGameCard.vue route push to named DLC-detail route
void router.push({
  name: ROUTES.PC_DLC,
  params: { rom: parentRomId, component: component.id },
});
```

### Component-specific immutable manifest totals

```typescript
// Source: PcComponentSchema manifest contract and PcComponents formatBytes use
const fileCount = computed(() => component.value?.manifest_members.length ?? 0);
const totalBytes = computed(
  () =>
    component.value?.manifest_members.reduce(
      (sum, member) => sum + member.size_bytes,
      0,
    ) ?? 0,
);
```

### Read-only rendering boundary

```typescript
// Source: persisted component local-media schema
const gallery = computed(() =>
  (component.value?.local_media ?? [])
    .filter((entry) => entry.role === "gallery")
    .map((entry) => `${FRONTEND_RESOURCES_PATH}/${entry.owned_path}`),
);
// No POST, provider lookup, source path, or filesystem API is called here.
```

## State of the Art

| Old Approach                                                          | Current Approach                                                | When Changed                      | Impact                                                                                                                                                                                                  |
| --------------------------------------------------------------------- | --------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overview local DLC card opens parent Files tab with `component` query | Dedicated DLC page required by Phase 12                         | Phase 12 decision                 | Move the local-DLC primary action to the canonical component-detail route while retaining parent back navigation. [VERIFIED: 12-CONTEXT.md, frontend/src/v2/components/GameDetails/RelatedGameCard.vue] |
| DLC metadata is absent or attached to base ROM                        | `RomComponentMetadata` is persisted independently per component | PC Phase 10 and 11 implementation | The detail page can use component metadata without overwriting or borrowing base metadata. [VERIFIED: backend/models/rom.py, backend/handler/database/roms_handler.py]                                  |

## Assumptions Log

All recommendations are based on inspected repository code and locked context. No `[ASSUMED]` claims remain. [VERIFIED: codebase inspection]

## Open Questions

1. **Which exact route spelling should be canonical?**
   - What we know: existing details URLs use `rom/:rom`, and the page needs both parent and component identifiers. [VERIFIED: frontend/src/plugins/router.ts]
   - What's unclear: no locked URL spelling is specified.
   - Recommendation: use `rom/:rom/dlc/:component`, register `ROUTES.PC_DLC`, and add it to `v2RouteComponents` plus `routeInventory`; it is readable, nested, and cannot conflict with current player subroutes. [VERIFIED: frontend/src/plugins/router.ts, frontend/src/v2/router/routes.ts]

2. **How should an unmatched DLC title render?**
   - What we know: `component_metadata.name` is optional, while `relative_path` is always persisted. [VERIFIED: backend/endpoints/responses/rom.py, backend/models/rom.py]
   - What's unclear: the context leaves fallback discretionary.
   - Recommendation: use selected metadata name when present, otherwise a localized DLC label plus the component relative path, with no inferred provider title. [VERIFIED: 12-CONTEXT.md, frontend/src/locales/en_US/rom.json]

3. **Should existing FilesTab be extracted or a DLC manifest section built?**
   - What we know: FilesTab already filters parent files by an exact component manifest, but it also owns parent-tab URL state and multi-file selection behavior. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue]
   - What's unclear: whether Phase 12 needs all parent file-tool affordances or only readable local-file evidence.
   - Recommendation: first reuse a presentational child from FilesTab only if it can accept a prevalidated component without route-query coupling; otherwise make a small read-only `PcDlcFiles` feature composite driven by `manifest_members`, preserving exact filename, size, and SHA-256 evidence. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue, frontend/src/v2/components/GameDetails/PcComponents.vue]

## Environment Availability

| Dependency      | Required By                                              | Available                 | Version    | Fallback                                                                                        |
| --------------- | -------------------------------------------------------- | ------------------------- | ---------- | ----------------------------------------------------------------------------------------------- |
| Node.js and npm | Frontend typecheck, Vitest, build                        | Not probed, research-only | Not probed | Verify at implementation start with `node --version` and `npm --version`. [VERIFIED: CLAUDE.md] |
| Python and uv   | Existing backend contract tests, if API behavior changes | Not probed, research-only | Not probed | Verify at implementation start with `uv --version`. [VERIFIED: CLAUDE.md]                       |

No external service, CLI, database migration, provider credential, or package installation is required for the planned route and presentation work. [VERIFIED: codebase inspection]

## Validation Architecture

### Test Framework

| Property           | Value                                                                                                                                                                                                                    |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Framework          | Vitest with Vue Test Utils for v2 components, plus pytest for backend endpoint contract tests. [VERIFIED: frontend/src/v2/components/GameDetails/PcComponents.test.ts, backend/tests/endpoints/roms/test_pc_metadata.py] |
| Config file        | `frontend/vitest.config.ts` and backend pytest configuration. [VERIFIED: codebase file inventory]                                                                                                                        |
| Quick run command  | `cd frontend && npm run test -- src/v2/components/GameDetails` [VERIFIED: CLAUDE.md]                                                                                                                                     |
| Full suite command | `cd frontend && npm run typecheck && npm run test && npm run build` [VERIFIED: CLAUDE.md, .claude/skills/pre-pr-verification/SKILL.md]                                                                                   |

### Phase Behaviors → Test Map

| Behavior                                                                                                         | Test Type                                      | Automated Command                                                                                                | File Exists?                                                                                                                                                                |
| ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overview local-DLC card reaches canonical DLC detail route, never IGDB                                           | Vue unit                                       | `cd frontend && npm run test -- src/v2/components/GameDetails/RelatedGameCard.test.ts`                           | Extend existing test. [VERIFIED: frontend/src/v2/components/GameDetails/RelatedGameCard.test.ts]                                                                            |
| DLC entry in PC Components reaches same route                                                                    | Vue unit                                       | `cd frontend && npm run test -- src/v2/components/GameDetails/PcComponents.test.ts`                              | Extend existing test. [VERIFIED: frontend/src/v2/components/GameDetails/PcComponents.test.ts]                                                                               |
| Route accepts only a DLC belonging to the fetched parent, handles invalid/stale/non-DLC ids safely               | Vue unit                                       | `cd frontend && npm run test -- src/v2/views/PcDlcDetails.test.ts`                                               | Wave 0 gap. [VERIFIED: frontend/src/plugins/router.ts, backend/models/rom.py]                                                                                               |
| Page renders selected component title, summary, owned cover/background/gallery, and never parent component media | Vue unit                                       | `cd frontend && npm run test -- src/v2/components/GameDetails/PcDlcDetail.test.ts`                               | Wave 0 gap. [VERIFIED: backend/endpoints/responses/rom.py]                                                                                                                  |
| Page renders only immutable manifest entries with size and SHA-256 evidence                                      | Vue unit                                       | `cd frontend && npm run test -- src/v2/components/GameDetails/PcDlcFiles.test.ts`                                | Wave 0 gap unless a narrow existing FilesTab child is extracted and tested. [VERIFIED: backend/models/rom.py, frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue] |
| Parent ROM response continues serializing metadata, local media, and manifests                                   | Backend endpoint                               | `cd backend && uv run pytest tests/endpoints/roms/test_pc_metadata.py -x`                                        | Existing coverage, extend only if schema changes. [VERIFIED: backend/tests/endpoints/roms/test_pc_metadata.py]                                                              |
| No source mutation or new media selection occurs when rendering/navigating the detail page                       | Component and existing immutability regression | `cd frontend && npm run test -- src/v2/sourceMutationControls.test.ts` plus relevant backend immutability subset | Existing source mutation guard exists, add a page-specific no-POST assertion. [VERIFIED: frontend/src/v2/sourceMutationControls.test.ts, 10-CONTEXT.md]                     |

### Sampling Rate

- **Per task commit:** focused Vitest tests and `npm run typecheck`. [VERIFIED: .claude/skills/pre-pr-verification/SKILL.md]
- **Per wave merge:** frontend `npm run test` and backend affected pytest subset if backend code changes. [VERIFIED: CLAUDE.md]
- **Phase gate:** frontend build, both themes, 320px through 4K layout, and mouse, touch, keyboard, and gamepad manual pass. [VERIFIED: .claude/skills/pre-pr-verification/SKILL.md, .claude/skills/frontend-v2-input/SKILL.md]

### Wave 0 Gaps

- [ ] `frontend/src/v2/views/PcDlcDetails.test.ts` for direct route and invalid route state. [VERIFIED: codebase file inventory]
- [ ] `frontend/src/v2/components/GameDetails/PcDlcDetail.test.ts` for media and metadata isolation. [VERIFIED: codebase file inventory]
- [ ] `frontend/src/v2/components/GameDetails/PcDlcFiles.test.ts` if a dedicated manifest composite is chosen. [VERIFIED: codebase file inventory]
- [ ] Route inventory test update if the repository has one covering `routeInventory`. [VERIFIED: frontend/src/v2/router/routeInventory.ts]

## Security Domain

### Applicable ASVS Categories

| ASVS Category         | Applies                        | Standard Control                                                                                                                                                                                                                                                                       |
| --------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| V2 Authentication     | Yes                            | Existing `Scope.ROMS_READ` and parent ROM visibility assertion on the only required read endpoint. [VERIFIED: backend/endpoints/roms/**init**.py]                                                                                                                                      |
| V3 Session Management | No new session behavior        | Preserve established authenticated API client behavior. [VERIFIED: frontend/src/services/api/rom.ts]                                                                                                                                                                                   |
| V4 Access Control     | Yes                            | Resolve component exclusively from an already-authorized parent response and reject missing/non-DLC IDs client-side. Backend remains authoritative for parent visibility. [VERIFIED: backend/endpoints/roms/**init**.py, frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue] |
| V5 Input Validation   | Yes                            | Safe integer parse of route params, strict parent membership, strict DLC kind check, and no path input accepted from the route. [VERIFIED: frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue, backend/models/rom.py]                                                        |
| V6 Cryptography       | No new cryptographic operation | Render existing SHA-256 manifest evidence only. [VERIFIED: backend/models/rom.py]                                                                                                                                                                                                      |

### Known Threat Patterns for this stack

| Pattern                                              | STRIDE                            | Standard Mitigation                                                                                                                                                                                                                |
| ---------------------------------------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Component-ID confusion or IDOR-style disclosure      | Information disclosure            | Parent endpoint enforces `assert_rom_visible`; page resolves member only within that response and does not create a global component lookup. [VERIFIED: backend/endpoints/roms/**init**.py, backend/endpoints/roms/pc_metadata.py] |
| Source-path disclosure or traversal                  | Information disclosure, tampering | Never turn `relative_path` into a fetch URL. Use owned media URLs and existing delivery APIs only. [VERIFIED: backend/models/rom.py, frontend/src/v2/utils/romArtwork.ts]                                                          |
| Silent source mutation or metadata/artwork overwrite | Tampering                         | Page performs no selection, provider, or filesystem mutation request. Existing explicit selection endpoints remain outside the route's load path. [VERIFIED: backend/endpoints/roms/pc_metadata.py, 11-CONTEXT.md]                 |
| Unsafe remote media load                             | Information disclosure            | Do not initiate provider artwork fetches. Render only already-owned local media or a neutral fallback. [VERIFIED: 12-CONTEXT.md, backend/models/rom.py]                                                                            |

## Sources

### Primary (HIGH confidence)

- [Phase 12 CONTEXT](12-CONTEXT.md) - locked detail page, navigation, existing-artwork, and source-read-only decisions.
- [Phase 10 CONTEXT](../10-pc-integration-model/10-CONTEXT.md) and [Phase 11 CONTEXT](../11-local-pc-media-and-dlc-navigation/11-CONTEXT.md) - immutable PC component and review-first media contracts.
- [ROM models](../../../backend/models/rom.py) - component, manifest, metadata, and owned local-media persistence.
- [ROM response schema](../../../backend/endpoints/responses/rom.py) and [ROM endpoint](../../../backend/endpoints/roms/__init__.py) - parent-detail payload and authorization behavior.
- [GameDetails view](../../../frontend/src/v2/views/GameDetails.vue), [FilesTab](../../../frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue), [PC components](../../../frontend/src/v2/components/GameDetails/PcComponents.vue), and [Related card](../../../frontend/src/v2/components/GameDetails/RelatedGameCard.vue) - live v2 patterns and current navigation behavior.

### Secondary (MEDIUM confidence)

None.

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, all required stack elements are existing repository dependencies. [VERIFIED: CLAUDE.md]
- Architecture: HIGH, parent detail endpoint and component relationships are already implemented and tested. [VERIFIED: backend/tests/endpoints/roms/test_pc_metadata.py]
- Pitfalls: HIGH, each is derived from current code boundaries and locked source-safety decisions. [VERIFIED: frontend/src/v2/views/GameDetails.vue, 12-CONTEXT.md]

**Research date:** 2026-09-02
**Valid until:** 2026-10-02, unless Phase 11 implementation changes the component response or route contracts first. [VERIFIED: project planning state]
