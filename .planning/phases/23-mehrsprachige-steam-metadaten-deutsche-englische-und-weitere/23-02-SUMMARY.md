---
phase: 23-mehrsprachige-steam-metadaten-deutsche-englische-und-weitere
plan: 02
subsystem: metadata
tags: [steam, metadata, localization, sqlalchemy, pytest]
requires:
  - phase: 23-mehrsprachige-steam-metadaten-deutsche-englische-und-weitere
    provides: Validated provenance-bearing localized Steam text variants
provides:
  - Additive validated Steam text-variant persistence for parent ROMs and DLC components
  - Dedicated component Steam provenance storage without provider-metadata shadowing
affects: [steam_metadata, PC metadata enrichment, Phase 23 plan 03]
tech-stack:
  added: []
  patterns:
    - Validated language-by-language JSON merge at a provider ownership boundary
    - Component metadata reads and writes its first-class Steam JSON column
key-files:
  created: []
  modified:
    - backend/handler/metadata/steam_merge.py
    - backend/handler/database/roms_handler.py
    - backend/handler/metadata/pc_automation.py
    - backend/handler/scan_handler.py
    - backend/endpoints/sockets/scan.py
    - backend/endpoints/roms/pc_metadata.py
    - backend/tests/handler/metadata/test_steam_merge.py
    - backend/tests/handler/metadata/test_pc_automation.py
    - backend/tests/handler/database/test_roms_handler.py
    - backend/tests/endpoints/roms/test_pc_metadata.py
    - backend/tests/endpoints/sockets/test_scan.py
key-decisions:
  - "Only allowlisted base tags with matching Steam source-language provenance can update text_variants."
  - "Component Steam provenance belongs in RomComponentMetadata.steam_metadata, never provider_metadata."
patterns-established:
  - "Steam variant refreshes merge per language and preserve prior valid language evidence when a request is unavailable."
requirements-completed: [STEAM-02, STEAM-05]
duration: 12min
completed: 2026-10-04
---

# Phase 23 Plan 02: Guarded Steam Text-Variant Persistence Summary

**Validated Steam language variants now merge additively for parent ROMs and DLC components while manual and non-Steam display authority remains intact.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-10-04T20:25:48Z
- **Completed:** 2026-10-04T20:37:48Z
- **Tasks:** 2 completed
- **Files modified:** 11

## Accomplishments

- Added bounded, provenance-checked per-language merging for `steam_metadata.text_variants`; malformed patches cannot remove valid persisted variants.
- Routed parent scans, automation, socket DLC enrichment, and reviewed parent and component selection through the guarded Steam metadata boundary.
- Corrected DLC metadata persistence and current-state construction to use `RomComponentMetadata.steam_metadata` and preserve unrelated provider metadata.

## Task Commits

1. **Task 1: Define additive variant merge and component-column persistence regressions** - `15697a5ab` (test)
2. **Task 2: Implement guarded parent and DLC text-variant persistence** - `d201636d3` (feat)

## Files Created/Modified

- `backend/handler/metadata/steam_merge.py` - Validates and merges Steam text variants by canonical language tag.
- `backend/handler/database/roms_handler.py` - Persists component Steam data in its dedicated column.
- `backend/handler/metadata/pc_automation.py`, `backend/handler/scan_handler.py`, `backend/endpoints/sockets/scan.py` - Read component Steam state from the authoritative column before applying a patch.
- `backend/endpoints/roms/pc_metadata.py` - Normalizes reviewed Steam component selections against current ownership state.
- `backend/tests/handler/metadata/test_steam_merge.py`, `backend/tests/handler/metadata/test_pc_automation.py`, `backend/tests/handler/database/test_roms_handler.py`, `backend/tests/endpoints/roms/test_pc_metadata.py`, `backend/tests/endpoints/sockets/test_scan.py` - Cover merge, persistence, automation, selection, and socket seams.

## Decisions Made

- Valid variants require an allowlisted canonical base tag, matching Steam request-language provenance, and at least one non-empty bounded text field.
- Retained the existing JSON columns and legacy scalar display fields. No schema migration or data rewrite is needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved scoped test type-check error**

- **Found during:** Task 2
- **Issue:** Scoped Trunk checking found an unchecked optional `AsyncMock.await_args` access in the edited reviewed-selection test file.
- **Fix:** Asserted the await call exists before accessing its arguments.
- **Files modified:** `backend/tests/endpoints/roms/test_pc_metadata.py`
- **Verification:** Scoped `trunk check --no-fix` passed.
- **Committed in:** `d201636d3`

**Total deviations:** 1 auto-fixed (1 blocking)

## Issues Encountered

- The required database-backed pytest command is blocked during fixture setup because the local MariaDB test endpoint at `127.0.0.1:3306` is unavailable. This is infrastructure blocking, not a test failure.
- The non-database focused verification passed with `--noconftest`; it intentionally excludes only the unavailable database bootstrap fixture.

## Verification

- PASS: Red gate, `cd backend && uv run pytest --noconftest tests/handler/metadata/test_steam_merge.py -q` produced 2 expected variant-loss failures before implementation.
- PASS: `cd backend && uv run pytest --noconftest tests/handler/metadata/test_steam_merge.py tests/handler/metadata/test_pc_automation.py::test_component_apply_retains_existing_steam_text_variants tests/endpoints/sockets/test_scan.py::test_scan_enrichment_retains_component_steam_text_variants -q` (12 passed).
- PASS: `trunk fmt -- [plan files]` and scoped `trunk check --no-fix -- [plan files]`.
- BLOCKED: Required focused pytest command, including database-backed handler and endpoint tests, cannot establish its MariaDB test connection at `127.0.0.1:3306`.

## TDD Gate Compliance

- PASS: `15697a5ab` is the failing-test Red commit, followed by the implementation Green commit `d201636d3`.

## Known Stubs

None.

## Next Phase Readiness

Phase 23 plan 03 can expose the durable parent and DLC variant maps and select localized detail text. Restore the local MariaDB test service to run the full focused suite.

## Self-Check: PASSED

- Confirmed all eleven modified implementation and test files exist.
- Confirmed commits `15697a5ab` and `d201636d3` exist in Git history.
