---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 17
subsystem: frontend-i18n
tags: [vue-i18n, locales, catalog-removal, source-safety]
requires:
  - phase: 06-16
    provides: Seven-key en_US catalog-removal contract and first eight peer translations
provides:
  - Source-safe catalog removal translations for the final nine peer locales
  - Repository-wide parity for all 18 locale catalogs
affects: [06-15, frontend-i18n, catalog-removal]
tech-stack:
  added: []
  patterns:
    - Locale-specific plural forms preserve the source placeholder contract
    - Catalog removal translations explicitly separate catalog state from source files
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
  - Final-batch translations use each locale's established catalog terminology and native plural requirements.
  - Every locale states that original files and folders remain unchanged and describes future-scan exclusion separately.
patterns-established:
  - All supported locales expose the same seven-key source-safe catalog removal contract.
requirements-completed: [CAT-01, CAT-04]
duration: 12m
completed: 2026-08-13
---

# Phase 6 Plan 17: Catalog Removal Final Locale Batch Summary

**Accurate catalog-only removal copy with source-preservation and future-scan semantics across the final nine locales, completing parity for all 18 supported locales**

## Performance

- **Duration:** 12 minutes
- **Started:** 2026-08-13T10:54:39Z
- **Completed:** 2026-08-13T11:06:26Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added the complete seven-key catalog-removal contract to Japanese, Korean, Polish, Brazilian Portuguese, Romanian, Russian, Turkish, Simplified Chinese, and Traditional Chinese.
- Preserved locale-specific plural forms and exact placeholder names while keeping every locale file valid and sorted.
- Completed repository-wide locale parity and confirmed the active v2 dialog remains catalog-only through its focused component test.
- Passed full frontend typecheck and a production build using task-owned output.

## Task Commits

1. **Task 1: Translate the first five final-batch locales** - `9445c35c0` (feat)
2. **Task 2: Finish translations and run global frontend gates** - `e4f3021d5` (feat)

## Files Created/Modified

- `frontend/src/locales/ja_JP/rom.json` - Japanese catalog-only removal copy.
- `frontend/src/locales/ko_KR/rom.json` - Korean catalog-only removal copy.
- `frontend/src/locales/pl_PL/rom.json` - Polish catalog-only removal copy with three plural forms.
- `frontend/src/locales/pt_BR/rom.json` - Brazilian Portuguese catalog-only removal copy.
- `frontend/src/locales/ro_RO/rom.json` - Romanian catalog-only removal copy.
- `frontend/src/locales/ru_RU/rom.json` - Russian catalog-only removal copy with three plural forms.
- `frontend/src/locales/tr_TR/rom.json` - Turkish catalog-only removal copy.
- `frontend/src/locales/zh_CN/rom.json` - Simplified Chinese catalog-only removal copy.
- `frontend/src/locales/zh_TW/rom.json` - Traditional Chinese catalog-only removal copy.

## Decisions Made

- Used natural locale-language catalog terminology rather than copying English values.
- Kept source preservation explicit in every locale and described future-scan exclusion as optional scan behavior.
- Used three plural variants for Polish and Russian while preserving the source placeholder sets.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Initialized task-owned Node volume permissions**

- **Found during:** Task 2 dependency installation
- **Issue:** The new Docker volume was initially owned by root, so the checkout owner could not create dependency directories.
- **Fix:** Changed only the task-owned volume mount root to UID/GID 1000, then installed dependencies as the checkout owner.
- **Files modified:** None.
- **Verification:** Node 24 dependency installation completed and all frontend gates ran as UID/GID 1000.
- **Committed in:** Not applicable, environment-only correction.

**2. [Rule 3 - Blocking] Redirected production build output to task-owned temporary storage**

- **Found during:** Final static verification
- **Issue:** The repository's pre-existing `frontend/dist` ownership blocked service-worker output.
- **Fix:** Re-ran Vite with output under the container's exact task-owned `/tmp/romm-06-17-dist` directory and removed it after the successful build.
- **Files modified:** None.
- **Verification:** Production build completed with 4,467 modules transformed and generated PWA assets.
- **Committed in:** Not applicable, environment-only correction.

---

**Total deviations:** 2 auto-fixed blocking environment issues.
**Impact on plan:** Both fixes were isolated to task-owned runtime storage. Product scope, repository files, and services were unchanged.

## Issues Encountered

- The task-owned dependency install reported eight pre-existing package audit findings. No dependency or lockfile changed.
- The build emitted pre-existing Browserslist, CSS pseudo-class, dependency eval, and bundle-size warnings. The build completed successfully.

## Verification

- Repository-wide locale parity passed for all 17 peer directories against en_US.
- Repository-wide locale sorting passed.
- Python JSON validation passed for all nine owned locale files.
- All seven keys exist in all nine locales with locale-language values and exact placeholder-set parity.
- Polish and Russian preserve three plural variants; the other locales preserve their applicable forms.
- No new owned value contains an em dash, TODO, FIXME, placeholder copy, machine-noise marker, or copied en_US value.
- Focused `DeleteRomDialog.test.ts`: 3 tests passed.
- Full `vue-tsc --noEmit`: passed.
- Prettier passed for the four Task 2 locale files; commit hooks passed all nine locale files across both commits.
- Production Vite build passed with task-owned output and no repository artifact.
- `git diff --check` passed across both task commits.
- Both commits contain only the nine declared locale files and delete no tracked files.

## Known Stubs

None.

## Threat Flags

None. The locale resources do not add a network, authentication, filesystem, schema, or trust-boundary surface beyond the plan threat model.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- All 18 locale files now expose the source-safe catalog-only contract.
- Plan 15 can perform final Phase 6 closure without reopening Plan 16 or Plan 17 locale files.
- No deployment, service restart, or v1 edit was performed.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_

## Self-Check: PASSED

- All nine declared locale files exist in the canonical Linux checkout.
- Task commits `9445c35c0` and `e4f3021d5` exist in git history.
- Parity, sorting, JSON, translation, placeholder, focused test, typecheck, formatting, build, hook, diff, and scope checks produced the evidence recorded above.
- The summary contains no unverified security surface or known stub claim.
- Plan 16 first-batch locale files remain untouched.
