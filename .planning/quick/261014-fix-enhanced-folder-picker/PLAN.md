---
name: fix-enhanced-folder-picker
status: planned
---

# Fix enhanced folder picker feedback

## Goal

Make enhanced folder downloads fail visibly and diagnostically when the browser cannot return a writable directory handle, instead of silently skipping manifest creation.

## Tasks

1. Make missing directory-picker support an explicit queue error and map picker cancellation/access failures to the existing localized folder-access message.
2. Add regression coverage for unsupported picker and cancelled picker paths.
3. Run focused frontend tests, typecheck, and production build; update GSD state and commit atomically.

## Verification

- Enhanced picker failures show a localized folder-access message.
- Standard downloads still create manifests and transfers.
- Frontend tests, typecheck, and build pass.
