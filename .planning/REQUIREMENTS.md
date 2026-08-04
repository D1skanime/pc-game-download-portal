# Requirements: RomM PC Library

**Defined:** 2026-08-04
**Core Value:** RomM adapts to an existing game archive without requiring or permitting any change to the archive's files, directories, or organization.

## v1 Requirements

### External Storage Roots

- [ ] **ROOT-01**: An operator can mount one existing NAS games root at a deployment-configured container path and register it as an active storage root.
- [ ] **ROOT-02**: Every external storage root has the immutable mode `external_read_only`; milestone 1 exposes no writable-library mode or toggle.
- [ ] **ROOT-03**: The application reports whether an external root is reachable, readable, non-writable, and when it was last checked, without creating anything below it.
- [ ] **ROOT-04**: Database records store the deployment-owned container root separately from platform mappings and never store NAS host paths in mappings.
- [ ] **ROOT-05**: Database, resources, assets, configuration, cache, hashes, scan state, temporary files, and audit records use writable locations outside the external root.

### Safe Path Resolution

- [ ] **PATH-01**: A central resolver accepts only normalized relative paths and rejects absolute Linux paths, Windows drive paths, UNC paths, empty invalid segments, and parent traversal.
- [ ] **PATH-02**: The resolver canonicalizes root and target and proves the target remains inside the selected root after symlink resolution.
- [ ] **PATH-03**: Platform mappings accept existing readable directories only and reject files, missing targets, disabled roots, and escaped symlinks.
- [ ] **PATH-04**: The resolver handles spaces, dots, hyphens, umlauts, Unicode, long names, and nested directories without unsafe string-prefix containment checks.
- [ ] **PATH-05**: Milestone 1 rejects symlinks by default unless a narrower in-root behavior is explicitly proven safe by tests.

### Platform Storage Mappings

- [ ] **MAP-01**: An administrator can assign a platform to an existing relative subdirectory of an active storage root.
- [ ] **MAP-02**: A platform has at most one active mapping in milestone 1, while the schema permits multiple storage roots for future use.
- [ ] **MAP-03**: Creating, changing, testing, or removing a mapping performs no source filesystem mutation.
- [ ] **MAP-04**: Multiple platforms can map to distinct directories below the same external root.
- [ ] **MAP-05**: Unsafe overlapping mappings are rejected unless a future explicit policy allows them.
- [ ] **MAP-06**: A missing mapping produces a clear operator-facing error and never falls back silently to an unrelated directory.

### Central Read-only Policy

- [ ] **SAFE-01**: A central server-side storage policy permits only list, read, scan, stat, hash, stream, and download operations on `external_read_only` roots.
- [ ] **SAFE-02**: The policy rejects create, upload, write, overwrite, rename, move, copy, delete, extract, patch, and directory creation before filesystem access.
- [ ] **SAFE-03**: Direct API calls receive `403 Forbidden` for prohibited operations even when the UI does not expose the action.
- [ ] **SAFE-04**: All existing filesystem mutation paths are inventoried and routed through the central policy or proven unable to address external roots.
- [ ] **SAFE-05**: Docker examples and integration tests mount the external library with `:ro`; application policy remains mandatory rather than relying on mount errors.
- [ ] **SAFE-06**: Reading, scanning, hashing, streaming, and downloading create no temporary, metadata, cover, sidecar, cache, or lock files inside the external root.

### Scanner, Watcher, and Preview

- [ ] **SCAN-01**: Scanner jobs resolve a platform through its active storage mapping instead of deriving `library/roms/<platform>`.
- [ ] **SCAN-02**: The scanner only reads source metadata and bytes and persists discoveries to RomM-owned database and storage locations.
- [ ] **SCAN-03**: Watcher events resolve safely through storage mappings and cannot escape or mutate an external root.
- [ ] **SCAN-04**: An administrator can preview a mapping's reachability, readability, non-writability, bounded file and directory counts, and estimated size without creating catalog records.
- [ ] **SCAN-05**: Large-directory preview work is bounded or asynchronous and communicates partial or pending results clearly.
- [ ] **SCAN-06**: Queued scan work retains or validates its mapping identity so a concurrent mapping change cannot redirect it silently.

### Catalog and Lifecycle Semantics

- [ ] **CAT-01**: The product distinguishes `Remove from catalog` from source-file deletion in API contracts and UI language.
- [ ] **CAT-02**: Removing a game from the catalog deletes only explicitly defined RomM-owned records and assets and preserves every source file and directory.
- [ ] **CAT-03**: Removing a platform mapping deletes only configuration and audit state required by policy and does not implicitly delete indexed games or source content.
- [ ] **CAT-04**: Source-file delete, rename, move, upload, extraction, and patch actions do not exist for external roots in the v2 UI and remain blocked server-side.

### Administration API and Audit

- [ ] **API-01**: Authorized administrators can list storage roots and inspect their safe status through the established FastAPI and OpenAPI conventions.
- [ ] **API-02**: Authorized administrators can list directories inside a root using relative paths only, with containment and permission checks on every request.
- [ ] **API-03**: Authorized administrators can read, create, change, test, preview, and remove platform mappings through typed endpoints.
- [ ] **API-04**: Non-administrators cannot mutate roots or mappings, and unauthenticated callers cannot enumerate library structure.
- [ ] **AUD-01**: Mapping creation, change, and removal records actor, timestamp, platform, action, and old/new root and relative path values.
- [ ] **AUD-02**: Audit output never exposes NAS host paths or unrelated filesystem paths.

### V2 Administration Experience

- [ ] **UI-01**: The v2 administration UI displays storage-root name, container path, immutable mode, active state, reachability, readability, non-writability, last check, and safe errors.
- [ ] **UI-02**: A v2 folder browser lists and navigates directories only inside the chosen root and supports safe selection of Unicode and nested paths.
- [ ] **UI-03**: The v2 platform workflow lets administrators select a root and directory, test it, preview a scan, save it, and remove the mapping.
- [ ] **UI-04**: The UI clearly states that RomM reads and indexes the external library but never changes its original files.
- [ ] **UI-05**: New storage workflows follow a RomM-native v2 design specification derived from read-only analysis of Team4s hierarchy, spacing, typography, navigation, cards, and state presentation.
- [ ] **UI-06**: Loading, empty, error, forbidden, unreachable, and pending-preview states remain accessible and usable with mouse, touch, keyboard, and gamepad.

### V1 Removal

- [ ] **V2-01**: The fork has one frontend mode and boots directly into UI v2 without a `uiVersion` preference or v1/v2 switch.
- [ ] **V2-02**: Frozen v1 views, components, layouts, console surfaces, banners, fallbacks, and v1-only routing are removed.
- [ ] **V2-03**: Pairing, authentication, theme, router, shared stores, API services, generated types, and overlays required by v2 continue to work after v1 removal.
- [ ] **V2-04**: Every supported route either has a real v2 view or is deliberately removed; no `NotReady` fallback sends users to v1.
- [ ] **V2-05**: The v1 removal is isolated and regression-tested separately from storage-domain changes.

### Legacy Migration and Compatibility

- [ ] **MIG-01**: A migration can represent existing RomM platform layouts as storage roots and relative mappings without moving, renaming, copying, or creating library content.
- [ ] **MIG-02**: Migration behavior is portable across MariaDB, MySQL, and PostgreSQL and is reversible at the database-schema level where practical.
- [ ] **MIG-03**: If an existing layout cannot be migrated safely, startup or administration reports a clear manual mapping requirement instead of guessing.
- [ ] **MIG-04**: Existing mapped platforms remain scanable after restart and mapping records survive normal deployment lifecycle operations.
- [ ] **MIG-05**: Any legacy fallback is explicit, observable, time-bounded, and unable to bypass the external-root policy.

### Verification and Documentation

- [ ] **TEST-01**: Unit tests cover valid, Unicode, nested, empty, traversal, absolute, drive, UNC, missing, file-target, disabled-root, and symlink path cases.
- [ ] **TEST-02**: API tests cover root listing, directory browsing, mapping lifecycle, authorization, traversal, mapping tests, and scan preview.
- [ ] **TEST-03**: Mutation tests prove delete, rename, move, overwrite, upload, directory creation, extraction, patching, sidecar writing, cover writing, and symlink escape fail for external roots.
- [ ] **TEST-04**: Integration tests prove read-only mounting, scanning, streaming, downloading, multiple mappings, mapping changes, restart persistence, and legacy migration.
- [ ] **TEST-05**: Before/after evidence proves source content, names, structure, sizes, hashes, and non-access timestamps remain unchanged across scan, metadata matching, mapping changes, catalog removal, download, and hashing.
- [ ] **TEST-06**: Production-like nginx and worker paths enforce the same authorized database-identity and storage-root boundary as development paths.
- [ ] **DOC-01**: Documentation explains the one-root `:ro` Docker mount, separate writable storage, mappings, folder browser, migration, and catalog-only removal.
- [ ] **DOC-02**: Documentation explains the defense-in-depth policy, symlink/traversal behavior, troubleshooting, known limitations, and `noatime` or NAS-specific access-time guidance.
- [ ] **DOC-03**: Operational instructions require a safe maintenance window for real NAS mount changes and prohibit changes or restarts to Team4s during active encode work.

## v2 Requirements

### PC Components

- **COMP-01**: A logical PC game can expose base game, update, DLC, hotfix, language, and extras components without changing its source tree.
- **COMP-02**: Component identity and metadata remain separate from broad `RomFile` categories.

### Manifest Downloads

- **MANI-01**: Clients can obtain immutable versioned manifests with safe relative paths, sizes, and strong file digests.
- **MANI-02**: Clients can resume authenticated per-file downloads and verify final integrity.

### Desktop Client

- **CLNT-01**: A Windows client can select components, download them safely, and reconstruct the existing relative tree under a user-selected install root.

### Broader Visual Redesign

- **UX-01**: Existing RomM v2 surfaces beyond the new storage workflows adopt the approved visual direction in a dedicated milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Writable external game libraries | Conflicts with the immutable archive boundary |
| Automatic source organization | Existing NAS structure remains user-owned |
| Original-file deletion from RomM | Unacceptable archive risk |
| Per-platform Docker mounts | One shared games root plus database mappings is the product model |
| Host-path entry in the normal UI | Deployment owns absolute container roots; UI stores relative mappings only |
| PC components in milestone 1 | Depends on the verified storage boundary |
| Manifest downloads and resume in milestone 1 | Depends on stable immutable file identity |
| Windows downloader in milestone 1 | Depends on component and manifest contracts |
| Full v2 visual redesign in milestone 1 | New storage surfaces establish direction; broader redesign is deferred |
| Copying Team4s React components | Team4s is a design reference, not a code or runtime dependency |

## Traceability

Roadmap creation populates this table. Every v1 requirement must map to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROOT-01 | Phase 1 | Pending |
| ROOT-02 | Phase 1 | Pending |
| ROOT-03 | Phase 1 | Pending |
| ROOT-04 | Phase 1 | Pending |
| ROOT-05 | Phase 2 | Pending |
| PATH-01 | Phase 1 | Pending |
| PATH-02 | Phase 1 | Pending |
| PATH-03 | Phase 1 | Pending |
| PATH-04 | Phase 1 | Pending |
| PATH-05 | Phase 1 | Pending |
| MAP-01 | Phase 3 | Pending |
| MAP-02 | Phase 3 | Pending |
| MAP-03 | Phase 3 | Pending |
| MAP-04 | Phase 3 | Pending |
| MAP-05 | Phase 3 | Pending |
| MAP-06 | Phase 3 | Pending |
| SAFE-01 | Phase 2 | Pending |
| SAFE-02 | Phase 2 | Pending |
| SAFE-03 | Phase 2 | Pending |
| SAFE-04 | Phase 2 | Pending |
| SAFE-05 | Phase 2 | Pending |
| SAFE-06 | Phase 2 | Pending |
| SCAN-01 | Phase 5 | Pending |
| SCAN-02 | Phase 5 | Pending |
| SCAN-03 | Phase 5 | Pending |
| SCAN-04 | Phase 5 | Pending |
| SCAN-05 | Phase 5 | Pending |
| SCAN-06 | Phase 5 | Pending |
| CAT-01 | Phase 6 | Pending |
| CAT-02 | Phase 6 | Pending |
| CAT-03 | Phase 6 | Pending |
| CAT-04 | Phase 6 | Pending |
| API-01 | Phase 3 | Pending |
| API-02 | Phase 3 | Pending |
| API-03 | Phase 3 | Pending |
| API-04 | Phase 3 | Pending |
| AUD-01 | Phase 3 | Pending |
| AUD-02 | Phase 3 | Pending |
| UI-01 | Phase 7 | Pending |
| UI-02 | Phase 7 | Pending |
| UI-03 | Phase 7 | Pending |
| UI-04 | Phase 7 | Pending |
| UI-05 | Phase 4 | Pending |
| UI-06 | Phase 7 | Pending |
| V2-01 | Phase 8 | Pending |
| V2-02 | Phase 8 | Pending |
| V2-03 | Phase 8 | Pending |
| V2-04 | Phase 8 | Pending |
| V2-05 | Phase 8 | Pending |
| MIG-01 | Phase 6 | Pending |
| MIG-02 | Phase 6 | Pending |
| MIG-03 | Phase 6 | Pending |
| MIG-04 | Phase 6 | Pending |
| MIG-05 | Phase 6 | Pending |
| TEST-01 | Phase 1 | Pending |
| TEST-02 | Phase 3 | Pending |
| TEST-03 | Phase 2 | Pending |
| TEST-04 | Phase 9 | Pending |
| TEST-05 | Phase 9 | Pending |
| TEST-06 | Phase 9 | Pending |
| DOC-01 | Phase 9 | Pending |
| DOC-02 | Phase 9 | Pending |
| DOC-03 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 63 total
- Mapped to phases: 63
- Unmapped: 0

---
*Requirements defined: 2026-08-04*
*Last updated: 2026-08-04 after initial definition*
