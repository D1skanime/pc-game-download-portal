---
phase: 21
plan: "04"
subsystem: PC scan metadata and owned media
tags: [steam, mariadb, metadata, scan]
requires: [21-01, 21-03]
provides: [view-safe Steam structured metadata persistence]
affects: [admin PC scans, PC metadata selection]
tech-stack: [SQLAlchemy, MariaDB]
key-files:
  modified:
    - backend/handler/scan_handler.py
    - backend/handler/database/roms_handler.py
    - backend/models/rom.py
    - backend/endpoints/sockets/scan.py
    - backend/tests/handler/test_scan_handler.py
    - backend/tests/handler/database/test_pc_igdb_enrichment.py
decisions:
  - Structured PC fields are persisted in Rom.igdb_metadata because roms_metadata is derived.
metrics:
  tasks_completed: 3
  uat_outcome: FAIL
---

# Phase 21 Plan 04: Administrator Steam Scan Parity Summary

Administrator Steam scans persist guarded structured fields through `Rom.igdb_metadata`, leaving the derived MariaDB metadata view read-only while preserving owned media and manual placements.

## Commits

- `d77b50980` test(21-04): cover Steam admin scan parity
- `a353e2c89` feat(21-04): enrich admin PC scans with Steam
- `4cdba6bba` fix(21-04): persist structured Steam scan metadata
- `8a247da19` fix(21-04): persist Steam PC fields through Rom metadata
- `1655fbbaa` fix(21-04): keep scan metadata view read-only

## Verification

- `trunk fmt` and `trunk check` passed for all changed backend files.
- The focused view-safety regression passed in the authorized isolated app process.
- The canonical host's pytest suite is blocked by its unavailable local MariaDB at `127.0.0.1`; no test infrastructure was created.
- Isolated COMPLETE and UPDATE scans completed without MariaDB view-update errors. Witcher retained uploads and placements and gained 21 Steam provider media candidates.

## UAT

`21-UAT.md` records an explicit FAIL. Existing UPDATE/COMPLETE evidence passes.
A new labelled Phase-9 stack cloned from the isolated source was also attempted,
then removed with its own volumes. Its documented seeder does not identify/map
the PC fixture for a NEW scan, so it could not provide NEW or browser
manual-override evidence.

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 1 - Bug] Prevented writes to the derived `roms_metadata` view.
   - Structured fields now merge into `Rom.igdb_metadata`, which the view projects.
   - The scan returns a view-free object to the outer persistence step and refreshes enriched ROM details for socket serialization.

## Self-Check: PASSED

- Code and UAT files exist.
- Listed commits are present on the active branch.
