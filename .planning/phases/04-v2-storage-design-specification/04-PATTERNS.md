# Phase 4: V2 Storage Design Specification - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 2
**Analogs found:** 2 / 2

## Phase Boundary

Phase 4 is documentation-only. Produce the normative design contract and validation handoff. Do not schedule runtime, generated-model, dependency, route, Phase 5, or deployment changes.

Locked flow: platform-led entry, friendly root, relative folder browse, select open folder, fast safety test, explicit save, then queued bounded preview. Keep the active mapping while editing a draft. Platform and settings entries converge on one flow. Display only root identity and server-authorized relative breadcrumbs, never technical or absolute locations.

## File Classification

| New/Modified File                                                      | Role                 | Data Flow                                | Closest Analog                                                          | Match      |
| ---------------------------------------------------------------------- | -------------------- | ---------------------------------------- | ----------------------------------------------------------------------- | ---------- |
| `docs/design/v2-storage-administration.md`                             | design specification | request-response plus event-driven state | `docs/FRONTEND_ARCHITECTURE.md` plus live v2 primitives                 | role-match |
| `.planning/phases/04-v2-storage-design-specification/04-VALIDATION.md` | validation handoff   | batch documentation checks               | `.planning/phases/03-mapping-administration-contracts/03-VALIDATION.md` | exact      |

## Pattern Assignments

### `docs/design/v2-storage-administration.md`

**Documentation analog:** `docs/FRONTEND_ARCHITECTURE.md`

Copy its numbered reference structure: table of contents, overview, architecture, routing, state, data flow, components, theming, i18n, and contracts (`docs/FRONTEND_ARCHITECTURE.md:1-30`, `:365-432`, `:528-625`, `:874-949`, `:1113-1149`).

```markdown
# RomM Frontend Architecture

## Table of Contents

## 1. Overview

## 5. Routing & Navigation

## 7. API & Data Layer

## 12. Theming & Styling
```

Specialize this as scope/non-goals, backend snapshot and mismatch log, overview, guided flow, browser, state/recovery, input, responsive behavior, tokens/primitives, accessible copy, provenance, decision traceability, and acceptance checklist.

**Contract authority:** `.planning/phases/03-mapping-administration-contracts/03-VERIFICATION.md:30-34`

Copy these semantics: root status and browsing are admin-only, relative, contained, paginated, and bounded; mapping lifecycle, test, and preview are typed and source-non-mutating; conflicts use optimistic versions and bounded disclosure; missing mappings never fall back. Phase 1 persists root identity plus normalized relative location only (`01-VERIFICATION.md:23-40`, `:92-100`). Phase 2 errors are bounded without location disclosure (`02-VERIFICATION.md:62-63`, `:85-88`).

**Hierarchy analog:** `frontend/src/v2/components/Settings/SettingsSection.vue:26-36`

```vue
<section class="r-v2-settings-section">
  <header class="r-v2-settings-section__header">
    <RIcon v-if="icon" :icon="icon" size="14" />
    <span class="r-v2-settings-section__title">{{ title }}</span>
    <slot name="header-actions" />
  </header>
  <div class="r-v2-settings-section__body"><slot /></div>
</section>
```

Its style uses semantic surface, border, foreground, and elevation tokens (`:44-71`). Specify one compact `RCard` or section shell with internal regions, not nested status cards. Keep the shell mounted during local state changes.

**Guided-flow analog:** `frontend/src/v2/lib/primitives/RSteps/RSteps.stories.ts:31-40`

```typescript
export const Labelled: Story = {
  args: { current: 2, direction: "forward" },
  render: (args) => ({
    components: { RSteps },
    setup: () => ({ args, steps: [{ label: "Library" }, { label: "Admin" }] }),
    template: `<RSteps v-bind="args" :steps="steps" />`,
  }),
};
```

Specify root, folder, fast test, and save. Preview is post-save background state, never a blocking step. The active mapping stays mounted while a separate draft is edited.

**Folder-browser analog:** `frontend/src/v2/lib/structural/RListItem/RListItem.stories.ts:92-105`, `:141-150`

```vue
<RList>
  <RListItem prepend-icon="mdi-folder" title="Folder" append-icon="mdi-chevron-right" />
</RList>
```

Rows show folder icon, name, safe availability, and chevron. Row activation navigates only. A separate labelled `RBtn` selects the open folder. Use one drill-down model at every breakpoint. Do not specify sizes or child counts.

**State analog:** `frontend/src/v2/views/Settings/LibraryManagement.vue:78-114`

```vue
<RAlert v-if="unreachable" type="error">
  <template #title>{{ t("storage.unreachable") }}</template>
  {{ t("storage.check-connection") }}
</RAlert>
```

Require icon, explicit localized text, and semantic tone. Add one effective local recovery. Loading, empty, pending, partial, unreachable, forbidden, stale, conflict, and error replace only the affected region and preserve focus.

**Route convergence:** `frontend/src/v2/router/routes.ts:21-62`, `:67-78`

The v2 registry owns one lazy view and settings owns nested chrome. Specify one canonical mapping route. Platform and settings actions link to it with platform context.

```typescript
"library-management": () =>
  import("@/v2/views/Settings/LibraryManagement.vue"),
administration: () => import("@/v2/views/Settings/Administration.vue"),
```

**Tokens and constitution:**

- Status tokens: `frontend/src/v2/tokens/index.ts:58-103`.
- Type scale/weights: `:273-304`; spacing/gutter: `:306-321`; radii: `:323-335`; 44px target: `:399-406`.
- Primitive imports and feature placement: `frontend-v2-components/SKILL.md:29-56`, `:65-82`.
- Universal input, focus zones, and overlay scope: `frontend-v2-input/SKILL.md:14-45`.
- Breakpoints `xs <600`, `sm 600-959`, `md 960-1279`, `lg 1280-1919`, `xl >=1920`; use `useBreakpoint` and `data-bp`: `frontend-v2-input/SKILL.md:49-58`.
- Loading, forms, `useCan("app.admin")`, destruction: `frontend-v2-patterns/SKILL.md:12-29`, `:53-88`.

Do not prescribe raw colors, raw layout media queries, raw Vuetify substitutes, or a second focus mechanism.

**Required matrices:**

1. Screen anatomy and priority.
2. API field to presentation, including null semantics.
3. State, copy, icon, tone, region, recovery.
4. Transitions: fast test, save, queued preview.
5. Focus movement, restoration, cancel, gamepad back.
6. Breakpoints xs through xl with one browser model.
7. Token and `R*` primitive mapping.
8. D-01 through D-21 traceability.
9. Principles Provenance Matrix: abstract principle, original RomM interpretation, token/primitive, no-copy confirmation.

### `.planning/phases/04-v2-storage-design-specification/04-VALIDATION.md`

**Analog:** `.planning/phases/03-mapping-administration-contracts/03-VALIDATION.md`

Copy progressive gates: infrastructure, sampling, per-task map, per-plan, per-wave, completion, manual review, sign-off. It uses concrete commands and stops on failure (`03-VALIDATION.md:39-64`, `:96-131`, `:147-161`).

```markdown
- After every task: run the narrowest affected check.
- After every plan: run changed-file checks plus git diff --check.
- After every wave: run the full phase gate.
- Stop on the first failing gate.
```

Retain Phase 4 shell checks and replace provisional task IDs after planning. Verify required sections; D-01 through D-21; fast test, save, queued preview; `pending | partial | complete`; one convergent flow; redacted location presentation; no external copying; no runtime or Phase 5 changes; `git diff --check`; writing rules.

Manual review covers RomM-native originality, responsive usability, universal-input focus continuity, backend fidelity, and meaningful recovery copy.

## Shared Patterns

### Backend authority and redaction

**Sources:** `03-VERIFICATION.md:30-34`, `:69-74`; `04-RESEARCH.md:141-172`

Backend/OpenAPI values are authoritative. Present root name and relative breadcrumbs without reconstructing a location. Keep active, reachable, readable, and non-writable distinct. Preserve Unicode/case. A version conflict offers local reload/review without discarding the draft.

### Active mapping and draft separation

**Sources:** `04-CONTEXT.md:16-27`; `04-RESEARCH.md:133-152`

Existing mapping is read-oriented. Change opens a prefilled draft. Successful fast test enables explicit save. Only the persisted result starts queued preview. Preview never blocks or invalidates saving.

### Stable shell and local regions

**Sources:** `04-CONTEXT.md:35-40`; `frontend-v2-patterns/SKILL.md:21-29`

Keep heading, platform identity, relative breadcrumbs, steps, and navigation stable. Replace only summary, browser, safety, or preview regions. Preserve focus.

### RomM-native provenance

**Sources:** `04-CONTEXT.md:42-48`; `.planning/ROADMAP.md:131-143`

Record abstract observations and original RomM decisions. Confirm no external component, source, asset, screenshot, brand identity, or runtime dependency was copied, modified, or added.

## No Analog Found

No established design-spec directory exists under `docs/`. Use the architecture guide for structure and Phase 4 matrices for provenance and interaction contracts. Do not create a visual artifact or copy an external design.

## Planner Boundaries

- Create only `docs/design/v2-storage-administration.md` and update Phase 4 validation as needed.
- Do not implement runtime code, generated files, dependencies, routes, translations, or Phase 5.
- Never show technical storage locations.
- Keep fast test before save and queued preview after save.
- Converge platform and settings entry on one route and draft model.
- Do not use external screenshots or identity.

## Metadata

**Search scope:** `docs/`, `frontend/src/v2/`, `.claude/skills/frontend-v2-*/`, Phases 1 through 3
**Strong analogs:** 5
**Files scanned:** 24
**Date:** 2026-08-11
