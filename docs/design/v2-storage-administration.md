# RomM V2 Storage Administration Design Contract

## Table of Contents

1. Scope and authority
2. Route and entry convergence
3. Backend Contract
4. Mapped storage overview

## 1. Scope and authority

This document is the normative design contract for RomM v2 storage administration. The live FastAPI and OpenAPI contracts remain authoritative for data and error semantics.

This phase is documentation and design only. It does not implement Vue components, backend behavior, routes, generated types, dependencies, deployment, Phase 5 read-path work, or Phase 7 UI work. New UI work belongs to RomM v2. Frozen v1 is not a design target.

The external archive is read-only. RomM indexes source content without changing original files. The interface never reconstructs or displays a container, NAS, host, composed, or absolute location. Location presentation is only a friendly root name followed by server-authorized relative breadcrumbs. This resolves UI-01 in favor of D-08 and the live redacted schema.

## 2. Route and entry convergence

The canonical route is named `platform-storage-mapping` at `/platforms/:platformId/storage`. Platform detail and storage settings both navigate to this route with platform context. Settings may provide administration chrome, but not a second workflow or draft model. The route answers: "Where are this platform's games stored?" It requires authenticated administrator authority. Frontend permission gating is only a usability hint; backend authorization remains decisive.

| Entry | Context | Destination | Rule |
|---|---|---|---|
| Platform detail | `platformId` | `platform-storage-mapping` | Primary platform-led entry |
| Storage settings | chosen `platformId` | `platform-storage-mapping` | Converges after platform selection |
| Direct route | route `platformId` | Same view and model | Missing, forbidden, and invalid states remain bounded |

## 3. Backend Contract

The client renders only allowlisted response fields and never combines identifiers into technical locations. Unicode and case are preserved exactly in root names, directory names, and relative breadcrumbs.

| Concern | Authoritative fields and states | Presentation contract | Prohibited inference |
|---|---|---|---|
| Roots | `id`, `name`, `mode`, `active`, timestamps, `health` | Friendly name, immutable mode, activity, and independent health properties | No technical path from identity or deployment knowledge |
| Health | `reachable`, `readable`, `non_writable`, `checked_at`, bounded `error` | `true` confirms non-writable, `false` warns, and `null` means unknown or unconfirmed | No filesystem detail beyond the bounded message |
| Browse | `name`, `relative_path`, `navigable`, `next_cursor` | Relative breadcrumbs and paginated rows in server order; preserve Unicode and case | No absolute breadcrumb, guessed parent, or changed casing |
| Mapping | IDs, `relative_path`, `active`, `version` | Bind active mapping by identity and version; join only to an authorized friendly root | No silent fallback for a missing mapping |
| Fast test | draft identity and path, `valid: true`, or bounded error/conflict | Success qualifies the unchanged draft for save; failure stays local | No persisted test history or implied full scan |
| Conflicts | bounded `code`, allowlisted IDs, optional `current_version` | Explain overlap, duplicate, missing, or stale state without unrelated mapping detail | No disclosure from conflict context |
| Shallow preview | persisted identity/version, bounded counts, truncation, cursor | Immediate bounded directory summary, not recursive discovery | No total size or completeness claim when truncated |
| Queued preview | identity/version, health, `pending`, `partial`, `complete`, observed values, bounds, timestamp, problems, stale, bounded error | Start only after save; label lower bounds and ignore stale results for current mapping | No request against an unsaved draft |

Create uses the selected root and relative path. Change and removal submit `expected_version`. On `storage_mapping_stale_version`, retain the local draft, state that the mapping changed, and offer `Reload mapping` followed by explicit review. Never retry with a substituted version or discard edits without confirmation.

## 4. Mapped storage overview

Use one compact read-oriented summary with stable regions, not nested cards. Priority order is safety and reachability, mapped root and relative folder, latest persisted-mapping preview, mapping actions, then spatially separated removal. Safety has the strongest emphasis. The single primary action is `Map storage` when unmapped or `Change mapping` when mapped. Test and preview are secondary.

An existing mapping opens in overview mode. `Change mapping` opens a prefilled draft while the current mapping remains active. Removal is destructive, requires confirmation, and states that source files remain unchanged. Local refresh replaces only its affected region; the page heading, platform identity, breadcrumbs, and navigation stay mounted.
## 5. Guided Mapping Flow

The active mapping and editable draft are separate records in the view model. Opening change mode copies the current root, relative path, and version into a draft. Browsing or testing never alters the active mapping. Cancel discards only the draft.

The required sequence is: choose a root, browse and explicitly select the open folder, run a fast safety test, save explicitly, then start a queued bounded preview. The safety test, save, and queued preview are distinct transitions. Preview is not a blocking step and cannot prevent a successfully tested mapping from being saved.

| Stage | Stable context | Draft action | Completion rule | Next stage |
|---|---|---|---|---|
| Overview | Platform and active mapping remain visible | `Map storage` or `Change mapping` | Administrator enters the guided flow | Choose root |
| Choose root | Existing mapping remains active | Select one authorized friendly root | Active, reachable selection is present | Select folder |
| Select folder | Friendly root and relative breadcrumbs | Drill down, then use `Select this folder` | Current open folder becomes the draft boundary | Review boundary |
| Review boundary | Selected relative breadcrumbs | Confirm folder and descendants are included and siblings are excluded | Administrator understands recursive scope | Fast safety test |
| Fast safety test | Draft remains editable | Test the exact platform, root, and relative path | Latest successful test still matches the draft | Save |
| Explicit save | Active mapping remains unchanged while request is pending | Create or update, using `expected_version` for update | Server returns the persisted mapping identity/version | Queued preview |
| Queued preview | Saved mapping is already active | Enqueue preview using persisted identity/version | Overview shows `pending`, then `partial` or `complete` | Overview |

Changing the root or selected folder after a successful test invalidates that test and disables save until retested. A test failure keeps the draft and gives one relevant recovery. A save conflict keeps the draft. For stale version, `Reload mapping` fetches the current active mapping while the administrator can review differences before replacing the draft. Duplicate and overlap conflicts name only bounded safe context.

Preview enqueue failure does not roll back or invalidate the saved mapping. Return to the updated overview and show a recoverable preview problem. Every queued request binds the persisted mapping ID and version; a stale result is labelled stale and never merged into the current preview summary.

### Screen anatomy

| Region | Content | Interaction priority |
|---|---|---|
| Stable page shell | Platform identity, page title, route navigation | Never replaced by local loading |
| Active mapping summary | Current root, relative folder, safety, preview | Read-only while a draft is open |
| Step context | Root, folder, test, save | Communicates progress without making preview a step |
| Draft workspace | Root selection or folder browser | One task at a time, current values retained between steps |
| Selection boundary | Friendly root and selected relative breadcrumbs | Explicitly states recursive inclusion and sibling exclusion |
| Action row | Back, cancel, contextual next/test/save | One primary action for the current stage |

## 6. Folder Browser

Use the same `RList` and `RListItem` drill-down model on every viewport. Activating a folder row navigates into it. It does not select it. A separate `Select this folder` button selects the currently open folder. Do not depend on double-click, long-press, a checkbox hidden in the row, or ambiguous highlight state.

Relative breadcrumbs begin with the friendly root identity. Each server-authorized segment navigates to that relative parent. The browser accepts folders at arbitrary depth. It preserves names, Unicode, punctuation, and case exactly as returned. It never displays, accepts, or derives an absolute path.

A selected folder includes that folder and all descendants recursively. Siblings of that selected folder are excluded. The confirmation restates this boundary before test and save.

Examples:

- Selecting `Games / GB GameBoy` includes `DE - Version`, other regional folders, and every descendant beneath them.
- Selecting `Games / GB GameBoy / DE - Version` includes only that subtree. Its regional siblings are excluded.
- Selecting `Games / Sony.Playstation / NTSC` includes the NTSC subtree. `PAL` is a sibling and is excluded.

| Row element | Source | Rule |
|---|---|---|
| Folder icon | RomM v2 icon vocabulary | Identifies a directory without suggesting selection |
| Name | Server `name` | Preserve exact Unicode and case; allow safe visual truncation without changing the value |
| Availability | Server `navigable` or bounded affected-region state | Use icon and text, not color alone |
| Navigation affordance | Row activation and chevron | Navigate only when authorized and navigable |

An empty page means the currently open folder has no navigable child directories. It may still be selected with `Select this folder`. Pagination appends or replaces a page without losing the open relative path, current breadcrumb, selected boundary, or focus anchor.

## 7. Scalability and bounded navigation

Navigation performs only the paginated directory browse request. It uses the opaque `next_cursor`, preserves stable server order, and never client-sorts by locale in a way that changes the backend sequence. Page size remains within the backend maximum. Invalid or stale cursors recover by reloading the current relative folder from its first page, not by changing location.

Folder rows are limited to name, folder icon, and safe availability. Navigation and all work before save must not calculate folder size, child count, recursive file count, hashes, scan results, or full-preview data. It must not recursively walk the selected directory. These operations would make large or terabyte-scale libraries unsafe to navigate.

Deep selection is constant in conceptual scope: store the authorized relative path, not an expanded descendant list. Recursive inclusion is a later read-consumer rule. Arbitrarily deep breadcrumbs may collapse visually on narrow screens, but the full ordered relative segments remain navigable and available to assistive technology.

Only after explicit save may the client enqueue the bounded background preview. A `partial` result states that observed counts are lower bounds and explains whether the entry or time budget stopped work. A `complete` result describes only the preview contract, not a future full library scan. Save remains complete regardless of preview duration or result.

## 8. Plan 04-01 decision traceability

| Decision | Contract location |
|---|---|
| D-01, D-04, D-05 | Guided flow ordering, active/draft separation, non-blocking preview |
| D-02 | Platform-led canonical route |
| D-03, D-06, D-07, D-09 | Read-oriented compact overview and action hierarchy |
| D-08 | Friendly root and authorized relative breadcrumbs only |
| D-10, D-13, D-14 | One drill-down list, explicit selection, bounded rows |
| D-11, D-12 | Arbitrary-depth recursive boundary and sibling exclusion |

This plan intentionally leaves D-15 through D-21 state, input, responsive, system mapping, and provenance detail to Plan 04-02 while preserving their locked constraints.