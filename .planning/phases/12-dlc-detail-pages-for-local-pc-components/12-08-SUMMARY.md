---
phase: 12-dlc-detail-pages-for-local-pc-components
plan: 08
subsystem: api
tags: [fastapi, sqlalchemy, pc-components, metadata, provider-media]
requires:
  - phase: 12-07
    provides: Component-owned media persistence with optimistic version guards
provides:
  - Query-bound review-first metadata matching for parent games and classified PC components
  - Explicit DLC-only provider image import into RomM-owned component storage
affects: [pc-metadata, dlc-detail-pages, match-rom-dialog]
tech-stack:
  added: []
  patterns:
    [
      target-aware candidate recomputation,
      candidate-media membership validation,
    ]
key-files:
  created: []
  modified:
    - backend/endpoints/roms/pc_metadata.py
    - backend/handler/metadata/pc_match_handler.py
    - backend/handler/filesystem/resources_handler.py
    - backend/tests/endpoints/roms/test_pc_metadata.py
key-decisions:
  - "Only classified component kinds can be metadata targets; unresolved components return 404."
  - "Provider media identifiers are derived from the reviewed candidate and accepted only for explicit DLC confirmation."
patterns-established:
  - "Recompute candidates using the submitted query before confirmation, then validate selected media membership server-side."
requirements-completed: [D-07, D-08, D-09, D-10]
duration: 12min
completed: 2026-09-03
---

# Phase 12 Plan 08: Target-aware PC matcher API Summary

**Parent and classified PC component targets now share a query-bound review-first matcher, with explicit DLC-only provider image imports into owned storage.**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-09-03T11:35:00Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- Expanded component matching to base, update, DLC, hotfix, language-pack, and extra targets while rejecting unresolved components with a bounded 404.
- Bound candidate queries and confirmations to the submitted target and query, preserving provider availability and non-mutating browse paths.
- Added candidate-media identifiers and DLC-only HTTPS image import with image MIME validation, image decoding, a 10 MiB byte limit, owned-path storage, and cleanup after failed owned-media persistence.

## Task Commits

1. **Task 1: Add target-aware candidate query and server-side revalidation**
   - `008fb4cbc` `test(12-08): specify target-aware PC matcher`
   - `8e415be3d` `feat(12-08): support target-aware PC metadata matching`
2. **Task 2: Import selected provider media only after confirmed component selection**
   - `217a4473a` `test(12-08): specify DLC provider media confirmation`
   - `a1329dd91` `feat(12-08): import confirmed DLC provider media`
   - `5e96d50bc` `test(12-08): type target-aware matcher assertions`

## Verification

- `cd backend && uv run pytest tests/endpoints/roms/test_pc_metadata.py tests/handler/metadata/test_pc_match_handler.py -q` passed, 32 tests.
- `trunk fmt --no-fix` and `trunk check --no-fix` passed for all seven changed backend files.

## Decisions Made

- Candidate media IDs are deterministic hashes of the reviewed candidate and its advertised media descriptor, so the server can reject foreign or stale media references without trusting browser URLs.
- Provider import remains an explicit DLC-only action. Other classified targets can confirm metadata through the same matcher but cannot import provider media.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Eager-loaded component-owned media for ROM list serialization**

- **Found during:** Task 1
- **Issue:** The new `owned_media` response field raised during gallery serialization because its relationship is configured with `lazy="raise"`.
- **Fix:** Added an explicit `selectinload(RomComponent.owned_media)` to the ROM list query.
- **Files modified:** `backend/endpoints/roms/__init__.py`
- **Verification:** Focused endpoint tests pass.
- **Committed in:** `8e415be3d`

**Total deviations:** 1 auto-fixed (1 Rule 2).
**Impact on plan:** Required for the changed component API response to remain serializable. No source-library authority was added.

## Issues Encountered

- The three-dialect migration harness remains unavailable in this checkout because Docker runner `romm-dev` has no gateway. No Team4s or NAS access was attempted. This plan introduced no migration and focused local verification passed.

## Next Phase Readiness

- The shared matcher can now supply provider filters and candidate results to parent and component entry points while retaining target-contained confirmation.
- Frontend consumers should submit `query` and optional `selected_media_ids` from the reviewed candidate response.

## Self-Check: PASSED

- All seven implementation and test files exist.
- All five Plan 12-08 task commits exist in Git history.
