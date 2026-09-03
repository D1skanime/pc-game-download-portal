---
phase: 12
slug: dlc-detail-pages-for-local-pc-components
status: draft
shadcn_initialized: false
preset: existing RomM v2
created: 2026-09-03
---

# Phase 12 - UI Design Contract

> Visual and interaction contract for a local PC DLC detail page. The DLC is a component-focused child of its parent game, never a synthetic standalone ROM.

---

## Design System

| Property          | Value                                                                |
| ----------------- | -------------------------------------------------------------------- |
| Tool              | RomM v2, no shadcn                                                   |
| Preset            | Existing RomM v2 tokens and primitives                               |
| Component library | Vue 3, Vuetify wrappers through `@v2/lib`                            |
| Icon library      | Material Design Icons through existing `RIcon` and `RBtn` APIs       |
| Font              | Existing v2 `--r-font-family-sans` and `--r-font-family-mono` tokens |

New feature composites belong below `frontend/src/v2/components/GameDetails/`. Reuse existing `GameDetails`, `RTabNav`, `RBtn`, `RMenu`, `RMenuItem`, `RChip` or `RTag`, `REmptyState`, `RAlert`, `RImg`, `RCollapsible`, detail media, notes, and file composites. Do not introduce a second visual language, raw Vuetify surface, colour literal, or source-artwork URL.

The established `MatchRomDialog` and `components/MatchRom/` experience is the mandatory visual and interaction reference for every PC parent and component metadata match. Do not create a simplified PC-specific candidate dialog.

---

## Detail Page Contract

### Route, identity, and entry points

1. The Overview DLC card and the DLC entry in PC Components navigate to the same named nested DLC-detail route with the parent ROM and component identifiers.
2. The route loads the authorised parent ROM, resolves only a safe integer component ID from that returned parent, and accepts it only when `kind === "dlc"`.
3. A missing, stale, malformed, foreign, or non-DLC component ID renders an unavailable state. It never substitutes the parent, a sibling component, or arbitrary component data.
4. The first page action is `Back to {game}`. It returns to the parent detail route and retains the parent overview context when available.

### Hero and primary information

The hero follows the parent Game Details hierarchy: parent-context back action, selected DLC cover or ordinary neutral v2 placeholder, DLC title, textual `DLC` identity tag, description, and compact technical facts. The fallback title is `DLC: {relativePath}` when no component metadata name exists. Never use the parent title as the DLC title.

Technical facts show only populated DLC-owned evidence: component relative path, version evidence, immutable-file count, aggregate size, and component checksums where the established detail pattern has space. Paths are display evidence only, not links or image sources.

### Tabs

The tab order is fixed: **Overview**, **Files**, **Media**, **Notes**. It reuses the parent detail page tab language and URL-persisted tab state. There is no Save Data tab, save count, or DLC save-data action. Save data belongs to the parent game because the DLC runs through it.

| Tab      | Required content                                                                                                                                                                                                          | Ownership and exclusions                                                                                                                                     |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Overview | Cover, DLC title, summary, textual DLC identity, technical facts, and selected DLC-only screenshots or other selected media.                                                                                              | Never show parent or sibling artwork, parent metadata, player controls, or parent save data.                                                                 |
| Files    | Only immutable manifest members of the resolved DLC, each with relative path, byte size, SHA-256, and existing per-file download affordance. DLC-specific downloadable artwork belongs here when it is a manifest member. | Exact manifest membership is authoritative. Do not derive membership by prefix matching, and do not offer upload, rename, delete, extract, or write actions. |
| Media    | RomM-owned DLC images, screenshots, artwork, soundtrack, and videos in the established media-subtab conventions. Empty categories use the existing empty treatment.                                                       | It can create, select, replace, or remove only RomM-owned records. It never writes to, moves, renames, or removes immutable source-library content.          |
| Notes    | Notes scoped to this individual DLC, with the same parent-detail note conventions.                                                                                                                                        | Never show or mutate parent-game notes.                                                                                                                      |

When no selected DLC background or gallery image exists, omit optional hero/media preview chrome rather than borrowing the parent cover or fetching provider content. A neutral v2 placeholder preserves the cover footprint.

---

## Actions and Matching Flow

The DLC hero has an accessible overflow action menu. Menu items appear only when applicable and use the established menu primitive:

| Action           | Label                                           | Behaviour                                                                                        |
| ---------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Metadata match   | `ROM zuordnen`                                  | Opens the shared `MatchRomDialog` with the resolved DLC as its explicit target.                  |
| Artwork or media | Existing localized poster/media-selection label | Opens the existing reviewed selection surface for DLC-owned media.                               |
| Local downloads  | Existing localized DLC file download label      | Uses existing per-file or selected-file download behaviour limited to the resolved DLC manifest. |

PC Components' `Metadaten suchen` and this `ROM zuordnen` action are two entry points into one shared matcher. The matcher retains its provider filters, result list, result description preview, and cover-selection UI. The active target is visible in its heading and accessible name so a user cannot confuse a PC parent match with a DLC match.

Only an explicit final confirmation applies the selected result. For a DLC target, metadata and provider-selected media write only to that DLC's component records and RomM-owned storage. Loading the page, opening the dialog, changing a filter, previewing a result, or closing the dialog performs no source-library mutation and no silent metadata or artwork application. Match errors leave the dialog and the user selection intact with the existing retry path.

---

## Layout and Responsive Contract

| Surface                              | Desktop (`md` and up)                                                                                                                                                            | Narrow or touch (`sm-and-down`)                                                                                                                                           |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Page frame                           | Reuse the Game Details centred frame and page gutter. Put cover in the fixed detail-cover column and identity, summary, facts, tabs, and actions in the adjacent content column. | Stack back action, cover, identity, summary, facts, action menu, and tabs in DOM order. Do not preserve an empty fixed cover column.                                      |
| Cover                                | Existing `xl` detail-cover geometry, `240px × 324px`, with `object-fit: cover`; placeholder uses the same footprint.                                                             | Existing `sm` or `md` detail-cover geometry selected by detail-page CSS. Centre only the cover, not textual content.                                                      |
| Technical facts                      | Compact wrapping definition-list grid below the summary.                                                                                                                         | One fact per row or two columns only when both values remain readable. Relative paths wrap anywhere with no horizontal scroll.                                            |
| Tab content                          | Overview media follows existing detail media treatment. Files align path, size, checksum, and existing download controls in a readable full-width list.                          | Keep tab controls in natural order. Stack each file row as path, size, checksum, then actions. Existing carousel is swipeable and preserves aspect ratio.                 |
| Overflow menu and matcher            | Right-align the menu with the hero action area. The shared matcher retains its established filter, list/grid, description preview, and cover-selection composition.              | Menu remains a 44px target. Existing `RMenu` and dialog mobile behaviour provide a bottom sheet or full-bleed dialog; do not create a floating desktop dialog on a phone. |
| Empty, unavailable, and error states | Centre existing `REmptyState` or `RAlert` in the normal page frame with a parent or library escape action.                                                                       | Same content and action order, with a minimum `--r-touch-target` control.                                                                                                 |

Use `useBreakpoint` and `html[data-bp]` selectors for layout changes, and `var(--r-row-pad)` for horizontal gutters. No raw layout media queries. Interactive controls use natural linear DOM focus order and work with mouse, touch, keyboard, and gamepad.

---

## Spacing Scale

Use existing v2 spacing tokens only. The page inherits `--r-row-pad` for its responsive horizontal gutter.

| Token          | Value | Usage                                                     |
| -------------- | ----- | --------------------------------------------------------- |
| `--r-space-1`  | 4px   | Icon-to-label and inline tag gaps                         |
| `--r-space-2`  | 8px   | Compact metadata, file-row, and menu-item gaps            |
| `--r-space-4`  | 16px  | Default hero, tab-panel, and manifest-row spacing         |
| `--r-space-6`  | 24px  | Section separation and expanded file/media padding        |
| `--r-space-8`  | 32px  | Page-column and major layout gaps                         |
| `--r-space-12` | 48px  | Major desktop break between hero and detailed tab content |

Exceptions: `--r-touch-target` (44px) applies to the back control, overflow trigger, tab controls, and compact touch/gamepad actions. No new spacing tokens or hard-coded values.

---

## Typography

Use exactly these four existing token sizes and two weights. Supporting path and checksum evidence uses `--r-font-family-mono` without changing the scale.

| Role    | Size                        | Weight         | Line Height                    | Usage                                                                        |
| ------- | --------------------------- | -------------- | ------------------------------ | ---------------------------------------------------------------------------- |
| Body    | `--r-font-size-md` (13px)   | regular (400)  | `--r-line-height-normal` (1.4) | Summary, notes, ordinary technical values, and matcher descriptions          |
| Label   | `--r-font-size-sm` (11.5px) | semibold (600) | `--r-line-height-normal` (1.4) | DLC tag, fact labels, media provenance, file metadata, and provider filters  |
| Heading | `--r-font-size-2xl` (22px)  | semibold (600) | `--r-line-height-tight` (1.1)  | DLC title, tab/section headings, and matcher target heading                  |
| Display | `--r-font-size-3xl` (32px)  | semibold (600) | `--r-line-height-tight` (1.1)  | Large title only when it matches the existing Game Details display treatment |

Long titles may truncate only where the existing title treatment provides an accessible full-name tooltip or label. Summaries, notes, relative paths, and checksums wrap rather than being silently clipped.

---

## Color

Use semantic RomM v2 tokens in both themes, never literal colours. The existing dark-art glass visual language supplies the 60/30/10 hierarchy.

| Role            | Value                                                                              | Usage                                                                                                       |
| --------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Dominant (60%)  | `--r-color-bg` and `--r-color-fg`                                                  | Page canvas, primary title, readable overview and notes content                                             |
| Secondary (30%) | `--r-color-bg-elevated`, `--r-color-surface`, `--r-color-border`                   | Facts, tab panels, media frames, file rows, placeholder, and matcher results                                |
| Accent (10%)    | `--r-color-brand-primary` with existing token-based tint                           | Current DLC identity, active tab, selected matcher result, explicit confirmation, and focus indication only |
| Destructive     | Existing danger token through `RAlert`, snackbar, or owned-media confirmation only | Source-library destructive action is never available                                                        |

Accent is not decoration for every file, provider, or media item. Supporting text uses `--r-color-fg-secondary` or `--r-color-fg-muted`. Existing semantic warning/danger surfaces explain unavailable routes, matcher failures, and owned-media deletion without exposing host paths.

---

## Copywriting Contract

All new user-visible English source text is added through `frontend/src/locales/` and follows the locale parity workflow. Sentence case, actionable language, and existing generic keys take precedence where available.

| Element                          | Copy                                                                                                         |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Primary CTA                      | `Back to {game}`                                                                                             |
| Overflow metadata action         | `ROM zuordnen`                                                                                               |
| Component identity               | `DLC`                                                                                                        |
| Tabs                             | `Overview`, `Files`, `Media`, `Notes`                                                                        |
| Matcher target heading           | `Match metadata for {component}`                                                                             |
| Local file section heading       | `Local files`                                                                                                |
| Empty files heading              | `No local files found`                                                                                       |
| Empty files body                 | `This DLC has no immutable file entries to show.`                                                            |
| Empty media handling             | Use the existing empty-media state for each media category. Do not show parent media as a fallback.          |
| Empty notes handling             | Use the existing DLC-scoped empty-notes state and creation affordance.                                       |
| Unavailable heading              | `This DLC is unavailable`                                                                                    |
| Unavailable body                 | `It may no longer belong to this game. Return to {game} and choose another DLC.`                             |
| Parent-load error                | `We could not load this game. Return to your library and try again.`                                         |
| Match failure                    | Reuse the existing matcher error and retry copy. Preserve the current result/filter state.                   |
| Owned-media removal confirmation | State that only the selected RomM-owned media item will be removed and original game files remain unchanged. |
| Destructive source confirmation  | None. No source-library destructive operation is available.                                                  |

---

## Accessibility and Input Acceptance

- The back control has an accessible name containing the parent game name and is the first interactive control.
- The overflow trigger exposes its menu state and has a label containing the DLC title. Menu items use `RMenu` focus trapping and return focus to the trigger when closed.
- `RTabNav` identifies the current tab programmatically. Arrow, keyboard, and gamepad navigation use the existing tab contract; tab panels have matching accessible labels.
- The matcher heading and final confirmation identify the current target as the PC parent or the exact DLC. Provider filters, candidate selection, result descriptions, covers, and confirmation controls retain their existing accessible matcher labels.
- Cover and gallery `alt` text identify DLC title, media role, and selected-owned status. A placeholder is announced as missing DLC cover artwork, never as parent artwork.
- The textual `DLC` tag does not rely on colour. Technical facts use a semantic definition list. Files use the existing semantic list/table structure, with full path/hash accessible names and no host paths.
- Loading uses existing skeleton semantics. Invalid routes and fetch failure retain a visible keyboard/gamepad reachable parent or library escape action.
- Focus rings use the established modality-gated v2 rules. Do not add parallel keyboard handlers or focus abstractions.

---

## Registry Safety

| Registry                                | Blocks Used                                                                                                                                                        | Safety Gate                                                                |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| RomM v2 primitives and existing matcher | Existing `RTabNav`, `RBtn`, `RMenu`, `RMenuItem`, `RChip` or `RTag`, `REmptyState`, `RAlert`, `RImg`, `RCollapsible`, `MatchRomDialog`, and `components/MatchRom/` | Existing local source, stories, and component tests. No external registry. |
| Third-party registry                    | None                                                                                                                                                               | Not applicable                                                             |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
