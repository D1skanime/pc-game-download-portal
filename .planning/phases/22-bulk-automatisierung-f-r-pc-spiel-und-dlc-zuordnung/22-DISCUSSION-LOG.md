# Phase 22: Bulk-automatisierung für PC-Spiel- und DLC-Zuordnung - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-01
**Phase:** 22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung
**Areas discussed:** Main-game automation, DLC and expansion automation, exception review queue, background processing

---

## Main-game automation

| Option          | Description                                                                                                    | Selected |
| --------------- | -------------------------------------------------------------------------------------------------------------- | -------- |
| Fully automatic | Apply one unambiguous Steam match, Steam/IGDB metadata, and provider media; queue no-match or ambiguous items. | ✓        |
| Steam first     | Set Steam identity first and enrich metadata later.                                                            |          |
| Suggest only    | Require confirmation before applying a match.                                                                  |          |

**User's choice:** Fully automatic.
**Notes:** Correct main-game folder names may be assumed.

---

## DLC and expansion automation

| Option              | Description                                       | Selected |
| ------------------- | ------------------------------------------------- | -------- |
| Strict automatic    | Apply only an exact DLC title match.              |          |
| Tolerant comparison | Apply one strongly plausible similarly named DLC. | ✓        |
| Detect only         | Suggest but do not link local DLCs.               |          |

**User's choice:** Tolerant comparison.
**Notes:** A single plausible candidate is required before automatic application.

---

## Exception review queue

| Option            | Description                                                              | Selected |
| ----------------- | ------------------------------------------------------------------------ | -------- |
| Efficient queue   | Show candidates and reasons, permit accept/search/skip and bulk actions. | ✓        |
| Individual review | Review each item separately.                                             |          |
| Error list        | Show only unprocessed entries.                                           |          |

**User's choice:** Efficient queue.
**Notes:** The queue prevents thousands of per-game clicks.

---

## Background processing

| Option                    | Description                                  | Selected |
| ------------------------- | -------------------------------------------- | -------- |
| Run after quick scan      | Enrich directly as part of a quick scan.     |          |
| Separate bulk button      | Start enrichment manually after scanning.    |          |
| Scheduled background work | Periodically discover and process new games. | ✓        |

**User's choice:** Scheduled background work.
**Notes:** This means a configurable periodic scan with a 15-minute production
default and a 10-second development/UAT setting, not an immediate filesystem
watcher when a folder is copied.

---

## Claude's Discretion

- Confidence-scoring, scheduling persistence, retry policy, and safe bulk-action implementation.

## Deferred Ideas

None.
