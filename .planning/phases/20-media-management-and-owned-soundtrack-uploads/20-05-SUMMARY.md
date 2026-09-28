---
phase: 20-media-management-and-owned-soundtrack-uploads
plan: "05"
subsystem: ui
tags: [vue, pinia, vitest, owned-media, soundtrack]
requires:
  - phase: 20-media-management-and-owned-soundtrack-uploads
    provides: parent-ROM owned-media API and typed media wrappers
provides:
  - owned-media playlist identity and deterministic ordered navigation
  - v2 owned soundtrack upload, inclusion, ordering, playback, download, and deletion controls
affects: [20-06, 20-07, v2-media-management]
tech-stack:
  added: []
  patterns:
    [
      ordered soundtrack placements drive both rendering and playback,
      owned-media-only audio operations,
    ]
key-files:
  created:
    - frontend/src/stores/soundtrackPlayer.test.ts
    - frontend/src/v2/components/GameDetails/SoundtrackPanel.test.ts
  modified:
    - frontend/src/stores/soundtrackPlayer.ts
    - frontend/src/v2/components/GameDetails/SoundtrackPanel.vue
key-decisions:
  - "The player identity is the stable parent-owned media ID, not a source RomFile ID."
  - "The ordered soundtrack placement list is the sole source for rendered included tracks and playback navigation."
requirements-completed:
  [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07]
duration: 15min
completed: 2026-09-28
---

# Phase 20 Plan 05: Owned Soundtrack Queue Summary

**RomM-owned audio upload and ordered playback queue using stable media IDs, protected media content, and no source-library soundtrack mutation routes.**

## Performance

- **Duration:** 15 min
- **Completed:** 2026-09-28
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Replaced source `RomFile` queue identity with parent-owned media IDs and tested deliberately non-alphabetical navigation plus decode-error retention.
- Replaced the legacy soundtrack panel with owned-media uploads, candidate inclusion, full-list order replacement, protected download links, playback controls, retry feedback, and destructive deletion.
- Ensured included placement order drives both rendered rows and `loadPlaylistForRom`.

## Task Commits

1. **Task 1: Generalize player identity for the ordered owned-media queue** - `11e65d9e9` (feat)
2. **Task 2: Implement the owned soundtrack panel** - `2d523a454` (feat)

## Decisions Made

- Audio labels use only the server-sanitized owned-media `display_label`; no tags or metadata enrichment are requested.
- Uploads run sequentially with the updated optimistic-lock version from each response, so a multi-file upload does not invalidate later files with a stale version.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Preserved the optimistic-lock version across multi-file uploads.**

- **Found during:** Task 2
- **Issue:** Parallel uploads reused the initial detailed-ROM version, allowing an earlier successful upload to make later files fail as stale.
- **Fix:** Upload each selected file in sequence and use the returned ROM version for the next request while retaining per-file failure reporting.
- **Files modified:** `frontend/src/v2/components/GameDetails/SoundtrackPanel.vue`
- **Verification:** Focused Vitest and scoped Trunk checks pass.
- **Committed in:** `2d523a454`

## Verification

- `npm run test -- SoundtrackPanel soundtrackPlayer` passed, 6 tests.
- `npm run typecheck` passed.
- Scoped `trunk check` passed for the four plan files.

## Issues Encountered

- The shared `sourceMutationInventory` suite currently lacks a classification for the Plan 20-04 `refreshOwnedMedia` wrapper. This plan did not modify that shared inventory file.

## Known Stubs

None.

## Next Phase Readiness

- Plan 20-06 can add the referenced translation keys and locale parity coverage.
- Plan 20-07 can perform browser UAT for the owned media workflow.

## Self-Check: PASSED

- Player and panel files exist and commits `11e65d9e9` and `2d523a454` are present in Git history.
