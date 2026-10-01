---
phase: 21-unify-admin-pc-scans-with-german-steam-metadata-and-media
plan: "02"
subsystem: database
tags: [sqlalchemy, alembic, steam, owned-media, reconciliation]
requires:
  - phase: 20-media-management-and-owned-soundtrack-uploads
    provides: provider-owned media, upload ownership, and placement models
provides:
  - Durable operator-suppression state for provider media
  - Atomic complete Steam media-inventory reconciliation
  - Unclaimed-surface-only automatic media placement
affects: [21-03, scan-handler, owned-media]
tech-stack:
  added: []
  patterns:
    [locked optimistic inventory reconciliation, provider-scoped tombstones]
key-files:
  created:
    - backend/alembic/versions/0132_steam_scan_owned_media_state.py
  modified:
    - backend/models/rom.py
    - backend/handler/database/roms_handler.py
    - backend/tests/handler/database/test_rom_media.py
key-decisions:
  - "Use a persisted operator_suppressed flag to distinguish operator deletion from ordinary scan tombstones."
  - "Treat Steam inventory placement as additive only on empty compatible surfaces."
patterns-established:
  - "Scan services inspect known Steam identities before downloading and pass complete stored inventory to one locked reconciliation call."
  - "Only paths proven unreferenced after flush are eligible for post-commit cleanup."
requirements-completed: [STEAM-02, STEAM-05]
duration: 10min
completed: 2026-09-30
---

# Phase 21 Plan 02: Owned Steam Media Reconciliation Summary

**Durable operator suppression and a locked Steam inventory reconciliation preserve uploads and manual media choices during administrator scans.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-09-30T13:05:00Z
- **Completed:** 2026-09-30T13:14:55Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Added migration 0132 and a persisted `operator_suppressed` marker, separating operator deletion from an ordinary stale-inventory tombstone.
- Retained Phase 20 explicit-refresh restoration semantics while keeping uploads outside provider suppression.
- Added a single locked, optimistic Steam inventory transaction that scopes mutations to Steam provider rows, preserves claimed placements, and returns only unreferenced retired paths.
- Added focused D-07 and D-08 regression coverage for stale candidates, suppression, idempotency, upload preservation, and unclaimed-surface placement.

## Task Commits

1. **Task 1: Persist operator suppression separately from scan tombstones** - `1a63b1388` (feat)
2. **Task 2: Add atomic Steam inventory reconciliation with unclaimed-only placement** - `103649a20` (feat)

## Files Created/Modified

- `backend/alembic/versions/0132_steam_scan_owned_media_state.py` - Adds reversible durable suppression state after revision 0131.
- `backend/models/rom.py` - Persists the operator-suppression marker on owned media.
- `backend/handler/database/roms_handler.py` - Adds Steam identity lookup and atomic complete-inventory reconciliation.
- `backend/tests/handler/database/test_rom_media.py` - Covers deletion intent, scope, idempotency, and placement rules.

## Decisions Made

- Operator deletion sets `operator_suppressed` only for provider media. Explicit refresh clears that marker when it restores a candidate.
- A normal Steam inventory leaves suppressed rows untouched, tombstones only active absent Steam candidates, and never mutates uploads or other providers.
- Automatic placement creates at most one compatible Steam placement per empty overview or background surface. It never replaces or reorders a claimed surface.

## Deviations from Plan

None - plan executed as specified.

## Issues Encountered

- `uv run pytest tests/handler/database/test_rom_media.py -x` could not reach the configured MariaDB at `127.0.0.1:3306`, before any test assertion ran. No Docker Compose, NAS, or Team4s service was accessed. The migration upgrade/downgrade cycle therefore remains blocked for authorized MariaDB/MySQL/PostgreSQL infrastructure.
- `ruff` is not available as a standalone `uv run ruff` command in this checkout. The commit hook formatted and checked both Task 2 files successfully; syntax parsing and the focused import smoke check also succeeded.

## Known Stubs

None.

## Next Phase Readiness

- Plan 21-03 can reuse `get_steam_owned_media_inventory()` to avoid downloading active paths and must invoke `reconcile_steam_owned_media_inventory()` only with a complete validated inventory.
- Database-backed assertions and cross-dialect migration validation require the authorized disposable database environment.

## Self-Check: PASSED

- Confirmed migration, model, handler, and focused test file exist.
- Confirmed task commits `1a63b1388` and `103649a20` exist.

---

_Phase: 21-unify-admin-pc-scans-with-german-steam-metadata-and-media_
_Completed: 2026-09-30_
