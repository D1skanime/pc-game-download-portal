---
phase: 12-dlc-detail-pages-for-local-pc-components
plan: 04
subsystem: frontend-localization
tags: [vue-i18n, locales, pc-dlc]
requires:
  - phase: 12
    provides: DLC detail-page copy contract
provides:
  - First-batch translations for the DLC detail page
  - Localized read-only manifest and unavailable-state copy
affects: [12-03, 12-05, 12-06]
tech-stack:
  added: []
  patterns: [sorted rom namespace keys, generic category-dlc reuse]
key-files:
  created: []
  modified:
    - frontend/src/locales/bg_BG/rom.json
    - frontend/src/locales/cs_CZ/rom.json
    - frontend/src/locales/de_DE/rom.json
    - frontend/src/locales/en_GB/rom.json
    - frontend/src/locales/en_US/rom.json
    - frontend/src/locales/es_ES/rom.json
    - frontend/src/locales/fr_FR/rom.json
    - frontend/src/locales/hu_HU/rom.json
    - frontend/src/locales/it_IT/rom.json
key-decisions:
  - "Reuse the existing rom.category-dlc key for the textual DLC identity."
  - "Keep manifest wording read-only and relative-path based."
patterns-established:
  - "DLC-detail locale keys use the pc-dlc prefix and retain game and relativePath placeholders."
requirements-completed: []
duration: 8min
completed: 2026-09-02
---

# Phase 12 Plan 04: First DLC Detail Locale Batch Summary

**Nine locale files now provide translated, read-only DLC detail copy for parent return, fallback identity, unavailable states, and immutable local-file evidence.**

## Performance

- **Duration:** 8 min
- **Completed:** 2026-09-02T15:35:00Z
- **Tasks:** 1/1
- **Files modified:** 9

## Accomplishments

- Added eight sorted `pc-dlc-*` keys to the first locale batch.
- Preserved `{game}` and `{relativePath}` placeholders in every locale.
- Reused the existing generic `rom.category-dlc` identity key.

## Task Commits

1. **Task 1: Add source copy and first locale translations** - `d9fe2e66b` (feat)

## Files Created/Modified

- `frontend/src/locales/{bg_BG,cs_CZ,de_DE,en_GB,en_US,es_ES,fr_FR,hu_HU,it_IT}/rom.json` - Sorted localized DLC detail copy.

## Verification

- `cd frontend && python3 src/locales/check_i18n_sorted.py` passed.
- Confirmed every modified locale contains all eight `pc-dlc-*` keys.

## Decisions Made

- Reused `rom.category-dlc` for the textual DLC identity because the plan requires existing generic copy to take precedence.
- The added copy refers only to local immutable file entries and relative paths. It does not imply fetching, applying, or changing artwork.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Issues Encountered

None.

## Next Phase Readiness

Plan 12-03 can consume the established `pc-dlc-*` keys. Plan 12-05 supplies the remaining locale batch before repository-wide locale parity validation in Plan 12-06.

## Self-Check: PASSED

- All nine modified locale files exist.
- Task commit `d9fe2e66b` exists in git history.

_Phase: 12-dlc-detail-pages-for-local-pc-components_
_Completed: 2026-09-02_
