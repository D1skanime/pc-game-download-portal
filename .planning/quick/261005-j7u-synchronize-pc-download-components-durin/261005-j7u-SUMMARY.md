---
quick_id: 261005-j7u
subsystem: scan orchestration
tags: [python, pytest, windows, pc-components, quick-scan]
requires:
  - quick: 261005-h08
    provides: Root-level directory files are emitted as the PC base component manifest.
provides:
  - Regression coverage for durable component reconciliation on existing nested Windows quick scans.
affects: [PC scanning, Game Download manifests]
tech-stack:
  added: []
  patterns:
    - Scan-path regressions patch component discovery and durable synchronization at the orchestration boundary.
key-files:
  created: []
  modified:
    - backend/endpoints/sockets/scan.py
    - backend/tests/endpoints/sockets/test_scan.py
    - backend/tests/handler/test_fastapi.py
key-decisions:
  - QUICK admission uses the current filesystem entry shape and remains limited to existing nested Windows ROMs.
  - The existing scan-handler reconciliation remains unchanged because it already runs after durable persistence.
metrics:
  duration: 12min
  completed: 2026-10-05
---

# Quick Task 261005-j7u Summary

**Unscoped QUICK scans now dispatch only existing nested Windows ROMs into the already-correct durable PC component reconciliation path.**

## Accomplishments

- Added an existing-ROM Witcher fixture with the h08 root ISO base manifest and a DLC manifest.
- Asserted component discovery receives the durable persisted parent and synchronization receives the exact base and DLC components on `newly_added=False` QUICK scans.
- Added non-Windows nested and Windows flat negative controls, and asserted seeded title, media, and IGDB metadata stay intact.
- Threaded the current `FSRom` shape through the socket scan admission gate without broadening scoped scans.
- Added socket-level dispatch coverage proving only the nested Windows entry reaches `_identify_rom` with the original QUICK type and metadata sources.

## Task Commits

1. **Prior scan-handler regression coverage** - `f66bc9f6f` (test)
2. **Task 1 and 2: Admit nested Windows component-only QUICK rescans** - `dabb232bd` (fix)

## Verification

- `trunk fmt backend/endpoints/sockets/scan.py backend/tests/endpoints/sockets/test_scan.py` passed.
- `trunk check backend/endpoints/sockets/scan.py backend/tests/endpoints/sockets/test_scan.py` passed.
- `uv run pytest tests/endpoints/sockets/test_scan.py --collect-only -q` collected 105 tests.
- Both focused pytest suites could not execute test bodies because the isolated MariaDB fixture cannot connect to `127.0.0.1:3306`. No service was started or changed.
- Isolated UAT passed in two parts: an unscoped QUICK scan visibly dispatched existing Windows ROMs before unrelated Steam automation made it impractical to wait for every fixture; a targeted QUICK scan of the already-existing `The Witcher 3: Wild Hunt` ROM then completed the same component-reconciliation path and persisted both `base/The Witcher 3 Wild Hunt.iso` (31 bytes) and `expansion/Hearts of Stone/Hearts of Stone.rar` (34 bytes).

## Deviations from Plan

### Existing Implementation

**1. Scan-handler reconciliation already satisfied its part of the original plan**

- **Found during:** Task 1 review
- **Evidence:** `scan_rom` has long gated reconciliation with `platform.slug == UPS.WIN and fs_rom["nested"]`, immediately after `db_rom_handler.add_rom` and before metadata lookup.
- **Resolution:** Added the regression coverage, then wired the actual missing socket admission condition that makes the path reachable for unscoped QUICK scans.

## Known Stubs

None.

## Self-Check: PASSED

- `backend/tests/handler/test_fastapi.py` exists.
- `backend/endpoints/sockets/scan.py` and `backend/tests/endpoints/sockets/test_scan.py` exist.
- Commits `f66bc9f6f` and `dabb232bd` exist in git history.
