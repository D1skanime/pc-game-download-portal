# RomM PC Library

## What This Is

RomM PC Library is a v2-only fork of RomM for people who already maintain game collections on a NAS. It indexes an existing directory tree through one immutable library root, lets administrators map platforms to existing relative subdirectories, and keeps every RomM-owned database record, asset, cache, and temporary file outside the original collection.

The first milestone delivers only the secure NAS integration and removes the legacy v1 frontend. PC component modeling, manifest downloads, and a Windows downloader belong to later milestones.

## Core Value

RomM adapts to an existing game archive without requiring or permitting any change to the archive's files, directories, or organization.

## Requirements

### Validated

- RomM represents a logical game as one `Rom` with one or more physical `RomFile` records and can scan top-level files or directories recursively. Existing upstream capability.
- RomM provides authenticated library browsing, metadata enrichment, streaming, downloading, collections, user state, and browser players through FastAPI and Vue. Existing upstream capability.
- RomM supports MariaDB, MySQL, and PostgreSQL, Redis-backed jobs and sessions, OpenAPI-generated frontend contracts, and container deployment. Existing upstream capability.
- The current branch contains the active UI v2 implementation under `frontend/src/v2/`, including the main library, scan, player, administration, and settings surfaces. Existing upstream capability.
- Phase 2 validated the deny-by-default external storage policy, pre-I/O mutation denials, trusted descriptor boundary, closed filesystem seam inventory, read-only mount parity, and separation of RomM-owned writable output. Validated in Phase 2: Read-only Policy Boundary.

### Active

- [ ] Mount one existing NAS games root read-only and never require per-platform Docker mounts or a RomM-owned physical folder layout.
- [ ] Model external storage roots as permanently `external_read_only`, with no writable-library toggle in the first milestone.
- [ ] Map each platform to at most one active relative subdirectory inside an approved storage root without storing host or absolute container paths in platform mappings.
- [ ] Provide a safe v2 administrator folder browser, mapping test, and non-mutating scan preview inside an approved root.
- [ ] Resolve all library paths centrally with canonical containment checks, traversal rejection, and symlink escape protection.
- [ ] Make scanning, hashing, streaming, and downloading read-only operations that write results only to RomM-owned database or storage locations.
- [ ] Enforce a central backend storage policy that rejects create, upload, write, overwrite, rename, move, copy, delete, extract, patch, and directory creation for external roots.
- [ ] Separate catalog removal from source deletion so removing a game or mapping never changes original files or directories.
- [ ] Migrate or safely bridge existing RomM platform layouts without moving, renaming, or creating library content.
- [ ] Record platform mapping creation, changes, and removal with actor, timestamp, old mapping, and new mapping.
- [ ] Remove the frozen v1 frontend, its UI-version toggle, named-view fallback, and v1-only compatibility paths so the fork has one v2 interface.
- [ ] Derive a RomM v2 UI specification from a read-only review of Team4s design principles, then apply it to the new storage-root, folder-browser, and platform-mapping surfaces without copying React components.
- [ ] Prove source immutability with unit, API, integration, container-mount, traversal, symlink, and before/after filesystem evidence tests.
- [ ] Document deployment mounts, storage roots, mappings, migration, security behavior, troubleshooting, and `noatime` guidance.

### Out of Scope

- PC base-game, update, DLC, hotfix, and extras components. Deferred until the read-only storage boundary is verified.
- Component or game manifests and immutable file revisions. Deferred to a later milestone.
- Resumable download orchestration and a Windows downloader. Deferred to a later milestone.
- Writable external libraries, file organization, rename, move, delete, extraction, upload, or patch operations. These conflict with the archive-safety boundary.
- Automatic import into the original archive. A future import area, if built, must be separate from the immutable library.
- Dynamic ZIP redesign and installation planning. They are unrelated to the first milestone.
- A complete visual redesign of every existing RomM v2 surface. Phase 1 establishes the direction on its new administration workflows; broader redesign is a later milestone.

## Context

The existing collection already lives under a long-maintained NAS root such as `/volume1/Mediathek/Games`, with directories including `Nintendo Switch`, `PlayStation 2`, `SNES Super Nintendo`, `GB GameBoy`, and `PC`. Users must mount this root once as `/romm/library:ro` and select those existing directories inside RomM.

Upstream RomM currently derives platform content from a fixed library convention and contains mutating workflows for uploads, manuals, extraction, patching, deletion, rename, and directory creation. The fork must inventory and gate every such path rather than relying only on hidden UI controls or filesystem errors.

The canonical repository is `/home/d1sk/romm` on `team4s-linux`. The Windows directory is a control and reference workspace only. Team4s services and the active encode workload must not be changed or restarted. Docker already stores its data on the separate 80 GB filesystem mounted at `/var/lib/docker`.

The codebase is a brownfield modular monolith: Python 3.13, FastAPI, SQLAlchemy, Alembic, MariaDB/MySQL/PostgreSQL, Redis/RQ, Vue 3, TypeScript, Vuetify, Pinia, and generated OpenAPI types. The v2 frontend is present and is currently the default, while v1 remains as a frozen compatibility surface scheduled for removal.

## Constraints

- **Archive safety**: The external games root is always mounted `:ro`; application authorization must independently reject every mutation before filesystem access.
- **Path safety**: Mappings store only normalized relative paths. Absolute Linux paths, drive paths, UNC paths, parent traversal, and symlink escapes are rejected after canonical resolution.
- **Storage separation**: Database, resources, assets, configuration, cache, hashes, scan state, temporary files, and audit records stay outside the external library.
- **No source restructuring**: Mapping, scanning, metadata matching, catalog removal, and migration never copy, move, rename, delete, or create source content.
- **Frontend**: The fork ships only UI v2. v1 removal must preserve shared services, stores, generated types, and router behavior required by v2.
- **Design reference**: Team4s is inspected read-only for hierarchy, spacing, typography, navigation, cards, and state presentation. RomM implements derived patterns in its own Vue v2 design system.
- **Compatibility**: Backend schema and migrations remain portable across MariaDB, MySQL, and PostgreSQL.
- **API contract**: Backend OpenAPI schemas remain authoritative and generated frontend types are regenerated when contracts change.
- **Operations**: No Team4s host restart or unrelated service interruption. The real NAS mount is configured only when the active encode phase permits it.
- **Quality**: New logic requires tests, v2 UI requires stories where applicable, and completion requires the repository's pre-PR verification gates.
- **Language**: Code, comments, identifiers, documentation, commits, and PR text are written in English.

## Key Decisions

| Decision                                                              | Rationale                                                                                                                     | Outcome |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------- |
| Name the fork RomM PC Library and repository `romm-pc-library`        | The name covers NAS-first storage, later PC components, and download workflows without implying a separate unrelated product  | Pending |
| Make the first milestone only the secure NAS integration              | The storage boundary must be proven before PC components or transfer protocols depend on it                                   | Pending |
| Mount one NAS games root and map platforms to relative subdirectories | Existing collections already have useful, user-owned organization and must not be restructured for RomM                       | Pending |
| Support only `external_read_only` for external roots                  | A writable toggle creates an unacceptable risk to the original archive                                                        | Pending |
| Enforce read-only behavior in Docker and a central backend policy     | Defense in depth protects the archive even when UI or endpoint code is bypassed                                               | Pending |
| Store no generated RomM data beside source games                      | Original directories remain clean and immutable                                                                               | Pending |
| Treat removal as catalog-only                                         | Users can correct the RomM index without risking source deletion                                                              | Pending |
| Build and retain only UI v2                                           | The user does not need v1, and maintaining two interfaces would duplicate work and preserve a frozen compatibility surface    | Pending |
| Remove v1 as a bounded milestone workstream                           | Deletion must be verified separately so storage safety work is not obscured by frontend cleanup                               | Pending |
| Use Team4s as a read-only design reference for new v2 surfaces        | RomM v2 needs a less administrative visual character, while its Vue architecture and product identity must remain independent | Pending |
| Defer a complete v2 visual redesign                                   | The first milestone applies the direction to new storage workflows without expanding into every existing screen               | Pending |
| Defer PC components, manifests, and Windows downloads                 | They depend on a stable storage-root and immutable-file contract                                                              | Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**

1. Move validated requirements to Validated with a phase reference.
2. Move invalidated requirements to Out of Scope with a reason.
3. Add requirements or decisions discovered during implementation.
4. Recheck that the project description and core value remain accurate.

**After each milestone:**

1. Review every section against the implemented system.
2. Reconfirm that archive immutability remains the primary value.
3. Audit deferred and excluded work before starting the next milestone.
4. Update the current technical and operational context.

---

_Last updated: 2026-08-10 after Phase 2 completion_
