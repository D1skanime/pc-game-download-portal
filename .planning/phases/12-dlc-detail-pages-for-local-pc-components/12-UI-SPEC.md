---
phase: 12
slug: dlc-detail-pages-for-local-pc-components
status: draft
shadcn_initialized: false
preset: existing RomM v2
created: 2026-09-02
---

# Phase 12 - UI Design Contract

> Visual and interaction contract for the v2 local-PC-DLC detail page. This page is a component-focused child of its parent game, never a synthetic standalone game.

---

## Design System

| Property          | Value                                                                |
| ----------------- | -------------------------------------------------------------------- |
| Tool              | RomM v2, no shadcn                                                   |
| Preset            | Existing RomM v2 tokens and primitives                               |
| Component library | Vue 3, Vuetify wrappers through `@v2/lib`                            |
| Icon library      | Material Design Icons through existing `RIcon` and `RBtn` APIs       |
| Font              | Existing v2 `--r-font-family-sans` and `--r-font-family-mono` tokens |

No new primitive is required. New feature composites belong below `frontend/src/v2/components/GameDetails/`; use `RBtn`, `RChip` or `RTag`, `REmptyState`, `RAlert`, `RImg`, `RCollapsible`, and the existing Game Details composition where applicable. Do not introduce a second page language, raw Vuetify surface, hex value, or a source-artwork URL.

---

## User Flow and Information Hierarchy

1. A user activates a locally present DLC from the Overview DLC card or the DLC row in PC Components. Both controls use the same named route with the parent ROM and component identifiers.
2. The route loads the visible parent ROM, resolves only a safe integer component ID whose returned component has `kind === "dlc"`, then renders that component. A missing, stale, malformed, or non-DLC ID never renders another component.
3. The page opens with a parent-context back control, then a component hero: selected DLC cover (or the ordinary neutral v2 placeholder), DLC title, `DLC` identity tag, description, and concise technical facts.
4. Below the hero, selected DLC-only background and gallery media appear in the existing media visual language. The page must not show parent or sibling component art. If no selected component media exists, omit the media surface rather than borrowing artwork or fetching a provider result.
5. A local-files section presents only the immutable manifest members for this DLC. Each member visibly retains its relative path, byte size, and SHA-256 evidence. It is read-only and must not derive membership by path-prefix matching.
6. The back action returns to the parent game detail route. It is the primary page CTA and preserves the parent overview context when available.

The page has no play action, metadata-application control, media-selection control, provider request, source-library mutation, or destructive action. Those workflows remain in their existing reviewed parent-game surfaces.

---

## Layout and Responsive Contract

| Surface           | Desktop (`md` and up)                                                                                                                                                                 | Narrow or touch (`sm-and-down`)                                                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Page frame        | Reuse the Game Details centred frame and page gutter. Place cover in the fixed detail-cover column with the identity, summary, and facts in the adjacent content column.              | Stack back control, cover, identity, summary, facts, media, and files in DOM order. Do not retain an empty fixed cover column.                  |
| Cover             | Use existing `xl` detail-cover geometry, `240px × 324px`, with `object-fit: cover`; neutral placeholder has the same footprint.                                                       | Use existing `sm` to `md` cover geometry selected by the established detail-page CSS. Centre only the artwork, not the textual content.         |
| Metadata facts    | Render a compact wrapping definition/list grid below the summary. Include only populated fields: component relative path, version evidence, immutable-file count, and aggregate size. | One fact per row or a two-column grid only when both values remain readable. Relative paths wrap anywhere and never cause horizontal scrolling. |
| Media             | Use the existing detail media/carousel treatment, with selected DLC images only. Hide the entire section when there is no selected background or gallery item.                        | One media item per visible row or the established swipeable carousel. Preserve image aspect ratio and touch targets.                            |
| Local files       | Use a full-width readable manifest list below the hero/media. Desktop rows align path, size, and SHA-256 evidence.                                                                    | Stack each row as path, size, then checksum. The checksum is selectable/copyable only through an existing accessible pattern.                   |
| Unavailable state | Centre `REmptyState` or `RAlert` in the normal page frame with a parent return button.                                                                                                | Same order and same return action, with a minimum `--r-touch-target` control.                                                                   |

Use `useBreakpoint` and `html[data-bp]` selectors for layout changes. Use `var(--r-row-pad)` for horizontal gutters. No raw layout media queries. All actions remain usable by mouse, touch, keyboard, and gamepad; linear page controls follow natural DOM focus order.

---

## Spacing Scale

Use existing v2 tokens only. The page inherits `--r-row-pad` for its responsive horizontal gutter.

| Token          | Value | Usage                                              |
| -------------- | ----- | -------------------------------------------------- |
| `--r-space-1`  | 4px   | Icon-to-label and inline tag gaps                  |
| `--r-space-2`  | 8px   | Compact metadata and file-row gaps                 |
| `--r-space-4`  | 16px  | Default hero, metadata, and manifest-row spacing   |
| `--r-space-6`  | 24px  | Section separation and expanded manifest padding   |
| `--r-space-8`  | 32px  | Page-column and major layout gaps                  |
| `--r-space-12` | 48px  | Major break between hero and files on wide layouts |

Exceptions: the existing `--r-touch-target` (44px) applies to the back control and any compact touch or gamepad action. No new spacing tokens or hard-coded values.

---

## Typography

Use exactly these four existing token sizes and two weights. Supporting path and checksum evidence uses `--r-font-family-mono` without changing the scale.

| Role    | Size                        | Weight         | Line Height                    | Usage                                                                        |
| ------- | --------------------------- | -------------- | ------------------------------ | ---------------------------------------------------------------------------- |
| Body    | `--r-font-size-md` (13px)   | regular (400)  | `--r-line-height-normal` (1.4) | Summary and ordinary technical values                                        |
| Label   | `--r-font-size-sm` (11.5px) | semibold (600) | `--r-line-height-normal` (1.4) | DLC tag, fact labels, file metadata labels                                   |
| Heading | `--r-font-size-2xl` (22px)  | semibold (600) | `--r-line-height-tight` (1.1)  | DLC title and section headings                                               |
| Display | `--r-font-size-3xl` (32px)  | semibold (600) | `--r-line-height-tight` (1.1)  | Large title only when it matches the existing Game Details display treatment |

Long titles truncate only where the existing title treatment provides an accessible full-name tooltip or label. Summaries and relative paths wrap instead of being silently clipped.

---

## Color

Use semantic RomM v2 tokens in both themes, never literal colours. The existing dark-art glass visual language supplies the intended 60/30/10 hierarchy.

| Role            | Value                                                            | Usage                                                                                      |
| --------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Dominant (60%)  | `--r-color-bg` and `--r-color-fg`                                | Page canvas, primary title, readable body content                                          |
| Secondary (30%) | `--r-color-bg-elevated`, `--r-color-surface`, `--r-color-border` | Metadata grouping, media frame, manifest surface, placeholder frame                        |
| Accent (10%)    | `--r-color-brand-primary` with existing token-based tint         | Current DLC identity tag, keyboard/gamepad focus indication, and parent return action only |
| Destructive     | Existing danger token through `RAlert` or snackbar only          | Not used by this read-only page                                                            |

Accent is reserved for the `DLC` identity, the focused/selected navigational affordance, and the explicit return-to-parent action. File rows, ordinary links, technical values, and decorative media do not receive accent treatment. Supporting text uses `--r-color-fg-secondary` or `--r-color-fg-muted`; unavailable/error messaging uses the existing semantic warning or danger surface supplied by `RAlert`.

---

## Copywriting Contract

All new user-visible English source text is added through `frontend/src/locales/` and follows the existing locale parity workflow. Sentence case, actionable wording, and existing generic keys take precedence where available.

| Element                    | Copy                                                                             |
| -------------------------- | -------------------------------------------------------------------------------- |
| Primary CTA                | `Back to {game}`                                                                 |
| Component identity         | `DLC`                                                                            |
| Local file section heading | `Local files`                                                                    |
| Empty media state          | Do not render a media section when the DLC has no selected local media.          |
| Empty files heading        | `No local files found`                                                           |
| Empty files body           | `This DLC has no immutable file entries to show.`                                |
| Unavailable state heading  | `This DLC is unavailable`                                                        |
| Unavailable state body     | `It may no longer belong to this game. Return to {game} and choose another DLC.` |
| Parent-load error          | `We could not load this game. Return to your library and try again.`             |
| Destructive confirmation   | None. The page exposes no destructive operation.                                 |

The fallback DLC title is `DLC: {relativePath}` when no selected component metadata name exists. It must not invent a provider-derived title or reuse the parent game title as the DLC title.

---

## Accessibility and Input Acceptance

- The back control has an accessible name containing the parent game name. It is the first interactive control and returns focus through normal route navigation.
- Cover and gallery `alt` text identify the DLC title, media role, and selected local nature. The neutral placeholder is announced as missing DLC cover artwork, not as the parent artwork.
- The `DLC` tag is textual, not colour-only. Facts use semantic definition-list markup; the local files use a semantic list or existing accessible file-row structure.
- Path and SHA-256 values wrap safely, expose their full value by accessible name or title, and never expose host filesystem paths.
- Loading uses existing skeleton/loading semantics. Route validation and fetch failure retain a visible, keyboard and gamepad reachable parent or library escape route.
- Focus rings use the established modality-gated v2 rules. No custom key handlers: use native linear focus order, and existing carousel/list controls retain their input contracts.

---

## Registry Safety

| Registry             | Blocks Used                                                                                                                    | Safety Gate                                                                |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| RomM v2 primitives   | Existing `RBtn`, `RChip` or `RTag`, `REmptyState`, `RAlert`, `RImg`, `RCollapsible`, and existing detail media/file composites | Existing local source, stories, and component tests. No external registry. |
| Third-party registry | None                                                                                                                           | Not applicable                                                             |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
