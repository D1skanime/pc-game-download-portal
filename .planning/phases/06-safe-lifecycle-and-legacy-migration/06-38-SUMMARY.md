---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 38
subsystem: frontend-i18n
tags: [vue-i18n, locales, primary-manual, source-safety]
requires:
  - phase: 06-UI-SPEC
    provides: Approved primary-manual ownership, state, failure, and recovery copy contract
  - phase: 06-16
    provides: Bounded first-batch locale execution and verification pattern
provides:
  - Exact canonical 13-key en_US primary-manual copy contract
  - Source-safe native translations for the first eight peer locales
affects: [06-39, frontend-i18n, primary-manual]
tech-stack:
  added: []
  patterns:
    - Primary manuals are described as RomM-owned resources, separate from immutable game-library files
    - Pre-success failures preserve the prior state while post-success refresh failures direct the user to reload
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
  - The canonical source copy matches the approved UI-SPEC exactly and reuses the existing upload-manual and manual-empty keys.
  - The first locale batch owns only nine files; Plan 39 completes the remaining nine locales without reopening this batch.
  - Every locale distinguishes safe API failure from a saved manual whose page refresh failed.
patterns-established:
  - Primary-manual ownership copy always names RomM resources and keeps game-library files unchanged.
  - Locale-batch verification proves exact owned-key parity while the complementary batch remains deliberately absent.
requirements-completed: [CAT-01, CAT-02]
duration: 8m
completed: 2026-08-21
---

# Phase 6 Plan 38: Primary Manual First Locale Batch Summary

**Exact 13-key primary-manual ownership and recovery copy across en_US and eight source-safe peer locales**

## Performance

- **Duration:** 8 minutes
- **Started:** 2026-08-21T12:11:22Z
- **Completed:** 2026-08-21T12:19:13Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Installed the approved en_US copy for replace, pending, success, safe failure, conflict, invalid-selection, refresh-warning, helper, and label states.
- Added native first-batch translations in en_GB, bg_BG, cs_CZ, de_DE, es_ES, fr_FR, hu_HU, and it_IT.
- Preserved every existing and frozen key while keeping all locale JSON valid, deterministically sorted, and free of new placeholders.
- Proved that repository-wide parity is missing only the exact 13 keys in the nine locale files assigned to Plan 39.

## RED/GREEN Evidence

- **Task 1 RED:** The contract probe exited 1 and reported all 65 expected missing entries across en_US, en_GB, bg_BG, cs_CZ, and de_DE.
- **Task 1 GREEN:** The exact-value, key-set, native-language, sorting, JSON, machine-noise, and diff gates passed for all five files.
- **Task 2 RED:** The contract probe exited 1 and reported all 52 expected missing entries across es_ES, fr_FR, hu_HU, and it_IT.
- **Task 2 GREEN:** The exact-value, key-set, native-language, safety-copy, sorting, JSON, and nine-file bounded-parity gates passed.

The project-level TDD mode and MVP mode were both disabled. These JSON-only tasks used the plan-required RED-to-content checks and one atomic feature commit per task; no test-only source artifact was appropriate.

## Task Commits

1. **Task 1: Add the exact en_US and first four peer contracts** - `d9b03867b` (feat)
2. **Task 2: Translate the remaining first-batch locales** - `f0177a7fb` (feat)

## Files Created/Modified

- `frontend/src/locales/en_US/rom.json` - Canonical approved primary-manual copy.
- `frontend/src/locales/en_GB/rom.json` - British English contract parity.
- `frontend/src/locales/bg_BG/rom.json` - Bulgarian ownership and recovery copy.
- `frontend/src/locales/cs_CZ/rom.json` - Czech ownership and recovery copy.
- `frontend/src/locales/de_DE/rom.json` - German ownership and recovery copy.
- `frontend/src/locales/es_ES/rom.json` - Spanish ownership and recovery copy.
- `frontend/src/locales/fr_FR/rom.json` - French ownership and recovery copy.
- `frontend/src/locales/hu_HU/rom.json` - Hungarian ownership and recovery copy.
- `frontend/src/locales/it_IT/rom.json` - Italian ownership and recovery copy.

## Decisions Made

- Used the exact UI-SPEC strings for en_US and natural locale terminology for every peer.
- Described primary manuals as RomM resources without source-folder, source-file, or game-library mutation language.
- Kept the existing-manual failure claim separate from the saved-but-refresh-failed warning.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Tracking Bug] Corrected inconsistent SDK progress and roadmap formatting**

- **Found during:** Plan closeout tracking
- **Issue:** The SDK reported 73 of 82 completed plans and 89 percent, but retained 56 percent in STATE frontmatter, 88 percent in the body, and collapsed ROADMAP table spacing.
- **Fix:** Aligned both STATE progress representations to the SDK count and restored the ROADMAP row formatting.
- **Files modified:** .planning/STATE.md, .planning/ROADMAP.md
- **Verification:** STATE frontmatter and body now show 89 percent, while the phase row shows 38 of 47 summaries.
- **Committed in:** Plan tracking commit

---

**Total deviations:** 1 auto-fixed tracking bug.
**Impact on plan:** Tracking now reflects the committed summary count. Locale scope and product behavior are unchanged.

## Issues Encountered

- The full locale parity command intentionally exits 1 at this bounded intermediate state. Its output lists only ja_JP, ko_KR, pl_PL, pt_BR, ro_RO, ru_RU, tr_TR, zh_CN, and zh_TW, each missing exactly the 13 Plan 38 source keys assigned to Plan 39.
- The disposable dependency install reported eight pre-existing package audit findings. No dependency or lockfile changed.

## Verification

- `python3 frontend/src/locales/check_i18n_sorted.py` passed for the repository.
- `python3 -m json.tool` passed for every owned `rom.json` file.
- Exact-value checks passed for all 117 new locale entries.
- The nine owned locale files contain the identical 13-key subset with zero interpolation placeholders.
- The nine Plan 39 locale files contain none of the new keys, proving bounded ownership without overlap.
- New values contain no TODO, FIXME, placeholder, coming-soon, source-folder, source-file, deletion, or em-dash noise.
- `vue-tsc --noEmit` passed in Node 24 with `NODE_OPTIONS=--max-old-space-size=4096`.
- Prettier passed for all nine owned locale files.
- `git diff --check d9b03867b^..HEAD` passed.
- Commit hooks checked the exact five Task 1 files and four Task 2 files with no issues.
- Task 1 and Task 2 commits contain exactly five and four files respectively, with no tracked deletions.
- Exact containers and the `romm-06-38-node-modules-1787314282` volume were removed and proved absent.
- The tracked worktree is clean and the approved 28-entry untracked baseline is preserved.

## Known Stubs

None.

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- Plan 39 can translate the exact 13-key contract into its nine owned locales and make repository-wide parity green.
- No Plan 38 locale needs reopening, and no deployment, service restart, runtime dependency, or component change was performed.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-21_

## Self-Check: PASSED

- All nine declared locale files exist in the canonical Linux checkout.
- Task commits `d9b03867b` and `f0177a7fb` exist in git history.
- RED, GREEN, exact-copy, native-language, JSON, sorting, placeholder, bounded-parity, typecheck, formatting, hook, diff, and cleanup evidence was reproduced.
- The summary contains no unverified threat surface or known stub claim.
