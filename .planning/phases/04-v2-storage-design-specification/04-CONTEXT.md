# Phase 4: V2 Storage Design Specification - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Define an implementation-ready RomM v2 design contract for storage roots, folder browsing, and platform mappings. The contract covers hierarchy, spacing, typography, navigation, card and state presentation, responsive behavior, and universal input. Team4s may inform abstract principles through read-only inspection, but no Team4s code, assets, branding, identity, or runtime dependencies may be copied or modified. Backend contracts, read-path cutover, lifecycle migration, and UI implementation remain in their later phases.

</domain>

<decisions>
## Implementation Decisions

### Platform-led Mapping Workflow

- **D-01:** Use a guided mapping flow in this order: choose a storage root, browse and select a folder, run a fast safety test, explicitly save, then start the queued/background bounded preview. The preview never blocks the save.
- **D-02:** Start the flow from the platform that needs a mapping. The design should answer, "Where are this platform's games stored?"
- **D-03:** An existing mapping opens on a read-oriented overview showing status, root, relative folder, latest safety result, and preview summary. An explicit "Change mapping" action opens the guided flow with current values prefilled.
- **D-04:** Keep the current mapping active while edits are in progress. Apply a replacement only through an explicit save action after the fast safety test succeeds.
- **D-05:** A full preview, scan, or hash pass must never block saving. The bounded preview runs independently and reports `pending`, `partial`, or `complete`.

### Information Hierarchy

- **D-06:** Use one compact summary with clear sections for platform status, root and folder, safety test, preview, and actions. Avoid excessive nested cards.
- **D-07:** Give safety and reachability the strongest visual emphasis. The mapped location and preview remain supporting information.
- **D-08:** Present locations only as a friendly root identity followed by server-authorized relative, navigable breadcrumbs. Never show a container path, NAS path, host path, composed absolute path, or other absolute path.
- **D-09:** Show one context-sensitive primary action: "Map storage" when unmapped and "Change mapping" when mapped. Keep test and preview secondary. Separate removal spatially and style it as destructive.

### Folder Browser

- **D-10:** Use a drill-down list with relative breadcrumbs on every supported viewport. Do not introduce a separate tree or split-pane navigation model for desktop.
- **D-11:** Allow the administrator to select the currently open folder at any depth. A mapping recursively includes that folder and every descendant.
- **D-12:** Always summarize the selection boundary before save: the selected folder and descendants are included, while sibling folders are excluded.
- **D-13:** Activating a folder row navigates into it. A separate, clearly labelled "Select this folder" action selects the currently open folder. Do not depend on double-click, long-press, or ambiguous row selection.
- **D-14:** Folder rows show only the name, folder icon, and safe availability state. Do not calculate sizes or child entry counts during navigation.

### State Presentation

- **D-15:** Keep the page shell, heading, breadcrumbs, and navigation stable. Loading, empty, pending, partial, unreachable, forbidden, and error states replace only the affected content region.
- **D-16:** Communicate every state through an icon, explicit text, and semantic RomM v2 color. Color must never carry meaning by itself.
- **D-17:** Place one contextual recovery action beside a recoverable state, such as "Check again" or "Choose another folder". Do not expose technical paths or offer ineffective generic actions.
- **D-18:** Preserve focus and navigation context when a local region changes state so keyboard and gamepad users are not displaced.

### RomM-native Provenance

- **D-19:** The design specification includes a principles matrix. Each entry records the abstract Team4s principle observed, an original RomM interpretation, the applicable RomM v2 tokens and `R*` primitives, and a no-copy confirmation.
- **D-20:** The provenance record explicitly confirms that no Team4s React component, source file, asset, branding, identity, or runtime dependency was copied, modified, or introduced.
- **D-21:** Do not embed Team4s screenshots or reproduce its visual identity in the specification. Describe principles abstractly and illustrate the result using RomM-native examples.

### Agent's Discretion

Exact copy, icon choices, token assignments, spacing values, component composition, breakpoint values, specification file organization, and the canonical route identifier are left to research and planning, provided platform entry and settings entry converge on one flow and all choices follow D-01 through D-21 and the existing RomM v2 constitution.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project and Phase Contract

- `.planning/ROADMAP.md` - Defines the Phase 4 goal, UI-05 requirement, success criteria, dependency on Phase 3, and boundaries with Phases 5 and 7.
- `.planning/STATE.md` - Records the immutable archive principle and the decision that Team4s is a read-only design-principles reference only.
- `CLAUDE.md` - Defines the frozen v1 boundary, active v2 location, repository rules, and required v2 guidance.
- `.planning/phases/02-read-only-policy-boundary/02-CONTEXT.md` - Defines the carried-forward read-only policy, bounded error details, and prohibition on host-path leakage.

### V2 Design Constitution

- `.claude/skills/frontend-v2-components/SKILL.md` - Defines v2 component tiers, primitive reuse, file placement, and SFC conventions.
- `.claude/skills/frontend-v2-theming/SKILL.md` - Defines RomM v2 tokens, theme behavior, and the zero-hex-literal rule.
- `.claude/skills/frontend-v2-input/SKILL.md` - Defines universal mouse, touch, keyboard, and gamepad behavior plus responsive conventions.
- `.claude/skills/frontend-v2-patterns/SKILL.md` - Defines loading, error, persistence, permissions, form, and destructive-action patterns.

### Codebase Maps

- `.planning/codebase/CONVENTIONS.md` - Captures v2 naming, primitive import, generated contract, and testing conventions.
- `.planning/codebase/STRUCTURE.md` - Locates v2 views, components, composables, primitives, routes, tokens, and styles.
- `.planning/codebase/STACK.md` - Defines the Vue 3, Vuetify, Pinia, responsive, Storybook, and testing stack.

No external specification or ADR was referenced during discussion. The temporary folder-layout screenshots informed the concrete examples but are not canonical source artifacts.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `frontend/src/v2/lib/primitives/RCard/`: can contain the compact mapping summary without creating a new card language.
- `frontend/src/v2/lib/structural/RList/` and `frontend/src/v2/lib/structural/RListItem/`: natural basis for the drill-down folder list.
- `frontend/src/v2/lib/primitives/RBadge/`, `RAlert/`, `REmptyState/`, `RSkeletonBlock/`, and progress primitives: existing vocabulary for safe, bounded state presentation.
- `frontend/src/v2/lib/primitives/RSteps/`: candidate for communicating the guided mapping sequence.
- `frontend/src/v2/lib/primitives/RBtn/`, `frontend/src/v2/lib/overlays/RDialog/`, and `RDrawer/`: established action, confirmation, focus, and gamepad-back behavior.
- `frontend/src/v2/components/Settings/SettingsSection.vue` and related settings composites: existing hierarchy patterns for administration surfaces.

### Established Patterns

- New frontend work belongs only under `frontend/src/v2/`; frozen v1 surfaces are not design targets.
- Domain-neutral primitives use the `R` prefix and v2 token system. Storage-specific composition belongs in feature or settings components.
- Input behavior must remain equivalent across pointer, touch, keyboard, and gamepad. Focus indicators and overlay dismissal already use modality-aware conventions.
- Backend OpenAPI models remain the source of truth for storage data shapes; the design contract must map to generated contracts once Phase 3 APIs exist.

### Integration Points

- The platform detail or administration surface provides the entry point for "Map storage" and "Change mapping".
- The settings layout and sidebar patterns provide the surrounding administration shell.
- Phase 3 supplies root, safe browsing, mapping, and audit contracts represented by the design.
- Phase 5 supplies bounded preview states, while Phase 7 implements the final v2 workflow from this contract.

</code_context>

<specifics>
## Specific Ideas

- Example archive: `Games/GB GameBoy` contains regional folders such as `DE - Version`, `EU - Version`, `Japan - Version`, and USA variants. Selecting `Games/GB GameBoy` includes every region recursively; selecting `Games/GB GameBoy/DE - Version` includes only that subtree.
- Example archive: `Games/Sony.Playstation` contains `NTSC` and `PAL`. The same recursive selection rule applies.
- A large PS3 or PC library may contain hundreds of titles and terabytes of data. Folder navigation and saving must remain fast without calculating directory sizes, scanning all content, or hashing files.
- Suggested partial-preview language: report that at least a bounded number of entries were observed, explain that the preview stopped at its limit, and state that full discovery occurs during the later scan.

</specifics>

<deferred>
## Deferred Ideas

None. Discussion stayed within the Phase 4 design-contract boundary.

</deferred>

---

_Phase: 4-v2-storage-design-specification_
_Context gathered: 2026-08-11_
