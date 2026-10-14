---
status: complete
commit: pending
---

# Summary

## Completed

- Made artwork-card actions a constrained responsive grid.
- Enabled wrapping and stable sizing for localized RBtn labels.
- Added min-width protection to artwork cards.

## Verification

- Focused ArtworkSubtab Vitest: 5 tests passed.
- Production frontend build passed.
- Live browser inspection passed in the running dev stack; German action labels no longer overlap in light and dark themed views.
- Typecheck remains blocked by the pre-existing missing source_language fixture field in useManualDescription/index.test.ts.
