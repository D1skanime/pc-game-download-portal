---
phase: 26-ui-ux-and-manual-metadata
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, vue, typescript, openapi, metadata, media]

requires: []
provides:
  - Locale-scoped manual descriptions for ROMs, DLCs, and expansions
  - Authorized backend description update and reset endpoints
  - Generated frontend contracts and a shared manual-description resolver
  - Durable provider-media tombstones with explicit restore behavior
affects: [phase-26-plan-02, phase-26-plan-03, metadata-ui, media-management]

tech-stack:
  added: []
  patterns:
    - Reuse existing manual_metadata JSON boundaries for locale-scoped overrides
    - Resolve manual text before provider variants and legacy fallback text
    - Preserve operator_suppressed provider tombstones during ordinary reconciliation

key-files:
  created:
    - backend/alembic/versions/0135_component_manual_metadata.py
    - backend/handler/metadata/manual_description.py
    - backend/tests/handler/metadata/test_manual_description.py
    - frontend/src/v2/composables/useManualDescription/index.ts
    - frontend/src/v2/composables/useManualDescription/index.test.ts
    - frontend/src/__generated__/models/ManualDescriptionRequest.ts
    - frontend/src/__generated__/models/ManualDescriptionResponse.ts
    - .planning/phases/26-ui-ux-and-manual-metadata/deferred-items.md
  modified:
    - backend/models/rom.py
    - backend/handler/database/roms_handler.py
    - backend/endpoints/roms/pc_metadata.py
    - backend/endpoints/roms/media.py
    - backend/handler/metadata/rom_media.py
    - backend/endpoints/responses/rom.py
    - backend/tests/endpoints/roms/test_pc_metadata.py
    - backend/tests/endpoints/roms/test_media.py
    - backend/tests/handler/database/test_rom_media.py
    - frontend/src/v2/views/GameDetails.vue
    - frontend/src/v2/components/GameDetails/PcDlcDetail.vue
    - frontend/src/__generated__/index.ts
    - frontend/src/__generated__/models/ManualMetadata.ts
    - frontend/src/__generated__/models/PcComponentMetadataSchema.ts

key-decisions:
  - "Store manual descriptions inside the existing manual_metadata boundaries instead of adding a parallel description model."
  - "Use exact normalized locale with language fallback for manual text, then provider locale variants, English, and legacy summary."
  - "Treat normal provider reconciliation as non-restoring; only explicit media refresh may reactivate an operator-suppressed tombstone."
  - "Keep provider file cleanup in the existing endpoint and cleanup-intent flow."

requirements-completed: [UI-26-01]

duration: 25min
completed: 2026-10-09
---

# Phase 26 Plan 01: UI UX and Manual Metadata Summary

**Locale-scoped manual descriptions now share the existing ROM and component metadata contract, while provider media deletions remain durable across ordinary refreshes.**

## Performance

- **Duration:** approximately 25 minutes
- **Started:** 2026-10-09T22:29:27Z
- **Completed:** 2026-10-09T22:40:54Z
- **Tasks:** 3 completed
- **Implementation files:** 21

## Accomplishments

- Added validated, optimistic-concurrency-protected description updates for parent ROMs and PC components, including DLC and expansion kinds.
- Added locale isolation, clear/reset fallback, permission, validation, and generated-contract coverage.
- Wired the shared frontend resolver into parent and PC DLC detail views.
- Preserved provider-media tombstones, removed owned files through the existing cleanup path, and added explicit restore behavior.
- Added placement cleanup consistency so returned tombstones reflect the persisted removal.

## Task Commits

Each task was committed atomically:

1. **Task 1: Trace and extend the existing metadata contract** - `58e37ac7b` (feat)
2. **Task 2: Cover lifecycle and authorization behavior** - `b562639e9` (feat)
3. **Task 3: Make provider-media deletion durable** - `28e98ac8a` (fix)
4. **Task 3 follow-up: return provider tombstones without placements** - `4f3a42e56` (fix)

## Verification Evidence

- Backend manual-description and lifecycle tests: **9 passed**
- Backend provider suppression and tombstone tests: **3 passed**
- Backend provider refresh failure-isolation tests: **3 passed**
- Backend focused media endpoint tests: **5 passed**
- Frontend manual-description and PC DLC tests: **13 passed**
- Frontend OpenAPI regeneration completed from the Linux backend
- Frontend typecheck: **passed**

Expected repository warnings remain: Alembic path separator deprecation, an existing SQLAlchemy relationship overlap warning, deprecated HTTP 422 naming, Vue test emitter warnings, and pytest cache permission warnings.

## Files Created and Modified

The 21 implementation and test files are listed in the frontmatter. The generated frontend files were refreshed from the sanitized Linux OpenAPI document. Unrelated generated storage files and all pre-existing dirty edits were left unstaged.

## Decisions Made

The implementation uses the existing parent ROM and component metadata ownership boundaries. It does not add a second resolver, storage mapping, scan path, or media model. Manual descriptions are removed per locale when cleared, allowing provider or legacy fallback to resume.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made component manual metadata optional in generated contracts**

- **Found during:** Task 2 frontend typecheck
- **Issue:** Existing PC component fixtures failed because the new nullable field was emitted as required.
- **Fix:** Added a default of `None` to the backend response schema, regenerated OpenAPI types, and reran typecheck.
- **Files modified:** `backend/endpoints/responses/rom.py`, generated frontend model files
- **Verification:** `npm run typecheck` passed.
- **Committed in:** `b562639e9`

**2. [Rule 1 - Bug] Used the correct owned-file result field during provider deletion**

- **Found during:** Task 3 endpoint cleanup test
- **Issue:** The endpoint accessed `replaced_owned_paths`, but `AppliedOwnedMedia` exposes `owned_paths`.
- **Fix:** Updated the endpoint to iterate over `applied.owned_paths`.
- **Files modified:** `backend/endpoints/roms/media.py`
- **Verification:** Physical cleanup endpoint test passed.
- **Committed in:** `28e98ac8a`

**3. [Rule 1 - Bug] Kept returned tombstone placement state consistent**

- **Found during:** Task 3 media lifecycle tests
- **Issue:** Placement rows were deleted, but the returned ORM collection still contained stale placements.
- **Fix:** Clear the in-memory placement collection after scheduling placement deletion.
- **Files modified:** `backend/handler/database/roms_handler.py`
- **Verification:** Provider deletion placement test passed.
- **Committed in:** `4f3a42e56`

**Total deviations:** 3 auto-fixed.
**Impact on plan:** All fixes were directly required for correctness and verification of the planned contract and media lifecycle.

## Issues Encountered

Broader pre-existing media tests exposed unrelated fixture, timezone, lazy-loading, immutability, and detailed-response timestamp failures. They are recorded in [deferred-items.md](./deferred-items.md); focused plan-scoped tests pass.

The working tree contained substantial pre-existing changes, including related provider-media refresh edits. Those contents were preserved and the directly related media changes were committed with the coherent Task 3 implementation. Unrelated generated and project files remain unstaged.

## Known Stubs

None found in files created or modified by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The shared manual-description contract, generated types, frontend resolver, authorization behavior, and durable provider-media lifecycle are ready for the remaining Phase 26 UI work.

---

_Phase: 26-ui-ux-and-manual-metadata_
_Completed: 2026-10-09_

## Self-Check: PASSED

- Summary file exists.
- Commits 58e37ac7b, b562639e9, 28e98ac8a, and 4f3a42e56 exist in git history.
- Plan requirement UI-26-01 is recorded in this summary; the repository REQUIREMENTS.md registry did not contain this ID, and the SDK requirements.mark-complete query reported not_found.
- No plan-scoped implementation files remain unstaged; the remaining generated index diff is unrelated pre-existing storage output.
