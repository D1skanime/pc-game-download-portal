---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 39
subsystem: frontend-i18n
tags: [vue-i18n, locales, primary-manual, source-safety]
requires:
  - phase: 06-38
    provides: Canonical 13-key en_US primary-manual contract and first eight peer translations
provides:
  - Native primary-manual ownership and recovery copy for the final nine peer locales
  - Exact repository-wide locale parity across all 18 supported locales
affects: [frontend-i18n, primary-manual, 06-42]
tech-stack:
  added: []
  patterns:
    - RomM-owned manual resources are explicitly separated from unchanged game-library files
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
  - Every final peer locale distinguishes RomM-owned primary manuals from immutable game-library files.
  - Pre-success replacement failure preserves the existing manual, while post-success refresh failure directs the user to reload.
requirements-completed: [CAT-01, CAT-02]
duration: 12m
completed: 2026-08-21
---

# Phase 6 Plan 39: Final Primary Manual Locale Parity Summary

**Native source-safe primary-manual copy across the final nine locales with exact 18-locale parity**

## Performance

- **Duration:** 12 minutes
- **Completed:** 2026-08-21
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added the exact approved 13-key primary-manual contract to Japanese, Korean, Polish, Brazilian Portuguese, Romanian, Russian, Turkish, Simplified Chinese, and Traditional Chinese.
- Preserved explicit RomM-resource ownership, unchanged game-library files, safe replacement failure, conflict recovery, and saved-but-refresh-failed semantics.
- Completed exact key and interpolation parity across all 18 supported locales without modifying Plan 38 files.

## RED/GREEN Evidence

- **Task 1 RED:** Repository parity exited 1 and reported the exact 13 missing keys in only the nine Plan 39 locales.
- **Task 1 GREEN:** Sorting and independent JSON validation passed for ja_JP, ko_KR, pl_PL, pt_BR, and ro_RO.
- **Task 2 RED:** After Task 1, parity exited 1 and reported the exact 13 missing keys in only ru_RU, tr_TR, zh_CN, and zh_TW.
- **Task 2 GREEN:** Repository-wide parity and sorting passed across all 18 locales.

The project-level MVP and TDD modes were disabled. These JSON-only tasks used plan-required failing contract probes followed by one hooked feature commit per task.

## Task Commits

1. **Task 1: Translate Japanese through Romanian locale peers** - `7bee8e6ce`
2. **Task 2: Finish peer translations and prove global parity** - `e6a38aeff`

## Verification

- `python3 frontend/src/locales/check_i18n_locales.py` passed.
- `python3 frontend/src/locales/check_i18n_sorted.py` passed.
- `python3 -m json.tool` passed independently for all nine owned files.
- Placeholder, TODO, FIXME, coming-soon, em-dash, machine-noise, and interpolation drift checks passed.
- Prettier passed for all nine owned files in `node:24-bookworm`.
- `npm run typecheck` passed with Node 24 and a 4096 MiB heap.
- `npm run build` passed with Node 24 using an isolated UID-1000 tmpfs for `dist`.
- `git diff --check` passed.
- Both commit hooks passed on the exact owned files.
- Exact task-owned containers and node_modules volumes were removed and proved absent.
- The tracked worktree is clean and the approved 28-entry untracked baseline remains exact with hash `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Verification Environment] Isolated the build from a pre-existing root-owned dist directory**

- **Found during:** Overall build verification
- **Issue:** The non-root Node runner could not write `frontend/dist/sw.js` because the ignored existing dist directory is owned by root.
- **Fix:** Re-ran the build with an exact UID-1000 tmpfs mounted at `frontend/dist`.
- **Files modified:** None.
- **Verification:** The production build completed successfully and the disposable resource cleanup passed.

**Total deviations:** 1 auto-fixed blocking issue.
**Impact:** Verification remained non-root, disposable, and checkout-neutral. Product scope was unchanged.

## Issues Encountered

- npm reported eight pre-existing dependency audit findings and existing build warnings. No dependency or lockfile changed.

## Known Stubs

None.

## Threat Flags

None. The plan changed locale data only and introduced no network, authentication, file-access, schema, or trust-boundary surface beyond the planned translation contract.

## User Setup Required

None.

## Next Phase Readiness

- The active manual UI can consume the complete 18-locale contract.
- Plan 06-42 is the earliest incomplete plan after already completed Plans 06-40 and 06-41.

## Self-Check: PASSED

- All nine declared locale files exist.
- Task commits `7bee8e6ce` and `e6a38aeff` exist in git history.
- RED, GREEN, JSON, sorting, global parity, native-copy, source-safety, placeholder, Prettier, typecheck, build, hook, diff, cleanup, and baseline evidence passed.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-21_
