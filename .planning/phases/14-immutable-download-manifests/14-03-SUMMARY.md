---
phase: 14-immutable-download-manifests
plan: 03
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, openapi, download-manifest]
requires:
  - phase: 14-immutable-download-manifests
    provides: Persisted immutable manifest aggregates and member evidence.
provides:
  - Owner-scoped JSON-only manifest creation and retrieval routes.
  - Canonical ROM binding for GET visibility authorization.
  - Generated TypeScript API contracts for immutable manifests.
affects: [15-range-delivery, 16-desktop-client, 17-v2-handoff]
tech-stack:
  added: []
  patterns: [owner-scoped manifest lookup, path-free response allowlists]
key-files:
  created:
    - backend/endpoints/download_manifests.py
    - backend/endpoints/responses/download_manifest.py
    - backend/alembic/versions/0120_download_manifest_rom.py
    - backend/tests/endpoints/test_download_manifests.py
  modified:
    - backend/main.py
    - backend/models/download_manifest.py
    - backend/handler/database/download_manifests_handler.py
    - frontend/src/__generated__/index.ts
key-decisions:
  - "GET authorizes visibility against the aggregate's persisted canonical ROM, never selected component rows."
  - "Manifest validation failures for the manifest create route are bounded so rejected client path text is not echoed."
  - "Member delivery URLs remain relative opaque future identifiers, with no delivery handler in Phase 14."
patterns-established:
  - "Manifest endpoints map missing, foreign, and hidden resources to one generic path-free 404."
  - "Public manifest serialization copies only immutable aggregate evidence into explicit response schemas."
requirements-completed: [DLMT-01, DLMT-02, DLMT-03]
duration: 11min
completed: 2026-09-15
---

# Phase 14 Plan 03: Immutable Manifest JSON API Summary

**Protected whole-game and selected-component immutable manifest JSON APIs with canonical-ROM visibility masking and generated client contracts.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-09-15T21:27:00Z
- **Completed:** 2026-09-15T21:38:31Z
- **Tasks:** 2 completed
- **Files modified:** 12

## Accomplishments

- Added scoped POST and GET manifest APIs that return only path-free, immutable JSON fields.
- Persisted each manifest's canonical ROM and enforce owner plus current ROM visibility before GET serialization.
- Added endpoint regression coverage for selection, masking, lifecycle states, 5 GiB values, and source-path disclosure.
- Regenerated the additive OpenAPI TypeScript contract from a local isolated loopback backend.

## Task Commits

1. **Task 1: Define strict path-free manifest JSON schemas and protected routes** - `f38c9c6c4`, `a98cd6cec`, `d008d53ee`, `956e50e68` (test, feat, fix)
2. **Task 2: Regenerate the additive frontend API contract and run phase-level checks** - `0f30e6b2b` (chore)

## Files Created/Modified

- `backend/endpoints/download_manifests.py` - Protected JSON-only create and retrieve routes.
- `backend/endpoints/responses/download_manifest.py` - Strict request and path-free response schemas.
- `backend/alembic/versions/0120_download_manifest_rom.py` - Canonical manifest-to-ROM binding.
- `backend/tests/endpoints/test_download_manifests.py` - API authorization, state, and disclosure regressions.
- `frontend/src/__generated__/models/DownloadManifestResponse.ts` - Generated manifest response surface.

## Decisions Made

- GET loads an owner-scoped aggregate and checks its stored `manifest.rom` before lifecycle evaluation or serialization.
- Expired and revoked manifests use bounded 410 codes, while source-changed uses a bounded 409 code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Persisted canonical ROM ownership on manifests.**

- **Found during:** Task 1
- **Issue:** The Phase 14 aggregate had no `rom_id`, so GET could only infer visibility from selected components, violating the canonical-ROM contract.
- **Fix:** Added the non-null foreign key, portable migration, eager aggregate relation, and persistence tests.
- **Files modified:** `backend/models/download_manifest.py`, `backend/handler/database/download_manifests_handler.py`, `backend/alembic/versions/0120_download_manifest_rom.py`, `backend/tests/models/test_download_manifest.py`
- **Verification:** Manifest model, handler, and endpoint suites passed; upgrade/downgrade/upgrade completed on the isolated test database.
- **Committed in:** `a98cd6cec`, `d008d53ee`

**2. [Rule 2 - Information Disclosure] Bounded create-route validation output.**

- **Found during:** Task 1
- **Issue:** FastAPI's default extra-field validation echoed a submitted source-like path.
- **Fix:** Returned a generic validation response only for the manifest create route.
- **Files modified:** `backend/main.py`, `backend/endpoints/download_manifests.py`, `backend/tests/endpoints/test_download_manifests.py`
- **Verification:** Endpoint disclosure regression and scoped Trunk check passed.
- **Committed in:** `a98cd6cec`, `956e50e68`

**Total deviations:** 2 auto-fixed Rule 2 issues.

## Verification

- `uv run pytest tests/models/test_download_manifest.py tests/handler/database/test_download_manifests_handler.py tests/endpoints/test_download_manifests.py -vv` - 16 passed.
- Isolated test database migration cycle, upgrade, downgrade, upgrade - passed.
- `trunk check` on all Plan 14-03 backend files - passed.
- `npm run typecheck` - passed.
- Local loopback OpenAPI generation at `127.0.0.1:3344` followed by `npm run generate` - passed.
- Delivery implementation scan for `StreamingResponse`, `FileResponse`, `Range`, `If-Match`, `zip`, and `open(` in the new router - passed with no matches.

## Issues Encountered

- The plan's broader filesystem test file has two pre-existing fixture failures outside these changes: an unwritable `backend/romm_test/library/n64/roms/dlc` fixture path and a shared PC integration fixture whose `extra` member count is 5 rather than the test's expected 4. These were not modified.

## Known Stubs

None.

## Next Phase Readiness

- Phase 15 can add manifest-scoped delivery using the relative member identifiers, while rechecking authorization and snapshot state per request.
- No file content route, streaming response, range handling, archive behavior, source mutation, desktop code, or v2 handoff was added.

## Self-Check: PASSED

- All created route, schema, migration, test, and generated contract files exist.
- Task commits `f38c9c6c4`, `a98cd6cec`, `d008d53ee`, `956e50e68`, and `0f30e6b2b` exist in Git history.
