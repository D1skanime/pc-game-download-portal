---
phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
plan: 03
subsystem: frontend-bootstrap-and-routing
tags: [vue-router, bootstrap, v2, legacy-cleanup]
requires: [24-01]
provides: [fail-closed-entity-routes, direct-v2-bootstrap-regression]
affects: [24-04, 24-05]
tech-stack:
  added: []
  patterns: [safe-route-id-guards, stale-state-prevention]
key-files:
  modified:
    - frontend/src/plugins/router.ts
    - frontend/src/main.ts
    - frontend/src/v2/router/v2Boot.test.ts
requirements-completed: [QA-03, QA-08]
duration: "15 min"
completed: "2026-10-05"
---

# Phase 24 Plan 03: Bootstrap and route safety summary

Hardened entity route guards, redirected failed ROM and DLC loads to the v2 not-found route, and locked direct-v2 bootstrap against the removed UI-version switch.

## Verification

- Router tests: 14 passed.
- Route inventory tests: 6 passed.
- V2 boot tests: 3 passed.
- Typecheck: passed in Linux Docker.
- Static reference audit: no active useUiVersion, NotReady, Passthrough, or v1 view references.

## Commits

| Hash      | Description                                             |
| --------- | ------------------------------------------------------- |
| 90ccd38dc | fix(24-03): remove dead v2 state and fail closed routes |

## Deviations from Plan

[Rule 1 - Routing] The existing ROM guard already used parseSafeRouteId after Plan 24-01. This plan extended the same fail-closed behavior to API failures in ROM and DLC guards instead of allowing a stale detail view to continue.

## Issues Encountered

Legacy console route aliases and v1 console cadence comments remain intentionally because they preserve redirects and input behavior. They are not frozen v1 view trees.

## Self-Check: PASSED

- Route and boot regression tests passed.
- Typecheck passed.
- Direct-v2 bootstrap remains intact.
- No dead UI-version state switch remains.

## Next Phase Readiness

Ready for Plan 24-04.
