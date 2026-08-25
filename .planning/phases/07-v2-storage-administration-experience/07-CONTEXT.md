# Phase 7: V2 Storage Administration Experience - Context

**Gathered:** 2026-08-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the active v2 administrator interface for viewing existing storage roots, safely browsing within a selected root, and creating, changing, testing, previewing, and removing platform mappings. The interface consumes the contracts from Phases 4-6, never exposes absolute paths or modifies archive files, and works with mouse, touch, keyboard, and gamepad.
</domain>

<decisions>
## Implementation Decisions

### Entry and Navigation

- **D-01:** Platform detail and Settings entry points open the same storage workflow; a platform entry preselects that platform.
- **D-02:** Settings opens on the root list. Each root row shows a compact count/link for its platform mappings.
- **D-03:** Changing a mapping opens the shared workflow with its current root and relative folder preselected. The existing mapping remains active until the replacement has passed its test and is explicitly saved.

### Root Overview

- **D-04:** Use a compact root list with activity, health, last check, and a short safe explanation in every row.
- **D-05:** Phase 7 uses existing backend roots only; it neither creates nor imports root sources or infrastructure configuration.
- **D-06:** Root details show mapped platforms with their relative folder, test status, and preview summary.
- **D-07:** Mapping removal is a spatially separated destructive action with a short confirmation that says original files remain unchanged.

### Mapping Workflow

- **D-08:** Use one stable guided page with sections for root selection, drill-down folder browser, safety test, save, and independent preview; do not use a multi-page or dialog wizard.
- **D-09:** The administrator manually runs the safety test. Save is unavailable until it succeeds.
- **D-10:** After save, return to the mapping overview with the new mapping active and the preview shown as pending.
- **D-11:** Beside folder selection, explain that the selected folder and all descendants are included while siblings are excluded.

### Failure and Recovery

- **D-12:** Unreachable roots retain the current mapping and offer Check again as the primary recovery.
- **D-13:** Forbidden access shows a safe explanation to inspect permissions/root configuration; the UI never changes permissions or picks a replacement root.
- **D-14:** A failed safety test leaves the current workflow and selection intact for adjustment and retry.
- **D-15:** A new preview retains the last result visibly, marks it stale, and presents pending/partial status clearly.

### the agent's Discretion

Exact route names, copy, icons, token assignments, component composition, responsive breakpoints, and the precise root-detail navigation are open, provided the Phase 4 design contract and current v2 conventions are followed.
</decisions>

<canonical_refs>

## Canonical References

### Phase Contract and Safety

- `.planning/ROADMAP.md` - Phase 7 goal, requirements, dependencies, and success criteria.
- `.planning/REQUIREMENTS.md` - UI-01, UI-02, UI-03, UI-04, and UI-06 acceptance scope.
- `.planning/phases/04-v2-storage-design-specification/04-CONTEXT.md` - Locked v2 administration workflow, safety, browser, state, and universal-input decisions.
- `.planning/phases/05-preview-and-read-path-cutover/05-CONTEXT.md` - Preview pending/partial/stale behavior and source safety rules.
- `.planning/phases/06-safe-lifecycle-and-legacy-migration/06-CONTEXT.md` - Root/mapping lifecycle contracts consumed by the UI.

### V2 Implementation

- `CLAUDE.md` - Active v2 boundary and repository rules.
- `.claude/skills/frontend-v2-components/SKILL.md` - Component placement and primitive reuse.
- `.claude/skills/frontend-v2-input/SKILL.md` - Mouse, touch, keyboard, gamepad, and responsive behavior.
- `.claude/skills/frontend-v2-patterns/SKILL.md` - Loading, errors, permissions, forms, and destructive action patterns.
- `.planning/codebase/CONVENTIONS.md` - v2 naming, generated contract, and testing conventions.
- `.planning/codebase/STRUCTURE.md` - v2 views, components, routing, and stores.
  </canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `frontend/src/v2/lib/structural/RList/` and `RListItem/` support the root and folder lists.
- `frontend/src/v2/lib/primitives/RCard/`, `RAlert/`, `REmptyState/`, `RSkeletonBlock/`, `RBtn/`, and overlay primitives support compact summaries, safe states, and actions.
- `frontend/src/v2/components/Settings/` provides the administration shell; platform detail provides the contextual entry point.

### Established Patterns

- New UI work belongs under `frontend/src/v2/`; frozen v1 surfaces are out of scope.
- Use generated OpenAPI contracts and existing v2 tokens/primitives; never hand-edit generated models.
- Keep page shell, breadcrumbs, and focus context stable while local regions update.

### Integration Points

- Phase 3/6 storage APIs supply roots, browse data, mappings, safety tests, and lifecycle states.
- Phase 5 supplies bounded preview states consumed by the mapping overview.
  </code_context>

<specifics>
## Specific Ideas

A root list should make active usage and health easy to scan. Folder selection must remain fast for large Unicode directory trees and must explain the recursive selection boundary before saving.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 7.
</deferred>

---

_Phase: 07-v2-storage-administration-experience_
_Context gathered: 2026-08-25_
