# Quick Task: Steam manual match media

## Goal

Manual PC metadata matching must show Steam candidate artwork instead of placeholder cards when only Steam is selected.

## Scope

- Hydrate Steam name-search results with the existing detailed Steam metadata path.
- Preserve provider filtering and existing language/fallback behavior.
- Add a regression test at the Steam handler boundary.
- Do not change scan, storage mapping, or legacy ROM behavior.

## Verification

- Regression test proves search candidates include cover and screenshots.
- Existing focused PC metadata tests pass.
