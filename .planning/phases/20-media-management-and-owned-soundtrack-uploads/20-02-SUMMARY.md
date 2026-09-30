---
phase: 20-media-management-and-owned-soundtrack-uploads
plan: "02"
subsystem: api
tags: [fastapi, owned-media, resources-storage, cleanup, openapi]
requires:
  - phase: 20-09
    provides: role-aware parent owned-media catalog
provides:
  - protected parent-ROM owned-media API
  - server-named owned media storage and durable cleanup worker
  - generated owned-media TypeScript schemas
affects: [20-03, 20-04, 20-05]
tech-stack:
  added: []
  patterns: [owned-resources-only media access, explicit provider refresh]
key-files:
  created:
    - backend/endpoints/roms/media.py
    - backend/handler/metadata/rom_media.py
    - backend/tasks/scheduled/owned_media_cleanup.py
  modified:
    - backend/handler/filesystem/resources_handler.py
    - backend/startup.py
    - frontend/src/__generated__/models/DetailedRomSchema.ts
key-decisions:
  - "Provider identities use normalized HTTPS URLs with a SHA-256 fallback when no native ID is available."
  - "Cleanup retries use the owned RESOURCES delete descriptor only."
requirements-completed:
  [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07]
duration: 18min
completed: 2026-09-28
---

# Phase 20 Plan 02: Owned Media API Summary

**Protected parent-ROM media catalog routes, server-generated owned-resource storage, and durable cleanup retry handling.**

## Accomplishments

- Added explicit HTTPS provider discovery with stable digest identities and no scan invocation.
- Added server-generated image/audio writes plus a scheduled retry worker restricted to owned resources.
- Added catalog, content, refresh, upload, placement, reorder, and delete API routes, with generated frontend media schemas.

## Task Commits

1. **Task 1: Add explicit provider discovery plus bounded owned-file primitives** - `adc55334c` (feat)
2. **Task 2: Publish protected parent-ROM media routes and regenerate the API client** - `41b371aa7` (feat)
3. **Generated API types** - `7f61be7a5` (feat)

## Decisions Made

- Provider refresh is the only API path that resolves provider media URLs.
- Filesystem deletes use a durable intent after an immediate owned-resource deletion failure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added due-intent selection to the database handler.**

- **Found during:** Task 1
- **Issue:** Plan 20-01 exposed individual cleanup claiming but no safe way for a worker to enumerate due intents.
- **Fix:** Added a bounded pending-intent query before the existing locked claim operation.
- **Files modified:** `backend/handler/database/roms_handler.py`
- **Committed in:** `adc55334c`

**Total deviations:** 1 auto-fixed.

## Issues Encountered

- Focused pytest collection is blocked by the unavailable MariaDB verifier at `127.0.0.1:3306`.
- `npm run generate` and `npm run typecheck` completed successfully. Unrelated generated API changes were left unstaged in the shared working tree.

## TDD Gate Compliance

The discovery tests were written and run red before implementation. The red test was not committed as a separate `test(...)` commit, so this plan does not meet the repository's separate RED-commit convention.

## Known Stubs

None.

## Self-Check: PASSED

- Implementation files and commits `adc55334c`, `41b371aa7`, and `7f61be7a5` exist.
