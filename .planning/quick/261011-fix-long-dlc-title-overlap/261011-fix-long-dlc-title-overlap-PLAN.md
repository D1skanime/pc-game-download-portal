---
name: 261011-fix-long-dlc-title-overlap
created: 2026-10-11
status: complete
---

# Fix long DLC title overlap

## Goal

Keep the DLC back link inside the fixed cover column so long game and DLC titles cannot overlap it.

## Scope

- Constrain the back link to the cover column width.
- Preserve a readable single-line label with ellipsis and an accessible full-label tooltip.
- Verify the shared PC DLC detail layout with a long title and run the focused frontend tests.

## Verification

- Browser check at a long-title DLC route.
- `npm run test -- --run frontend/src/v2/views/PcDlcDetails.test.ts frontend/src/v2/components/GameDetails/PcDlcDetail.test.ts`
- `npm run typecheck`
