---
phase: 20-media-management-and-owned-soundtrack-uploads
plan: "03"
subsystem: ui
tags: [vue, vite, vitest, v2, owned-media, accessibility]
requires:
  - phase: 20-media-management-and-owned-soundtrack-uploads
    provides: parent-ROM owned-media endpoints and generated contracts
provides:
  - typed v2 parent-owned screenshot media client calls
  - accessible URL-synchronised Media tab panels
  - provider screenshot candidate placement, deletion, and refresh controls
affects: [20-04, 20-05, v2-media-management]
tech-stack:
  added: []
  patterns:
    [
      authoritative detail refetch after owned-media mutation,
      candidate-placement separation,
    ]
key-files:
  created:
    - frontend/src/v2/components/GameDetails/ScreenshotsSubtab.test.ts
  modified:
    - frontend/src/services/api/rom.ts
    - frontend/src/stores/roms.ts
    - frontend/src/v2/components/GameDetails/MediaTab.vue
    - frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue
    - frontend/src/v2/sourceMutationControls.test.ts
key-decisions:
  - "Provider candidates are rendered only from parent-owned media records, never legacy source paths or RomFile audio APIs."
  - "Every successful mutation and every 409 conflict refetches the canonical detailed ROM before feedback."
patterns-established:
  - "Use typed owned-media wrappers with the current detailed ROM version for every v2 media mutation."
  - "Keep candidate existence distinct from overview and background placement state."
requirements-completed:
  [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07]
duration: 9min
completed: 2026-09-28
---

# Phase 20 Plan 03: Provider Screenshot Management Summary

**Accessible v2 provider screenshot management using parent-owned media candidates, separate display placements, destructive confirmation, and explicit recovery refresh.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-09-28T14:06:00Z
- **Completed:** 2026-09-28T14:15:00Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- Added typed parent-owned media wrappers plus a single store-level detailed-ROM refresh path.
- Linked URL-synchronised Media tabs to labelled panels and expose owned soundtrack content without the legacy source gate.
- Replaced source-derived provider screenshot display with a permission-gated owned candidate grid supporting overview/background placement, permanent deletion, and explicit refresh.
- Added focused source-safety and candidate-management Vitest coverage.

## Task Commits

1. **Task 1: Wire typed media calls and Media tab accessibility state** - `beded437a` (feat)
2. **Task 2: Implement provider screenshot candidate management** - `dd9961d0b` (feat)

## Files Created/Modified

- `frontend/src/services/api/rom.ts` - Typed parent-owned media request wrappers.
- `frontend/src/stores/roms.ts` - Canonical detailed-ROM refresh action.
- `frontend/src/v2/components/GameDetails/MediaTab.vue` - URL-preserving accessible tab and panel linkage.
- `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue` - Owned provider screenshot candidate UI.
- `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.test.ts` - Candidate, conflict, permission, and preview regression inventory.
- `frontend/src/v2/sourceMutationControls.test.ts` - Source-route regression coverage for v2 Media.

## Decisions Made

- Provider screenshot candidates use only `/api/roms/{romId}/media/{mediaId}/content`; no provider UI derives paths from `RomFile` or source folders.
- Placement operations are non-destructive, while deletion is gated through a danger confirmation and the server-owned tombstone lifecycle.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced stale source-gallery assertions with owned-media assertions.**

- **Found during:** Task 2
- **Issue:** Existing regression assertions expected screenshots rendered from legacy source paths, contrary to the revised owned-media contract.
- **Fix:** Updated the source-mutation inventory to require parent-owned content routes and forbid source file-content/path seams.
- **Files modified:** `frontend/src/v2/sourceMutationControls.test.ts`
- **Verification:** Focused Vitest suite passes.
- **Committed in:** `dd9961d0b`

**Total deviations:** 1 auto-fixed (Rule 1)

## Issues Encountered

- Production build passes with pre-existing dependency/style warnings from `vue3-pdf-app` and a legacy `:deep` selector. Neither warning is in this plan's files.

## Known Stubs

None.

## Next Phase Readiness

- Plans 20-04 and 20-05 can reuse the typed wrappers and canonical refresh pattern for artwork and owned soundtrack controls.

## Self-Check: PASSED

- All six implementation and test files exist.
- Task commits `beded437a` and `dd9961d0b` exist in Git history.

---

_Phase: 20-media-management-and-owned-soundtrack-uploads_
_Completed: 2026-09-28_
