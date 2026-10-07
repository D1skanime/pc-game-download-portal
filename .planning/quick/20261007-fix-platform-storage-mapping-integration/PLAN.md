---
name: fix-platform-storage-mapping-integration
created: 2026-10-07
status: in_progress
---

# Fix Platform Storage Mapping Integration

## Goal

Make the existing Phase 1-7 `PlatformStorageMapping` workflow reachable from Library Management and make manual scans consume the platform selection sent by the UI. Prevent a scan with no active mappings from being reported as a successful no-op.

## Constraints

- Reuse the existing storage root, mapping, scan command, and legacy platform models.
- Do not add a second storage model or bypass read-only root safety.
- Do not activate or change Steam behavior.
- Preserve legacy folder-mapping data and unrelated working-tree changes.

## Tasks

1. Add the existing storage administration component as a Library Management tab.
2. Pass `platform_fs_slugs` into mapping command selection and select mappings by filesystem slug for explicit scans.
3. Emit an actionable scan failure when no active mapping can execute the requested library scan instead of reporting success with `commands=[]`.
4. Add focused regression coverage and run frontend/backend checks.

## Verification

- Existing storage endpoint tests remain green.
- Scan orchestration tests prove filesystem-slug filtering and empty-mapping failure behavior.
- Frontend typecheck passes.
- Linux-only commit contains only the intentional quick-task files plus GSD state artifacts.
