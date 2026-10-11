---
phase: 20
slug: media-management-and-owned-soundtrack-uploads
status: draft
shadcn_initialized: false
preset: none
created: 2026-09-28
---

# Phase 20: Media management and owned soundtrack uploads, UI Design Contract

> Visual and interaction contract for the v2 Media management surface. Media is the only operator-management surface. Overview only renders the selected overview media and never exposes selection, refresh, upload, ordering, or deletion controls.

---

## Design System

| Property          | Value                                                                                                           |
| ----------------- | --------------------------------------------------------------------------------------------------------------- |
| Tool              | none, use the established RomM v2 primitives                                                                    |
| Preset            | not applicable                                                                                                  |
| Component library | Vue 3, Vuetify wrappers exposed through `@v2/lib`                                                               |
| Icon library      | Material Design Icons through `RIcon` and `RBtn`                                                                |
| Font              | `--r-font-family-sans`, Segoe UI-first system stack                                                             |
| Theme policy      | Existing v2 tokens only. No hex or `rgba()` literals in phase code. Both `v2-dark` and `v2-light` are required. |

Use `RBtn`, `RDropzone`, `REmptyState`, `RSkeletonBlock`, `RProgressLinear`, `RChip`, `RCarousel`, `RDialog`/`useConfirm`, `RTooltip`, and the existing soundtrack player. Do not introduce shadcn, a third-party registry, a second audio element, a pointer-only sortable dependency, or raw Vuetify/HTML substitutes where an `R*` primitive exists.

## Information Architecture and Ownership

Keep the existing URL-persistent Media subtab navigation: `?tab=media&subtab=screenshots`, `artwork`, or `soundtrack`. The vertical Media sidebar remains navigation only. Each active panel owns its heading and contextual actions.

| Surface            | Responsibility                                                                              | Explicitly excluded                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Overview           | Render the ordered selected overview screenshots and resolved selected background(s).       | Upload, refresh, select, reorder, deselect, and delete controls.                      |
| Media, Screenshots | Manage provider screenshot candidates and their overview/background membership.             | Per-user/community screenshot controls remain their existing separate sections.       |
| Media, Artwork     | Manage provider and operator-uploaded artwork candidates and ordered background membership. | Any external artwork/source-library write.                                            |
| Media, Soundtrack  | Upload, include, order, play, download, and delete RomM-owned tracks.                       | Legacy `/soundtracks` upload/delete routes, external audio providers, tag enrichment. |

Candidate existence, display membership, and display order are separate UI states. Removing an item from Overview or Backgrounds is a non-destructive placement change. Deleting an owned candidate permanently removes it from the candidate catalog and its placements, with provider identity retained server-side so normal scans do not restore it. Explicit full-media refresh restores provider candidates as unselected, without changing placements or order.

## Spacing Scale

Use the existing v2 4px-base token scale. Do not create phase-local spacing values.

| Token          | Value | Usage in this phase                                                           |
| -------------- | ----- | ----------------------------------------------------------------------------- |
| `--r-space-1`  | 4px   | Icon and chip gaps                                                            |
| `--r-space-2`  | 8px   | Compact controls and row internals                                            |
| `--r-space-4`  | 16px  | Candidate-card metadata, ordered-list row, default card, panel, and grid gaps |
| `--r-space-6`  | 24px  | Panel padding and section separation                                          |
| `--r-space-8`  | 32px  | Media shell and major panel separation                                        |
| `--r-space-12` | 48px  | Empty-state breathing room                                                    |

Exceptions: use `--r-touch-target` (44px) for action targets on touch or gamepad input. Continue to use `var(--r-row-pad)` for page gutters. No arbitrary pixel spacing and no non-multiple-of-4 values.

## Typography

Use the existing sans stack and these four phase roles only. Use regular and semibold only; hierarchy comes from size, color, grouping, and casing rather than additional weights.

| Role                        | Token / Size                | Weight | Line Height | Usage                                                       |
| --------------------------- | --------------------------- | ------ | ----------- | ----------------------------------------------------------- |
| Metadata label              | `--r-font-size-sm` / 11.5px | 600    | 1.4         | Origin, role, selected-state label, compact section eyebrow |
| Body                        | `--r-font-size-md` / 13px   | 400    | 1.4         | Descriptions, filenames, empty/error guidance               |
| Section heading             | `--r-font-size-lg` / 14.5px | 600    | 1.1         | Candidate group and playlist headings                       |
| Now-playing / panel heading | `--r-font-size-xl` / 17px   | 600    | 1.1         | Active track and primary panel title                        |

Use tabular numerals for durations and counts. Long uploaded filenames truncate visually with a tooltip or accessible full name, never overflow or change the card grid.

## Color

This phase consumes semantic v2 tokens and follows the existing 60/30/10 allocation. Token values vary by light/dark theme and must not be replaced with literals.

| Role           | Token                                                                     | Usage                                                                                                                          |
| -------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Dominant, 60%  | `--r-color-bg` and `--r-color-surface`                                    | Page canvas, Media panel canvas, neutral rows                                                                                  |
| Secondary, 30% | `--r-color-bg-elevated`, `--r-color-border`, `--r-color-surface-hover`    | Candidate cards, player controls, Media sidebar, hover affordance                                                              |
| Accent, 10%    | `--r-color-brand-primary` and its token-based `color-mix()` selected tint | Selected Media subtab, selected overview/background/included track state, primary upload/refresh action, active playback state |
| Destructive    | `--r-color-danger` and semantic danger tint                               | Delete control, confirmation button, destructive error emphasis only                                                           |

Accent is reserved for the active subtab, explicit selected-placement controls, the one primary contextual action, focused progress, and active playback. It is not a generic decoration, card border, or default icon color. Status feedback uses the established semantic success/warning/error tokens through `useSnackbar`.

## Component and Layout Contract

### Shared management header

Every management panel starts with a section heading, a one-sentence ownership hint where needed, then right-aligned contextual actions in DOM order: refresh (provider panels only), upload (owned-upload panels only). On `xs`, retain actions as accessible icon buttons with tooltip and aria-label, with 44px touch targets. Loading uses the action's built-in `:loading`; other actions in that operation group are disabled until completion.

The active panel heading and one contextual primary action form the visual focal point for every Media subtab. The panel heading is the largest text in its panel and the primary action is the only filled/brand-toned action in that header; secondary actions use outlined or text treatment.

| Media subtab | Active panel heading      | Contextual primary action | Secondary contextual action                                                       |
| ------------ | ------------------------- | ------------------------- | --------------------------------------------------------------------------------- |
| Screenshots  | `Provider screenshots`    | `Refresh provider media`  | None; per-candidate placement and delete actions remain compact controls          |
| Artwork      | `Artwork and backgrounds` | `Upload artwork`          | `Refresh provider media`                                                          |
| Soundtrack   | `Soundtrack`              | `Upload soundtrack`       | None; include, reorder, playback, download, and delete remain row/player controls |

### Screenshot candidates

Display provider candidates as labelled image cards in a responsive wrapping grid. Each card has: contained/cropped preview appropriate to a screenshot, origin label `Provider`, non-interactive metadata, and a compact action group.

- `Show in overview` is a toggle placement, not deletion. Its selected state is obvious in text and icon, not color alone.
- `Use as background` adds/removes the candidate from the ordered Backgrounds list. If selected, its position is displayed as an ordinal label.
- `Delete from RomM` is a danger icon button with the candidate label in `aria-label`.
- Candidate preview opens the existing `RCarousel` lightbox. Action controls do not open the lightbox.
- If no provider candidates exist, show the panel empty state and, if permitted, `Refresh provider media`; do not imply that a scan will repopulate it.

Existing personal and community screenshot sections retain their current read-only/owner-specific behavior and are visually separate from this provider management group.

### Artwork and backgrounds

Retain the artwork gallery's contained previews, semantic asset labels, lazy loading, and `RCarousel` preview. Add a distinct `Backgrounds` ordered list above or beside the candidate gallery.

- Provider and uploaded artwork are visibly labelled by origin. Uploaded artwork also exposes `Delete from RomM`.
- `Add to backgrounds` creates membership, never overwrites the candidate. The control becomes `Remove from backgrounds` when selected.
- The Backgrounds list is the sole editing surface for order. Each row has a preview, name/origin, ordinal position, and explicit `Move up` and `Move down` buttons. First/last unavailable movement is disabled with an explanation tooltip.
- Movement updates the entire ordered list atomically. On a version conflict, restore the server order, show the error state, and do not silently retain a local speculative order.
- Use native linear DOM order for rows and controls. Do not implement drag-only behavior. Keyboard and gamepad users must be able to add, remove, and reorder every background.
- The first background is the static fallback. With two or more selected backgrounds, the details page rotates in this order only while it is active.

Artwork upload uses `RDropzone`, accepts images only in the picker, presents allowed types/size limit from the API contract, and supports native picker, drag/drop, keyboard activation, and progress. Client `accept` is advisory only; server validation decides acceptance.

### Owned soundtrack

The soundtrack panel keeps the single existing app-wide player and mini-player contract. It consumes only ordered, included owned soundtrack placements, never `RomFile` source-library tracks.

- Header action: `Upload soundtrack`. `RDropzone` accepts MP3, AAC, FLAC, OGG, OPUS, M4A, and WAV and presents per-file/progress feedback. Do not display or infer automatic title, artist, album, or tag metadata. Filename is the track label.
- Candidate list separates `Available uploads` from `Included in soundtrack`. `Include in soundtrack` and `Remove from soundtrack` change placement only.
- The included list is the playback queue and uses the same explicit `Move up`/`Move down` controls and ordinal labels as Backgrounds. The rendered row order, Next/Previous queue order, and selected placement order must be identical.
- Selecting a row starts it with the existing player. Existing play/pause, seek, previous, next, volume, download, buffering, and active-track affordances remain available.
- When a browser cannot decode an accepted format, preserve the track in the owned catalog and list, stop/bypass the failed item according to the existing player behavior, and show a bounded playback error with a retry action. Do not offer transcoding.
- Deleting an uploaded track stops playback first when it is active, removes it from all placements, then requires confirmation before the owned candidate is deleted.

## Interaction, Permissions, and Accessibility

Gate operator controls through `useCan` with the ROM scope. Users without the appropriate write grant may view resolved media and playback, but management controls are absent rather than emitting an authorization error. The backend remains authoritative.

- Use only `R*` controls. Every icon-only action has a translated visible tooltip and an `aria-label` naming the target item and outcome.
- Native buttons and form controls provide keyboard activation. Linear candidate/order lists use native tab order. Grids use the established grid-navigation composable if focusable card geometry needs arrow navigation; do not add ad hoc key handlers.
- Tab selection is URL-synchronized as it is today. Tabs must provide `aria-controls` and panels `role="tabpanel"` with a matching label/id when the implementation updates the current tab shell.
- Focus follows the existing modality-gated ring. Never add bare `:focus` styling. Dialogs and menus use `RDialog`/`RMenu` so Escape and gamepad cancellation stay scoped.
- Refresh, upload, selection, include/exclude, and reorder announce completion/error through `useSnackbar`; inline controls expose busy state. Field/file validation failures remain adjacent to the dropzone.
- The candidate grid and ordered lists remain readable at 320px. At `xs`, the Media sidebar stacks above content, management header actions collapse to labelled/icon controls as necessary, dialogs are full-screen/bottom-sheet via `RDialog`, and touch/pad controls meet 44px.

## Motion Contract

Use `useReducedMotion().enabled` as the single source of truth plus `@media (prefers-reduced-motion: reduce)` for CSS-only effects.

- Normal mode: selected backgrounds rotate only while the current Game Details page is active and at least two backgrounds are selected. Route, ROM, placement, and preference changes clean up the timer. Each transition delegates to the existing two-layer `BackgroundArt` setter and its tokenized cross-fade.
- Reduced-motion mode: clear/never create the rotation timer, make no periodic backdrop swaps or preload churn, and render only the first selected background. Existing artwork fades, card transforms, player-disc spin, and progress effects obey the global reduced-motion behavior.
- Motion is never the only indication of selection, successful reordering, upload progress, or playback state.

## Copywriting Contract

All strings are translated through the existing locale files. These English source strings define the required intent and action language.

| Element                              | Copy                                                                                                                          |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| Primary CTA, artwork                 | `Upload artwork`                                                                                                              |
| Primary CTA, soundtrack              | `Upload soundtrack`                                                                                                           |
| Provider recovery CTA                | `Refresh provider media`                                                                                                      |
| Overview toggle                      | `Show in overview` / `Remove from overview`                                                                                   |
| Background toggle                    | `Add to backgrounds` / `Remove from backgrounds`                                                                              |
| Track toggle                         | `Include in soundtrack` / `Remove from soundtrack`                                                                            |
| Reorder controls                     | `Move up` / `Move down`                                                                                                       |
| Screenshot empty heading             | `No provider screenshots available`                                                                                           |
| Screenshot empty body                | `Refresh provider media to retrieve available provider screenshots. Regular scans do not restore deleted media.`              |
| Artwork empty heading                | `No artwork yet`                                                                                                              |
| Artwork empty body                   | `Upload artwork or refresh provider media. Uploaded artwork is stored by RomM.`                                               |
| Soundtrack empty heading             | `No soundtrack tracks yet`                                                                                                    |
| Soundtrack empty body                | `Upload audio to RomM, then include tracks to build this game's playback order.`                                              |
| Generic upload error                 | `This file could not be uploaded. Check the supported format and size, then try again.`                                       |
| Refresh error                        | `Provider media could not be refreshed. Your current selections and order were not changed. Try again later.`                 |
| Playback error                       | `This track cannot be played in this browser. Try another supported browser or select a different track.`                     |
| Reorder conflict                     | `The media order changed elsewhere. The latest order has been restored.`                                                      |
| Provider delete confirmation         | `Delete “[name]” from RomM? It will be removed from this game's media and will return only after you refresh provider media.` |
| Uploaded artwork delete confirmation | `Delete “[name]” from RomM? This permanently removes the uploaded artwork and its selections.`                                |
| Soundtrack delete confirmation       | `Delete “[name]” from RomM? This permanently removes the uploaded track and removes it from the soundtrack.`                  |

All destructive dialogs use `useConfirm` with `tone: "danger"`, translated `Delete from RomM` confirm text, and initial focus on Cancel. While deletion is pending, confirm is loading and Cancel is disabled. A failed delete leaves the dialog open and shows an error snackbar. No type-to-confirm is needed because only RomM-owned resources are affected; no action in this phase can touch the external source library.

## State Contract

| State                                            | Required rendering and behavior                                                                                                                                                                          |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| First load                                       | `RSkeletonBlock` mirrors the management header, card grid, and ordered rows. Do not use an empty state until data resolves.                                                                              |
| Refresh pending                                  | Refresh button is loading; provider candidate grid remains visible and non-destructive actions are disabled. Existing placements and upload-origin candidates remain visible.                            |
| Upload pending                                   | `RDropzone` reports accepted files/progress; duplicate submits are disabled. Successful files appear after the authoritative ROM refresh. Partial outcomes report the successful count and failed count. |
| No candidates                                    | Use the panel-specific empty state and its permitted CTA.                                                                                                                                                |
| No selected overview/background/queue placements | Candidate collection remains visible. State explicitly says nothing is selected; the Overview shows no management prompt.                                                                                |
| Validation failure                               | Keep dropped/selected filename in context, show file-specific inline reason, and leave retry available.                                                                                                  |
| Server/network failure                           | Preserve last confirmed list/order, show bounded snackbar copy, and provide retry through the original action.                                                                                           |
| Conflict                                         | Refetch authoritative candidate/placement state before displaying the reorder conflict snackbar.                                                                                                         |
| Deletion pending                                 | Keep the row visible but disabled/loading until confirmed success.                                                                                                                                       |

## Safety Boundary

Every UI operation in this phase targets a typed Phase 20 owned-media endpoint and RomM-owned storage only. The UI must not call or expose `POST /api/roms/{id}/soundtracks`, `DELETE /api/roms/{id}/soundtracks/{file_id}`, legacy `RomFile` content/mutation APIs for uploads, or any source-library path action. Do not claim that deleting a provider candidate changes the provider or external library.

## Registry Safety

| Registry        | Blocks Used | Safety Gate                               |
| --------------- | ----------- | ----------------------------------------- |
| shadcn official | none        | not applicable, shadcn is not initialized |
| Third-party     | none        | not applicable                            |

## Verification Contract

- Unit/component tests cover candidate versus placement distinction, optimistic reorder conflict rollback, provider refresh restoring a deleted candidate unselected, permissions, copy/aria labels, and every destructive confirmation path.
- Reduced-motion tests prove that no rotation interval/swap is active when enabled, that the first selected background remains static, and that re-enabling motion restores rotation only for two or more selected backgrounds on the active details route.
- Player tests prove the included placement order drives row order and Next/Previous playback, and an unsupported browser decode produces the prescribed error without deleting the track.
- Browser verification covers dark and light themes; mouse, keyboard, touch, and gamepad; `xs`, `sm`, `md`, and desktop breakpoints; loading, empty, validation, error, conflict, and destructive states.
- Source-safety regression proves no Phase 20 browser action calls a legacy soundtrack mutation route and no backend Phase 20 operation requests external source write authority.

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
