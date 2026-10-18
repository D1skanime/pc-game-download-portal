---
name: manual-pc-subfolder-scan
status: complete
created: 2026-10-18
---

# Manual PC subfolder scan

Add a correction flow to the v2 scan result for directory-backed Windows entries. The action must be available even when metadata matched, because a container folder such as `Tales of War` can receive a formally valid but structurally wrong match. The user can inspect child directories, select one, and scan only that subtree without rescanning the full library or creating a duplicate container entry.

## Acceptance criteria

- Windows scan rows expose an "inspect folder" action with the source-relative path.
- The action browses only the mapped read-only storage root and rejects unsafe paths.
- Selecting a child directory starts a scoped scan for that subtree.
- The scoped scan preserves the parent path, skips the selected container as a game, and does not mark unrelated ROMs missing.
- Existing ROMs are not duplicated when the selected child was already scanned.
- User-visible text is localized in every locale.
- Tests cover path validation, scoped scan translation, and the scan-row interaction.

## Verification

- Affected backend tests and frontend tests.
- Frontend typecheck and locale checks.
- Browser test with `Tales of War` or equivalent nested PC fixture.
