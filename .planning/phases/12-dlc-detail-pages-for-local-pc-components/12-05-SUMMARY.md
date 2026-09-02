---
phase: 12-dlc-detail-pages-for-local-pc-components
plan: 05
subsystem: frontend-localization
tags: [vue-i18n, locales, pc-dlc]
requires:
  - phase: 12
    provides: DLC detail-page copy contract
provides:
  - Second-batch translations for the DLC detail page
  - Localized read-only manifest and unavailable-state copy
affects: [12-03, 12-06]
tech-stack:
  added: []
  patterns: [sorted rom namespace keys, generic category-dlc reuse]
key-files:
  created: []
  modified:
    - frontend/src/locales/ja_JP/rom.json
    - frontend/src/locales/ko_KR/rom.json
    - frontend/src/locales/pl_PL/rom.json
    - frontend/src/locales/pt_BR/rom.json
    - frontend/src/locales/ro_RO/rom.json
    - frontend/src/locales/ru_RU/rom.json
    - frontend/src/locales/tr_TR/rom.json
    - frontend/src/locales/zh_CN/rom.json
    - frontend/src/locales/zh_TW/rom.json
key-decisions:
  - "Preserve the exact game and relativePath placeholders from the English source."
  - "Keep manifest wording read-only and relative-path based."
requirements-completed: []
duration: 3min
completed: 2026-09-02
---

# Phase 12 Plan 05: Second DLC Detail Locale Batch Summary

**Nine remaining locale files now provide translated, read-only DLC detail copy for parent return, fallback identity, unavailable states, and immutable local-file evidence.**

## Performance

- **Duration:** 3 min
- **Completed:** 2026-09-02T15:37:50Z
- **Tasks:** 1/1
- **Files modified:** 9

## Accomplishments

- Added eight sorted `pc-dlc-*` keys to the second locale batch.
- Preserved `{game}` and `{relativePath}` placeholders in every locale.
- Kept all local-file copy relative-path based and read-only.

## Task Commits

1. **Task 1: Add the remaining locale translations** - `2b8ffb803` (feat)

## Files Created/Modified

- `frontend/src/locales/{ja_JP,ko_KR,pl_PL,pt_BR,ro_RO,ru_RU,tr_TR,zh_CN,zh_TW}/rom.json` - Sorted localized DLC detail copy.

## Verification

- `cd frontend && python3 src/locales/check_i18n_sorted.py` passed.
- Confirmed every modified locale contains all eight `pc-dlc-*` keys.
- Confirmed `{game}` and `{relativePath}` are preserved wherever used by the English source.
- `git diff --check` passed.

## Decisions Made

- The localized copy only describes existing immutable local-file entries and relative paths. It does not imply fetching, applying, or changing artwork.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Issues Encountered

None.

## Next Phase Readiness

Plan 12-03 can consume the established `pc-dlc-*` keys. Plan 12-06 can run repository-wide locale parity validation now that both locale batches are complete.

## Self-Check: PASSED

- All nine modified locale files exist.
- Task commit `2b8ffb803` exists in git history.

_Phase: 12-dlc-detail-pages-for-local-pc-components_
_Completed: 2026-09-02_
