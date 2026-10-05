---
quick: 261005-gqn
subsystem: ui
tags: [vue, vitest, steam, igdb, localization]
requires:
  - phase: 23
    provides: Steam text variant resolver for PC game details
provides:
  - DLC details retain localized Steam summaries after IGDB metadata selection
  - Manual DLC summaries retain display precedence
affects: [pc-dlc-details, steam-localization]
tech-stack:
  added: []
  patterns:
    - Steam variants are authoritative for non-manual DLC metadata sources
key-files:
  created: []
  modified:
    - frontend/src/v2/components/GameDetails/PcDlcDetail.vue
    - frontend/src/v2/components/GameDetails/PcDlcDetail.test.ts
key-decisions:
  - "Use retained Steam text for every non-manual DLC source, including IGDB."
  - "Keep manual summaries ahead of Steam variants."
duration: 3min
completed: 2026-10-05
status: complete
---

# Quick Task 261005-gqn: Retain Steam DLC Text After IGDB Selection

**DLC detail views now display the selected localized Steam summary after an IGDB metadata selection, while manual summaries remain authoritative.**

## Accomplishments

- Added a controllable locale fixture and regression coverage for retained German and English Steam variants after IGDB selection.
- Added coverage that manually authored DLC text remains visible when Steam variants exist.
- Made the existing Steam resolver authoritative for every non-manual DLC metadata source, preserving its malformed and missing-variant fallbacks.

## Task Commits

1. **Regression coverage** - `94b880e66` (`test`)
2. **DLC summary source selection** - `57e4376e1` (`fix`)

## Verification

- `cd frontend && npm run test -- PcDlcDetail steamTextVariants` passed, 48 tests across 3 files.
- `cd frontend && npm run typecheck` passed.

## Decisions Made

- Retained Steam text variants are authoritative unless `metadata_source` is `manual`.
- No scan, enrichment, backend persistence, parent-game display, UAT fixture, mapping, or database behavior was changed.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- Both modified source and test files exist.
- Both task commits are present in Git history.
