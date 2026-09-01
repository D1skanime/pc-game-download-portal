---
phase: 11
slug: local-pc-media-and-dlc-navigation
status: approved
shadcn_initialized: false
preset: not-applicable
created: 2026-09-01
---

# Phase 11 - UI Design Contract

> Visual and interaction contract for the v2 PC local-media and DLC flows.

## Design System

| Property          | Value                                                  |
| ----------------- | ------------------------------------------------------ |
| Tool              | RomM v2                                                |
| Preset            | Not applicable                                         |
| Component library | Vue 3, Vuetify wrappers through `@v2/lib`              |
| Icon library      | Material Design Icons via existing `RIcon`/`RBtn` APIs |
| Font              | Existing v2 typography tokens                          |

No new primitive is required. The feature uses `RBtn`, `RDialog`, `RAlert`,
`REmptyState`, `RImg`, `RTag`, `RCollapsible`, and the existing game-detail
composition. New feature components belong under `components/GameDetails/`.

## User Flows

### Local artwork review

1. In a PC game's component/files surface, the operator opens **Select local
   artwork**.
2. The dialog lists only verified direct PNG, JPEG, and WebP candidates from
   recognized DLC and extra components. Each row shows a bounded preview,
   source-relative path, component label, and available role controls.
3. The operator explicitly applies exactly one role: Cover, Background, or Add
   to gallery. The selected action uses its own loading state.
4. Success closes the dialog, refreshes the game details, and shows a success
   snackbar. Failure preserves the dialog and shows the safe next step.
5. PDFs, ZIPs, and invalid images never appear in this picker. They remain in
   the ordinary downloadable-file surface.

### DLC metadata review

1. Each recognized DLC component has its own **Find metadata** control and
   current selection status.
2. Candidate choice and application mirrors the existing base-game review
   dialog. The component label remains visible in the dialog header, so the
   operator cannot mistake DLC metadata for base-game metadata.
3. Applying a DLC match refreshes only the component status. It never changes
   the base-game title or summary.

### Overview-to-local-DLC navigation

1. A locally identified expansion or DLC tile is an internal action.
2. Activating it changes the current detail URL to `tab=files` with a
   URL-persisted component filter and focuses the matching component manifest.
3. No DLC/expansion action opens IGDB. A locally unavailable DLC tile is a
   non-navigating informational card, not an external link.

## Layout and Responsive Contract

| Surface               | Desktop                                                                                                                        | Narrow/touch                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| Component/files panel | Component summary and actions precede the collapsible manifest; selected filter has a visible heading and clear-filter action. | Stack controls above the manifest and keep touch targets at least `--r-touch-target`.      |
| Local-art dialog      | Single-column candidate list with preview on the leading edge and role actions in a compact trailing action group.             | Preview moves above text/actions; role actions wrap without horizontal scrolling.          |
| DLC status row        | Component name, metadata state, and `Find metadata` action align in one row.                                                   | Name and status remain first; the action moves to a second row at full width.              |
| Related DLC card      | Retains the existing game-card footprint and focus behavior.                                                                   | Retains card dimensions and keyboard/gamepad activation, with no hidden external behavior. |

The selected component is bookmarkable in the URL. Dialog state, chosen role,
candidate hover, and loading state are ephemeral `ref` state, never a user
preference.

## Visual and Interaction Contract

- Reuse existing `GameDetails`, `FilesTab`, and `PcComponents` visual hierarchy.
  Do not introduce a parallel PC page or a new navigation rail.
- Component groups keep their current iconography. A selected DLC filter uses
  the existing brand-tinted selected state, never a new color literal.
- A selected local cover is rendered through the ordinary cover path. A selected
  background is used by the existing background-art composable. Gallery entries
  appear in the Artwork subtab alongside owned artwork and use its established
  carousel behavior.
- Candidate previews use `object-fit: contain`, a neutral elevated surface, and
  an explicit filename/path label. Artwork must not be cropped so the operator
  can distinguish posters, wallpapers, and covers.
- All actions are reachable by mouse, touch, keyboard, and gamepad. Candidate
  rows are semantic buttons or controls with an announced selected state. The
  dialog receives focus on open and returns focus to its trigger on close.
- Disabled or unavailable metadata sources retain the established warning
  treatment. Do not hide why a candidate list is empty.
- Successful explicit selections receive one success snackbar. Errors use the
  existing error snackbar while leaving the operator's reviewed choices intact.

## Spacing Scale

Use existing spacing tokens only.

| Token         | Value | Usage                                     |
| ------------- | ----- | ----------------------------------------- |
| `--r-space-2` | 8px   | Inline labels, compact candidate metadata |
| `--r-space-3` | 12px  | Action clusters and manifest rows         |
| `--r-space-4` | 16px  | Candidate cards and dialog sections       |
| `--r-space-5` | 20px  | Expanded manifest padding                 |
| `--r-space-6` | 24px  | Major files/component sections            |

Exceptions: none.

## Typography

| Role              | Token/size                       | Weight                     | Usage                                                     |
| ----------------- | -------------------------------- | -------------------------- | --------------------------------------------------------- |
| Section heading   | `--r-font-size-md`               | `--r-font-weight-semibold` | Local artwork and selected component headings             |
| Component name    | `--r-font-size-sm`               | `--r-font-weight-semibold` | DLC identity and filter label                             |
| Candidate path    | `--r-font-size-sm`               | normal                     | Monospace/overflow-wrapped source-relative evidence       |
| Supporting status | `--r-font-size-sm`               | normal                     | Provider availability and digest-preservation explanation |
| Caption           | existing artwork caption styling | bold                       | Gallery provenance label                                  |

## Color

Use semantic v2 tokens only.

| Role            | Token                                             | Usage                                                     |
| --------------- | ------------------------------------------------- | --------------------------------------------------------- |
| Surface         | `--r-color-bg-elevated`                           | Candidate cards and previews                              |
| Border          | `--r-color-border`                                | Card boundaries and image frames                          |
| Selected        | `--r-color-brand-primary` with existing color mix | Selected component/candidate and primary selection action |
| Supporting text | `--r-color-fg-secondary` / `--r-color-fg-muted`   | Paths, hash context, and empty-state guidance             |
| Warning/error   | Existing `RAlert` and snackbar tones              | Provider failures, invalid files, stale source evidence   |

Accent is reserved for the active component/candidate and the explicit apply
action. It is not used merely to decorate every file row.

## Copywriting Contract

All user-visible copy is added through `frontend/src/locales/` and translated
with the existing locale workflow. The English source strings use sentence case
and actionable language.

| Element                 | English source copy                                                                |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Artwork trigger         | `Select local artwork`                                                             |
| Role actions            | `Use as cover`, `Use as background`, `Add to gallery`                              |
| Empty artwork state     | `No eligible local artwork`                                                        |
| Empty artwork guidance  | `Add a PNG, JPEG, or WebP directly to a DLC or extras component, then scan again.` |
| Component match trigger | `Find DLC metadata`                                                                |
| Selected filter heading | `Files for {component}`                                                            |
| Filter clear action     | `Show all PC components`                                                           |
| Stale-source error      | `This source image changed. Scan again and choose it again.`                       |
| Metadata unavailable    | Reuse `rom.pc-metadata-source-unavailable`                                         |
| Internal DLC affordance | `View local DLC files`                                                             |

No destructive confirmation is needed. Removing a stale selected-media record
is automatic reconciliation of a source change and never modifies the source
library. Manual replacement is an explicit non-destructive selection.

## Accessibility and Input Acceptance

- Image previews have descriptive alt text containing filename and component.
- Each role control includes the target role in its accessible name.
- The selected component filter is announced as the current view and can be
  cleared with keyboard/gamepad activation.
- Focus order is component heading, metadata action, local-art trigger,
  candidate controls, then manifest entries.
- Error messages identify whether the image is unsupported, invalid, or changed
  since review, without exposing host paths.

## Registry Safety

| Registry             | Blocks Used                   | Safety Gate                                       |
| -------------------- | ----------------------------- | ------------------------------------------------- |
| RomM v2 primitives   | Existing `R*` primitives only | Existing stories and component tests remain valid |
| Third-party registry | None                          | Not applicable                                    |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-09-01
