---
phase: 09
slug: operational-immutability-proof
status: draft
shadcn_initialized: false
preset: none
created: 2026-08-27
---

# Phase 09 - UI Design Contract

> Visual and interaction contract for frontend-facing parts of Phase 9. Generated inline for gsd-ui-phase, verified against the existing RomM v2 system and Phase 9 operational-proof scope.

---

## Design System

| Property          | Value                                                                   |
| ----------------- | ----------------------------------------------------------------------- |
| Tool              | none                                                                    |
| Preset            | not applicable                                                          |
| Component library | existing RomM v2 primitives and Vuetify-backed app shell, no new UI kit |
| Icon library      | `@mdi/font`                                                             |
| Font              | `var(--r-font-family-sans)` and `var(--r-font-family-display)`          |

Phase 9 does not introduce a new runtime visual language. It reuses the established RomM v2 system from the storage administration and player surfaces so browser evidence reflects real production UI rather than a test-only facade.

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage                                                  |
| ----- | ----- | ------------------------------------------------------ |
| xs    | 4px   | Inline icon gaps, status-dot spacing                   |
| sm    | 8px   | Compact metadata separation, chip padding              |
| md    | 16px  | Default control and paragraph spacing                  |
| lg    | 24px  | Section padding inside cards and evidence panels       |
| xl    | 32px  | Major view gaps and page section separation            |
| 2xl   | 48px  | Route-level spacing between shell blocks               |
| 3xl   | 64px  | Reserved for page-level breathing room on wide layouts |

Exceptions: `--r-row-pad: 36px` remains the governing row padding for list and detail layouts; `--r-touch-target: 44px` is mandatory for every tappable or gamepad-focusable control.

## Typography

| Role    | Size                           | Weight                              | Line Height                       |
| ------- | ------------------------------ | ----------------------------------- | --------------------------------- |
| Body    | `var(--r-font-size-md)` 13px   | `var(--r-font-weight-regular)` 400  | `var(--r-line-height-normal)` 1.4 |
| Label   | `var(--r-font-size-sm)` 11.5px | `var(--r-font-weight-semibold)` 600 | `var(--r-line-height-normal)` 1.4 |
| Heading | `var(--r-font-size-xl)` 17px   | `var(--r-font-weight-bold)` 700     | `var(--r-line-height-tight)` 1.1  |
| Display | `var(--r-font-size-2xl)` 22px  | `var(--r-font-weight-semibold)` 600 | `var(--r-line-height-tight)` 1.1  |

Use existing v2 hierarchy only. Phase 9 may surface evidence through the existing storage admin, download, stream, player, auth, and route shells, but it must not invent a second typography scale for "proof" screens or docs-driven overlays.

## Color

| Role            | Value                                                         | Usage                                                                      |
| --------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Dominant (60%)  | `--r-color-bg` (`#07070f` dark, `#f5f5fa` light)              | Page background, stable shell, route canvas                                |
| Secondary (30%) | `--r-color-surface` and `--r-color-bg-elevated`               | Cards, summary regions, local evidence/status containers                   |
| Accent (10%)    | `--r-color-brand-primary` `#8B74E8`, light override `#553E98` | Primary navigation cues, active step state, current proof action only      |
| Destructive     | `--r-color-danger` `#FF5050`, light override `#DC2626`        | Mapping removal, catalog-only removal confirmation, blocked proof failures |

Accent reserved for: current primary action, active step marker, selected evidence tab or section, and focused "rerun" or "open details" actions. Never use accent for all buttons, all links, or passive status text.

Status tones stay on the existing semantic tokens: `--r-color-success`, `--r-color-warning`, `--r-color-danger`, `--r-color-info`. Proof and immutability messaging must rely on icon + text + semantic tone, never color alone.

## Copywriting Contract

| Element                  | Copy                                                                                                                  |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| Primary CTA              | `Run proof` or `Start preview`, depending on whether the action executes operational evidence or bounded preview      |
| Empty state heading      | `No operational proof yet`                                                                                            |
| Empty state body         | `Run the isolated proof stack to capture browser, worker, and nginx evidence without changing the source library.`    |
| Error state              | `Proof could not be completed. Review the isolated stack result and fix the reported boundary issue before retrying.` |
| Destructive confirmation | `Remove mapping`: `Remove this mapping from RomM only. Original files and folders stay unchanged.`                    |

Additional copy rules:

- Say `read-only`, `unchanged`, `original files`, and `source library` explicitly when describing safety outcomes.
- Never imply that RomM "fixes", "organizes", "moves", or "cleans up" source content in Phase 9 surfaces.
- Download, stream, preview, and scan success copy may confirm completion, but must not claim the source was modified, optimized, or migrated automatically.
- When access-time guidance is relevant, distinguish `file access time may change without noatime` from the stronger `content and structure remain unchanged` guarantee.

## Registry Safety

| Registry             | Blocks Used | Safety Gate    |
| -------------------- | ----------- | -------------- |
| shadcn official      | none        | not required   |
| third-party registry | none        | not applicable |

Phase 9 must not add a new component registry dependency. Any browser-facing work reuses existing RomM v2 primitives, existing generated API contracts, and existing route shells.

## Browser Proof Contract

Phase 9 validates existing user-facing workflows through the browser. It does not authorize a parallel proof dashboard, test-only route, or alternate storage UI. The browser evidence must drive the same v2 surfaces operators and users already use:

- storage root and mapping administration flows from the Phase 7 design direction
- authentication and boot flows required by the Phase 8 deferred smoke scope
- stream, play, and download surfaces that prove nginx-backed delivery

If a phase task needs a human-visible result for the proof, render it as a bounded local status region inside an existing page shell. Keep the page heading, navigation context, and current active mapping visible while local proof-related states update.

## Interaction and Accessibility Contract

- Mouse, touch, keyboard, and gamepad must produce equivalent outcomes through existing RomM v2 input mechanisms.
- Every proof-relevant action must remain reachable with 44px targets and visible focus for `data-input="key"` and `data-input="pad"`.
- Browser test selectors should prefer semantic roles, headings, button names, and stable region labels rather than implementation-detail hooks.
- Loading, pending, partial, stale, forbidden, blocked, and success states must stay local to the affected region and preserve surrounding navigation context.
- Streaming and download success must be visible from the real nginx-backed app flow, not a mocked or API-only substitute.

## State Presentation Contract

| State         | Presentation rule                                                          | Recovery rule                                     |
| ------------- | -------------------------------------------------------------------------- | ------------------------------------------------- |
| Loading       | Use existing skeleton or local loading shell, never blank the full route   | Keep focus in the stable shell                    |
| Pending proof | Show that browser, worker, or nginx evidence is still running              | Do not offer duplicate execution while active     |
| Partial proof | Explain which bounded step finished and which evidence is still missing    | Offer one explicit retry or refresh path          |
| Success       | Confirm workflow completed and source content remained unchanged           | Provide link or action to inspect bounded details |
| Blocked       | State the boundary that failed, not generic "something went wrong" copy    | Offer a local recovery action or review path      |
| Forbidden     | Explain missing authorization without exposing paths or policy internals   | Return to the nearest safe route                  |
| Stale         | Mark older preview or proof results as stale when mapping identity changed | Offer rerun against current mapping               |

## Non-Goals

- No Phase 9-specific redesign of RomM v2 colors, fonts, or layout system
- No new absolute-path display, host-path debug panel, or direct filesystem browser outside authorized relative browsing
- No test-only UI that bypasses the production nginx, worker, or storage-policy path
- No UI copy that suggests Team4s is touched, restarted, or used as a fixture

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-08-27
