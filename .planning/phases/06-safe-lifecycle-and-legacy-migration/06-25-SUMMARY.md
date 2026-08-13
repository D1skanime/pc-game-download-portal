---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 25
subsystem: storage-policy
tags: [frontend-v2, upload-retirement, setup-guard, temp-patch, tdd]
requires:
  - phase: 06-18
    provides: external source policy boundary and mutation inventory
  - phase: 06-24
    provides: retired firmware upload and source-delete authority
provides:
  - active v2 source-neutral upload, platform, setup, and patch surfaces
  - pre-I/O CREATE and MKDIR denial for crafted setup requests
  - retained POST /roms/{id}/patch as external READ plus owned TEMP PATCH
affects: [06-26, CAT-01, CAT-04]
tech-stack:
  added: []
  patterns:
    - semantic method-route-authority inventory
    - neutral empty legacy routes
    - policy authorization before source inspection
key-files:
  created: []
  modified:
    - frontend/src/v2/sourceMutationControls.test.ts
    - frontend/src/v2/views/Upload.vue
    - frontend/src/v2/components/GameDetails/PatcherTab.vue
    - frontend/src/v2/components/Auth/SetupStepPlatforms.vue
    - frontend/src/services/api/rom.ts
    - frontend/src/services/api/platform.ts
    - frontend/src/services/api/setup.ts
    - backend/endpoints/heartbeat.py
    - backend/endpoints/roms/files.py
    - backend/endpoints/roms/patch.py
    - backend/tests/endpoints/test_storage_policy_denials.py
key-decisions:
  - "Keep the legacy v2 upload route inert while removing every active v2 navigation and mutation control."
  - "Classify the retained patch call as POST /roms/{id}/patch with READ/external input and PATCH/TEMP output."
  - "Authorize both CREATE and MKDIR before setup structure detection, with empty input remaining neutral."
metrics:
  duration: 42m
  completed: 2026-08-13
  tasks: 2
  files: 17
---

# Phase 6 Plan 25: External Upload and Setup Closure Summary

**Active v2 upload, setup creation, and patch persistence authority retired while the typed temporary patch download remains available and crafted setup writes deny before source inspection.**

## Performance

- **Duration:** 42 minutes
- **Started:** 2026-08-13T20:24:21Z
- **Completed:** 2026-08-13T21:06:00Z
- **Tasks:** 2
- **Files modified:** 17

## Accomplishments

- Removed every active v2 `ROUTES.UPLOAD` navigation entry, upload dropzone/file control, platform creation selector, and setup creation call under maximum grants.
- Removed `uploadRoms`, `uploadPlatform`, and `createPlatforms` service exports without adding a raw replacement client.
- Reduced patching to one typed `POST /roms/{id}/patch` call, external READ input, owned TEMP PATCH output, and local browser download.
- Added fail-closed CREATE and MKDIR setup authorization before library structure detection or filesystem mutation.
- Added rendered authority controls, semantic patch inventory, neutral empty-input, replay, path replacement, symlink, and immutable-manifest regression coverage.

## Task Commits

1. **Task 1 RED: expose external upload controls** - `a042985ac`
2. **Task 1 GREEN: remove external upload authority** - `880f97a61`
3. **Task 2 RED: deny setup source creation** - `e191e04bb`
4. **Task 2 GREEN: guard setup source creation** - `41dd91caa`
5. **Closeout Rule 3: resolve scoped static errors** - `48b1c3066`
6. **Closeout Rule 1: complete replay immutability coverage** - `4d70abb01`
7. **Post-wave Rule 1: remove retired backend imports** - `524923703`

## Files Created/Modified

- `frontend/src/v2/views/Upload.vue` - Neutral read-only legacy route with no upload client or file control.
- `frontend/src/v2/components/GameDetails/PatcherTab.vue` - Temporary patch generation and local download only.
- `frontend/src/v2/components/Auth/SetupStepPlatforms.vue` - Detected platform display without creation selection.
- `frontend/src/v2/components/AppShell/UserMenu.vue`, `frontend/src/v2/components/Settings/SettingsSidebar.vue`, `frontend/src/v2/views/Home.vue`, `frontend/src/v2/views/Gallery/Platform.vue` - Removed upload navigation and actions.
- `frontend/src/services/api/rom.ts`, `frontend/src/services/api/platform.ts`, `frontend/src/services/api/setup.ts` - Removed forbidden mutation exports.
- `backend/endpoints/heartbeat.py` - Added CREATE and MKDIR authorization before setup detection.
- `frontend/src/v2/sourceMutationControls.test.ts`, `frontend/src/v2/views/Upload.test.ts`, `backend/tests/endpoints/test_storage_policy_denials.py` - Added TDD authority, route, replay, and immutability gates.
- `frontend/src/components/common/Game/Dialog/UploadRom.vue`, `frontend/src/views/Auth/Setup.vue` - Retired legacy callers of removed service exports without adding network mutation.

## Decisions Made

- The v2 upload route remains resolvable but renders only a neutral scan-oriented empty state, so stale links cannot mutate external source storage.
- Patch input remains a browser-selected temporary patch file or existing library patch reference; output remains an owned TEMP response downloaded locally.
- Every non-empty setup request requests CREATE and MKDIR authority against the trusted `legacy_external_storage` descriptor before detection. Phase 6 policy denies the first operation deterministically.
- Empty setup input performs no authorization, path detection, filesystem call, or database mutation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Retired legacy consumers of removed service exports**

- **Found during:** Task 1 GREEN typecheck
- **Issue:** Two inactive v1 components still called `uploadRoms`, `uploadPlatform`, or `createPlatforms` after the required exports were removed.
- **Fix:** Made the legacy upload finish action inert and removed legacy setup folder creation while preserving read and admin-user flows.
- **Files modified:** `frontend/src/components/common/Game/Dialog/UploadRom.vue`, `frontend/src/views/Auth/Setup.vue`
- **Commit:** `880f97a61`

**2. [Rule 3 - Blocking] Isolated frontend dependencies and test database**

- **Found during:** Task 1 RED and Task 2 RED
- **Issue:** The canonical host had no frontend package manager dependencies, and the test database user could not create `romm_test_0625`.
- **Fix:** Used task-owned `/tmp` dependency and build mounts, a task-only auth secret, and an explicitly created test schema. All were removed and absence asserted.
- **Files modified:** None
- **Commit:** Not applicable

**3. [Rule 3 - Blocking] Scoped static errors after authority retirement**

- **Found during:** Final static verification
- **Issue:** Removed controls left unused imports, and a touched legacy setup read path had an untyped error catch.
- **Fix:** Removed the imports and typed the read-path error without changing behavior or authority.
- **Files modified:** `frontend/src/v2/sourceMutationControls.test.ts`, `frontend/src/v2/views/Home.vue`, `frontend/src/views/Auth/Setup.vue`
- **Commit:** `48b1c3066`

**4. [Rule 1 - Bug] Restored the crafted setup replay test tail**

- **Found during:** Cached Ruff verification and stub scan
- **Issue:** The initial RED patch hunk ended after fixture setup, so the crafted request loop and immutable-manifest assertions were missing.
- **Fix:** Restored all direct requests, exact path-free denial assertions, source manifest comparison, and untouched mutation spies; reran all 47 policy tests.
- **Files modified:** `backend/tests/endpoints/test_storage_policy_denials.py`
- **Commit:** `4d70abb01`

**5. [Rule 1 - Bug] Removed retired backend imports exposed by the cumulative gate**

- **Found during:** Mandatory Wave 3 post-merge verification
- **Issue:** Four imports retired by prior endpoint migrations remained unused and caused scoped Ruff F401 failures.
- **Fix:** Removed only `FileRedirectResponse`, `OwnedCreate`, `OwnedDelete`, and `OwnedDirectory` imports after verifying no usages remained.
- **Files modified:** `backend/endpoints/roms/files.py`, `backend/endpoints/roms/patch.py`
- **Commit:** `524923703`

## Issues Encountered

- The standalone Trunk command timed out twice while resolving tools. Mandatory commit hooks passed, and the exact cached Trunk Ruff 0.15.22 binary then passed both backend files for lint and format.
- Existing Vitest router and emitter warnings remained non-failing.
- Production build completed with existing dependency, chunk-size, pseudo-selector, and third-party eval warnings.
- Scoped frontend ESLint exited zero with no errors and 29 pre-existing style warnings in touched legacy or surrounding templates.

## Verification

- Focused frontend authority gate: 10 passed.
- Focused backend setup, mkdir, and upload gate: 9 passed.
- Full backend storage-policy denial suite after replay-tail correction: 47 passed.
- Frontend typecheck with 4096 MB Node memory: passed.
- Frontend production build with 4096 MB Node memory: passed, 4,463 modules transformed.
- Frontend installed ESLint across 15 touched frontend files: zero errors.
- Cached Trunk Ruff 0.15.22 across all 15 changed backend endpoint modules: lint passed after the post-wave import cleanup; AST compilation passed for all 15 modules.
- Semantic inventory: active v2 upload routes 0; forbidden service exports 0; Upload mutation clients 0; patch raw POSTs 1; patch persistence controls 0; setup creation controls 0.
- Live patch descriptor pair: `READ / legacy_external_storage` plus `PATCH / OwnedStorageKind.TEMP`.
- `git diff --check`: passed.
- Mandatory hooks passed for all six implementation commits without bypass.
- TDD sequence: Task 1 `a042985ac` before `880f97a61`; Task 2 `e191e04bb` before `41dd91caa`.
- Cleanup: `romm_test_0625` dropped with remaining count 0; task-owned dependency and build directories absent; no service restarted or deployed.

## Known Stubs

None. The legacy v1 upload completion handler is intentionally inert after service authority retirement and is not a future implementation placeholder.

## Threat Flags

None. The plan removed network and filesystem mutation surfaces and added a pre-I/O policy guard; it introduced no endpoint, authentication path, schema, raw client, or new storage authority.

## Next Phase Readiness

Active v2 upload and setup authority is source-neutral, crafted setup writes fail before inspection, and the retained temporary patch contract is ready for Plan 26 final all-v2 semantic inventory and closure.

## Self-Check: PASSED

All declared key files and implementation commits were verified in the canonical Linux checkout.
