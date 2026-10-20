---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 07
subsystem: setup-locales
tags: [frontend, i18n, setup, pgdp]
requires: [33-04]
provides: [batch-a-setup-translations, complete-setup-locale-parity]
affects: [phase-33-09, first-run-setup]
tech-stack:
  added: []
  patterns: [locale-source-parity, translated-json-copy]
key-files:
  created: []
  modified:
    - frontend/src/locales/en_US/setup.json
    - frontend/src/locales/en_GB/setup.json
    - frontend/src/locales/bg_BG/setup.json
    - frontend/src/locales/cs_CZ/setup.json
    - frontend/src/locales/de_DE/setup.json
    - frontend/src/locales/es_ES/setup.json
    - frontend/src/locales/fr_FR/setup.json
    - frontend/src/locales/hu_HU/setup.json
    - frontend/src/locales/it_IT/setup.json
    - frontend/src/locales/ja_JP/setup.json
    - frontend/src/locales/ko_KR/setup.json
    - frontend/src/locales/pl_PL/setup.json
    - frontend/src/locales/pt_BR/setup.json
    - frontend/src/locales/ro_RO/setup.json
    - frontend/src/locales/ru_RU/setup.json
    - frontend/src/locales/tr_TR/setup.json
    - frontend/src/locales/zh_CN/setup.json
    - frontend/src/locales/zh_TW/setup.json
decisions:
  - Keep identical setup assignment structure across all 18 locales.
  - Keep assignment copy in locale JSON only, with no duplicate locale logic.
  - Remove RomM branding and legacy roms path wording from setup values.
metrics:
  duration: 19m
  completed: 2026-10-16
---

# Phase 33 Plan 07: PGDP setup locale coverage

The inline first-run setup now has translated direct Games-folder assignment copy, PGDP platform labels, retry/error states, and ready-continuation copy across every locale.

## Tasks

| Task | Result | Commit |
| --- | --- | --- |
| 1. Roll out inline assignment copy to batch A | PASS | 11c49e0b7 |
| 2. Validate locale batch A against the setup surface | PASS for focused setup tests and setup structure; full locale parity has one pre-existing unrelated failure | 25a7ac2be |

## Verification

- Locale sorted-key validator: PASS, all locale files sorted.
- Focused setup tests: PASS, 2 files and 4 tests.
- All 18 setup files contain the 12 assignment keys with matching structure and placeholders: PASS.
- Forbidden setup terminology scan across all setup files: PASS, no RomM or roms/{platform} matches.
- Changed locale files are 113 lines each, below the 500-line limit.
- git diff --check: PASS.
- Pre-commit checks: PASS for both commits.

The repository-wide locale parity validator reports only the pre-existing storage.json extra key preview-pending in en_GB, de_DE, and fr_FR. No setup.json parity failures remain. Those unrelated storage files were not modified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking tooling] Used available JSON tooling when Linux lacked apply_patch**
- Found during: Task 1 implementation.
- Issue: The verified Linux host has no apply_patch executable.
- Fix: Applied scoped JSON transformations through the available Python runtime, limited to locale data files.
- Verification: Diff check, pre-commit validation, locale sorting, and focused tests passed.
- Commit: 11c49e0b7

**2. [Rule 2 - Missing critical parity] Added assignment keys to the dependent nine locales**
- Found during: Task 1 locale parity verification.
- Issue: The repository validator checks all 18 locales, while the plan file list covers only batch A.
- Fix: Added identical assignment structure and translated values to ja_JP, ko_KR, pl_PL, pt_BR, ro_RO, ru_RU, tr_TR, zh_CN, and zh_TW.
- Verification: All 18 setup files have matching key structure and focused setup tests pass.
- Commit: 25a7ac2be

Total deviations: 2 auto-fixed. Impact: setup locale coverage is complete for all locales. Three unrelated storage locale extras remain deferred.

## Deferred Issues

- en_GB/storage.json, de_DE/storage.json, and fr_FR/storage.json contain the pre-existing extra key preview-pending. This is outside Plan 33-07 scope and was not changed.

## Known Stubs

None.

## Authentication Gates

None.

## Threat Flags

None. Locale copy adds no endpoints, auth paths, filesystem access, or schema changes. Host paths, credentials, and raw storage errors remain absent from assignment strings.

## Self-Check: PASSED

- Summary file exists after creation.
- Both production commits are present in Git history.
- All 18 setup locale files contain required assignment keys.
- Unrelated dirty compose files and backend/pgdp_test/ remain untouched.

