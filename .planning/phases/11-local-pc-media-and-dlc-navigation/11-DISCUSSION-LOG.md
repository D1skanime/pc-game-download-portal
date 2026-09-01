# Phase 11: Local PC Media and DLC Navigation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-01
**Phase:** 11-local-pc-media-and-dlc-navigation
**Areas discussed:** local image roles, source-image persistence, DLC discovery,
DLC navigation

---

## Local image roles

| Option                        | Description                                                       | Selected |
| ----------------------------- | ----------------------------------------------------------------- | -------- |
| Cover only                    | Local images can replace only the cover.                          |          |
| Cover, background, or gallery | An operator selects the desired role for each direct local image. | ✓        |
| Gallery only                  | Local images can appear only in the gallery.                      |          |

**User's choice:** Cover, background, or gallery.
**Notes:** Only direct local images are candidates. PDFs and ZIPs stay extras.

---

## Source-image persistence

| Option                    | Description                                                            | Selected |
| ------------------------- | ---------------------------------------------------------------------- | -------- |
| Keep unchanged selections | Preserve the selection while its source path and digest are unchanged. | ✓        |
| Clear on every scan       | Require an operator to reselect after every scan.                      |          |

**User's choice:** Keep unchanged selections.
**Notes:** The user selected the first option.

---

## DLC discovery and navigation

| Option                                                | Description                                                       | Selected |
| ----------------------------------------------------- | ----------------------------------------------------------------- | -------- |
| Include direct images below DLC and extra directories | Recursively offer direct image files, without archive extraction. | ✓        |
| Ignore nested component images                        | Consider only game-root images.                                   |          |

**User's choice:** Include direct images below DLC and extra directories.
**Notes:** Each DLC has its own reviewable metadata selection. A recognized
overview expansion opens the local Files area filtered to that DLC, with no
IGDB link as its primary or secondary navigation.

---

## Claude's Discretion

- Choose safe direct-image validation, canonical component matching, and the
  internal filtered-route mechanism using existing RomM patterns.

## Deferred Ideas

None.
