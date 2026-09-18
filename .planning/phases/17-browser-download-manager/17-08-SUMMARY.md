---
phase: 17-browser-download-manager
plan: 08
subsystem: frontend
tags: [vue, vitest, file-system-access, streaming, sha256, resume]
requires:
  - phase: 17-browser-download-manager
    provides: immutable browser download manifests and standard handoff queue
provides:
  - capability-gated File System Access enhanced transfer path
  - safe relative destination validation and strict Range/If-Match response checks
  - incremental SHA-256 worker verification with bounded enhanced scheduling
affects: [browser-download-manager]
tech-stack:
  added: [hash-wasm@4.12.0]
  patterns:
    [
      user-initiated FSA capability detection,
      streamed worker hashing,
      exact 206 resume validation,
    ]
key-files:
  created:
    - frontend/src/v2/utils/downloadManifestPath.ts
    - frontend/src/v2/utils/downloadManifestPath.test.ts
    - frontend/src/v2/workers/downloadHash.worker.ts
    - frontend/src/v2/composables/useBrowserDownloadQueue/index.test.ts
    - frontend/src/v2/components/GameDetails/DownloadManager.test.ts
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/v2/composables/useBrowserDownloadQueue/index.ts
    - frontend/src/v2/components/GameDetails/DownloadManager.vue
key-decisions:
  - "Human approval was required and received for the exact hash-wasm@4.12.0 package before installation."
  - "Standard browser attachment handoff remains unchanged; enhanced behavior is an opt-in capability path."
  - "Enhanced resume accepts only an exact 206 Content-Range and never appends a 200 response."
requirements-completed: [UXDL-01, SAFE-01, TEST-01]
metrics:
  duration: 18min
  completed: 2026-09-18
---

# Phase 17 Plan 08: Enhanced Browser Transfer Summary

**Capability-detected File System Access downloads now stream directly to user-selected folders and verify output with incremental worker-based SHA-256 hashing.**

## Accomplishments

- Added the human-approved exact `hash-wasm@4.12.0` dependency and incremental hash worker protocol.
- Added safe manifest destination validation, child-directory traversal, permission checks, and overwrite refusal.
- Added strict enhanced response handling with exact `Range`/`If-Match` resume requests and exact `206 Content-Range` acceptance.
- Preserved the standard browser handoff path and added focused Vitest coverage for capability detection, path safety, and resume response validation.

## Task Commits

1. **Task 1: Approve provenance for incremental SHA-256 package** - human checkpoint approval, no code commit
2. **Task 2 RED: Add enhanced download protocol tests** - `f4702da74` (test)
3. **Task 2 GREEN: Implement streamed enhanced browser downloads** - `d089a61ca` (feat)

## Files Created/Modified

- `frontend/src/v2/utils/downloadManifestPath.ts` - validates safe relative POSIX destination segments.
- `frontend/src/v2/workers/downloadHash.worker.ts` - maintains incremental SHA-256 state in a worker.
- `frontend/src/v2/composables/useBrowserDownloadQueue/index.ts` - capability detection, strict streaming/resume, local verification, and bounded enhanced scheduling.
- `frontend/src/v2/components/GameDetails/DownloadManager.vue` - advertises enhanced mode only when the browser capability exists.
- `frontend/package.json`, `frontend/package-lock.json` - exact approved hash dependency.

## Decisions Made

- Human provenance approval gates the package installation, as required by the threat model.
- Existing local bytes are hashed incrementally before a resume; a full-size local file is verified without downloading again.
- Handles, permissions, and active controllers remain in memory only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adapted the worker to hash-wasm's asynchronous hasher API.**

- **Found during:** Task 2 typecheck
- **Issue:** `createSHA256()` returns a promise in the installed package typings.
- **Fix:** Awaited the hasher before reset, update, and digest operations.
- **Files modified:** `frontend/src/v2/workers/downloadHash.worker.ts`
- **Verification:** `npm run typecheck`
- **Committed in:** `d089a61ca`

**2. [Rule 3 - Blocking] Added typed permission compatibility for File System Access handles.**

- **Found during:** Task 2 typecheck
- **Issue:** The repository TypeScript DOM definitions do not expose directory `queryPermission` and `requestPermission` methods.
- **Fix:** Added a narrow local capability type for those browser methods.
- **Files modified:** `frontend/src/v2/composables/useBrowserDownloadQueue/index.ts`
- **Verification:** `npm run typecheck`
- **Committed in:** `d089a61ca`

**Total deviations:** 2 auto-fixed (Rule 3: 2)

## Issues Encountered

- `npm install` reported existing audit vulnerabilities in the dependency tree. No unrelated dependency remediation was performed.

## Verification

- `npm run test -- downloadManifestPath downloadHash useBrowserDownloadQueue DownloadManager` passed, 4 files and 11 tests.
- `npm run typecheck` passed.
- `git diff --check` passed.
- Standard queue code and attachment semantics were preserved.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The enhanced queue primitives are available for subsequent UI/state-history work. The browser must provide `showDirectoryPicker()` and the user must grant read/write access for enhanced transfers; standard browser downloads remain the fallback.

## Self-Check: PASSED

- Summary and all declared implementation/test files exist.
- Commits `f4702da74` and `d089a61ca` are present in Git history.
- No tracked files were deleted by the task commits.

---

_Phase: 17-browser-download-manager_
_Plan: 08_
_Completed: 2026-09-18_
