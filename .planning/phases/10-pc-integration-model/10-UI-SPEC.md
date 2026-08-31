---
phase: 10
slug: pc-integration-model
status: approved
shadcn_initialized: false
preset: existing RomM v2
created: 2026-08-31
---

# Phase 10 - UI Design Contract

> Extend existing RomM v2 surfaces. Do not introduce a second visual language.

## Design System

| Property          | Value                         |
| ----------------- | ----------------------------- |
| Tool              | none                          |
| Preset            | existing RomM v2              |
| Component library | existing `@v2/lib` primitives |
| Icon library      | existing v2 icon wrapper      |
| Font              | inherited v2 application font |

## Spacing Scale

| Token | Value | Usage                          |
| ----- | ----- | ------------------------------ |
| xs    | 4px   | icon and badge gaps            |
| sm    | 8px   | compact component rows         |
| md    | 16px  | default field and card spacing |
| lg    | 24px  | section separation             |
| xl    | 32px  | page-level separation          |

Exceptions: none.

## Typography and color

Use the existing v2 theme tokens and semantic text classes. Do not hard-code a
new palette, font, or spacing system. Component role labels use existing small/
muted text; game name is the existing details-heading style; error and unresolved
states use the established warning/destructive semantic tokens.

## Interaction Contract

- A PC game's details show a component section grouped as Base game, Updates, DLC,
  Hotfixes, Language packs, and Extras. Each component exposes its immutable file
  manifest on demand, including relative path, byte size, and digest.
- An unresolved layout is visibly marked `Needs classification`; no implied category
  or destructive repair action is offered.
- `Find metadata` opens a review surface with provider-attributed candidate rows.
  Selecting a row enables `Apply selected metadata`; there is no automatic apply.
- Candidate rows may preview approved available media. A provider error uses a
  clear message and a retry path, while retaining the current game details.
- Local LaunchBox media labels its source. RiotPixels is not shown as a selectable
  runtime source in this phase.

## Copywriting Contract

| Element                 | Copy                                                                       |
| ----------------------- | -------------------------------------------------------------------------- |
| Primary CTA             | `Find metadata`                                                            |
| Apply CTA               | `Apply selected metadata`                                                  |
| Empty component heading | `No PC components found`                                                   |
| Unresolved state        | `Needs classification`                                                     |
| Candidate empty state   | `No metadata matches found`                                                |
| Provider error          | `This metadata source is unavailable. Try again or choose another source.` |

## Registry Safety

| Registry           | Blocks Used                                            | Safety Gate              |
| ------------------ | ------------------------------------------------------ | ------------------------ |
| Existing `@v2/lib` | existing list, dialog, alert, button, badge primitives | no external registry use |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-08-31
