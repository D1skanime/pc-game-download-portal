# Architecture Patterns: RomM PC Library Milestone 1

**Domain:** Immutable NAS-backed library
**Researched:** 2026-08-04
**Confidence:** HIGH for current architecture, MEDIUM for deployed legacy layouts

## Recommended Architecture

Keep the modular monolith, but place a storage-domain boundary between every library consumer and filesystem I/O.

```text
v2 UI -> FastAPI endpoints/sockets -> application handlers
                                  -> mapping/audit repositories
                                  -> scan orchestrator
                                            |
                                  LibraryPathResolver
                         normalize -> canonicalize -> contain
                                            |
                                  StorageOperationPolicy
                                            |
                              read-only source adapter

DB, resources, assets, cache, temp, configuration and logs remain separately writable.
```

Milestone 1 adds no PC component model. `Rom` stays the logical game, `RomFile` stays the physical file, and `Platform.fs_slug` remains metadata/compatibility identity. A new mapping chooses the scanned directory.

## Component Boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| Storage root | Approved container mount, immutable mode, health | Host path in mappings, writable toggle |
| Platform mapping | One normalized relative directory per platform, lifecycle, audit | Directory creation, metadata alias binding |
| Path resolver | Cross-platform parsing, canonical containment, typed resolved path | User authorization or mutation |
| Storage policy | Typed operation allow/deny by root mode | Path construction or OS-error handling |
| Scanner | Read discovery/hash, metadata, catalog reconciliation | Source organization or mutation |
| Catalog service | Database-only removal/missing state | Source deletion |
| Owned storage | Resources, assets, cache, temp, saves, logs | Files beside source games |
| v2 UI | Root status, browser, mapping/test/preview/history | Absolute paths or source mutations |

Put resolver/policy in a focused backend storage package. Scans, workers, watchers, hashers, streaming, downloads and nginx redirects must use it.

## Models

Create `storage_roots`: `id`, unique `name`, server-controlled `mount_path`, mode constrained to `external_read_only`, `enabled`, timestamps. Seed one root, normally `/romm/library`. Do not expose arbitrary host-path configuration or a writable mode.

Create `platform_storage_mappings`: `id`, unique non-null `platform_id` FK, `storage_root_id` FK, normalized POSIX-style `relative_path`, timestamps. Uniqueness on `(storage_root_id, relative_path)`; reject ancestor/descendant overlap in application logic. Do not replace `Platform.fs_slug`.

Create append-only `platform_storage_mapping_audits`: platform/root ids, nullable actor FK with `ON DELETE SET NULL`, action (`created|updated|removed`), JSON old/new normalized snapshots, `created_at`. Mapping mutation and audit insert share one transaction. Never store host paths. Mapping removal never cascades to Platform, Rom, RomFile or source.

## Migration Sequence

1. Add tables/indexes/constraints without scanner changes.
2. Seed the external root without filesystem I/O.
3. Bridge legacy layouts read-only. If exactly one of `roms/{fs_slug}` or `{fs_slug}/roms` exists safely, propose/create a mapping. Both/neither, overlap or symlink escape requires admin resolution.
4. Prefer mappings; temporarily allow warning-emitting legacy fallback for unmapped platforms. Never bootstrap `roms`.
5. Require mapping coverage, then disable fallback.
6. Retire external calls to `create_library_structure`, `add_platform`, and `FSHandler.__init__` base-path mkdir.
7. Remove the bridge only after legacy upgrade tests.

Alembic upgrade/downgrade must work on MariaDB/MySQL and PostgreSQL and never touch source. Keep migration separate from v1 deletion.

## Canonical Paths and Symlink Containment

Current `FSHandler.validate_path()` is unsafe for this contract because a symlink switches it to lexical validation, permitting escape. Its constructor also mutates the base directory.

Only the resolver creates `ResolvedLibraryPath(root_id, relative_path, absolute_path)`. Reject NUL/control characters, POSIX absolute paths, Windows drive/device paths, UNC paths, all `..` segments and excessive lengths on every OS. Normalize separators to `/`, remove `.`, preserve case and persist only relative text.

Every browse, preview, scan, hash, stream and download must:

1. Load enabled root/mapping by database identity.
2. Strictly canonicalize the approved root.
3. Join only stored normalized paths and server-derived descendants.
4. Canonicalize the target following links.
5. Require target equals root or is relative to canonical root.
6. Never recurse through directory symlinks; reject any link escaping root. Rejecting all directory-link traversal is recommended.
7. Return the typed capability, never a client path.
8. Recheck immediately before read-only open; where practical compare opened descriptor stat data to reduce check/use races.

Folder browsing returns relative names/type/readability/rejection state, never absolute paths, and bounds/paginates children.

## Central Storage Policy

Allowed for `external_read_only`: `LIST, STAT, OPEN_READ, HASH, STREAM, DOWNLOAD`.

Denied: `CREATE_FILE, UPLOAD, WRITE, OVERWRITE, RENAME, MOVE, COPY, DELETE_FILE, DELETE_DIRECTORY, CREATE_DIRECTORY, EXTRACT, PATCH`.

Deny with a domain error before I/O; HTTP maps it to stable 403 and workers to stable failed/skipped results. Audit every FSHandler mutation and direct Path/AnyioPath/os/shutil/archive/upload/patch call. Enforce at application command and low-level adapter boundaries. Docker `:ro` is final defense, not application authorization.

All generated/cached/transformed output stays in RomM-owned storage.

## Scanner Data Flow

```text
save mapping -> normalize -> contain/conflict/readability checks
             -> transaction(mapping + audit)

preview -> resolve -> shared bounded enumeration -> delta/warnings
        -> no DB, queue, cache, resource or audit writes

scan -> resolve mapping -> enumerate -> read-only hash -> enrich
     -> reconcile Rom/RomFile DB rows -> owned resource writes -> socket progress
```

Replace `get_roms_fs_structure(fs_slug)` with mapping-aware resolution and pass a resolved scan source into enumeration. Separate metadata platform identity from source mapping. Preview and scan share enumeration. Missing/catalog reconciliation never implies source deletion.

## APIs

| Route | Purpose | Safety contract |
| --- | --- | --- |
| `GET /api/storage-roots` | Root health | No host-path disclosure |
| `GET /api/storage-roots/{id}/folders` | Browse | Relative, bounded, canonical |
| `POST /api/storage-roots/{id}/validate-path` | Test | Non-mutating diagnostics |
| `GET/PUT/DELETE /api/platforms/{id}/storage-mapping` | Mapping lifecycle | Transactional audit; delete DB-only |
| `POST /api/platforms/{id}/scan-preview` | Preview delta | No persistence/jobs |
| `GET /api/storage-mapping-audits` | History | Admin-only, append-only |
| explicit catalog removal route or revised ROM delete | Remove entry | Owned state only |

Use protected routes, admin/platform-write scopes, CSRF and visibility masking. Pydantic/OpenAPI stays authoritative. Content routes resolve RomFile by DB id, derive root/mapping, invoke resolver, then serve verified targets. Nginx aliases cannot expose a broader tree. No content API accepts paths/names. UI capabilities are advisory; backend policy is authoritative.

## V2 Integration

Add to `Settings/LibraryManagement.vue` using v2 primitives/tokens/i18n and universal input:

- immutable root health card;
- mapping table with relative folder/status/last scan;
- relative-breadcrumb browser;
- mapping validation/conflict panel;
- preview split into additions/changes/missing/skipped/warnings;
- audit history;
- explicit `Remove from catalog`, never `Delete files`.

Existing `FolderMappingsSection` manages metadata alias/version config. Do not overload it with storage mappings.

## V1 Removal Sequence

1. Prove v2 parity for every route, including auth/setup/pair/player/errors/settings.
2. Move genuinely shared dependencies to neutral locations; preserve services, stores, generated types, plugins, locales/assets.
3. Replace named-view injection with one v2 route/layout, then remove fallback/passthrough/dispatch compatibility.
4. Make `RomM.vue` always render/scope v2; remove `useUiVersion`, persisted toggle and duplicate conditional components.
5. Delete frozen v1 trees only after import-reachability checks.
6. Remove v1-only styles/dependencies/tests/locales/assets; run typecheck, unit, Storybook, E2E and build.

Do not combine this work with storage migration/policy rollout.

## Audit and Test Seams

| Seam | Evidence |
| --- | --- |
| Parser/resolver | Absolute/traversal rejection on all path dialects; containment, nonexistent targets, links at every segment, race-aware reopen |
| Policy/inventory | Full operation matrix; denial before mocked I/O; every write call site covered |
| Mapping/audit | Uniqueness, overlap, concurrency, rollback, actors/snapshots, auth, cross-dialect |
| Browser/preview | Bounded relative output, unreadable/hidden entries, same candidates as scan, zero side effects |
| Scanner/content | Mapping precedence, read-only hashes, no link loops, DB-id downloads, nginx containment, Range regression |
| Catalog removal | Owned state changed while source bytes/metadata remain identical |
| Container | `:ro` fixture, no startup mkdir, mutation endpoints return 403 rather than 500 |
| Migration | Fresh, both legacy shapes, ambiguity, downgrade, MariaDB/PostgreSQL |
| UI/removal | Stories, themes, responsive/input/accessibility, route matrix, no stale imports/toggle, full frontend gates |

Use fixtures with flat/nested games, spaces/Unicode, unreadable entries, link loops, in-root links and escapes. Assert errors and absence of side effects. `EROFS` alone is not proof. Before/after evidence should cover names, types, sizes, hashes, modes and mtimes; only assert atime where `noatime` is guaranteed.

## Anti-Patterns

- Extending current validate_path without separating immutable from owned-writable semantics.
- Treating fs_slug as the storage mapping.
- Catching EROFS as authorization.
- Hiding controls while APIs/workers remain mutable.
- Accepting lexical symlink containment.
- Cascading mapping removal to catalog/source.
- Separate preview enumeration.
- Adding PC component/manifest models before this boundary is proven.

## Recommended Phase Order

1. Models/migration, typed resolver/policy and unit tests.
2. Read-only adapters, mutation inventory/gating, owned-storage separation, container tests.
3. Mapping CRUD/audit, browser/validation, compatibility bridge, generated contracts.
4. Shared preview/scanner cutover, catalog removal and content integration.
5. V2 administration workflow, stories/accessibility/E2E.
6. V1 router/toggle/compatibility removal and frozen-tree deletion.
7. Deployment docs and immutability proof, including one `:ro` mount and `noatime` guidance.

## Sources

- `CLAUDE.md`, `.planning/PROJECT.md`
- `.planning/codebase/{ARCHITECTURE,STRUCTURE,TESTING,CONCERNS,CONVENTIONS}.md`
- `docs/PC_GAME_COMPONENTS_AND_MANIFEST_DOWNLOADS_ANALYSIS.md`
- `backend/handler/filesystem/{base_handler,platforms_handler,roms_handler}.py`
- `backend/models/platform.py`, `backend/handler/scan_handler.py`, `backend/endpoints/platform.py`
- `frontend/src/RomM.vue`, `frontend/src/plugins/router.ts`, `frontend/src/v2/router/routes.ts`, v2 Library Management
- Alembic revisions, backend tests and database CI workflows

All cited repository sources are HIGH confidence. Open design questions are whether in-root leaf symlinks are allowed, whether mapping overlaps can ever be valid, exact config-binding bridge behavior, catalog-delete compatibility, and nginx alias containment.