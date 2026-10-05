---
phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
plan: 05
subsystem: v2-domain-migration
tags: [vue, adapters, stores, services, migration]
requires: [24-04]
provides: [adapter-only-v2-production-imports, catalog-navigation-migration]
affects: [24-06, 24-07]
tech-stack:
  added: []
  patterns: [temporary-legacy-adapter-boundary, vertical-catalog-slice]
key-files:
  created:
    - frontend/src/v2/data/adapters/catalog.ts
    - frontend/src/v2/data/adapters/home.ts
    - frontend/src/v2/data/adapters/legacy
  modified:
    - frontend/src/v2/views/Home.vue
    - frontend/src/v2/views/PlatformsIndex.vue
    - frontend/src/v2/views/CollectionsIndex.vue
    - frontend/src/v2/views/Gallery/Platform.vue
    - frontend/src/v2/views/Gallery/Collection.vue
requirements-completed: [QA-02, QA-08]
duration: "45 min"
completed: "2026-10-05"
---

# Phase 24 Plan 05: V2 domain adapter migration summary

Moved v2 production imports for stores, API services, and socket transport behind a centralized temporary adapter boundary, with explicit catalog and home adapters for the first vertical migration slice.

## Verification

- Typecheck: passed in Linux Docker.
- Source mutation inventory: 20 tests passed.
- Data boundary tests: 5 passed.
- Full Vitest: 98 files, 869 tests passed.
- Formatter and pre-commit checks: passed.

## Commits

| Hash      | Description                                                   |
| --------- | ------------------------------------------------------------- |
| 0bb1ec298 | refactor(24-05): route home data through v2 adapter           |
| 8fa60e890 | refactor(24-05): route v2 production imports through adapters |

## Deviations from Plan

[Rule 1 - Migration safety] The broad domain migration is implemented as temporary adapter routing first. Feature behavior and legacy store APIs remain unchanged, while the adapter inventory makes later typed contract replacement incremental and auditable.

[Rule 1 - Boundary enforcement] The import guard allows legacy references only within v2/data/adapters. Production v2 files no longer import stores, API services, or socket transport directly.

## Issues Encountered

The adapters intentionally still expose legacy shapes and are not the final domain repositories. Plan 24-06 and later cleanup must replace these wrappers with typed domain implementations and remove adapters one domain at a time.

## Self-Check: PASSED

- Production v2 imports are routed through the adapter boundary.
- Existing behavior is preserved by the full passing test suite.
- Remaining legacy coupling is centralized and measurable.

## Next Phase Readiness

Ready for Plan 24-06.
