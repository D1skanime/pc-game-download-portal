# Phase 4: V2 Storage Design Specification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 4-v2-storage-design-specification
**Areas discussed:** Workflow structure, information density and hierarchy, folder browser interaction, state presentation and design provenance

---

## Workflow Structure

| Question              | Options considered                                                                                  | Selected                                       |
| --------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Primary workflow      | Guided flow; single management page; separate areas                                                 | Guided flow                                    |
| Entry point           | Platform; storage root; both                                                                        | Platform                                       |
| Existing mapping      | Overview with change action; reopen flow directly; compact list row                                 | Overview with change action                    |
| Large-library preview | Save after safety test while preview continues; wait for bounded preview; wait for complete preview | Save after safety test while preview continues |

**User's choice:** A platform-led guided flow with an overview for existing mappings and non-blocking bounded preview.

**Notes:** The user highlighted PS3 libraries with roughly 40 GB per title and PC libraries around 1 TB. Full scanning or hashing before save was rejected as impractical.

---

## Information Density and Hierarchy

| Question           | Options considered                                                                       | Selected                       |
| ------------------ | ---------------------------------------------------------------------------------------- | ------------------------------ |
| Overview layout    | Compact sections; multiple status cards; dense table                                     | Compact sections               |
| Strongest emphasis | Safety and reachability; mapped folder; preview; equal weighting                         | Safety and reachability        |
| Location display   | Root plus relative breadcrumbs; relative path only; full technical path; plain text path | Root plus relative breadcrumbs |
| Action hierarchy   | One contextual primary action; all equal; action menu                                    | One contextual primary action  |

**User's choice:** A compact, safety-led hierarchy with relative breadcrumbs and one clear main action.

**Notes:** Destructive removal remains separate from test and preview actions. Technical host paths are not shown.

---

## Folder Browser Interaction

| Question              | Options considered                                                                               | Selected                              |
| --------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------- |
| Navigation model      | Drill-down list; expandable tree; two columns; responsive combination                            | Drill-down list                       |
| Inclusion explanation | Always summarize; only with siblings; no notice                                                  | Always summarize                      |
| Open versus select    | Row opens and separate action selects; row selects and arrow opens; double-click; selection mode | Row opens and separate action selects |
| Row metadata          | Name and availability; child counts; size and date; name only                                    | Name and availability                 |

**User's choice:** A universal-input drill-down browser with explicit current-folder selection and recursive subtree inclusion.

**Notes:** The user supplied Game Boy and PlayStation examples organized by regional subfolders. They confirmed that selecting the platform parent should include all regions, while navigating deeper permits mapping only a specific region such as `DE - Version`.

---

## State Presentation and Design Provenance

| Question          | Options considered                                                          | Selected                       |
| ----------------- | --------------------------------------------------------------------------- | ------------------------------ |
| State placement   | Stable shell with local state; full-page state; snackbar; dialog            | Stable shell with local state  |
| State encoding    | Icon, text, and semantic color; colored badges; text only; progress for all | Icon, text, and semantic color |
| Recovery          | Contextual local action; generic retry; header action; technical action set | Contextual local action        |
| Team4s provenance | Principles matrix; short note; image comparison; omit mention               | Principles matrix              |

**User's choice:** Local accessible states with contextual recovery and a traceable RomM-native principles matrix.

**Notes:** The matrix must document abstract inspiration and its original RomM implementation without reproducing Team4s screenshots, code, assets, branding, identity, or dependencies.

---

## Explicit Resolutions

- **UI-01 path presentation:** Reconciled in favor of locked D-08 and the live API. The UI shows only friendly root identity plus server-authorized relative breadcrumbs. It never shows container, NAS, host, composed absolute, or other absolute paths.
- **Mapping and preview ordering:** The final order is fast safety test, explicit save, then queued/background large preview. Preview is non-blocking, and this resolution does not expand Phase 4 or require backend API changes.
- **Entry convergence:** Preserve the platform-led entry decision. The canonical route identifier remains planner discretion, provided platform entry and settings entry converge on one flow.

## Agent's Discretion

- Exact copy, icon selection, token assignments, spacing values, component composition, breakpoint values, and specification organization.

## Deferred Ideas

None.
