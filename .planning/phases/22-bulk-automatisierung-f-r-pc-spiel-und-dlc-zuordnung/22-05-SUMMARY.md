---
phase: 22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung
plan: 05
subsystem: ui
tags: [vue-i18n, localization, pc-automation, v2-administration]
requires:
  - phase: 22-04
    provides: PC automation review queue and its i18n consumer keys
provides:
  - Complete, sorted PC automation review strings in all shipped locales
  - Automated parity and frontend typecheck proof for the queue namespace
affects: [pc-automation, v2-administration, uat]
tech-stack:
  added: []
  patterns:
    - en_US source keys mirrored by explicit translations in every shipped locale
key-files:
  created: []
  modified:
    - frontend/src/locales/en_US/settings.json
    - frontend/src/locales/bg_BG/settings.json
    - frontend/src/locales/cs_CZ/settings.json
    - frontend/src/locales/de_DE/settings.json
    - frontend/src/locales/en_GB/settings.json
    - frontend/src/locales/es_ES/settings.json
    - frontend/src/locales/fr_FR/settings.json
    - frontend/src/locales/hu_HU/settings.json
    - frontend/src/locales/it_IT/settings.json
    - frontend/src/locales/ja_JP/settings.json
    - frontend/src/locales/ko_KR/settings.json
    - frontend/src/locales/pl_PL/settings.json
    - frontend/src/locales/pt_BR/settings.json
    - frontend/src/locales/ro_RO/settings.json
    - frontend/src/locales/ru_RU/settings.json
    - frontend/src/locales/tr_TR/settings.json
    - frontend/src/locales/zh_CN/settings.json
    - frontend/src/locales/zh_TW/settings.json
key-decisions:
  - "The queue contract uses one sorted pc-automation object in settings.json for every locale."
  - "All 17 non-US locale values are explicit translations, including loading, rejection, and permission recovery states."
requirements-completed: [D-05, D-06, D-08]
duration: 12min
completed: 2026-10-02
---

# Phase 22 Plan 05: PC Automation Queue Localization Summary

**The PC automation review queue now has translated labels, actions, states, and failure feedback across all 18 shipped UI locales.**

## Accomplishments

- Added the 19-key English `pc-automation` source contract for queue review, selection, batching, correction, progress, and failures.
- Added explicit translations for all 17 non-US locales, retaining sorted JSON structure and no English fallback placeholders.
- Proved locale parity, alphabetical key order, and Vue TypeScript compilation.

## Task Commits

1. **Task 1: Add complete English source strings for the queue contract** - `c308f6d0c` (feat)
2. **Task 2: Translate the bounded 17-locale PC automation queue batch** - `1dce65ca0` (feat)
3. **Task 3: Verify localized queue keys through frontend compilation** - no source change required

## Files Created/Modified

- `frontend/src/locales/*/settings.json` - the sorted `pc-automation` translation contract in each shipped locale.

## Decisions Made

- Kept queue strings in the existing `settings.json` namespace, matching the queue's `vue-i18n` references.
- Translated safety-critical loading, error, rejection, and recovery messages alongside normal actions.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Repository-wide `git diff --check` reports four pre-existing blank-line warnings in unrelated generated API models. The locale-only diff is clean.

## Verification

- `cd frontend && python3 src/locales/check_i18n_locales.py` passed.
- `cd frontend && python3 src/locales/check_i18n_sorted.py` passed.
- `cd frontend && npm run typecheck` passed.

## Next Phase Readiness

- The localized queue can be exercised by the isolated Docker UAT workflow in Plan 22-06.

## Self-Check: PASSED

- Confirmed all 18 declared settings locale files contain the sorted queue contract.
- Confirmed commits `c308f6d0c` and `1dce65ca0` exist in Git history.
