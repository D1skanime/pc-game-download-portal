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
## 9. State Matrix and Recovery Contract

The page shell, platform heading, route navigation, relative breadcrumbs, and current step stay mounted. Each state replaces only its named region and combines an icon, localized explicit text, and semantic tone. Color never carries meaning alone. Recovery is local and effective. Focus remains on the activating control when it exists, otherwise it moves to the region heading or recovery action. No state exposes a technical path, raw exception, cursor, or unrelated identifier.

| State | Region | Icon and localized text intent | Tone | Recovery and focus restoration | Forbidden disclosure |
|---|---|---|---|---|---|
| Loading | Affected summary, list, or preview | Loading label with `RSkeletonBlock` matching final shape | neutral | Keep focus in stable shell; announce local completion | Guessed content or location |
| Unmapped | Mapping summary | Link-off icon, no storage folder mapped | info | `Map storage`; focus first root | Lookup details |
| Empty folder | Folder list | Folder-open icon, no children but open folder is selectable | neutral | `Select this folder`; retain breadcrumb and focus anchor | Implied scan result |
| Inactive | Safety summary | Pause icon and explicit inactive label | warning | `Choose another root`; return focus to prior selection | Administrative internals |
| Unreachable | Safety or browser | Link-off icon and reachability text | danger | `Check again`; restore that button | Endpoint or mount detail |
| Unreadable | Safety or browser | Lock icon and readable-state text | danger | `Choose another folder`; focus breadcrumb or first row | Filesystem detail |
| Writable warning | Safety | Shield-alert icon, non-writability not confirmed | warning | `Check again`; keep draft | Claim that archive is safe |
| Unknown non-writability | Safety | Help icon, write protection not verified | warning | `Check again`; focus stays local | Treating `null` as safe |
| Forbidden | Administration region | Lock icon and bounded authorization text | danger | `Return to platform`; focus destination | Role, policy, or path detail |
| Missing | Summary | Search-off icon and bounded missing text | warning | `Reload mapping` or `Choose another root`; preserve draft | Silent fallback |
| Unsafe symlink | Browser or fast test | Shield-lock icon and bounded unsafe-folder text | danger | `Choose another folder`; focus breadcrumb | Link target or resolved path |
| Invalid cursor | Folder list | Refresh icon and bounded pagination text | warning | `Reload this folder` from page one; nearest surviving row | Cursor value |
| Scan limit | Shallow preview | Gauge icon and bounded-result text | info | `Continue preview` only with an API cursor | Invented totals |
| Test failure | Fast-test region | Close icon and bounded reason | danger | One relevant `Choose another folder` or `Check again` action | Raw validation data |
| Stale version | Save region | History icon, mapping changed since draft opened | warning | `Reload mapping`, compare, then explicitly replace draft | Actor or unrelated mapping |
| Overlap or duplicate | Save region | Layers-alert icon and bounded conflict text | danger | `Choose another folder`; keep draft and focus boundary | Conflicting location |
| Preview missing | Preview | Chart icon, no preview for saved mapping | neutral | `Start preview`; keep focus local | Unsaved-draft inference |
| Pending preview | Preview | Clock icon, preview queued or running | info | No retry while active; overview remains usable | Invented percent |
| Partial preview | Preview | Progress icon, `At least {observed} entries` plus server budget reason | warning | `Refresh preview` when available; mapping remains active | Exact totals or percentages |
| Complete preview | Preview | Check icon and bounded completion timestamp | success | Optional `Refresh preview`; restore action anchor | Claim of a full future scan |
| Stale preview | Preview | History icon, older mapping version | warning | `Start current preview`; never merge stale observations | Stale facts as current |
| Bounded problems | Preview | Alert icon, localized count and allowlisted summaries | warning | `Review problems`; return focus to summary | Raw exception, path, or unbounded list |
| Generic error | Affected region | Alert icon and bounded fallback text | danger | `Try again` only when effective, otherwise relevant navigation | Technical diagnostics |

## 10. Typography, Spacing, Navigation, Cards, and States

Typography uses repository type and weight tokens for titles, headings, body, metadata, and labels. Breadcrumbs retain the full accessible name when visually truncated. Spacing uses repository space tokens and `--r-row-pad`. Navigation uses the one canonical route and one drill-down model; `RSteps` shows root, folder, fast test, and save, while preview is post-save status. Use one `RCard` or Settings section shell with repository radius, elevation, border, foreground, surface, and semantic status tokens. Nested-card stacks, raw colors, raw Vuetify substitutes, and decorative motion that ignores reduced-motion tokens are prohibited.

## 11. Universal Input and Focus Geometry

Mouse, touch, keyboard, and gamepad provide equivalent outcomes through the existing `useInput` system. Declare `RFocusZone` regions for route navigation, overview actions, guided steps, breadcrumbs and folder rows, and dialog actions. Do not create ad hoc key handlers or a parallel focus system.

| Context | Mouse and touch | Keyboard | Gamepad | Focus continuity |
|---|---|---|---|---|
| Overview | Activate visible primary action; targets are at least 44px | Tab and arrows follow zones; Enter confirms | D-pad moves spatially; confirm activates; cancel returns | Local refresh retains action or focuses region heading |
| Guided flow | Direct activation cannot skip test or save | Ordered zones match stage | Confirm advances enabled action; cancel discards draft only | New stage focuses heading then first control |
| Folder browser | Row opens; separate button selects | Up/down moves rows; Enter opens; breadcrumbs move upward | D-pad follows list; confirm opens | Pagination restores row identity or nearest row |
| Dialog or drawer | Explicit Cancel and confirm | Trapped focus; destructive removal starts on Cancel; Escape cancels once | Overlay scope prevents input leakage | Close returns focus to opener |
| Conflict recovery | Adjacent recovery control | Announcement precedes recovery | Recovery is next spatial target | Reload preserves draft and focuses changed summary |
| Preview update | Overview remains usable | Live announcement never steals focus | Geometry does not change under focus | pending, partial, complete, stale, and problems stay local |

Focus rings use repository focus tokens only for `data-input="key"` and `data-input="pad"`. Touch and gamepad targets meet 44px. Hidden controls are unmounted and excluded from tab and spatial navigation.

## 12. Responsive Composition

Use `useBreakpoint` for conditional mounting and `html[data-bp]` selectors for layout. Raw layout media queries are prohibited. The same drill-down browser and selection boundary apply at xs, sm, md, lg, and xl.

| Breakpoint | Composition | Browser and overlays | Focus rule |
|---|---|---|---|
| xs | One column, stacked actions, `--r-row-pad` | Browser, `RDialog`, and `RDrawer` are full-bleed; breadcrumbs may collapse visually | Mount-gate desktop chrome; 44px targets |
| sm | One column with wider spacing | Same list; established sheet behavior for large menus | Unmount hidden wide actions |
| md | Summary above guided workspace | Same list, no tree or split pane | Zones order shell, summary, workspace |
| lg | Wider measure may use sibling summary and workspace regions | Same list and pagination | Spatial movement follows visible geometry |
| xl | More breathing room, not more information density | Same bounded list; no recursive prefetch | No desktop-only focus model or action |

## 13. Token and Primitive Matrix

| Need | Tokens or mechanism | Primitive or composition |
|---|---|---|
| Hierarchy | Type scale, weights, foreground, `--r-row-pad` | Semantic headings in `RCard` or Settings section shell |
| Surface | Space, radius, elevation, border, surface | `RCard`, no nested cards |
| Sequence | Brand and foreground | `RSteps`, `RBtn` |
| Folder navigation | Row padding, hover, selected, focus | `RList`, `RListItem`, breadcrumb actions |
| State and recovery | Success, warning, danger, info, neutral | `RAlert`, `REmptyState`, `RBtn` |
| Loading and progress | Skeleton, motion, reduced motion | `RSkeletonBlock`; `RProgressLinear` only for real determinate values |
| Forms and actions | Focus, disabled, touch target | Existing form primitives and `RBtn` |
| Confirmation and mobile workspace | Panel, border, radius, elevation, focus, motion | `RDialog`, `RDrawer` with managed scope |

Phase 7 uses `useCan("app.admin")` as an administration visibility hint while backend authorization remains authoritative. Visible copy is localized. Parallel overlay, breakpoint, and focus systems do not satisfy this contract.

## 14. Plan 04-02 State and System Traceability

| Decision | Contract location |
|---|---|
| D-15 | Stable shell and local State Matrix regions |
| D-16 | Icon, localized text, and semantic tone in every state row |
| D-17 | Effective local recovery and forbidden-disclosure columns |
| D-18 | Universal Input matrix and focus restoration |

## 15. Principles Provenance Matrix

Team4s was inspected read-only only to identify abstract presentation principles. The resulting contract is an original RomM interpretation expressed through the existing RomM v2 system.

| Abstract principle observed | Original RomM interpretation | RomM tokens and primitives | No-copy confirmation |
|---|---|---|---|
| Hierarchy makes the primary administrative question immediately legible | Lead with platform identity and archive safety, then friendly root, relative folder, preview, and actions | Type and foreground tokens, `RCard`, semantic headings | no-copy: no external markup, component structure, or wording |
| Consistent spacing separates related groups without excess containers | Use `--r-row-pad` and repository space tokens inside one section shell | Space, radius, border, elevation tokens, `RCard` | no-copy: no external measurements or style declarations |
| Restrained typography distinguishes title, status, metadata, and action | Apply the RomM type scale and weights with localized labels | Type and foreground tokens, `RAlert`, `RBtn` | no-copy: no external font, type stylesheet, or identity |
| Navigation preserves context while advancing one task | Converge two entries on one platform-led route and use one drill-down list | `RSteps`, `RList`, `RListItem`, breadcrumb actions | no-copy: no React navigation component or route source |
| Cards group information without fragmenting the page | Use one compact RomM surface with stable internal regions, not nested stacks | Surface, border, radius, elevation tokens, `RCard` | no-copy: no external card component, CSS, or asset |
| State presentation couples strong status cues with recovery | Use icon, localized text, semantic tone, local recovery, and focus continuity | Status and focus tokens, `RAlert`, `REmptyState`, `RSkeletonBlock`, `RBtn` | no-copy: no external state copy, illustration, or implementation |

D-19 is satisfied by the abstract-principle, original-interpretation, token/primitive, and no-copy columns. D-20 is satisfied because no Team4s React component, source file, screenshot, asset, branding, identity, runtime dependency, or other code was copied, modified, embedded, or introduced. D-21 is satisfied because this text-only specification contains no Team4s screenshot and does not reproduce its visual identity. RomM examples and existing RomM v2 primitives are the only implementation references.

## 16. D-01 through D-21 Traceability

| Decisions | Objective evidence |
|---|---|
| D-01, D-04, D-05 | Guided Mapping Flow orders choose, browse/select, fast test, explicit save, queued preview; active and draft stay separate |
| D-02 | Route and entry convergence is platform-led |
| D-03, D-06, D-07, D-09 | Mapped overview and screen anatomy define compact, safety-led hierarchy and one contextual primary action |
| D-08 | Scope and Backend Contract allow friendly root plus authorized relative breadcrumbs only |
| D-10, D-13, D-14 | Folder Browser uses one lean drill-down list and explicit current-folder selection |
| D-11, D-12 | Folder Browser examples and boundary confirmation cover arbitrary-depth recursive subsets and sibling exclusion |
| D-15, D-16, D-17, D-18 | State Matrix and Universal Input require local replacement, icon/text/tone, effective recovery, and focus continuity |
| D-19 | Principles Provenance Matrix records each required field |
| D-20 | Explicit no-copy disclosure rejects external code, artifacts, identity, and dependencies |
| D-21 | Text-only abstract principles and RomM-native examples reject screenshots and identity reproduction |

## 17. UI-05 Acceptance Checklist

- [x] One platform-led route receives platform-detail and settings entry without a second workflow or draft model.
- [x] Backend root, health, browse, mapping, conflict, shallow preview, and queued preview fields remain authoritative and are not conflated.
- [x] Location display is limited to friendly root identity and server-authorized relative breadcrumbs; absolute and technical paths are prohibited.
- [x] Fast test, explicit versioned save using `expected_version`, persisted overview update, and queued preview occur in that exact order; preview cannot block or roll back save.
- [x] Deep Unicode folders use arbitrary-depth breadcrumbs and one selected recursive subtree; descendants are included and siblings excluded.
- [x] Navigation remains paginated and bounded for hundreds of folders and terabyte-scale libraries, with no size, recursive walk, full scan, or hash work before save.
- [x] Loading, empty, health, authorization, browse, conflict, preview, problem, stale, and bounded error states have icon, localized text intent, semantic tone, recovery, redaction, and focus behavior.
- [x] Hierarchy, Typography, Spacing, Navigation, Cards, and state presentation map to existing RomM tokens and `R*` primitives in both themes.
- [x] Mouse, touch, keyboard, and gamepad use the existing input and focus systems with modal scope and focus restoration.
- [x] xs, sm, md, lg, and xl use one browser model, `useBreakpoint`, `data-bp`, mount-gated chrome, 44px targets, and full-bleed mobile overlays.
- [x] The Principles Provenance Matrix provides original RomM interpretations and explicit no-copy confirmation for abstract Team4s principles.
- [x] This phase changes documentation only. Runtime UI, backend, generated contracts, dependencies, deployment, and Phase 5 artifacts remain outside scope.
