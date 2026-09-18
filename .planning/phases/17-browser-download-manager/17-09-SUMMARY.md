---
phase: 17-browser-download-manager
plan: 09
subsystem: frontend
tags: [vue, vue-i18n, localization, browser-downloads]

# Dependency graph
requires:
  - phase: 17-browser-download-manager
    provides: browser download selection, standard handoff queue, and enhanced transfer states
provides:
  - truthful browser-manager copy in the English source and first nine locales
  - sorted archive-set, fallback, queue, recovery, and transfer-history terminology
affects: [17-10-browser-download-manager, browser-download-manager]

# Tech tracking
tech-stack:
  added: []
  patterns:
    [
      locale parity within the staged locale group,
      explicit browser handoff versus server-served versus enhanced-verified wording,
    ]

key-files:
  created: []
  modified:
    - frontend/src/locales/en_US/rom.json
    - frontend/src/locales/en_GB/rom.json
    - frontend/src/locales/bg_BG/rom.json
    - frontend/src/locales/cs_CZ/rom.json
    - frontend/src/locales/de_DE/rom.json
    - frontend/src/locales/es_ES/rom.json
    - frontend/src/locales/fr_FR/rom.json
    - frontend/src/locales/hu_HU/rom.json
    - frontend/src/locales/it_IT/rom.json

key-decisions:
  - "Reserve Handed to browser for standard attachment handoff, Served for server response delivery, and Verified for enhanced local checksum equality."
  - "Keep full-locale parity validation deferred until Plan 17-10 adds the remaining nine locales, while enforcing exact parity across this plan's nine-file group."

patterns-established:
  - "Browser download copy names capability fallback, folder permission denial, source changes, expiry, and recovery as distinct states."

requirements-completed: [UXDL-01, SAFE-01]

# Metrics
duration: 15min
completed: 2026-09-18
---

# Phase 17 Plan 09: Browser Download Manager Locale Summary

**Truthful browser-download terminology is now translated and sorted across the English source and first eight translated locales.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-18T07:03:00Z
- **Completed:** 2026-09-18T07:18:00Z
- **Tasks:** 1
- **Files modified:** 9

## Accomplishments

- Added archive-set, optional-exclusion, standard limitation, enhanced capability, permission fallback, queue-control, and recovery copy.
- Added exact transfer-history labels for handed-to-browser, served, verified, stale, cancelled, expired, and failed outcomes without asserting browser-local completion.
- Added translated values to `en_GB`, `bg_BG`, `cs_CZ`, `de_DE`, `es_ES`, `fr_FR`, `hu_HU`, and `it_IT`, preserving sorted keys and exact key parity with `en_US`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add truthful source and first-group locale keys** - `bf9da0ce7` (feat)

## Files Created/Modified

- `frontend/src/locales/en_US/rom.json` - English browser-manager source strings.
- `frontend/src/locales/en_GB/rom.json`, `bg_BG/rom.json`, `cs_CZ/rom.json`, `de_DE/rom.json`, `es_ES/rom.json`, `fr_FR/rom.json`, `hu_HU/rom.json`, `it_IT/rom.json` - translated first-group locale strings.

## Decisions Made

- Standard attachment attempts are labelled as handed to the browser, not downloaded or complete.
- Server delivery is labelled separately from enhanced local checksum verification.
- Full parity is intentionally left for Plan 17-10; this plan validated JSON and exact key parity across its declared nine files.

## Deviations from Plan

None - plan executed as written. The locale sorter made the required deterministic ordering adjustment within the nine declared files.

## Issues Encountered

None. Full 18-locale parity was not run because Plan 17-10 owns the remaining nine locale files.

## Known Stubs

None in the modified locale files.

## Threat Flags

None. This plan changed localized presentation strings only and introduced no new endpoint, authorization path, file access, or schema surface.

## Verification

- `python3 frontend/src/locales/check_i18n_sorted.py` passed.
- JSON parsing and exact key parity across the nine declared locales passed (`545` keys).
- `cd frontend && npm run typecheck` passed.
- `cd frontend && npm run test -- DownloadManager DownloadSelectionDialog useBrowserDownloadQueue` passed (3 files, 4 tests).
- `git diff --check` passed.

## Self-Check: PASSED

- All nine modified locale files exist.
- Commit `bf9da0ce7` exists in Git history.
- The task commit contains no tracked file deletions.

## Next Phase Readiness

Plan 17-10 can add the same 44 keys to the remaining nine locales and run the full parity validator.

---

_Phase: 17-browser-download-manager_
_Completed: 2026-09-18_
