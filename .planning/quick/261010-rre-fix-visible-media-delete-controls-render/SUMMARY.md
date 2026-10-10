---
status: complete
commit: e5fb985fd
---

# Summary

Moved the parent-ROM provider screenshot and uploaded artwork delete controls into visible `RBtn` activators with the existing `RTooltip activator="parent"` pattern.

## Completed

- Preserved the scoped `rom.edit` gates, upload-origin gate, labels, loading bindings, handlers, confirmations, mutations, refreshes, and styles.
- Added focused source-level assertions that require the visible button and reject the old tooltip-default-slot structure.
- Kept unrelated dirty files untouched.

## Task Commits

1. **Task 1: Pin the visible delete-control regression contract** - `7b0b6184a`
2. **Task 2: Repair both delete activators** - `e5fb985fd`

## Verification

- `Node v24.19.0`
- Focused Vitest: `ScreenshotsSubtab.test.ts` and `ArtworkSubtab.test.ts`, 2 files and 10 tests passed.
- Frontend typecheck: `npm run typecheck`, passed.
- Scoped `git diff --check`, passed. Pre-existing unrelated generated-file EOF warnings were not modified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test contract maintenance] Updated an existing source-level indentation assertion**

- **Found during:** Task 2
- **Issue:** The existing assertion encoded the old nested-tooltip indentation and failed after the required outer-`RBtn` structure was applied.
- **Fix:** Updated it to the new structure and made the new structural assertions whitespace-tolerant with focused regular expressions.
- **Files modified:** `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.test.ts`, `frontend/src/v2/components/GameDetails/ArtworkSubtab.test.ts`
- **Verification:** Focused Vitest passed with 10/10 tests.
- **Committed in:** `e5fb985fd`

---

_Quick task: 261010-rre_
_Completed: 2026-10-10_

## Self-Check: PASSED

- SUMMARY.md exists in the requested quick-task directory.
- Task commits `7b0b6184a` and `e5fb985fd` exist.
- The metadata commit exists and contains this SUMMARY.md and STATE.md update.
