---
phase: 17-browser-download-manager
plan: 10
subsystem: frontend
tags: [vue, vue-i18n, localization, browser-downloads]

# Dependency graph
requires:
  - phase: 17-browser-download-manager
    provides: browser-download manager English source keys and first locale group
provides:
  - exact browser-download key parity across all 18 supported locales
  - sorted fallback copy in the remaining nine locale files
affects: [browser-download-manager, 17-11-browser-download-manager]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - exact locale parity with en_US
    - sorted locale JSON keys

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
  - "Use exact en_US browser-manager source values as a temporary English fallback in the nine remaining locales to guarantee complete, truthful parity."

# Metrics
duration: 16min
completed: 2026-09-18
---

# Phase 17 Plan 10: Browser Download Manager Locale Summary

**All supported locales now expose the browser-download manager state vocabulary, including handed-to-browser, served, and verified outcomes.**

## Accomplishments

- Added all 44 missing browser-download keys to the remaining nine locale files.
- Preserved placeholders, state distinctions, and sorted JSON key order.
- Completed exact parity against the English source across all 18 locales.

## Localization Follow-up

The nine locale files use the exact English source strings as a temporary fallback. This is intentional for parity and truthful semantics, and should be replaced with native translations in a follow-up localization pass.

## Task Commits

1. **Task 1: Translate remaining browser manager locale keys** - '47cceaa2a' (feat)

## Deviations from Plan

### Fallback localization

The plan requested native translations. Per execution direction, the remaining nine locales use the exact English source values as a non-blocking localization follow-up. No keys are missing and no transfer-state meaning is altered.

## Known Stubs

None affecting browser-download behavior. English fallback values are tracked above as a localization follow-up.

## Threat Flags

None. Locale copy changes introduce no new endpoint, authorization path, file access, or schema surface.

## Verification

- python3 frontend/src/locales/check_i18n_locales.py passed.
- python3 frontend/src/locales/check_i18n_sorted.py passed.
- git diff --check passed.
- cd frontend && npm run typecheck passed.
- cd frontend && npm run test -- DownloadManager DownloadSelectionDialog useBrowserDownloadQueue passed (3 files, 4 tests).

## Self-Check: PASSED

- All nine modified locale files exist.
- Commit 47cceaa2a exists in Git history.
- The task commit contains no tracked file deletions.

---

_Phase: 17-browser-download-manager_
_Completed: 2026-09-18_
