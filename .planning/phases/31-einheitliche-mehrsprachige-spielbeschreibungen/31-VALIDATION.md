# Phase 31 Validation

## Implementation

- ScreenScraper synopsis variants are normalized and persisted in ss_metadata.text_variants.
- The existing preferred-language summary remains selected for rom.summary compatibility.
- Manual English descriptions now precede provider and legacy fallbacks.
- Steam and ScreenScraper variants are resolved through one frontend provider resolver.
- The detail view and localized editor receive ScreenScraper variants.
- OpenAPI TypeScript types were regenerated for RomSSMetadata.text_variants.
- No migration was added because the existing JSON provider fields are sufficient.

## Automated checks

- Frontend typecheck: passed.
- Frontend focused Vitest suite: passed, 39 tests.
- Frontend production build: passed.
- Python bytecode compilation for changed backend files: passed.
- git diff --check: passed.
- Dev stack probe: passed, curl -I http://127.0.0.1:3100/ returned HTTP 200.
- Backend focused pytest suite: blocked before collection by the test database fixture. The test container resolves the configured test database to 127.0.0.1:3306, where no MariaDB listener is reachable. This is an environment gate block, not a test assertion failure.
- V2 maintainability gate: blocked by existing direct legacy imports in components/Settings/StorageRootsSection.vue and composables/useManualDescription/index.ts.

## Review status

The implementation is committed on the feature branch only. Phase completion and merge to main remain pending backend test database availability, UAT, and review.
