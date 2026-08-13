---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 26
subsystem: storage-policy
tags: [frontend-v2, source-rename, semantic-inventory, fail-closed, tdd]
requires:
  - phase: 06-18
    provides: initial source mutation inventory and external read-only policy
  - phase: 06-24
    provides: catalog-only delete controls and typed owned-resource retention
  - phase: 06-25
    provides: upload/setup retirement and external READ plus owned TEMP patch contract
provides:
  - metadata-only active-v2 ROM edit and match flows with no source rename intent
  - all-active-v2 semantic method-route-payload-authority inventory
  - pre-I/O denial for crafted changed fs_name requests
  - complete external mutation-family and owned descriptor coverage
affects: [CAT-01, CAT-04, phase-06-verification]
tech-stack:
  added: []
  patterns:
    - recursive production-module and reachable-service inventory
    - semantic method-route-payload-authority classification
    - mixed-authority preflight before database, resource, or filesystem effects
key-files:
  created: []
  modified:
    - frontend/src/v2/sourceMutationInventory.test.ts
    - frontend/src/v2/sourceMutationControls.test.ts
    - frontend/src/v2/components/Dialogs/EditRomDialog.vue
    - frontend/src/v2/components/Dialogs/MatchRomDialog.vue
    - frontend/src/v2/components/MatchRom/MatchRomBodyGrid.vue
    - frontend/src/v2/components/MatchRom/MatchRomBodyList.vue
    - frontend/src/v2/components/MatchRom/types.ts
    - frontend/src/services/api/rom.ts
    - backend/endpoints/roms/__init__.py
    - backend/tests/endpoints/test_storage_policy_denials.py
key-decisions:
  - "Keep source filename visible but read-only in edit, and remove rename intent entirely from match UI, types, and payload construction."
  - "Narrow updateRom at its function boundary and multipart serializer while retaining the shared UpdateRom model for frozen v1 type consumers."
  - "Treat PUT /roms/{id} as external RENAME only when fs_name changes, and authorize that operation before every durable or resource effect."
metrics:
  duration: 22m
  completed: 2026-08-13
  tasks: 2
  files: 10
---

# Phase 6 Plan 26: Source Rename and Semantic Inventory Closure Summary

**Active v2 source rename authority is removed across UI and services, backed by a 435-module semantic inventory and fail-closed server authorization before any mixed-authority update effect.**

## Performance

- **Duration:** 22 minutes
- **Started:** 2026-08-13T21:27:33Z
- **Completed:** 2026-08-13T21:49:59Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Made the edit source filename read-only and removed `renameFromSource` state, controls, emitted payload fields, and filename rewriting from both match layouts and their dialog/type boundary.
- Prevented `updateRom` from accepting or serializing `fs_name` while preserving metadata, cover, manual, media, and catalog updates.
- Replaced the partial v2 scan with recursive coverage of 435 production v2 modules and 19 reachable API service modules, classified by method, route, payload capability, operation, and storage authority.
- Bound the inventory to all 13 external mutation operations, all 10 `OwnedStorageKind` descriptors, reviewed route registrations, mixed-authority branches, aliases, dynamic calls, conditional flags, and safe generic-client positives.
- Added adversarial changed-name requests for ordinary rename, traversal, symlink alias, collision, and replay; every denial is path-redacted and precedes database, resource, and filesystem activity.
- Preserved same-name metadata and owned-resource updates without requesting external rename authority.

## Task Commits

1. **Task 1 RED: inventory all v2 external mutation** - `bb1a74efc`
2. **Task 1 GREEN: remove v2 rename authority** - `0982c0762`
3. **Task 2 RED: deny source rename atomically** - `1f84c5447`
4. **Task 2 GREEN: guard source rename before mutation** - `36a8acd53`

## Files Created/Modified

- `frontend/src/v2/sourceMutationInventory.test.ts` - Recursive semantic inventory, live operation/descriptor assertions, closed route review, positive generic clients, and maximum-grant negative fixtures.
- `frontend/src/v2/sourceMutationControls.test.ts` - Rendered edit and match assertions proving rename intent cannot be expressed.
- `frontend/src/v2/components/Dialogs/EditRomDialog.vue` - Read-only source filename display with metadata-only form validity.
- `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`, `frontend/src/v2/components/MatchRom/MatchRomBodyGrid.vue`, `frontend/src/v2/components/MatchRom/MatchRomBodyList.vue`, `frontend/src/v2/components/MatchRom/types.ts` - Removed rename controls, state, and payload propagation.
- `frontend/src/services/api/rom.ts` - Metadata-only `updateRom` input and multipart payload with no `fs_name` field.
- `backend/endpoints/roms/__init__.py` - Changed-name external RENAME authorization immediately after sanitize/compare.
- `backend/tests/endpoints/test_storage_policy_denials.py` - Crafted request, replay, immutable-manifest, call-order, and same-name positive coverage.

## Decisions Made

- The current source filename remains visible in edit as immutable context; active v2 offers no checkbox, state, event field, service parameter, or serializer path that can request a rename.
- The exported `UpdateRom` model remains compatible with frozen v1 type consumers, but the callable `updateRom` contract uses `Omit<UpdateRom, "fs_name">` and never appends the field.
- A changed sanitized filename is a mixed-authority external RENAME request even when the same request also carries permitted metadata or owned-resource changes. The external decision happens first and Phase 6 denies it.
- Same-name and omitted-name requests remain metadata/resource operations and do not request RENAME authority.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Scoped payload classification to the enclosing service function**

- **Found during:** Task 1 GREEN
- **Issue:** The first inventory implementation scanned the entire service module for payload capabilities, so the type-level `Omit<UpdateRom, "fs_name">` falsely classified the metadata-only `updateRom` serializer as a rename request.
- **Fix:** Limited payload capability analysis to the enclosing function and retained detection of member access, multipart keys, raw object fields, aliases, and conditional flags.
- **Files modified:** `frontend/src/v2/sourceMutationInventory.test.ts`
- **Commit:** `0982c0762`

**2. [Rule 3 - Blocking] Provisioned an isolated backend test schema**

- **Found during:** Task 2 RED
- **Issue:** The application database user could not create `romm_test_0626` during pytest setup.
- **Fix:** Created and granted only the task-named schema through the existing database container, ran the tests with a task-only authentication secret, then revoked the grant, dropped the schema, and asserted its absence.
- **Files modified:** None
- **Commit:** Not applicable

**3. [Rule 3 - Blocking] Followed the live plural filesystem handler path**

- **Found during:** Task 2 read-first inspection
- **Issue:** The plan referenced `backend/handler/filesystem/rom_handler.py`, while the live repository module is `backend/handler/filesystem/roms_handler.py`.
- **Fix:** Inspected the live imported handler without changing code or architecture.
- **Files modified:** None
- **Commit:** Not applicable

## Issues Encountered

- The first typecheck command used the nonexistent script spelling `type-check`; the repository-declared `typecheck` command was then run and passed.
- Existing Vitest router, injection, cache, and locale warnings remained non-failing.
- Production build completed with existing third-party eval, chunk-size, and CSS pseudo-selector warnings.
- Scoped frontend ESLint reported zero errors and 11 existing template style warnings.

## Verification

- Focused frontend authority and rendered-control gate: 20 passed.
- Focused backend rename/update gate: 6 passed.
- Complete backend storage-policy denial matrix: 52 passed.
- Full frontend suite: 53 files and 653 tests passed.
- Frontend `vue-tsc --noEmit` with 4096 MB Node memory: passed.
- Frontend production build: passed, 4,463 modules transformed and PWA output generated.
- Scoped frontend ESLint: zero errors; 11 non-failing existing style warnings.
- Cached Trunk Ruff 0.15.22 and Python AST compilation for both changed backend files: passed.
- Semantic inventory: 435 production v2 modules, 19 reachable service modules, 13 external mutation operations, 10 owned descriptor kinds, 19 reviewed route families, and zero forbidden active-v2 authorities.
- Static scans: active rename controls 0; `updateRom` `fs_name` serialization 0; changed-name guard occurs before `cleaned_data` and every resource/database/filesystem effect.
- `git diff --check`: passed.
- Mandatory hooks passed all four implementation commits without bypass.
- TDD sequence: Task 1 `bb1a74efc` before `0982c0762`; Task 2 `1f84c5447` before `36a8acd53`.
- Cleanup: `romm_test_0626` privilege revoked, schema dropped, and remaining count asserted as 0; no service restarted or deployed.

## Known Stubs

None. Existing visual cover placeholders are intentional empty-art fallbacks and do not defer plan behavior.

## Threat Flags

None. The plan removed client mutation surface and added policy enforcement to an existing mixed-authority route; it introduced no endpoint, authentication path, schema, raw client, or new storage authority.

## Next Phase Readiness

CAT-04 now has final active-v2 semantic closure across source modules, reachable services, live operations, descriptors, routes, payload branches, and crafted direct requests. The phase verifier can repeat the authoritative gates without any service or deployment change.

## Self-Check: PASSED

All ten declared implementation files and all four TDD commits were verified in the canonical Linux checkout; the task database cleanup assertion returned zero.
