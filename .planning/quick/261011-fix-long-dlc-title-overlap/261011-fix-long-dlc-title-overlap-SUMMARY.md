---
name: 261011-fix-long-dlc-title-overlap
status: complete
completed: 2026-10-11
---

# Quick Fix Summary

Fixed the PC DLC detail header so the back-to-game action is constrained to the 240px cover column. Long parent-game labels now stay inside that column and truncate with an ellipsis instead of overlapping the DLC title and tabs. The title column remains independently shrinkable and retains its existing long-title ellipsis behavior.

## Verification

- Linux preflight passed for `/home/d1sk/romm` on `main`.
- Focused Vitest: 49 tests passed across `PcDlcDetails.test.ts` and `PcDlcDetail.test.ts`.
- Frontend typecheck passed.
- Browser UAT passed on a long-title DLC route. The back link stayed inside the cover column and the title remained readable without overlap.

## Commit

- Pending at summary creation.
