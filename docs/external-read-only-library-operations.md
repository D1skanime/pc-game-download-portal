# External Read-Only Library Operations

## Scope and Phase 9 Safety Boundary

This guide documents the tested operating model for RomM PC Library with one external library root mounted read-only. It is tied to the Phase 9 synthetic proof harness and its acceptance artifacts.

Use only synthetic or repository-controlled fixtures for Phase 9 proof. Phase 9 does not authorize Team4s changes, a real NAS mount change, host restarts, or any action against active encode workloads.

## Read-Only Mount Topology

Mount one library root read-only at `/romm/library:ro`.

The tested model uses one mount for the source archive and keeps every RomM-owned write target outside that tree. Platform mappings resolve to relative paths beneath the registered root. The UI and API present only friendly root names and server-authorized relative paths.

## Writable Separation

RomM-owned writes stay on separate writable storage.

Keep `/romm/assets`, `/romm/cache`, `/romm/config`, `/romm/database`, `/romm/resources`, and `/romm/tmp` outside the source library mount. Do not bind any writable target beneath `/romm/library`. Original files and folders stay unchanged.

## Register a Root and Browse Mappings

Register the external root once, then browse only through the authorized folder browser. Select a relative platform folder, run the bounded mapping test, and save the mapping only after the test passes.

Do not expose absolute host paths from the UI or operator workflow. Relative browsing is the only approved selection path. Traversal attempts and symlink escapes are rejected by the backend policy even when the source tree is mounted read-only.

## Scan, Preview, Stream, and Download

Scanning, preview, metadata matching, stream/play, and download operate as read-only source workflows. They may update RomM-owned database rows, cache files, resources, or temporary artifacts, but they must not create, rename, move, delete, or overwrite source content.

The tested browser and backend proof paths use nginx-backed delivery and worker-backed jobs against isolated fixtures only. Content and directory structure remain unchanged even when access time changes.

## Migration and Catalog-Only Removal

Legacy migration reconnects catalog state to existing source content without moving or rewriting files. Catalog removal and platform mapping removal detach RomM records from the source library only. Original files and folders stay unchanged.

If a mapping changes or is removed, verify the catalog outcome inside RomM and re-run the bounded proof or preview as needed. Do not treat a catalog action as permission to delete or reorganize source content.

## noatime and NAS-Equivalent Guidance

Access time can still change during ordinary reads unless `noatime` or a NAS-equivalent setting is enabled.

Use the storage vendor's documented equivalent when `noatime` is not exposed directly. Access-time controls reduce metadata churn, but they are separate from the core safety guarantee. Content and directory structure remain unchanged even when access time changes.

## Troubleshooting and Defense in Depth

Docker read-only mounting is mandatory, and the application policy must still deny mutations before filesystem access. If a workflow fails, inspect the isolated proof artifacts, service logs, and bounded error messages first.

Common checks:

- Confirm the source root is mounted exactly once at `/romm/library:ro`.
- Confirm no writable bind or volume overlaps `/romm/library`.
- Confirm RomM-owned writable targets resolve outside the source mount.
- Confirm the selected platform folder is a valid relative path beneath the registered root.
- Confirm proof artifacts were generated from isolated synthetic fixtures, not a real NAS.

## Maintenance Window Checklist

Use this checklist only for a separately authorized future deployment review:

- Confirm authorization for the maintenance window and review active workloads first.
- Confirm backups or recovery readiness for RomM-owned state before any mount or mapping change.
- Confirm the intended source root and writable targets before starting.
- Confirm the source mount is read-only and writable storage is separate.
- Confirm the latest proof artifacts, manifest diffs, and cleanup evidence before applying the same topology.
- Confirm rollback steps for mappings and writable storage changes before proceeding.
- Confirm post-window validation, including browse, scan, stream/download, and unchanged-source evidence.

Phase 9 does not authorize a real NAS mount change.

## Team4s Safeguards

Do not edit Team4s source or configuration.

Do not restart or stop Team4s services, the Team4s host, or active encode workloads.

Do not use Team4s paths, containers, mounts, or data as Phase 9 fixtures or proof inputs.

## Known Limitations

This guide covers the immutable external-library model only. It does not authorize writable external libraries, host-path disclosure, direct filesystem manipulation, or proof execution against production data.
