---
phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
plan: 06
subsystem: v2-maintainability
tags: [vue, composables, maintainability, guardrails, testing]
requires: [24-04, 24-05]
provides: [v2-maintainability-gate, game-details-media-boundary]
affects: [24-07]
tech-stack:
  added: []
  patterns: [baseline-with-no-regression, pure-media-orchestration-composable]
key-files:
  created:
    - frontend/scripts/check-v2-maintainability.ts
    - frontend/src/v2/composables/useGameDetailsMedia.ts
  modified:
    - frontend/package.json
    - frontend/src/v2/views/GameDetails.vue
    - frontend/src/v2/views/GameDetails.test.ts
requirements-completed: [QA-05, QA-06, QA-07]
duration: "35 min"
completed: "2026-10-05"
---

# Phase 24 Plan 06: V2 maintainability guardrails and details boundary summary

Added a repeatable v2 maintainability gate and extracted GameDetails background/audio orchestration into a focused composable. The extraction preserves the existing public behavior and keeps the view responsible for route and composition concerns.

## Verification

- npm run v2:maintainability: passed; 457 production files scanned.
- Typecheck: passed in Linux Docker.
- Focused GameDetails tests: 10 passed.
- Full Vitest: 98 files, 869 tests passed.
- Production build: passed.
- Formatter/pre-commit checks: passed.

## Commits

| Hash      | Description                                               |
| --------- | --------------------------------------------------------- |
| 0070311c9 | refactor(24-06): extract game details media orchestration |

## Deviations from Plan

[Rule 1 - Existing decomposition] RSelect, GalleryShell, and GameCard already contain focused child components and composables, but their aggregate Vue files remain large. A behavior-preserving full template split would require a separate UI-focused change with browser interaction coverage. They are therefore recorded as explicit size baselines rather than changed speculatively.

[Rule 1 - Baseline enforcement] Existing exceptions are explicit in the gate: RSelect 1800, GalleryShell 1350, GameCard 1100, GameDetails 800, Scan 1500, RTextField 1050, EmulatorJS 1100, and Stream 1000 lines. New v2 production files default to a 900-line limit, and direct legacy imports outside v2/data/adapters fail the gate.

## Issues Encountered

Full tests continue to emit pre-existing harness warnings for Cache API fallback, missing injected emitter, and incomplete i18n fixtures in the gallery provenance tests. They do not fail the suite. The build continues to report existing third-party eval/chunk-size and CSS pseudo-selector warnings.

## Self-Check: PASSED

- GameDetails media logic has an explicit testable boundary.
- No direct legacy store/service imports were introduced.
- Existing interaction and build behavior is preserved by the full verification suite.
- Future v2 monoliths and boundary bypasses now fail the maintainability command.

## Next Phase Readiness

Ready for Plan 24-07 browser/UAT checkpoint. The remaining size-baselined hotspots should be decomposed in a dedicated UI refactor when browser coverage is available.
