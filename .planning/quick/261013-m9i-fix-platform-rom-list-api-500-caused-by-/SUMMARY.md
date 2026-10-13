---
status: complete
commit: 46ea9c4b1
---

# Summary

Fixed the platform ROM gallery API contract so requests that disable optional sidecars still return a valid page. The platform page now renders the imported ROMs and their covers again.

## Completed

- Added defaults for the optional `char_index` and `rom_id_index` response fields.
- Added the missing `genre_ids` and `theme_ids` keys to the default filter payload introduced by Phase 29.
- Added a regression test matching the frontend platform-gallery request.
- Verified the repaired platform page in the running browser. Windows rendered 27 ROMs with covers, including Baldur's Gate 3, Cyberpunk 2077, Diablo IV, Dwarf Fortress, Skyrim, Starfield, and The Witcher 3.

## Verification

- Container Python compilation passed for `backend/endpoints/roms/__init__.py`.
- `git diff --check` and Trunk pre-commit checks passed.
- Backend regression test was added but could not execute because the test fixture database at `127.0.0.1:3306` was unavailable. This is an environment limitation, not a test pass.
- Browser UAT passed after reload: platform API returned ROMs and visible cover cards instead of the loading skeleton.
- Dev stack remained reachable at `http://127.0.0.1:3100/` with HTTP 200.

## Task Commits

1. **Fix ROM list response defaults and add regression coverage** - `46ea9c4b1`

_Quick task: 261013-m9i_
