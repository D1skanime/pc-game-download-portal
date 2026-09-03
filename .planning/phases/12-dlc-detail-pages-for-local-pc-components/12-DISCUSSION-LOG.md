# Phase 12: DLC detail pages for local PC components - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or
> execution agents. Decisions are captured in CONTEXT.md.

**Date:** 2026-09-03
**Phase:** 12-dlc-detail-pages-for-local-pc-components
**Areas discussed:** DLC presentation approach, detail-page scope, metadata
matching reuse, DLC media and notes

---

## DLC presentation approach

| Option                    | Description                                            | Selected |
| ------------------------- | ------------------------------------------------------ | -------- |
| Compact card              | Show details within the expanded component row.        |          |
| Enriched component header | Add key data to the existing collapsible heading.      |          |
| Dedicated detail page     | Open a page with cover, description, media, and files. | ✓        |

**User's choice:** Dedicated detail page.

**Notes:** The user explicitly requested this as Phase 12 and confirmed the
related navigation, content, artwork, and technical-information areas should
be captured for later planning.

---

## Claude's Discretion

- Exact responsive composition, Media subtab mapping, cover fallback, and
  technical metadata presentation remain open for the Phase 12 plan, subject
  to the existing v2 and immutable-source contracts.

---

## Detail-page scope

| Decision        | Selected                                                                                                       |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| Tabs            | Overview, Files, Media, and Notes. No DLC save-data feature. Save data remains with the parent game.           |
| Files and media | DLC-only manifest downloads plus RomM-owned uploads and selected artwork, screenshots, soundtrack, and videos. |
| Notes           | Separate notes for each DLC.                                                                                   |
| Actions         | Overflow actions for matching metadata, selecting poster/media, and downloading DLC files.                     |

**Notes:** The user wants the DLC page to follow the parent-game detail
experience, but content and actions must remain scoped to the individual DLC.

---

## Metadata matching reuse

| Decision     | Selected                                                                                                                |
| ------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Entry points | PC Components' `Metadaten suchen` and DLC overflow `ROM zuordnen` open the same flow.                                   |
| Visual flow  | Reuse the existing polished `ROM zuordnen` dialog, provider filters, results, description preview, and cover selection. |
| Targets      | The same flow must work for the PC parent game and each PC component, including DLCs.                                   |
| Persistence  | An explicitly selected DLC match writes metadata and imported provider media only to that DLC.                          |

**Notes:** The user supplied screenshots showing that the existing dialog
already finds `Kingdom Come: Deliverance - A Woman's Lot`, including its
description and cover. A bespoke simplified PC metadata-candidate UI is not
acceptable where this established UI can be reused.

## Deferred Ideas

- DLC-specific save data is intentionally not a feature. Save data remains
  with the parent game because DLCs run through it.
