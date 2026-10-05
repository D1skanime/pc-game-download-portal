---
phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
plan: 01
subsystem: frontend-routing-and-settings
tags: [vue, vitest, vue-router, regression]
requires: [Phase 23]
provides:
  [safe-rom-route-guards, pc-automation-title-fallback, router-warning-coverage]
affects: [24-02, 24-03]
tech-stack:
  added: []
  patterns: [fail-closed-route-guards, normalized-accessible-target-labels]
key-files:
  created:
    - frontend/src/plugins/router.test.ts
  modified:
    - frontend/src/plugins/router.ts
    - frontend/src/v2/components/Settings/PcAutomationQueue.vue
    - frontend/src/v2/components/Gallery/FirmwareTab.test.ts
key-decisions:
  - "Queue labels prefer target_title, then candidate_title, then the localized placeholder."
  - "Invalid ROM and DLC route ids redirect to the not-found route before entity loading."
  - "The settings layout child is named locally without adding it to the public route inventory."
requirements-completed: [QA-01, QA-03]
duration: "35 min"
completed: "2026-10-05"
---

# Phase 24 Plan 01: V2 baseline warning and route hardening summary

Normalized PC automation target labels, made ROM and DLC route guards fail closed, removed the unnamed settings layout warning, and added regression coverage.

## Tasks Completed

| Task                           | Result | Verification                                 |
| ------------------------------ | ------ | -------------------------------------------- |
| PC automation title fallback   | Passed | Focused queue test: 7 passed                 |
| Firmware label typing          | Passed | Focused FirmwareTab test: 3 passed           |
| Route bootstrap and id safety  | Passed | Router: 14 passed; route inventory: 6 passed |
| Full frontend regression suite | Passed | 96 files, 863 tests passed                   |
| Typecheck                      | Passed | npm run typecheck in Linux Docker            |

## Commits

| Hash      | Description                            |
| --------- | -------------------------------------- |
| d7400bc22 | fix(24-01): harden v2 queue and routes |

## Deviations from Plan

[Rule 1 - Bug] The queue fixture exposed candidate_title without target_title. The implementation now prefers target_title but falls back to candidate_title before the localized placeholder.

[Rule 1 - Test harness] The FirmwareTab warning came from its test i18n mock returning the interpolation object. The mock now returns a string-safe value; production RCheckbox typing remains strict.

## Issues Encountered

The full suite remains noisy from pre-existing cache, unresolved test-component, and locale warnings. The storage.administration locale warning is intentionally deferred to Plan 24-02. No test failures remain.

## Self-Check: PASSED

- Target files exist.
- Commit d7400bc22 contains the implementation.
- Focused and full test commands passed.
- Requirements QA-01 and QA-03 are addressed for this plan.

## Next Phase Readiness

Ready for Plan 24-02.
