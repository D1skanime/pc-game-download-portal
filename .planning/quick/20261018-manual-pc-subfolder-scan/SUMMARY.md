# Summary

Implemented the manual PC subfolder correction flow for directory-backed Windows scan results.

## Delivered

- Added a folder inspection action to Windows directory rows, including rows with an existing metadata match.
- Added a storage-backed dialog that lists child directories below the mapped game folder.
- Added scoped scan translation carrying the selected relative path through the socket payload.
- Added backend path composition through the immutable storage mapping and disabled missing-ROM reconciliation for scoped scans.
- Added a regression test for selected filesystem subfolder translation.

## Verification

- Backend Python compilation: passed.
- Focused frontend tests: 16 passed.
- Frontend production build: passed; existing dependency/style warnings remain.
- Full frontend typecheck: still reports the two pre-existing errors in `MatchRom/types.test.ts` and `Settings/pgdpFolderMappings.ts`.
- Browser smoke attempt: the UI scan request was sent, but the current dev data has an existing `storage root:0` / missing `roms` target error, so no live result row was available for clicking.
