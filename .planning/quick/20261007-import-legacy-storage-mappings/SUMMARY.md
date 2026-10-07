---
name: import-legacy-storage-mappings
status: complete
completed: 2026-10-07
---

# Quick Task Summary

## Delivered

- Added an admin-only `/storage/legacy/bootstrap` action that uses the trusted configured library root, existing filesystem-platform discovery, `DBStorageHandler.register_root`, `DBPlatformsHandler`, and `DBStorageHandler.create_mapping`.
- Made the action idempotent: existing roots, platforms, and active mappings are retained.
- Exposed the import action in the existing Storage administration view.
- Mounted the UAT game library read-only in `docker-compose.yml`, preserving the external-file deletion boundary.

## Live UAT evidence

- `/home/d1sk/romm/Games` is mounted at `/app/romm/library` as read-only.
- The import created one active root named `Legacy ROM library`.
- The database contains seven detected platforms and seven active mappings, including `fs_slug=pc`, platform slug `win`, and relative path `roms/pc`.
- No ROM, media, or legacy configuration files were modified.

## Verification

- Backend endpoint files pass AST parsing.
- Frontend `vue-tsc --noEmit` completed in the Linux Compose container without reported errors.
- The running Compose services are healthy after restart.
