---
phase: 29-rollenbewusste-metadaten-klickbare-themes-und-mehrsprachige-
plan: 03
subsystem: frontend-i18n
tags: [vue, i18n, locale, metadata, overview]
requires:
  - phase: 29-02
    provides: Stable metadata facet IDs, PC-scoped chip navigation, and single-owner Overview release field
provides:
  - Primary-locale regression coverage for locale-aware release dates, stable facet IDs, PC scope, and truthful role rendering
  - German and French translations for provider and metadata fallback labels in the active rom locale namespace
affects: [phase-29-04]
tech-stack:
  added: []
  patterns:
    - Keep provider-qualified identities in test fixtures while locale labels remain presentation-only
    - Use the active browser locale for the Overview release date and assert one canonical release row
key-files:
  created: []
  modified:
    - frontend/src/locales/de_DE/rom.json
    - frontend/src/locales/fr_FR/rom.json
    - frontend/src/v2/components/GameDetails/OverviewTab.test.ts
    - frontend/src/v2/views/GameDetails.test.ts
metrics:
  tests: 130
  test_files: 28
  typecheck: passed
completed: 2026-10-13
---

# Phase 29 Plan 03: Primary locale overview coverage

## Objective

Establish the source and primary locale regression coverage for the Phase 29 Overview metadata behavior without changing provider identities or starting the remaining locale batch.

## Implementation

- Confirmed the active locale namespace is \`rom.json\`; the plan's referenced \`detail.json\` files do not exist in this checkout and are not loaded by \`frontend/src/locales/index.ts\`.
- Preserved the existing en_US source and en_GB fallback labels because the affected English application labels were already complete.
- Translated German and French provider/fallback labels, including manual metadata, provider metadata, existing-summary fallback, provider preview, crawled release date, and crawled genres.
- Added Overview tests for:
  - en-US, de-DE, and fr-FR release-date formatting;
  - exactly one PC release row;
  - canonical \`igdb:\` facet identities with preserved PC platform query;
  - roleless provider companies remaining neutral instead of gaining guessed developer or publisher labels.
- Added primary locale assertions that application labels exist, English fallback parity is retained, and provider identity labels remain raw provider names.

## Task Commits

| Commit    | Description                                     |
| --------- | ----------------------------------------------- |
| 540f6b289 | feat(29-03): localize primary metadata overview |

## Deviations from Plan

### [Rule 3 - Blocking] Adapted the planned locale path to the canonical frontend namespace

- **Found during:** Task 1
- **Issue:** \`frontend/src/locales/*/detail.json\` is not present; the active loader and existing Phase 29 UI use \`rom.json\`.
- **Fix:** Applied the primary-locale changes to the existing \`rom.json\` namespace and added tests against that loaded namespace.
- **Verification:** All four affected JSON files parse successfully; focused Vitest and typecheck pass.
- **Impact:** No new unused locale namespace was introduced.

### [Rule 3 - Baseline] Repository locale gates remain blocked by pre-existing debt

- **Found during:** Task 1 verification
- **Issue:** \`check_i18n_locales.py\` still reports the baseline missing keys \`refreshing-media\`, \`account-exists\`, \`media-only\`, \`media-only-desc\`, and \`media-only-existing-platforms\` in the existing non-English locale set. \`check_i18n_sorted.py\` still reports the pre-existing unsorted locale files.
- **Fix:** Did not expand Wave 3 into the remaining-locale batch or unrelated baseline cleanup; no new parity keys were added.
- **Verification:** The post-change failure set matches the recorded baseline, and no new missing key is reported.
- **Impact:** Wave 4 remains responsible for the remaining locale coverage and final baseline-aware gates.

**Total deviations:** 2 documented adaptations. **Impact:** Primary-locale behavior is complete; remaining repository-wide locale debt is unchanged and explicitly deferred to Wave 4.

## Verification Evidence

- \`docker exec romm-dev sh -lc 'cd /app/frontend && npm run test -- OverviewTab GameDetails'\` - passed, 28 test files / 130 tests.
- \`docker exec romm-dev sh -lc 'cd /app/frontend && npm run typecheck'\` - passed.
- \`python3 -m json.tool\` for en_US, en_GB, de_DE, and fr_FR \`rom.json\` - passed.
- \`git diff --check\` - passed.
- \`python3 frontend/src/locales/check_i18n_locales.py\` - failed only on the documented baseline missing keys.
- \`python3 frontend/src/locales/check_i18n_sorted.py\` - failed only on the documented baseline unsorted files.
- No v1 files were modified.

## Self-Check: PASSED

- Plan 29-03 production commit \`540f6b289\` exists.
- Primary locale and regression files are committed.
- Focused tests, typecheck, JSON parsing, and diff checks pass.
- Wave 4 and the phase verifier were not started.
