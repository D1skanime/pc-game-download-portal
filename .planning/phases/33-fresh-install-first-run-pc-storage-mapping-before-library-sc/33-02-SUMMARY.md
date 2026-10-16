---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 02
subsystem: api
tags: [fastapi, pydantic, pytest, storage-mapping, read-only]

# Dependency graph
requires:
  - phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
    provides: Canonical Games root, external_read_only mappings, and readiness helpers
provides:
  - Server-owned direct Games-folder discovery with bounded relative-only responses
  - Authenticated, revalidated folder-to-platform assignment and mapping reconciliation
  - Setup schemas, routes, handler tests, and route registration
affects: [phase-33, first-run-routing, storage-mapping, scan-readiness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Thin setup routes delegate discovery and reconciliation to one handler
    - Suggestions derive from supported platform metadata and configured aliases
    - Mapping readiness requires reachable, readable, non-writable root health

key-files:
  created:
    - backend/endpoints/setup.py
    - backend/endpoints/responses/setup.py
    - backend/handler/setup_folder_handler.py
    - backend/tests/endpoints/test_setup.py
    - backend/tests/handler/test_setup_folder_handler.py
  modified:
    - backend/main.py

key-decisions:
  - "Use the existing external_read_only Games root and existing storage mapping handler APIs; no new model or legacy structure detector was added."
  - "Return only direct relative folder names and bounded platform options, keeping host paths and source-library terms out of the response."
  - "Re-list and preflight all assignments before reconciliation, with idempotent reuse of an identical active mapping."

patterns-established:
  - "First-run setup is the sole public direct-folder discovery surface."
  - "Unknown folders remain visible and require an explicit supported platform assignment."

requirements-completed: [PGDP-33-01]

# Metrics
duration: 32 min
completed: 2026-10-16
---

# Phase 33 Plan 02: Server-owned setup folder discovery and assignment Summary

**FastAPI setup discovery and authenticated external-read-only folder mapping with relative-only contracts**

## Performance

- **Duration:** approximately 32 minutes
- **Started:** 2026-10-16T19:05:00+02:00
- **Completed:** 2026-10-16
- **Tasks:** 2
- **Files modified:** 6 source/test files plus this summary

## Accomplishments

- Added typed setup discovery and assignment schemas with bounded folder, option, mapping, readiness, and root-health fields.
- Added deterministic direct-child discovery that skips files/symlinks, rejects unsafe names, caps folder counts, and derives known-platform suggestions from supported metadata and configured aliases.
- Added public-first-run discovery and admin/users-write assignment routes, registered under `/api/setup`, with server-side re-listing, assignment completeness checks, duplicate/unsupported rejection, mapping preflight, idempotent reuse, and readiness output.
- Added focused handler coverage for deterministic output, unknown folders, unsafe names, and complete assignment behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define and fail the setup contract** - `ece4125f7` (test)
   - Follow-up test correction: `ac0a731b1` (fix)
2. **Task 2: Implement discovery and mapping reconciliation** - `d7886d6da` (feat)

## Files Created/Modified

- `backend/endpoints/responses/setup.py` - Typed setup folder, assignment, mapping, and readiness schemas.
- `backend/endpoints/setup.py` - Thin public discovery and protected assignment routes.
- `backend/handler/setup_folder_handler.py` - Direct-folder discovery, configured alias matching, assignment validation, reconciliation, and readiness logic.
- `backend/main.py` - Registers the setup router.
- `backend/tests/endpoints/test_setup.py` - Response-boundary, auth, and legacy-detector regression coverage.
- `backend/tests/handler/test_setup_folder_handler.py` - Determinism, unsafe-name, unknown-folder, and assignment coverage.

## Decisions Made

- Reused the existing storage root, resolver, platform, audit, and mapping handler contracts instead of adding a second storage model or legacy bootstrap path.
- Kept `Games` as the response root label required by the plan, while deriving platform behavior from supported metadata and configuration rather than hardcoding product/platform aliases.
- Preserved the existing shared-checkout compose changes and `backend/pgdp_test/` artifact without staging or modifying them.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reject separator-bearing direct folder names explicitly**
- **Found during:** Task 2 focused handler verification
- **Issue:** The shared relative-path normalizer permits nested POSIX segments, while a direct-child setup row must represent exactly one folder name.
- **Fix:** Added explicit separator rejection before normalization.
- **Files modified:** `backend/handler/setup_folder_handler.py`
- **Verification:** Isolated handler suite passes 6 tests.
- **Committed in:** `d7886d6da`

**2. [Rule 1 - Bug] Align setup actor attribution with the existing request contract**
- **Found during:** Task 2 implementation review
- **Issue:** The first route draft read actor data through `request.auth.user`, unlike existing storage routes.
- **Fix:** Reused the established `request.user.id` and `request.user.username` contract.
- **Files modified:** `backend/endpoints/setup.py`
- **Verification:** Module compilation/import path reviewed; route uses the same actor shape as storage routes.
- **Committed in:** `d7886d6da`

### Verification Environment Limitations

- The prescribed `romm-dev` service is not present in this checkout; Compose exposes `pgdp-dev`, `pgdp-db-dev`, and `pgdp-valkey-dev`.
- The equivalent container focused suite reaches the existing MariaDB setup boundary and fails before assertions because `pgdp_test` cannot authenticate through the configured host/network path. No Compose or database changes were made.
- Frontend typecheck could not start because `frontend/node_modules/.bin/vue-tsc` is absent.
- Repository-wide Trunk was started but did not complete in the execution window; its task-owned processes were stopped. No pass is claimed.
- OpenAPI generation was not run because the development frontend dependencies and authenticated application/database runner were unavailable.

**Total deviations:** 2 auto-fixed (2 bugs). No architectural changes or unrelated source changes were made.
**Impact on plan:** The implementation and isolated handler verification completed. Container, frontend, and full Trunk gates remain explicitly blocked by the shared checkout environment.

## Issues Encountered

- Initial focused pytest execution was blocked before assertions by the canonical test database credentials/network boundary, matching the existing project state concern. The handler behavior was independently verified with `pytest --noconftest`.
- The stale pre-existing `33-02-SUMMARY.md` described an older frontend plan. It was replaced with this summary for the revised backend plan, without changing unrelated implementation files.
- The remote Linux checkout does not provide `apply_patch`; file changes were applied through the verified checkout using the available remote tooling and then formatted/checked by repository hooks.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The backend setup contract and routes are available for the dependent first-run UI work. Before claiming full phase verification, rerun the focused container suite with valid disposable MariaDB credentials/networking, install or mount frontend dependencies for typecheck and OpenAPI generation, and complete Trunk.

## Known Stubs

None. The only `not available` text is a bounded runtime validation error, not placeholder UI or an unwired data source.

## Self-Check: PASSED

- Summary path exists at `.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-02-SUMMARY.md`.
- Plan commits `ece4125f7`, `ac0a731b1`, and `d7886d6da` exist in Git history.
- Changed production files are below the 500-line repository limit: handler 251 lines, endpoint 54 lines, schemas 49 lines.
- Unrelated `docker-compose.override.yml`, `docker-compose.yml`, and `backend/pgdp_test/` remain unstaged.

---
*Phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc*
*Completed: 2026-10-16*