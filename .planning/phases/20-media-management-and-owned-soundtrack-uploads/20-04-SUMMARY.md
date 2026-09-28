---
phase: 20-media-management-and-owned-soundtrack-uploads
plan: "04"
subsystem: ui
tags: [vue, vitest, v2, owned-media, background-rotation, reduced-motion]
requires:
  - phase: 20-media-management-and-owned-soundtrack-uploads
    provides: parent-ROM owned-media API and generated contracts
provides:
  - owned artwork upload, deletion, placement, and accessible complete-list ordering
  - route-scoped ordered backdrop rotation with behavioral reduced-motion protection
affects: [20-05, 20-06, v2-game-details]
tech-stack:
  added: []
  patterns:
    [
      typed owned-media multipart uploads,
      authoritative reorder conflict recovery,
      cleanup-bound background timers,
    ]
key-files:
  created:
    - frontend/src/services/api/rom-owned-media.test.ts
    - frontend/src/v2/components/GameDetails/ArtworkSubtab.test.ts
  modified:
    - frontend/src/services/api/rom.ts
    - frontend/src/v2/components/GameDetails/ArtworkSubtab.vue
    - frontend/src/v2/views/GameDetails.vue
    - frontend/src/v2/views/GameDetails.test.ts
key-decisions:
  - "Use complete ordered placement replacement for moves, then refetch before displaying a 409 conflict."
  - "Keep backdrop animation selection in GameDetails and leave BackgroundArt's two-layer transition unchanged."
patterns-established:
  - "Owned-media mutations always target parent-ROM routes and refresh the canonical detail record after success or conflict."
  - "A reduced-motion-disabled rotation is one interval with watcher cleanup, while fallback art is applied synchronously."
requirements-completed:
  [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07]
duration: 10min
completed: 2026-09-28
---

# Phase 20 Plan 04: Owned Artwork and Background Rotation Summary

**Owned artwork candidates now support upload, deletion, background membership and accessible server-order reordering, while Game Details rotates confirmed backgrounds only when motion is allowed.**

## Performance

- **Duration:** 10 min
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- Added typed parent-owned media wrappers for role-bound multipart uploads and atomic full-list placement replacement.
- Replaced the legacy artwork-only display with owned provider/upload candidates, deletion confirmation, upload progress, and a native-linear Backgrounds ordering list.
- Applied parent owned-media background placements in server order with fake-timer coverage for rotation, cleanup, and reduced-motion static behavior.

## Task Commits

1. **Shared API wrapper deviation** - `2e3e00251` (feat)
2. **Task 1: Build artwork upload and atomic background ordering controls** - `02c3f7d47` (feat)
3. **Task 2: Apply ordered backgrounds through a route- and motion-safe lifecycle** - `3f16096fa` (feat)

## Files Created/Modified

- `frontend/src/services/api/rom.ts` - Typed owned-media upload and complete-list reorder wrappers.
- `frontend/src/services/api/rom-owned-media.test.ts` - Wrapper contract coverage.
- `frontend/src/v2/components/GameDetails/ArtworkSubtab.vue` - Owned candidate gallery, background list, and mutation lifecycle.
- `frontend/src/v2/components/GameDetails/ArtworkSubtab.test.ts` - Artwork candidate and ordering regression coverage.
- `frontend/src/v2/views/GameDetails.vue` - Ordered, cleanup-bound background rotation selection.
- `frontend/src/v2/views/GameDetails.test.ts` - Fake-timer rotation and reduced-motion tests.

## Decisions Made

- Moves submit the complete confirmed background membership, not a local position delta, so the backend remains authoritative.
- GameDetails owns only URL sequence and interval lifetime. BackgroundArt continues to own the visual cross-fade.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing shared owned-media API wrappers.**

- **Found during:** Task 1
- **Issue:** The API client exposed placement add/remove but not the planned multipart upload or complete-list reorder operations.
- **Fix:** Added generated-type-backed wrappers and focused contract coverage before building the UI.
- **Files modified:** `frontend/src/services/api/rom.ts`, `frontend/src/services/api/rom-owned-media.test.ts`
- **Verification:** `npm run test -- rom-owned-media` passes.
- **Committed in:** `2e3e00251`

**Total deviations:** 1 auto-fixed (Rule 3)

## Issues Encountered

- No focused verification failures remained. The initial combined typecheck briefly observed concurrent uncommitted SoundtrackPanel changes; the final focused test run and typecheck passed after that work stabilized.

## Known Stubs

- The new `rom.*` copy keys used by this UI are intentionally supplied by Plans 20-06 and 20-07, the phase's locale batches. They are not hard-coded user-visible strings.

## Next Phase Readiness

- Plan 20-05 can reuse the owned-media upload and full placement replacement wrappers for soundtrack controls.
- Plans 20-06 and 20-07 need to supply locale entries for the new owned-media copy keys.

## Self-Check: PASSED

- All six implementation and test files exist.
- Commits `2e3e00251`, `02c3f7d47`, and `3f16096fa` exist in Git history.
