---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 50
subsystem: frontend-v2
tags: [vue, typescript, vitest, manuals, accessibility, concurrency]
requires:
  - phase: 06-49
    provides: primary-manual CAS serialization and failure-safe redownload behavior
provides:
  - one pending boundary for every active-v2 primary-manual mutation
  - deterministic redownload race and recovery coverage
affects: [phase-06-verification, primary-manuals, v2-game-details]
tech-stack:
  added: []
  patterns:
    - feature-owned computed pending state guards controls and mutation handlers together
key-files:
  created: []
  modified:
    - frontend/src/v2/components/GameDetails/ManualSubtab.vue
    - frontend/src/v2/components/GameDetails/ManualSubtab.test.ts
key-decisions:
  - "Redownload is part of manualMutationPending, while its own loading indicator remains local to the redownload control."
  - "Delete and replacement handlers defensively enforce the same pending boundary as their disabled controls."
patterns-established:
  - "A visible disabled control is backed by a handler guard so synthetic or stale gestures cannot bypass a feature mutation boundary."
requirements-completed: [CAT-02]
duration: 6min
completed: 2026-08-24
---

# Phase 6 Plan 50: Shared Manual Mutation Boundary Summary

**Primary-manual redownload now shares the active-v2 pending boundary with upload and refresh, preventing competing gestures while retaining the authoritative viewer until refresh succeeds.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-24T16:24:00Z
- **Completed:** 2026-08-24T16:30:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added a named RED regression proving a deferred redownload marks the region busy, disables all competing primary-manual gestures, retains the viewer, refreshes the initiating ROM before success, and recovers from a conflict.
- Included `redownloadingManual` in `manualMutationPending`, so the existing dropzone, viewer controls, Replace control, and aria-busy state use one truth source.
- Added defensive pending guards to delete and replacement handlers, preventing stale or synthetic events from bypassing disabled controls.

## TDD Gate Compliance

- **RED:** `0519f0ec1` ran the exact named selector in a nonce-owned Node 24 lifecycle. It failed only on the expected `aria-busy` pending-boundary assertion.
- **GREEN:** `2b771b785` passed the ManualSubtab and ManualViewerControls test modules, seven tests total, plus `vue-tsc --noEmit` in a fresh nonce-owned Node 24 lifecycle.

## Task Commits

1. **Task 1: RED prove redownload blocks every competing manual gesture** - `0519f0ec1` (test)
2. **Task 2: GREEN include redownload in the shared pending state** - `2b771b785` (feat)

## Files Created/Modified

- `frontend/src/v2/components/GameDetails/ManualSubtab.vue` - extends the shared mutation boundary to redownload and guards delete and replacement entry points.
- `frontend/src/v2/components/GameDetails/ManualSubtab.test.ts` - verifies pending accessibility semantics, competing gestures, stable viewer state, refresh ordering, conflict recovery, and retry.

## Decisions Made

- Redownload begins only from idle, then its own state becomes part of the shared pending computation. This avoids self-deadlock while blocking every subsequent mutation.
- Success remains after the same-ROM refresh, and errors leave the existing viewer in place.

## Deviations from Plan

None - the implementation followed the planned scope.

## Issues Encountered

- The Linux host has no standalone `trunk` executable. The commit hook formatted and checked the modified frontend file successfully; focused disposable tests, typecheck, and `git diff --check` also passed.

## Verification and Cleanup

- RED exact selector: one intended assertion failure, with normal test collection and execution.
- GREEN disposable Node 24 lifecycle: 7/7 focused tests passed and `npm run typecheck` passed.
- The RED and GREEN runners used exact owned IDs, `io.romm.phase6.round4=06-50`, no published ports, and exact-ID cleanup before exact-volume cleanup.
- No `p0650` runners or `romm-p0650` volumes remain. `romm-dev` remains exited.
- `git diff --check` passed and the exact 28-entry untracked baseline retains SHA-256 `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1`.

## Known Stubs

None.

## Threat Review

No new endpoint, authentication path, schema, filesystem authority, or responsive/input system was added. The shared handler guard and `aria-busy` state mitigate duplicate gestures without changing the existing permission gating or viewer layout.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 53 can bind a disposable browser verification to this committed UI boundary.
- Plan 54 can include this focused evidence in the final Phase 6 acceptance run.

## Self-Check: PASSED

- Both modified source files and commits `0519f0ec1` and `2b771b785` exist in repository history.
- Disposable runner cleanup, stopped-service state, and baseline continuity were verified.

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-24_
