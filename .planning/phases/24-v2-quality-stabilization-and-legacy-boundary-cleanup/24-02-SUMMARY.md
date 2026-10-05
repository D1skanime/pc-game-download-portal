---
phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
plan: 02
subsystem: frontend-locales-and-forms
tags: [vue, vitest, storybook, accessibility, i18n]
requires: [24-01]
provides: [locale-key-parity, rselect-nested-interactive-fix]
affects: [24-04, 24-06, 24-07]
tech-stack:
  added: []
  patterns:
    [
      locale-namespace-parity-test,
      noninteractive-select-field-with-keyboard-handler,
    ]
key-files:
  created:
    - frontend/src/locales/localeParity.test.ts
  modified:
    - frontend/src/v2/lib/forms/RSelect/RSelect.vue
    - frontend/src/v2/lib/forms/RSelect/RSelect.stories.ts
requirements-completed: [QA-01, QA-04]
duration: "25 min"
completed: "2026-10-05"
---

# Phase 24 Plan 02: Locale and RSelect accessibility summary

Added the missing storage namespace to all 18 supported locales, enforced namespace parity, and removed the RSelect nested-interactive Axe violation while retaining keyboard activation and clear behavior.

## Verification

- Locale parity: 1 test passed.
- RSelect focused tests: 1 test passed.
- Storybook suite: 364 tests passed.
- Typecheck: passed in Linux Docker.
- Formatter and pre-commit checks: passed.

## Commits

| Hash      | Description                                            |
| --------- | ------------------------------------------------------ |
| 85da965a3 | fix(24-02): close locale and select accessibility gaps |

## Deviations from Plan

[Rule 1 - Accessibility] The smallest behavior-preserving fix was to make the styled select field a keyboard-focusable noninteractive group, keeping the clear button as a separate interactive descendant and preserving the existing keyboard handler.

[Rule 1 - Localization] Only the German storage label is translated locally; other locales receive the English fallback text until native translations are available. Parity is enforced now so missing namespaces cannot recur.

## Issues Encountered

No test failures. The broader suite may still contain unrelated test-harness warnings, but the RSelect Storybook Axe violation and storage.administration warning are resolved.

## Self-Check: PASSED

- All 18 locale storage files and parity test exist.
- Commit 85da965a3 contains the plan changes.
- Locale, RSelect, Storybook, and typecheck verification passed.

## Next Phase Readiness

Ready for Plan 24-03.
