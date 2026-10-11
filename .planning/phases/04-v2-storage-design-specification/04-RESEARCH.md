# Phase 4: V2 Storage Design Specification - Research

**Researched:** 2026-08-11
**Domain:** RomM v2 storage administration design contract
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use a guided mapping flow in this order: choose a storage root, browse and select a folder, run a fast safety test, explicitly save, then start the queued/background bounded preview. The preview never blocks the save.
- **D-02:** Start the flow from the platform that needs a mapping. The design should answer, "Where are this platform's games stored?"
- **D-03:** An existing mapping opens on a read-oriented overview showing status, root, relative folder, latest safety result, and preview summary. An explicit "Change mapping" action opens the guided flow with current values prefilled.
- **D-04:** Keep the current mapping active while edits are in progress. Apply a replacement only through an explicit save action after the fast safety test succeeds.
- **D-05:** A full preview, scan, or hash pass must never block saving. The bounded preview runs independently and reports `pending`, `partial`, or `complete`.
- **D-06:** Use one compact summary with clear sections for platform status, root and folder, safety test, preview, and actions. Avoid excessive nested cards.
- **D-07:** Give safety and reachability the strongest visual emphasis. The mapped location and preview remain supporting information.
- **D-08:** Present locations only as a friendly root identity followed by server-authorized relative, navigable breadcrumbs. Never show a container path, NAS path, host path, composed absolute path, or other absolute path.
- **D-09:** Show one context-sensitive primary action: "Map storage" when unmapped and "Change mapping" when mapped. Keep test and preview secondary. Separate removal spatially and style it as destructive.
- **D-10:** Use a drill-down list with relative breadcrumbs on every supported viewport. Do not introduce a separate tree or split-pane navigation model for desktop.
- **D-11:** Allow the administrator to select the currently open folder at any depth. A mapping recursively includes that folder and every descendant.
- **D-12:** Always summarize the selection boundary before save: the selected folder and descendants are included, while sibling folders are excluded.
- **D-13:** Activating a folder row navigates into it. A separate, clearly labelled "Select this folder" action selects the currently open folder. Do not depend on double-click, long-press, or ambiguous row selection.
- **D-14:** Folder rows show only the name, folder icon, and safe availability state. Do not calculate sizes or child entry counts during navigation.
- **D-15:** Keep the page shell, heading, breadcrumbs, and navigation stable. Loading, empty, pending, partial, unreachable, forbidden, and error states replace only the affected content region.
- **D-16:** Communicate every state through an icon, explicit text, and semantic RomM v2 color. Color must never carry meaning by itself.
- **D-17:** Place one contextual recovery action beside a recoverable state, such as "Check again" or "Choose another folder". Do not expose technical paths or offer ineffective generic actions.
- **D-18:** Preserve focus and navigation context when a local region changes state so keyboard and gamepad users are not displaced.
- **D-19:** The design specification includes a principles matrix. Each entry records the abstract Team4s principle observed, an original RomM interpretation, the applicable RomM v2 tokens and `R*` primitives, and a no-copy confirmation.
- **D-20:** The provenance record explicitly confirms that no Team4s React component, source file, asset, branding, identity, or runtime dependency was copied, modified, or introduced.
- **D-21:** Do not embed Team4s screenshots or reproduce its visual identity in the specification. Describe principles abstractly and illustrate the result using RomM-native examples.

### the agent's Discretion

Exact copy, icon choices, token assignments, spacing values, component composition, breakpoint values, and specification file organization are left to research and planning, provided they follow D-01 through D-21 and the existing RomM v2 constitution.

### Deferred Ideas (OUT OF SCOPE)

None. Discussion stayed within the Phase 4 design-contract boundary.
</user_constraints>

<phase_requirements>

## Phase Requirements

| ID                    | Description                                                                                                                                                                             | Research Support                                                                                                                                          |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UI-05                 | New storage workflows follow a RomM-native v2 design specification derived from read-only analysis of Team4s hierarchy, spacing, typography, navigation, cards, and state presentation. | Produce a normative specification with screen, state, input, responsive, primitive, token, and provenance matrices. [VERIFIED: .planning/REQUIREMENTS.md] |
| </phase_requirements> |

## Summary

Phase 4 is documentation and design specification only. It should produce one implementation-ready contract for a platform-led overview, guided mapping flow, drill-down browser, local state replacement, universal input, responsive behavior, RomM tokens/primitives, and no-copy Team4s provenance. [VERIFIED: .planning/ROADMAP.md] [VERIFIED: 04-CONTEXT.md]

The completed Linux backend is more specific than the discussion snapshot. Roots expose name, immutable mode, active state, timestamps, and live health, but no path. Browsing is relative, paginated, cursor-bound, and directory-only. Mappings carry optimistic versions. Preview now has both a shallow synchronous result and a queued `pending | partial | complete` state with health, counts, bytes, lower-bound semantics, budget reason, problems, and stale status. [VERIFIED: backend/endpoints/responses/storage.py] [VERIFIED: backend/endpoints/storage.py]

UI-01 is RESOLVED in favor of locked D-08 and the live redacted contract: show only friendly root identity plus server-authorized relative breadcrumbs, never container, NAS, host, composed absolute, or other absolute paths. This does not expand Phase 4 or the backend API. [VERIFIED: user resolution 2026-08-11] [VERIFIED: backend/endpoints/responses/storage.py]

**Primary recommendation:** Create `docs/design/v2-storage-administration.md` as the normative Phase 4 artifact. [ASSUMED]

## Architectural Responsibility Map

| Capability                            | Primary Tier     | Secondary Tier     | Rationale                                                                                                                        |
| ------------------------------------- | ---------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| Overview and guided-flow presentation | Browser / Client | API / Backend      | Vue owns presentation and draft state; FastAPI owns authoritative data. [VERIFIED: CLAUDE.md]                                    |
| Root and folder safety                | API / Backend    | Database / Storage | Typed responses are redacted and resolver browsing is contained. [VERIFIED: backend/endpoints/storage.py]                        |
| Mapping replacement                   | API / Backend    | Database / Storage | Optimistic versioning and atomic persistence are backend contracts. [VERIFIED: 03-VERIFICATION.md]                               |
| Preview presentation                  | Browser / Client | API / Backend      | UI renders states; backend owns budgets, counts, stale detection, and health. [VERIFIED: backend/endpoints/responses/storage.py] |
| Design provenance                     | Documentation    | Browser / Client   | Phase 4 records principles; Phase 7 implements them. [VERIFIED: .planning/ROADMAP.md]                                            |

## Project Constraints (from AGENTS.md)

- Canonical artifacts and commands belong only in verified Linux `/home/d1sk/romm`. [VERIFIED: AGENTS.md] [VERIFIED: CLAUDE.md]
- V1 is frozen; new frontend design targets only `frontend/src/v2/`. [VERIFIED: CLAUDE.md]
- Backend OpenAPI is the frontend API source of truth. [VERIFIED: CLAUDE.md]
- Existing `R*` primitives and semantic tokens are mandatory; both themes and zero color literals apply. [VERIFIED: frontend-v2-components/SKILL.md] [VERIFIED: frontend-v2-theming/SKILL.md]
- Every interaction supports mouse, touch, keyboard, and gamepad with the existing focus and breakpoint systems. [VERIFIED: frontend-v2-input/SKILL.md]
- Visible copy uses vue-i18n and all locales remain in parity during implementation. [VERIFIED: frontend-i18n/SKILL.md]
- Documentation is English and must not contain em dashes. [VERIFIED: CLAUDE.md]

## Standard Stack

| Library            | Version    | Purpose                               | Why Standard                                                                                            |
| ------------------ | ---------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Vue                | `^3.4.27`  | V2 compositions                       | Existing framework. [VERIFIED: frontend/package.json]                                                   |
| Vuetify            | `^3.9.2`   | Wrapped substrate and utilities       | Existing basis for `R*` primitives. [VERIFIED: frontend/package.json]                                   |
| Pinia              | `^3.0.1`   | Shared session state only when needed | Existing store layer; wizard draft should remain local unless shared. [VERIFIED: frontend/package.json] |
| Vue Router         | `^4.3.2`   | Platform/settings entry               | Existing named-view route system. [VERIFIED: frontend/src/v2/router/routes.ts]                          |
| vue-i18n           | `^11.1.10` | Visible workflow copy                 | Repository localization contract. [VERIFIED: frontend/package.json]                                     |
| Vitest             | `^4.1.5`   | Later component tests                 | Existing test runner. [VERIFIED: frontend/package.json]                                                 |
| Storybook Vue/Vite | `^10.2.19` | Primitive examples                    | Required if Phase 7 extends primitives. [VERIFIED: frontend/package.json]                               |

**Installation:** None. Phase 4 adds documentation only. [VERIFIED: .planning/ROADMAP.md]

**Version note:** These are repository declarations. The non-interactive Linux SSH environment did not expose `node`, so registry queries could not run; no upgrade is proposed. [VERIFIED: remote probe]

## Architecture Patterns

### System Architecture Diagram

```text
Platform entry -> active mapping lookup
  -> missing -> unmapped region -> Map storage
  -> found -> stable overview -> Change mapping
Guided draft -> choose root -> browse relative folders -> select open folder
  -> fast test
     -> invalid -> local recovery
     -> valid -> explicit create/update with expected version
        -> conflict -> keep draft + reload authority
        -> success -> overview + enqueue preview
Queued preview -> pending -> partial/complete
  -> stale/error -> local recovery without invalidating saved mapping
```

[VERIFIED: backend/endpoints/storage.py] [VERIFIED: 04-CONTEXT.md]

### Recommended Specification Structure

```text
docs/design/v2-storage-administration.md
├── scope and non-goals
├── backend contract snapshot and mismatch log
├── overview and guided-flow anatomy
├── folder browser and recursive boundary
├── state and recovery matrix
├── responsive and universal-input contract
├── tokens, typography, spacing, and primitive map
├── accessible copy and i18n guidance
├── Team4s principles provenance matrix
└── implementation acceptance checklist
```

[ASSUMED]

### Stable Shell, Local Regions

Keep platform identity, heading, breadcrumbs, step position, and navigation mounted. Replace only summary, folder-list, safety, or preview content. Use skeletons for known initial shapes, inline loading for actions, alerts for recoverable failures, and empty states only for genuine zero results. [VERIFIED: 04-CONTEXT.md] [VERIFIED: frontend-v2-patterns/SKILL.md]

### Active Mapping Versus Draft

The overview reads the active mapping and the flow edits a separate draft. The queued preview endpoint requires a persisted mapping identity. The ordering is RESOLVED as fast safety test, explicit save, then queued/background large preview while the stable overview remains usable. Preview is non-blocking, and neither Phase 4 nor the backend API expands. [VERIFIED: user resolution 2026-08-11] [VERIFIED: backend/endpoints/storage.py]

### Data-to-Presentation Contract

| API value                                | Required presentation                                                                                                                        |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `health.reachable/readable/non_writable` | Highest-emphasis safety region using icon, text, and semantic tone. `null` means unknown. [VERIFIED: backend/endpoints/responses/storage.py] |
| `root.name`                              | Friendly root label only. Never synthesize an absolute path. [VERIFIED: backend/endpoints/responses/storage.py]                              |
| `relative_path`                          | Relative breadcrumbs preserving Unicode and case. [VERIFIED: backend/endpoints/responses/storage.py]                                         |
| `entry.name/navigable`                   | Folder icon, name, availability; row activates navigation. [VERIFIED: backend/endpoints/responses/storage.py]                                |
| `mapping.version`                        | Hidden `expected_version`; 409 gets a local reload/review action. [VERIFIED: backend/endpoints/responses/storage.py]                         |
| `preview.state`                          | Pending progress, partial lower-bound summary, or complete summary. [VERIFIED: backend/endpoints/responses/storage.py]                       |
| `lower_bound/budget_reason`              | Say "at least" and explain the bounded stop reason. [VERIFIED: backend/endpoints/responses/storage.py]                                       |
| `stale`                                  | Mark outdated and offer refresh; never merge with current facts. [VERIFIED: backend/endpoints/responses/storage.py]                          |

### Anti-Patterns to Avoid

- Container-path display contradicts D-08 and the live schema. [VERIFIED: 04-CONTEXT.md] [VERIFIED: backend/endpoints/responses/storage.py]
- Preview-before-save is not supported by the queued API, which requires `mapping_id`. [VERIFIED: backend/endpoints/storage.py]
- Folder rows navigate; they do not select. Selection is a separate action. [VERIFIED: 04-CONTEXT.md]
- Do not collapse the stable shell into one loading/error state. [VERIFIED: 04-CONTEXT.md]
- Do not create nested status-card stacks or encode status by color alone. [VERIFIED: 04-CONTEXT.md]
- Do not create new breakpoint, focus, overlay, form, or snackbar mechanisms. [VERIFIED: frontend-v2-input/SKILL.md] [VERIFIED: frontend-v2-patterns/SKILL.md]

## Don't Hand-Roll

| Problem                                         | Don't Build                  | Use Instead                                                                 | Why                                                                                                 |
| ----------------------------------------------- | ---------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Cards, lists, alerts, buttons, steps, skeletons | Raw HTML/Vuetify substitutes | `RCard`, `RList`, `RListItem`, `RAlert`, `RBtn`, `RSteps`, `RSkeletonBlock` | Existing RomM visual/input contracts. [VERIFIED: frontend/src/v2/lib/index.ts]                      |
| Focus/gamepad                                   | Ad hoc key handlers          | `useInput` and focus geometry primitives                                    | Mandatory modality, scope, and geometry. [VERIFIED: frontend-v2-input/SKILL.md]                     |
| Responsive logic                                | Raw layout media queries     | `useBreakpoint` and `data-bp`                                               | One system reaches overlays and excludes hidden focusables. [VERIFIED: frontend-v2-input/SKILL.md]  |
| Error translation                               | Technical details            | Typed codes mapped to localized recovery copy                               | API errors are bounded and copy belongs in i18n. [VERIFIED: backend/endpoints/responses/storage.py] |
| Concurrency                                     | Last-write-wins              | `expected_version` and 409 recovery                                         | Existing optimistic contract. [VERIFIED: backend/endpoints/responses/storage.py]                    |
| Preview progress                                | Invented percentages         | State, observations, lower bound, reason, stale flag                        | API exposes no percentage. [VERIFIED: backend/endpoints/responses/storage.py]                       |

## Common Pitfalls

### UI-01 Conflict

UI-01 requires container path display, while D-08 and the live schema prohibit it. Specify root name plus relative breadcrumbs and require requirements reconciliation before Phase 7. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: 04-CONTEXT.md]

### Conflating Preview Models

The shallow GET preview exposes examined/candidate counts and cursor. The queued preview exposes states, bytes, bounds, problems, and stale status. Do not combine fields as one response. [VERIFIED: backend/endpoints/responses/storage.py]

### Losing Draft on Conflict

A stale-version 409 must not silently discard the selected root/folder. Preserve the draft, announce locally, and offer reload/review. [ASSUMED]

### Ambiguous Health

Do not treat active as reachable or `non_writable: null` as safe. Keep active, reachable, readable, and non-writable meanings independently legible. [ASSUMED]

### Untestable Design Prose

Require matrices for anatomy, API fields, states/recovery, focus transitions, breakpoints, tokens/primitives, and provenance so Phase 7 has no structural decisions left. [ASSUMED]

## Code Examples

```css
/* Source: frontend-v2-input/SKILL.md */
.storage-map {
  padding-inline: var(--r-row-pad);
}
html[data-bp~="sm-and-down"] .storage-map__actions {
  flex-direction: column;
}
```

```typescript
// Source: generated StorageMappingPreviewStateSchema
type PreviewState = "pending" | "partial" | "complete";
const countPrefix = (lowerBound: boolean) =>
  lowerBound ? "at-least" : "exact";
```

## State of the Art

| Discussion Assumption                     | Current Linux Contract                            | Impact                                                                                                     |
| ----------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Preview was later-phase concept           | Queued preview routes and generated models exist  | Specify exact state, bound, problem, and stale presentations. [VERIFIED: backend/endpoints/storage.py]     |
| Root could expose technical location      | Root response has no path field                   | Root name plus relative breadcrumbs only. [VERIFIED: backend/endpoints/responses/storage.py]               |
| "Latest safety result" might be persisted | Root health is live; preview has its own snapshot | Label observation time and do not invent a persisted test record. [VERIFIED: backend/endpoints/storage.py] |
| Preview could precede save                | Queued preview requires persisted mapping ID      | Clarify fast test, save, preview ordering. [VERIFIED: backend/endpoints/storage.py]                        |

## Assumptions Log

| #   | Claim                                                         | Section  | Risk if Wrong                                                 |
| --- | ------------------------------------------------------------- | -------- | ------------------------------------------------------------- |
| A1  | Use `docs/design/v2-storage-administration.md`.               | Summary  | Planner may find a stronger established docs location.        |
| A2  | Preserve the operator's draft on stale conflict.              | Pitfalls | Product may prefer forced restart.                            |
| A3  | Render health properties independently rather than one badge. | Pitfalls | Final composition may compact them while retaining semantics. |
| A4  | Matrices make the document implementation-ready.              | Pitfalls | Planner may require an additional wireframe artifact.         |

## Open Questions

1. **RESOLVED, UI-01 reconciliation:** UI-01 follows D-08 and the live API. Show only friendly root identity plus server-authorized relative breadcrumbs, never container, NAS, host, composed absolute, or other absolute paths. [VERIFIED: user resolution 2026-08-11]
2. **RESOLVED, ordering:** Fast safety test, explicit save, then queued/background large preview. Preview is non-blocking; Phase 4 and backend API scope do not expand. [VERIFIED: user resolution 2026-08-11]
3. **RESOLVED, entry convergence:** Preserve platform-led entry. The canonical route identifier remains planner discretion, provided platform and settings entry points converge on one flow. [VERIFIED: user resolution 2026-08-11]

## Environment Availability

Step 2.6 skipped because Phase 4 is documentation-only. The SSH environment lacks `node`, which blocks registry probing but not this phase. [VERIFIED: remote probe]

## Validation Architecture

| Property      | Value                                                                                                                                 |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Framework     | Shell documentation contract checks                                                                                                   |
| Config        | `04-VALIDATION.md`                                                                                                                    |
| Quick command | `test -f docs/design/v2-storage-administration.md && grep -q "Principles Provenance Matrix" docs/design/v2-storage-administration.md` |
| Full gate     | Required sections, D-01 through D-21 traceability, prohibited-copy/path checks, and `git diff --check`                                |

| Req ID | Behavior                                                                                                                                      | Test Type              | File Exists? |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- | ------------ |
| UI-05  | Normative RomM-native specification covers hierarchy, spacing, typography, navigation, cards, states, input, responsive rules, and provenance | documentation contract | No, Wave 0   |

### Wave 0 Gaps

- [ ] `docs/design/v2-storage-administration.md` for UI-05.
- [ ] Required-section, decision-traceability, prohibited-copy, path-leak, and writing-rule checks.

## Security Domain

| ASVS Category         | Applies | Standard Control                                                                                                |
| --------------------- | ------- | --------------------------------------------------------------------------------------------------------------- |
| V2 Authentication     | yes     | Established authenticated admin contract. [VERIFIED: 03-VERIFICATION.md]                                        |
| V3 Session Management | no      | No session change. [VERIFIED: .planning/ROADMAP.md]                                                             |
| V4 Access Control     | yes     | `useCan("app.admin")` for UX; backend remains authoritative. [VERIFIED: frontend-v2-patterns/SKILL.md]          |
| V5 Input Validation   | yes     | Typed relative browse selection; backend containment is authoritative. [VERIFIED: backend/endpoints/storage.py] |
| V6 Cryptography       | no      | No cryptographic behavior. [VERIFIED: .planning/ROADMAP.md]                                                     |

| Threat                            | STRIDE                 | Mitigation                                                                                     |
| --------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------- |
| Path disclosure                   | Information Disclosure | Root name and relative breadcrumbs only; bounded errors. [VERIFIED: 04-CONTEXT.md]             |
| Client privilege assumption       | Elevation of Privilege | UX gating plus backend admin checks. [VERIFIED: 03-VERIFICATION.md]                            |
| Stale overwrite                   | Tampering              | Expected version and explicit 409 recovery. [VERIFIED: backend/endpoints/responses/storage.py] |
| Misleading partial result         | Repudiation            | Explicit lower-bound and budget reason. [VERIFIED: backend/endpoints/responses/storage.py]     |
| Copied external assets/dependency | Supply Chain           | Text-only abstract provenance and no-copy confirmation. [VERIFIED: 04-CONTEXT.md]              |

## Sources

### Primary (HIGH confidence)

- `AGENTS.md`, `CLAUDE.md`, roadmap, requirements, state, and Phase 4 context.
- Phase 1 through 3 CONTEXT, SUMMARY, and VERIFICATION artifacts.
- Live storage endpoint, response, generated-model, v2 primitive, token, settings, route, and skill files.

### Secondary (MEDIUM confidence)

- None required; this is a repository-contract phase.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, repository manifest and source.
- Architecture: HIGH, locked context and live contracts.
- Pitfalls: HIGH, verified contract mismatches and typed states.

**Research date:** 2026-08-11
**Valid until:** 2026-09-10
