---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 16
subsystem: frontend-i18n
tags: [vue-i18n, locales, catalog-removal, source-safety]
requires:
  - phase: 06-11
    provides: Catalog-only v2 ROM removal key consumers and IDs-only client boundary
provides:
  - Canonical seven-key en_US catalog-removal locale contract
  - Source-safe catalog removal translations for the first eight peer locales
affects: [06-17, frontend-i18n, catalog-removal]
tech-stack:
  added: []
  patterns:
    - Source locale keys preserve placeholders and plural forms across translated peers
    - Locale batches stay file-bounded while final repository parity is completed by the next plan
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
  - The source contract uses seven dedicated catalog-removal keys with no generic source-deletion wording.
  - Plan 16 owns only the first eight peers; Plan 17 completes the remaining nine locales without reopening these files.
patterns-established:
  - Catalog removal copy always states that original files and folders remain unchanged.
  - Future-scan exclusion is described as a separate optional scan behavior, not deletion.
requirements-completed: [CAT-01, CAT-04]
duration: 8m
completed: 2026-08-13
---

# Phase 6 Plan 16: Catalog Removal First Locale Batch Summary

**Seven-key catalog-only removal copy with source-preservation, retained-value, and future-scan semantics across nine locale files**

## Performance

- **Duration:** 8 minutes
- **Started:** 2026-08-13T10:35:52Z
- **Completed:** 2026-08-13T10:43:56Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Defined the canonical en_US contract for catalog-only title, body, confirmation, success, source preservation, retained user value, and optional future-scan exclusion.
- Added accurate locale-language values for en_GB, bg_BG, cs_CZ, de_DE, es_ES, fr_FR, hu_HU, and it_IT.
- Preserved all frozen-v1 keys, JSON structure, plural forms, and placeholders while keeping every owned file alphabetically sorted.
- Confirmed that repository-wide parity is missing only the exact seven keys in the nine locales assigned to Plan 17.

## Task Commits

1. **Task 1: Define source keys and translate the first four peers** - `54903fbcc` (feat)
2. **Task 2: Translate and validate the remaining first-batch locales** - `f15d0afac` (feat)

## Files Created/Modified

- `frontend/src/locales/en_US/rom.json` - Canonical seven-key catalog-only removal contract.
- `frontend/src/locales/en_GB/rom.json` - British English catalogue terminology.
- `frontend/src/locales/bg_BG/rom.json` - Bulgarian catalog-removal safety copy.
- `frontend/src/locales/cs_CZ/rom.json` - Czech catalog-removal safety copy with four plural forms.
- `frontend/src/locales/de_DE/rom.json` - German catalog-removal safety copy.
- `frontend/src/locales/es_ES/rom.json` - Spanish catalog-removal safety copy.
- `frontend/src/locales/fr_FR/rom.json` - French catalog-removal safety copy.
- `frontend/src/locales/hu_HU/rom.json` - Hungarian catalog-removal safety copy.
- `frontend/src/locales/it_IT/rom.json` - Italian catalog-removal safety copy.

## Decisions Made

- Used dedicated catalog language in every locale and explicitly stated that original files and folders remain unchanged.
- Kept retained saves, states, and play history distinct from catalog visibility.
- Presented future-scan exclusion as an optional scanning outcome rather than a filesystem action.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The full locale parity script exits nonzero at this bounded intermediate state. Its output lists only ja_JP, ko_KR, pl_PL, pt_BR, ro_RO, ru_RU, tr_TR, zh_CN, and zh_TW, each missing exactly the seven Plan 16 source keys. Those files are assigned exclusively to Plan 17.
- The Node 24 dependency install reported pre-existing package audit findings. No dependency or lockfile was changed.

## Verification

- Both task sorting gates passed for all locale files.
- Python JSON validation passed for each of the nine owned `rom.json` files.
- The seven-key subset exists in all nine owned locales with exact placeholder parity.
- All seven non-English translations differ from the en_US source values, with en_GB using British catalogue terminology.
- No new owned value contains an em dash, placeholder copy, TODO, FIXME, generic source-deletion claim, or source-file deletion instruction.
- `git diff --check` passed across both task commits.
- Node 24 `vue-tsc --noEmit` passed in the task-owned container.
- Prettier passed for all nine locale files.
- Commit hooks checked all five Task 1 files and all four Task 2 files with no issues.
- Both commits contain only the nine locale files declared by the plan and delete no tracked files.
- Task-owned Node containers and the `romm-06-16-node-modules-1786617352` volume were removed by exact identity.

## Known Stubs

None.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- Plan 17 can add the exact seven-key contract to its nine owned locales and make repository-wide parity green.
- No Plan 16 locale needs reopening, and no deployment or service restart was performed.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_

## Self-Check: PASSED

- All nine declared locale files exist in the canonical Linux checkout.
- Task commits `54903fbcc` and `f15d0afac` exist in git history.
- Sorting, JSON, owned-key subset, placeholder, translation, typecheck, formatting, hook, diff, and bounded-parity checks produced the evidence recorded above.
- The summary contains no unverified security surface or known stub claim.
- Plan 17 locale files remain untouched.
