---
phase: 29-rollenbewusste-metadaten-klickbare-themes-und-mehrsprachige-
plan: 02
subsystem: frontend
tags: [vue, metadata, facets, router, i18n]
key-files:
  - frontend/src/v2/components/GameDetails/InfoGrid.vue
  - frontend/src/v2/components/GameDetails/OverviewTab.vue
  - frontend/src/v2/views/GameDetails.vue
  - frontend/src/v2/composables/useGalleryFilterUrl/index.ts
metrics:
  tests: 126
  test_files: 28
  typecheck: passed
---

# Plan 29-02 Summary

## Objective

Wire stable provider-qualified metadata facets and explicit company roles into the v2 details and gallery navigation while keeping PC release presentation singular.

## Implementation

- Facet links carry provider-qualified IDs and preserve the current PC platform scope through URL, Pinia, and gallery request state.
- Overview role sections consume explicit role records; labels are localized while IDs remain canonical.
- The PC release field remains owned by Overview; duplicate developer, publisher, and theme presentation was removed from the overview fact block in favor of the role/facet grid.
- Metadata source and provenance details remain available in the metadata view.

## Commits

| Commit    | Description                                            |
| --------- | ------------------------------------------------------ |
| e97b187a7 | feat(29-02): wire stable metadata facet filters        |
| 1183bacbf | feat(29-02): make overview metadata role-aware         |
| b1622786e | fix(29-02): keep overview metadata backward compatible |

## Deviations

- The backend OpenAPI listener at `127.0.0.1:3344` was unavailable during execution, so generated frontend model changes were checked against the committed backend contract and kept additive/backward-compatible. No new package was introduced.

## Verification

- `docker exec romm-dev sh -lc 'cd /app/frontend && npm run test -- InfoGrid OverviewTab GameDetails'` — passed, 28 files / 126 tests.
- `docker exec romm-dev sh -lc 'cd /app/frontend && npm run typecheck'` — passed.
- `git diff --check` — passed.

## Self-check

PASSED — role-aware metadata, canonical facet navigation, PC scoping, and single release ownership are implemented and verified.
