---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 18
subsystem: frontend-storage-authority
tags: [authorization, storage-policy, tdd, vue, static-analysis]
requires:
  - phase: 06-24
    provides: closed external operation policy and typed owned descriptor precedent
provides:
  - source-safe active-v2 ROM file, manual, soundtrack, and shared screenshot panels
  - semantic client authority inventory by operation, route, storage operation, and descriptor
  - rendered maximum-grant controls proving external mutation stays absent
affects: [rom-files, manuals, soundtracks, screenshots, storage-policy]
tech-stack:
  added: []
  patterns:
    - classify concrete calls instead of banning generic Axios or raw API imports
    - preserve typed RESOURCES and ASSETS mutation while external source storage remains read-only
key-files:
  created:
    - frontend/src/v2/sourceMutationInventory.test.ts
    - frontend/src/v2/sourceMutationControls.test.ts
  modified:
    - frontend/src/services/api/rom.ts
    - frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue
    - frontend/src/v2/components/Dialogs/DeleteManualDialog.vue
    - frontend/src/v2/components/Dialogs/ManualUploadTargetDialog.vue
    - frontend/src/v2/components/GameDetails/ManualSubtab.vue
    - frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue
    - frontend/src/v2/components/GameDetails/MediaTab.vue
    - frontend/src/components/Details/MediaTab.vue
    - frontend/src/components/common/Game/Dialog/DeleteManual.vue
    - frontend/src/components/common/Game/Dialog/EditRom.vue
    - frontend/src/components/common/Game/Dialog/ManualUploadTarget.vue
key-decisions:
  - "Keep generic HTTP clients available and reject only semantically classified external mutation pairs."
  - "Keep primary manuals in RESOURCES and personal screenshots in ASSETS mutable while shared source files stay read-only."
patterns-established:
  - "A shared client contract must remain source-neutral across active and retired callers."
requirements-completed: [CAT-01, CAT-04]
duration: 37m
completed: 2026-08-13
---

# Phase 6 Plan 18: External Shared-File Mutation Closure Summary

**Active v2 can read and download shared ROM files but cannot create, overwrite, or delete external generic files, manuals, soundtracks, or screenshots, while RomM-owned RESOURCES and ASSETS flows remain usable.**

## Performance

- **Duration:** 36 minutes 39 seconds
- **Started:** 2026-08-13T18:45:59Z
- **Completed:** 2026-08-13T19:22:38Z
- **Tasks:** 1
- **Files modified:** 13

## Accomplishments

- Removed seven external shared-file mutation exports from the ROM API and all corresponding active-v2 controls and call paths.
- Kept generic ROM file reads and downloads, primary manual upload/redownload/removal in typed RESOURCES, and personal screenshot upload/delete/visibility in typed ASSETS.
- Added a TypeScript AST inventory that resolves aliases and raw client calls, normalizes routes, and reports method, route, StorageOperation, descriptor, importer, and call for forbidden or unknown covered combinations.
- Added maximum-grant rendered controls proving that permissions cannot restore generic delete or external manual, soundtrack, and shared screenshot mutation.
- Retired matching legacy caller affordances required by the shared source-neutral API contract.

## TDD Evidence

- **RED:** `7c45031cf` added the semantic inventory and rendered controls. The focused run had 3 passing and 5 intended failing tests, identifying 9 active-v2 forbidden calls, 7 forbidden exports, and exposed maximum-grant controls.
- **GREEN:** `179849f08` removed external shared-file authority. The focused suite passed 8 tests across 2 files, and the server denial regression passed 17 cases.
- **REFACTOR:** No separate refactor commit was required. Mandatory hooks formatted and rechecked the GREEN files.

## Task Commits

1. **Task 1 RED: Inventory external shared-file mutation** - `7c45031cf` (test)
2. **Task 1 GREEN: Remove external shared-file mutation** - `179849f08` (fix)

## Files Created/Modified

- `frontend/src/v2/sourceMutationInventory.test.ts` - Builds the semantic call and authority inventory, including alias, raw-client, positive owned, and safe unknown controls.
- `frontend/src/v2/sourceMutationControls.test.ts` - Renders maximum-grant panels and asserts the remaining mutation boundaries.
- `frontend/src/services/api/rom.ts` - Removes generic file, manual sidecar, soundtrack, and shared screenshot mutation exports.
- `frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue` - Keeps file browsing, selection, download, and copy-link behavior without delete or upload controls.
- `frontend/src/v2/components/Dialogs/DeleteManualDialog.vue` - Limits deletion to the primary RESOURCES manual.
- `frontend/src/v2/components/Dialogs/ManualUploadTargetDialog.vue` - Uploads manuals only to managed RESOURCES.
- `frontend/src/v2/components/GameDetails/ManualSubtab.vue` - Presents the primary managed manual without external manual-category entries or conversion prompts.
- `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue` - Keeps shared screenshots read-only and personal ASSETS screenshots mutable.
- `frontend/src/v2/components/GameDetails/MediaTab.vue` - Keeps the soundtrack player read-only.
- Four legacy v1 callers - Retire stale mutation affordances so the shared ROM API remains source-neutral and type-safe.

## Decisions Made

- Classify authority at the concrete operation and normalized route boundary, not at the generic client import boundary.
- Preserve explicitly typed RomM-owned behavior without granting any external source-tree mutation.
- Remove stale legacy caller affordances rather than restoring unsafe API compatibility shims.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Bug] Asserted Vue boolean attributes semantically**

- **Found during:** Task 1 GREEN focused verification
- **Issue:** The rendered control expected serialized boolean strings, but Vue omits false attributes and serializes true attributes as present with an empty value.
- **Fix:** Asserted attribute absence for false and presence for true without weakening the behavior under test.
- **Files modified:** `frontend/src/v2/sourceMutationControls.test.ts`.
- **Verification:** The focused suite passed all 8 tests.
- **Committed in:** `179849f08`.

**2. [Rule 3 - Blocking] Retired legacy callers of removed shared authority**

- **Found during:** Full frontend typecheck
- **Issue:** Four legacy v1 components still referenced removed shared manual and soundtrack mutation exports, causing type errors.
- **Fix:** Kept primary RESOURCES manual behavior, made legacy soundtracks read-only, and removed external target and sidecar controls.
- **Files modified:** `frontend/src/components/Details/MediaTab.vue`, `frontend/src/components/common/Game/Dialog/DeleteManual.vue`, `frontend/src/components/common/Game/Dialog/EditRom.vue`, `frontend/src/components/common/Game/Dialog/ManualUploadTarget.vue`.
- **Verification:** Typecheck, production build, installed ESLint, and commit hooks passed.
- **Committed in:** `179849f08`.

**3. [Rule 3 - Blocking] Used repository-installed ESLint after isolated Trunk resolution failed**

- **Found during:** Scoped static verification
- **Issue:** Trunk's isolated ESLint 10 runner could not resolve the repository dependency `@eslint/js`.
- **Fix:** Kept Trunk for Prettier and git-diff-check, then ran the repository-installed ESLint inside the development container against all modified frontend files.
- **Files modified:** None beyond the planned GREEN files.
- **Verification:** Trunk reported no Prettier or diff issues, and installed ESLint exited with no errors.
- **Committed in:** Not applicable, verification environment only.

**4. [Rule 3 - Blocking] Completed the metadata commit with the verified host identity**

- **Found during:** Plan closeout
- **Issue:** The disposable Node GSD commit handler staged the exact tracking set but had no Git author identity.
- **Fix:** Committed the exact staged summary and approved tracking files from the verified Linux checkout with mandatory hooks.
- **Files modified:** None beyond the summary and approved tracking files.
- **Verification:** The final metadata commit contains only the summary, STATE, and ROADMAP files.
- **Committed in:** Final metadata commit.

---

**Total deviations:** 4 auto-fixed correctness or blocking issues.
**Impact on plan:** The fixes preserved and broadened source neutrality without adding endpoints, raw clients, storage authority, dependencies, or service changes.

## Issues Encountered

- The production build retained existing dependency, CSS, and bundle-size warnings and completed successfully.
- The focused rendered test emits a non-failing missing-emitter warning for the isolated ManualSubtab mount.

## Verification

- Focused frontend authority gate: 2 files and 8 tests passed.
- Server pre-I/O denial regression: 17 tests passed.
- Frontend typecheck with 4096 MB Node memory: passed.
- Frontend production build with task-owned output and 4096 MB Node memory: passed.
- Scoped Trunk Prettier and git-diff-check across 13 files: no issues.
- Repository-installed ESLint across 13 files: no errors.
- Semantic inventory after GREEN: zero forbidden active-v2 calls and zero forbidden ROM API exports.
- Maximum-grant rendered panels: generic files and external sidecars remain read-only; RESOURCES manuals and ASSETS screenshots retain owned mutation.
- `git diff --check`: passed.
- Commit hooks: passed without bypass for RED and GREEN commits.
- TDD sequence: `7c45031cf` precedes `179849f08`.
- Cleanup: task database `romm_test_0618` dropped, task build output removed, and no task `.rej`, `.orig`, or temporary files remain.

## Known Stubs

None. No modified source introduces empty or placeholder data that flows to the UI.

## Threat Flags

None. The plan removed client authority and introduced no endpoint, authentication path, filesystem access pattern, schema, or mutation capability.

## Next Phase Readiness

The shared-file client boundary is source-neutral, external route families remain denied before I/O, and Plans 25-26 can broaden the same semantic inventory to upload, setup, patch, and rename surfaces.

## Self-Check: PASSED

- Summary artifact exists at the required phase path.
- RED commit `7c45031cf` and GREEN commit `179849f08` exist.
- All 13 created or modified files exist and neither task commit deleted a tracked file.
- Stub scan found no unresolved blocking placeholder in modified implementation files.
- Task-owned database and build output cleanup were verified.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_
