---
phase: 20-media-management-and-owned-soundtrack-uploads
plan: "06"
subsystem: ui
tags: [i18n, vue-i18n, locales, owned-media]
requires:
  - phase: 20
    provides: completed Media and owned-soundtrack UI contract
provides:
  - first bounded sorted locale batch for Media management copy
affects: [20-07, v2-media-management]
tech-stack:
  added: []
  patterns: [en_US source locale, sorted locale JSON]
key-files:
  created: []
  modified:
    - frontend/src/locales/en_US/rom.json
    - frontend/src/locales/en_GB/rom.json
    - frontend/src/locales/de_DE/rom.json
    - frontend/src/locales/bg_BG/rom.json
    - frontend/src/locales/cs_CZ/rom.json
    - frontend/src/locales/es_ES/rom.json
    - frontend/src/locales/fr_FR/rom.json
    - frontend/src/locales/hu_HU/rom.json
    - frontend/src/locales/it_IT/rom.json
key-decisions:
  - "The first batch establishes the exact Media key set; Plan 20-07 supplies the remaining locales and full parity validation."
requirements-completed:
  [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07]
duration: 10min
completed: 2026-09-28
---

# Phase 20 Plan 06: First Media Locale Batch Summary

**Sorted first locale batch for owned-media artwork, backgrounds, soundtrack placement, upload, ordering, and recovery copy.**

## Accomplishments

- Added the Media copy keys used by the completed artwork and owned-soundtrack surfaces.
- Kept explicit RomM-owned storage wording in the source copy.
- Verified JSON sorting for the bounded locale batch.

## Task Commits

1. **Task 1: Add all Media management copy to every locale** - `90e3388c2` (feat)

## Decisions Made

- The source key set is limited to the completed components' Media labels, errors, ordered-placement controls, and owned-storage hints.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Next Phase Readiness

Plan 20-07 can translate the established key set into the remaining nine locales and run full parity validation.

## Self-Check: PASSED

- All nine planned locale files exist.
- Task commit `90e3388c2` exists.
