---
status: complete
commit: 6cb6eb7d8
---

# Summary

Implemented context-aware PC component matching.

- Main-game and base-component matching remain unchanged.
- DLC component searches now keep IGDB candidates only when they belong to the parent game's cached `expansions` or `dlcs` relationships.
- Steam component candidates must be `type=dlc` and pass the existing parent-game relationship validation.
- Providers without a component relationship/type contract no longer leak ordinary games into DLC/expansion searches.
- RomM keeps the existing component classification; Steam's generic `dlc` type is used only as provider transport metadata.

## Verification

- Focused handler test passed: `1 passed, 40 deselected`.
- Python AST syntax validation passed for implementation and test files.
- Full backend pytest remains subject to the existing container test-database wiring issue.
