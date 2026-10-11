---
phase: 17
slug: browser-download-manager
status: draft
shadcn_initialized: false
preset: not-applicable
created: 2026-09-17
---

# Phase 17: Browser Download Manager UI Design Contract

> Visual and interaction contract for the browser-only PC download manager. This contract extends the active RomM v2 system. It does not introduce shadcn, a second component system, a local-path field, a ZIP flow, or a desktop-client handoff.

## Product Boundary and Information Architecture

The PC game detail page is the entry point. The **PC components** tab is the primary download surface. The existing Files tab remains a detailed inspection surface and must not become the primary selection or queue interface.

| Surface                   | Required content and purpose                                                                                                                                                              |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PC components tab         | Component groups, required archive sets, the primary `Download components` action, current queue summary, and recent browser transfer outcomes for this game.                             |
| Download selection dialog | Select one server-authoritative required archive set or an explicitly complete custom component set, choose browser mode, review included files and aggregate size, then start the queue. |
| Download manager          | Queue items grouped by component, per-file details on demand, active enhanced-transfer progress, and recovery actions. It is rendered in the PC components tab, not as a new route.       |
| Files tab                 | Read-only manifest/file evidence, such as destination, size, and SHA-256. It may deep-link or reveal a queue item but never owns component selection.                                     |

Components remain the unit users recognize. Files are nested details only. A collapsed component row displays its kind, file count, total size, readiness, and download state. Expanding it reveals files in safe relative-destination order, with filename, size, and status. Never show a source path, NAS path, browser-local path, raw manifest ID, snapshot, or transfer authorization URL.

## Design System

| Property               | Value                                                                                                                                        |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Tool                   | RomM v2 primitives, no shadcn                                                                                                                |
| Preset                 | Not applicable                                                                                                                               |
| Component library      | Vue 3, Vuetify only through existing `R*` wrappers                                                                                           |
| Icon library           | Material Design Icons through `RIcon` and `RBtn`                                                                                             |
| Font                   | Existing `--r-font-sans` token stack                                                                                                         |
| Existing visual source | `frontend/src/v2/tokens/index.ts`, `RDialog`, `RCard`, `RBtn`, `RCheckbox`, `RAlert`, `RBadge`, `RProgressLinear`, `REmptyState`, `RTooltip` |

Use feature composites in `v2/components/GameDetails/` for domain logic and import v2 primitives from `@v2/lib`. Do not use raw Vuetify controls or raw HTML controls where an `R*` primitive applies. New primitives require a Storybook story and appropriate interaction play coverage.

Every user-visible string is a vue-i18n key. Add the English source and translated, alphabetically sorted keys to all 18 locale folders in the same change. Primitives receive text by prop or slot and never call `$t`.

## Spacing Scale

Use the existing v2 scale and existing responsive gutter token. Do not introduce one-off spacing values.

| Token | Value | Required usage                                                     |
| ----- | ----: | ------------------------------------------------------------------ |
| xs    |   4px | Inline icon-to-label gaps and compact status gaps                  |
| sm    |   8px | File metadata rows and compact button groups                       |
| md    |  16px | Default row interior spacing, dialog sections, checkbox groups     |
| lg    |  24px | Component group separation and desktop dialog padding              |
| xl    |  32px | Major manager sections                                             |
| 2xl   |  48px | Page-level separation when the manager follows component inventory |
| 3xl   |  64px | Not used inside the dialog; only inherited page rhythm             |

Exceptions: `--r-row-pad` is the horizontal page gutter. Interactive controls use at least `--r-touch-target` (44px) in touch or gamepad modality and on `xs`; compact desktop icon controls may use the existing primitive size only when their accessible label is available.

## Typography

Use only the inherited v2 typography tokens below in this feature. Numeric values are the existing token values, not a new type scale.

| Role           |   Size | Weight | Line height | Required usage                                                            |
| -------------- | -----: | -----: | ----------: | ------------------------------------------------------------------------- |
| Metadata       | 11.5px |    400 |         1.4 | File count, byte size, mode and source-status explanation                 |
| Body           |   13px |    400 |         1.4 | Dialog description, empty/error guidance, destination-relative file names |
| Section label  | 14.5px |    500 |         1.4 | Component name, archive-set name, queue item label, button label          |
| Dialog heading |   22px |    500 |         1.1 | `Download components` and recovery dialog title                           |

Only weights 400 and 500 are used. SHA-256 values, opaque diagnostic identifiers visible in developer-only test output, and long filenames use the existing mono token and must wrap without overflowing.

## Color and State Contract

The page retains the existing v2 glass-over-artwork vocabulary and must render correctly under both `.r-v2-dark` and `.r-v2-light`. Consume semantic CSS tokens only. No hex, `rgba()`, Vuetify runtime-theme color prop, or feature-local palette is permitted.

| Allocation           | Tokens                                                                                          | Usage                                                                                                                                                                                   |
| -------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dominant, about 60%  | `--r-color-bg`, `--r-color-surface`, `--r-color-fg*`, `--r-color-border*`                       | Canvas, text, rows, dividers, default dialogs and file details                                                                                                                          |
| Secondary, about 30% | `--r-color-bg-elevated`, `--r-color-panel`, `--r-color-panel-border`, `--r-color-surface-hover` | Component cards, expanded file details, queue panel, dialog and menu surfaces                                                                                                           |
| Accent, at most 10%  | `--r-color-brand-primary`, hover and pressed tokens                                             | The primary `Download components` action, selected archive-set control, selected checkbox state, keyboard/gamepad focus-compatible selected row, and determinate enhanced progress only |
| Semantic success     | `--r-color-status-success*`                                                                     | `Verified` only, after enhanced streamed SHA-256 equality                                                                                                                               |
| Semantic info        | `--r-color-status-info*`                                                                        | `Handed to browser`, capability information, and non-blocking browser limitations                                                                                                       |
| Semantic warning     | `--r-color-status-warning*`                                                                     | Incomplete selection, permission needed, paused work, and recoverable browser limitations                                                                                               |
| Semantic danger      | `--r-color-status-danger*`                                                                      | Failed, cancelled, stale source, and destructive queue-clear confirmation                                                                                                               |

Accent is never used for every clickable row, for error controls, or as a claim of download completion. Status tints use the established `color-mix` pattern over semantic base tokens. Icons are paired with text, never the only carrier of status.

## Component Inventory

| Component                 | Tier                                          | Contract                                                                                                                                                                                                          |
| ------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DownloadManager`         | GameDetails feature composite                 | Lives under the PC components tab. Receives the current ROM and server-authoritative component/archive-set data. Owns local queue display and delegates API and browser operations to typed services/composables. |
| `DownloadSelectionDialog` | GameDetails feature composite using `RDialog` | Opens from `Download components`. Uses a linear, native focus order. Blocks start until one valid server-authoritative set is selected and its included components are visible.                                   |
| `DownloadQueueItem`       | GameDetails feature composite                 | Displays exactly one manifest member within its component group. File details are collapsed by default.                                                                                                           |
| `DownloadModeSelector`    | GameDetails feature composite                 | Offers Standard browser download by default, plus Enhanced folder download only when capability is detected. It does not emulate unavailable browser features.                                                    |
| Existing primitives       | v2 lib                                        | `RDialog`, `RBtn`, `RCheckbox`, `RAlert`, `RBadge`, `RProgressLinear`, `RCard`, `RDivider`, `REmptyState`, `RTooltip`, `RSkeletonBlock`, `RSpinner`                                                               |

No new generic primitive is required unless implementation discovers a reusable, domain-free gap. If one is created, it must follow the primitive constitution, including story coverage.

## Selection and Queue Interaction Contract

1. The PC components tab shows archive sets before individual component checkboxes. Each set states its name, included components, aggregate file count, aggregate size, and whether it is complete.
2. The default selected choice is the server-provided complete whole-game required archive set, when available. If it is unavailable, no selection is prechecked and the primary action is disabled with inline guidance.
3. A custom selection is valid only when the server response marks the exact selected archive set complete. The UI never infers that base, update, DLC, language pack, hotfix, or extras are dependencies, never silently adds a component, and never starts an incomplete selection.
4. Selecting a component updates a visible `Included components` summary and aggregate size. If it omits a required component, show an inline warning naming the missing required component and disable `Start download` until the selection is made complete. Do not use a confirmation to permit an incomplete archive set.
5. The review area lists components first. Each component can expand to show safe destination-relative file details. The review states `Files download individually. No archive is created.`
6. `Start download` creates one immutable manifest and one queue from the reviewed selection. While creating, the button uses its inline loading state and duplicate activation is impossible.
7. Queue order is component order from the manifest, then manifest member order. Do not reorder files based on browser observations. Enhanced mode has a bounded active-file concurrency supplied by the queue implementation; the UI shows `N active, M queued` and does not expose an unsupported arbitrary concurrency setting.
8. A queue item has one explicit state label from the state table. Expanded detail includes expected size and bytes observed only when page code actually observes them.

## Browser Mode and Truthful Transfer Semantics

| State or mode                            | User-facing label and behavior                                                                                                                                                                  | Controls                                                                                                                                                                             |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Standard browser download, default       | `Standard browser download` with body `Your browser will handle each file. RomM cannot confirm that a file finished or matches its checksum.` Each member is user-initiated attachment handoff. | `Start download` only. No page-level progress, checksum, completed, or resume claim.                                                                                                 |
| Handed to browser                        | `Handed to browser` badge. This is the terminal recorded result for a standard attachment attempt, not `Downloaded`, `Complete`, or `Verified`.                                                 | `Open browser downloads` only if the browser provides no privileged API requirement. Otherwise show no fake link. No `Resume download` or `Retry download` claim for the attachment. |
| Enhanced folder download, available      | `Enhanced folder download` with body `Choose a folder. RomM writes and verifies each file in this browser.` The initiating click opens the directory picker.                                    | `Choose folder and start download`. Selection dialog must retain Standard as a switch-back option.                                                                                   |
| Capability unavailable                   | Standard remains selected. Inline info: `Enhanced folder download is not available in this browser. Standard browser download is still available.`                                              | No disabled enhanced selector that blocks the flow.                                                                                                                                  |
| Directory selection cancelled or denied  | Return to mode selection with warning: `Folder access was not granted. Choose a folder again or use Standard browser download.`                                                                 | `Choose folder again`, `Use standard download`.                                                                                                                                      |
| Queued                                   | `Queued`, with component and file position.                                                                                                                                                     | `Cancel download` is available.                                                                                                                                                      |
| Downloading, enhanced only               | `Downloading`, determinate `RProgressLinear`, observed bytes and total using existing byte formatter.                                                                                           | `Pause download` and `Cancel download`.                                                                                                                                              |
| Paused, enhanced only                    | `Paused`, retaining locally validated partial state.                                                                                                                                            | `Resume download` and `Cancel download`. `Resume download` remains unavailable for Standard browser download.                                                                        |
| Verifying, enhanced only                 | `Verifying checksum`, indeterminate progress.                                                                                                                                                   | `Cancel download` only if cancellation safely stops before finalization.                                                                                                             |
| Verified, enhanced only                  | `Verified` success badge only after the local streamed SHA-256 matches the manifest digest.                                                                                                     | Reveal read-only file details. Never offer automatic overwrite.                                                                                                                      |
| Failed                                   | `Download failed` plus a bounded, plain-language cause and next step.                                                                                                                           | `Retry download` where the transfer rules permit it, `Cancel download`.                                                                                                              |
| Cancelled                                | `Cancelled`. Explain that any enhanced partial file remains only for a later safe resume if local state permits it.                                                                             | `Resume download` where valid, otherwise `Remove from queue`.                                                                                                                        |
| Stale source or expired/revoked manifest | `Source changed. Prepare the download again.` or `This download is no longer available. Prepare it again.` Do not call every lifecycle error a source change.                                   | `Prepare download again` creates a new selection flow. It never resumes or mixes prior bytes.                                                                                        |

Pause, resume, byte progress, verification, and retry are enhanced-mode controls only. Standard browser downloads are intentionally non-resumable from the page because the page cannot bind a resumed attachment to the exact snapshot. Browser download-manager UI outside RomM is not represented as application progress.

## Error, Empty, Loading, and Confirmation Copy

All copy below is English source copy for locale keys. Implement translations in all locale folders.

| Element                         | Required copy                                                                                                                                                                                                                                                                     |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary CTA                     | `Download components`                                                                                                                                                                                                                                                             |
| Dialog primary action, Standard | `Start download`                                                                                                                                                                                                                                                                  |
| Dialog primary action, Enhanced | `Choose folder and start download`                                                                                                                                                                                                                                                |
| Empty heading                   | `No downloads prepared`                                                                                                                                                                                                                                                           |
| Empty body                      | `Choose a complete component set to prepare a browser download.`                                                                                                                                                                                                                  |
| No eligible set                 | `No complete download set is available` / `This game needs a complete, manifest-backed component set before it can be downloaded.`                                                                                                                                                |
| Incomplete selection            | `This selection is incomplete` / `Add the required components shown above before starting the download.`                                                                                                                                                                          |
| Standard limitation             | `Your browser will handle each file. RomM cannot confirm that a file finished or matches its checksum.`                                                                                                                                                                           |
| Enhanced unavailable            | `Enhanced folder download is not available in this browser. Standard browser download is still available.`                                                                                                                                                                        |
| Permission failure              | `Folder access was not granted. Choose a folder again or use Standard browser download.`                                                                                                                                                                                          |
| Source changed                  | `Source changed. Prepare the download again.`                                                                                                                                                                                                                                     |
| Manifest unavailable            | `This download is no longer available. Prepare it again.`                                                                                                                                                                                                                         |
| Generic enhanced error          | `RomM could not continue this file. Check your connection and folder permission, then retry.`                                                                                                                                                                                     |
| Clear queue confirmation        | Title: `Remove cancelled downloads?` Body: `This removes cancelled items from this browser queue. Files already handed to your browser are not affected.` Confirm: `Remove cancelled downloads`. Dismiss: `Keep cancelled downloads`. Focus starts on `Keep cancelled downloads`. |

Starting, pausing, resuming, retrying, or cancelling a transfer is not destructive to the source library and does not require a confirmation dialog. Removing cancelled local queue entries uses `ConfirmDialog` at low friction. Any future action that deletes an enhanced local file must use a separate confirmation, danger tone, focus on an object-specific dismissal such as `Keep enhanced local file`, and a precise description of the local effect. No action may claim to delete an external-library source file.

Use inline `RAlert` for state-specific recovery that affects the current dialog or queue item. Use `useSnackbar` once for a significant outcome such as queue prepared, verified item, or unrecoverable failure. Do not toast per-file routine progress or every browser handoff.

## Accessibility, Universal Input, and Responsive Contract

| Requirement          | Contract                                                                                                                                                                                                                                                                                                                                 |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Semantic structure   | Component groups use labelled sections. File lists use semantic list or table markup through existing primitives. Progress exposes text equivalent containing state, observed bytes when known, and total.                                                                                                                               |
| Names                | Every icon-only control has a localized `aria-label` and tooltip. State icons always have visible localized text.                                                                                                                                                                                                                        |
| Focus                | `RDialog` manages focus trap and overlay scope. On open, focus the dialog heading or first selection control. On validation failure, move focus to the inline incomplete-set message. The cancelled-download confirmation starts on `Keep cancelled downloads`; every other confirmation starts on its object-specific dismissal action. |
| Keyboard and gamepad | Linear archive-set selection, component checkboxes, mode selector, queue controls, and file disclosure use native DOM order. No custom key handler. `useGamepad` activates the focused native primitive. Use `useGridNav` only if a future visual implementation creates true grid rows.                                                 |
| Focus visibility     | Use existing modality-gated focus styles only. Rings appear for keyboard and gamepad, not mouse click.                                                                                                                                                                                                                                   |
| Touch                | Controls meet 44px target requirements in touch/pad and `xs` contexts. Never rely on hover to reveal a required action or status.                                                                                                                                                                                                        |
| Responsive           | At `md` and up, the selection review may use a two-column layout with archive choices beside the included summary. At `sm-and-down`, render a single DOM-ordered column: choice, mode, summary, actions. Do not visually hide focusable controls.                                                                                        |
| Mobile dialogs       | `RDialog` uses `fullscreenOnMobile`; selection and recovery dialogs are full-bleed on `xs`. Queue rows wrap filenames and metadata rather than horizontal clipping.                                                                                                                                                                      |
| Breakpoints          | Use `useBreakpoint` and `html[data-bp]` selectors. Use `--r-row-pad` for gutters. No raw layout media query.                                                                                                                                                                                                                             |
| Motion               | Progress animation respects `prefers-reduced-motion`. State changes remain understandable without animation.                                                                                                                                                                                                                             |

## Data, Persistence, and Safety Boundaries

- The view may persist only browser-local, non-authoritative enhanced-resume material that has passed the strict manifest/member/destination/snapshot validation. It never stores a source path, access grant, arbitrary destination string, or browser directory handle as an assumed durable permission.
- Open dialogs and expanded component/file rows are ephemeral local state. The active Game Details tab remains URL state according to the existing view convention. Do not put active downloads in URL query parameters or `useUISettings`.
- The server is authoritative for visible components, required archive-set completeness, immutable manifest membership, lifecycle errors, and authorization. The browser queue is observational and never a delivery credential.
- Every item request uses the existing authenticated manifest-member endpoint. The UI never creates a replacement URL, custom byte range, digest, or authorization bypass.
- Display only safe relative destinations already approved by the manifest. Never accept a typed local destination path. Enhanced mode obtains a directory through the browser picker directly from the initiating user action, validates each manifest destination again, walks child handles only, and refuses automatic overwrite.
- There is no installer execution, archive extraction, packaging, source mutation, or source-directory browsing in this phase.

## Testable Acceptance Contracts

| Scenario              | Observable contract                                                                                                                                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Component-first entry | A PC game exposes `Download components` in the PC components tab. The Files tab contains no primary download-start action.                                                                                                      |
| Complete archive set  | The default complete set is visibly selected when supplied; its component names, aggregate files, and aggregate size match the review before one manifest/session is created.                                                   |
| Incomplete selection  | A missing required component is named in an inline warning and disables start. The UI neither silently adds it nor permits acknowledgement to bypass it.                                                                        |
| Standard baseline     | Standard mode is default and works when File System Access is absent. After initiation each item is labelled `Handed to browser`, never `Verified`, with no page-level resume or byte progress.                                 |
| Enhanced capability   | Enhanced appears only after feature detection. Directory picker cancellation/denial preserves the selection and offers Standard fallback without losing the dialog.                                                             |
| Enhanced states       | Mocked enhanced transfer proves queued, downloading, paused, resumed, verifying, verified, failed, cancelled, and stale render their exact labels and permitted controls. `Verified` requires the mocked digest-success result. |
| Source lifecycle      | 412/source change yields `Source changed. Prepare the download again.` Expired or revoked status yields its distinct unavailable copy. Neither permits resuming old bytes.                                                      |
| Safety                | Rendered UI and API payload handling expose no source path, NAS path, raw browser-local path, or ZIP option. No client control claims browser attachment completion.                                                            |
| Input and viewport    | Vitest or Storybook interaction tests activate selection and queue controls through keyboard/gamepad-compatible native controls. Test `xs`, `sm`, `md`, and `xl` layouts, both themes, and touch target behavior.               |
| Localization          | Tests assert locale keys, not hard-coded UI copy, and locale parity and sorting checks pass.                                                                                                                                    |

## Registry Safety

| Registry               | Blocks used | Safety gate                                     |
| ---------------------- | ----------- | ----------------------------------------------- |
| shadcn official        | none        | Not applicable, project uses RomM v2 primitives |
| Third-party registries | none        | Not applicable                                  |

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
