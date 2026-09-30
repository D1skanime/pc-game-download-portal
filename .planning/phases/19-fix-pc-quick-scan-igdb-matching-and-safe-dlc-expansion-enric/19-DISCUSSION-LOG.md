# Phase 19: Fix PC quick-scan IGDB matching and safe DLC/expansion enrichment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-28
**Phase:** 19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric
**Areas discussed:** PC scan title normalization, Steam-only recovery, DLC and expansion safety, manual component selection, media follow-up, soundtrack follow-up

---

## PC scan title normalization

| Option                | Description                                                                              | Selected |
| --------------------- | ---------------------------------------------------------------------------------------- | -------- |
| PC-only normalization | Normalize compact PC filesystem names before IGDB lookup without changing classic scans. | ✓        |
| Generic normalization | Change all platform scan matching.                                                       |          |

**User's choice:** PC-only normalization.

---

## Existing Steam-only records

| Option                     | Description                                                                         | Selected |
| -------------------------- | ----------------------------------------------------------------------------------- | -------- |
| Repair on metadata refresh | Re-attempt IGDB assignment for existing PC records with Steam but no IGDB identity. | ✓        |
| Future scans only          | Leave existing records untouched.                                                   |          |

**User's choice:** Repair existing records.

---

## DLC and expansion identity

| Option                            | Description                                                                                       | Selected |
| --------------------------------- | ------------------------------------------------------------------------------------------------- | -------- |
| Fail closed with manual selection | Automatically enrich only unambiguous related IGDB entries; require explicit selection otherwise. | ✓        |
| Broaden automatic matching        | Accept looser automatic results.                                                                  |          |

**User's choice:** Fail closed, with an exact-title review and explicit candidate selection for individual expansions.

---

## Deferred media and soundtrack work

**User's choices:**

- Manage provider screenshots in Media, deselecting images from the overview or deleting them completely.
- Persist deletion across normal scans; an explicit full-media refresh can restore all provider candidates.
- Support artwork and screenshot candidates as backgrounds, permit owned uploads, and rotate multiple chosen backgrounds with smooth reduced-motion-aware transitions.
- Add only manual, RomM-owned soundtrack uploads first; automatic track metadata and external audio providers remain later work.

## Claude's Discretion

- Choose the smallest safe normalizer and focused test placement for the Phase 19 bugfix.

## Deferred Ideas

- Media management and soundtrack enhancements are follow-up phases after Phase 19.
