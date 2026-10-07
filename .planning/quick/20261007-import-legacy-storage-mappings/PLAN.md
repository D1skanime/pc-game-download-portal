---
name: import-legacy-storage-mappings
created: 2026-10-07
status: in_progress
---

# Import Legacy Storage Mappings

## Goal

Provide an idempotent administrator action that converts the configured legacy library folders into the existing canonical `StorageRoot` and `PlatformStorageMapping` records.

## Constraints

- Reuse the existing storage handler and filesystem-platform discovery.
- Register only the server-configured library root; never accept an arbitrary client host path.
- Require the existing external read-only root safety check.
- Preserve ROM files, media files, legacy configuration, and existing active mappings.
- Do not add another storage model or activate Steam.

## Tasks

1. Add a protected bootstrap endpoint using the configured library root and existing filesystem platform discovery.
2. Create missing platform rows and active mappings at `ROMS_FOLDER_NAME/<fs_slug>` while retaining existing rows.
3. Expose the bootstrap action in the existing storage administration view.
4. Make the Linux UAT game mount read-only and verify the real database rows and UI flow.

## Verification

- Live UAT creates one read-only root and mappings for all detected test platforms.
- Existing platform mapping remains `pc` filesystem slug with `win` platform slug.
- Frontend typecheck and backend syntax checks pass.
- No ROM or media files are modified.
