<!-- refreshed: 2026-10-15 -->

# Architecture

**Analysis Date:** 2026-10-15 (original mapping: 2026-08-04)

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                  Browser application                          │
│  Vue 3 v1 named view       Vue 3 v2 named view                │
│  `frontend/src/views/`     `frontend/src/v2/`                 │
└─────────────────────────────────┬───────────────────────────┘
                                 │ `/api/*`, `/ws`, `/netplay`
                                 ▼
┌────────────────────────────────────────────────────────────┐
│             FastAPI presentation and middleware                │
│ `backend/main.py`, `backend/endpoints/`, `backend/decorators/` │
└─────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                   Application handlers                         │
│ scan/orchestration | database | filesystem | metadata | auth │
│                    `backend/handler/`                          │
└───────────┬───────────────┬───────────────┬──────────────────┘
           │               │               │
           ▼               ▼               ▼
  SQLAlchemy models    Library/resources FS   Provider adapters
  `backend/models/`    `backend/handler/      `backend/adapters/
  MariaDB/MySQL/PG      filesystem/`           services/`
           │               │
           └───────┬────────┘
                   ▼
        Redis cache, sessions and RQ queues
        `backend/handler/redis_handler.py`
```

## Component Responsibilities

| Component                 | Responsibility                                                                                                              | File                                 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| ASGI composition root     | Creates FastAPI, installs middleware, registers `/api` routers, and mounts Socket.IO applications                           | `backend/main.py`                    |
| Startup coordinator       | Initializes recurring RQ jobs and seeds Redis caches from metadata fixtures                                                 | `backend/startup.py`                 |
| Endpoint layer            | Validates HTTP input, applies `@protected_route`, checks entity visibility, calls handlers, and serializes response schemas | `backend/endpoints/`                 |
| Scan orchestrator         | Resolves platforms, scans ROMs and assets, runs provider lookups concurrently, and composes persisted ROM attributes        | `backend/handler/scan_handler.py`    |
| Database handlers         | Own SQLAlchemy queries and mutations per aggregate; `roms_handler.py` is the ROM repository                                 | `backend/handler/database/`          |
| Filesystem handlers       | Validate rooted paths, enumerate library folders, hash files/archives, and manage ROM/resource/asset bytes                  | `backend/handler/filesystem/`        |
| Metadata handlers         | Normalize provider-specific records and apply provider priority during scans                                                | `backend/handler/metadata/`          |
| External adapters         | Typed clients for IGDB, MobyGames, ScreenScraper, SteamGridDB, RetroAchievements, and related services                      | `backend/adapters/services/`         |
| ORM domain model          | Defines ROM, platform, user, collection, asset, device, permission, and synchronization persistence                         | `backend/models/`                    |
| Background work           | Defines scheduled and manual RQ tasks, including library scans and cleanup                                                  | `backend/tasks/`                     |
| Frontend composition root | Registers plugins, loads heartbeat/auth/config concurrently, and mounts the router                                          | `frontend/src/main.ts`               |
| UI-version gate           | Switches between v1 default and v2 named router views and owns v2 theme scope                                               | `frontend/src/RomM.vue`              |
| Shared API client         | Central Axios client for `/api`, CSRF, session failure, and backend reachability signaling                                  | `frontend/src/services/api/index.ts` |
| Generated contract        | Backend OpenAPI-derived TypeScript request and response models                                                              | `frontend/src/__generated__/`        |

## Pattern Overview

**Overall:** Layered modular monolith with filesystem-backed game content, relational metadata, asynchronous workers, and a progressively migrated SPA.

**Key Characteristics:**

- Keep the HTTP path `endpoint -> handler -> database/filesystem/metadata -> model or adapter`; endpoints remain thin and handler code owns behavior.
- Treat the backend response schemas as the API source of truth. Regenerate `frontend/src/__generated__/` when routes or response shapes change.
- Treat a `Rom` as the logical game/library entry and `RomFile` rows as physical members. Never encode DLC, patches, manuals, discs, or nested files as parallel ROM tables.
- Keep library bytes outside the database. The database stores normalized paths, sizes, hashes, categories, provider IDs, and user state.
- Use Redis for sessions, caches, real-time coordination, and RQ queues; do not use process-local state for durable work.
- Put all new frontend feature work in `frontend/src/v2/`; the v1 tree is a frozen compatibility surface.

## Layers

**Presentation Layer:**

- Purpose: Expose REST, Socket.IO, authentication, request validation, and response serialization.
- Location: `backend/endpoints/`, `backend/decorators/`, `backend/main.py`
- Contains: FastAPI routers, Pydantic response schemas, form models, socket event handlers, middleware registration.
- Depends on: Handler layer, auth scopes, response schemas.
- Used by: `frontend/src/services/api/`, browser downloads, third-party API clients.

**Application/Business Layer:**

- Purpose: Coordinate scanning, metadata selection, authorization policy, synchronization, and task behavior.
- Location: `backend/handler/`, `backend/tasks/`
- Contains: Scan orchestration, per-domain handlers, RQ task classes, Socket.IO coordination.
- Depends on: Database handlers, filesystem handlers, adapters, Redis, models.
- Used by: Endpoints, scheduled workers, watcher processes.

**Data Access Layer:**

- Purpose: Encapsulate relational queries and filesystem access behind domain-specific handlers.
- Location: `backend/handler/database/`, `backend/handler/filesystem/`
- Contains: SQLAlchemy session/query code, validated path operations, hashing, archive inspection, resource persistence.
- Depends on: `backend/models/`, `backend/config/`, library/resource paths.
- Used by: Application handlers and tasks.

**Domain/Persistence Layer:**

- Purpose: Represent library, user, collection, asset, permission, and synchronization state.
- Location: `backend/models/`
- Contains: SQLAlchemy 2.0 mapped classes, enums, relationships, computed column properties.
- Depends on: `backend/models/base.py`, SQLAlchemy, database-dialect utilities.
- Used by: Database handlers, response schemas, scanner.

**Frontend Application Layer:**

- Purpose: Render library workflows, preserve client UI state, and call the REST/socket surfaces.
- Location: `frontend/src/`, with active feature development in `frontend/src/v2/`
- Contains: Views, feature composites, shared design primitives, Pinia stores, composables, router, API services.
- Depends on: Generated OpenAPI types, Axios, Vue Router, Pinia, Socket.IO.
- Used by: Browser users and player integrations.

## Data Flow

### Library Scan Path

1. A scheduled job or scan socket request enters through `backend/tasks/scheduled/scan_library.py` or `backend/endpoints/sockets/scan.py`.
2. Platform discovery and provider platform mapping run in `scan_platform` (`backend/handler/scan_handler.py:183`).
3. `FSRomsHandler.get_roms` combines top-level files and top-level directories into flat and nested ROM candidates (`backend/handler/filesystem/roms_handler.py:702`).
4. `scan_rom` parses the candidate, compares it with database state, calculates files/hashes, and gathers provider metadata (`backend/handler/scan_handler.py:334`).
5. `FSRomsHandler.get_rom_files` recursively enumerates folder ROMs, assigns categories from subfolder names, hashes top-level members, and preserves archive-member hashes (`backend/handler/filesystem/roms_handler.py:321`).
6. `DBRomsHandler.add_rom` or `update_rom` persists the logical ROM, its `rom_files`, and aggregate metadata (`backend/handler/database/roms_handler.py:413`, `backend/handler/database/roms_handler.py:1679`).
7. Socket events update the scan UI through `backend/endpoints/sockets/scan.py` and `frontend/src/v2/composables/useScanLifecycle/index.ts`.

### API Read Path

1. The browser calls `/api/roms` or `/api/roms/{id}` through `frontend/src/services/api/rom.ts`.
2. The Axios interceptor adds CSRF state and centralizes 401/403 and reachability handling (`frontend/src/services/api/index.ts:40`).
3. A protected FastAPI route validates filters and scope in `backend/endpoints/roms/__init__.py`.
4. `backend/handler/database/roms_handler.py` builds an eager-load profile appropriate to simple, detailed, or paginated output.
5. Pydantic schemas in `backend/endpoints/responses/rom.py` serialize ORM objects into generated frontend shapes under `frontend/src/__generated__/`.

### Single and Multi-file Download Path

1. `getDownloadPath` encodes a logical ROM id plus optional `rom_files.id` values (`frontend/src/utils/index.ts:117`).
2. `downloadRom` triggers a normal browser navigation to that URL (`frontend/src/services/api/rom.ts:464`).
3. `get_rom_content` resolves the ROM, enforces visibility, and filters `rom.files` by requested ids (`backend/endpoints/roms/__init__.py:1325`).
4. One selected file becomes a direct file response in development or an internal nginx redirect in production (`backend/endpoints/roms/__init__.py:1377`, `backend/endpoints/roms/__init__.py:1456`).
5. Multiple files become a ZIP. If no `.m3u` exists, a generated playlist lists `.cue` files preferentially and otherwise the selected members (`backend/endpoints/roms/__init__.py:1372`, `backend/endpoints/roms/__init__.py:1428`).
6. Range downloads use the ZIP cache; ordinary production downloads use nginx `mod_zip` instructions (`backend/endpoints/roms/__init__.py:1462`, `backend/utils/zip_cache.py`, `backend/utils/nginx.py`).
7. Direct per-file media/manual/soundtrack access uses `backend/endpoints/roms/files.py:67`, with inline media types restricted to trusted database category and filename data.

**State Management:**

- Persistent domain state lives in SQLAlchemy models and the configured relational database.
- Library/media bytes live under configured library, resources, and assets roots.
- Session, cache, RQ, scan coordination, and room state use Redis via `backend/handler/redis_handler.py`.
- Frontend cross-view state uses Pinia under `frontend/src/stores/` and v2-local stores under `frontend/src/v2/stores/`.
- Per-disc player selection is local browser state resolved against current `RomFile` ids by `frontend/src/v2/utils/playerDisc.ts`.

## ROM and File Modeling

**Logical ROM (`Rom`):**

- Purpose: The central game/library aggregate with platform ownership, display metadata, provider identifiers, hashes, artwork paths, missing state, and user relationships.
- Examples: `backend/models/rom.py:297`, `backend/endpoints/responses/rom.py`
- Pattern: One `roms` row represents one browsable game entry regardless of whether storage is one file, a directory, or an archive.

**Physical member (`RomFile`):**

- Purpose: Represent a downloadable/playable/scannable physical file belonging to a ROM.
- Examples: `backend/models/rom.py:106`, `backend/handler/filesystem/roms_handler.py:262`
- Pattern: Store file name, relative path, size, timestamps, CRC/MD5/SHA1/RA/CHD hashes, category, and optional archive-member manifest.

**Multi-file and multi-disc:**

- A top-level directory is one `Rom`; recursive files become multiple `RomFile` rows (`backend/handler/filesystem/roms_handler.py:350`).
- `Rom.multi_file` is computed by the existence of a member whose path differs from `Rom.fs_path`; `top_level_file_count` distinguishes nested single-file from true multi-file layouts (`backend/models/rom.py:543`, `backend/models/rom.py:674`).
- `.m3u` is an ordinary member recognized by `Rom.has_m3u_file`; downloads synthesize one only when absent (`backend/models/rom.py:608`).
- EmulatorJS chooses a `RomFile.id`, persists it per ROM, and validates it after rescans (`frontend/src/v2/utils/playerDisc.ts`, `frontend/src/v2/views/Player/EmulatorJS.vue:421`).

**DLC, patch, update, manual, and other extras:**

- `RomFileCategory` defines `GAME`, `DLC`, `HACK`, `MANUAL`, `PATCH`, `UPDATE`, `MOD`, `DEMO`, `TRANSLATION`, `PROTOTYPE`, `CHEAT`, `SOUNDTRACK`, and `SCREENSHOT` (`backend/models/rom.py:71`).
- The scanner derives category from a matching nested directory name or plural directory name (`backend/handler/filesystem/roms_handler.py:109`, `backend/handler/filesystem/roms_handler.py:274`).
- These are categorized child files, not independent DLC/patch/manual entities. UI grouping belongs in `frontend/src/v2/components/GameDetails/FilesTab/`.
- ROM-owned manual uploads promote a single-file ROM to a folder, write under `manual/`, and add a `MANUAL` `RomFile` (`backend/endpoints/roms/manual.py:191`).
- Provider/manual cover metadata remains on the `Rom` (`manual_metadata`, `path_manual`, `url_manual`) while locally managed manual files use `RomFileCategory.MANUAL` (`backend/models/rom.py:400`, `backend/models/rom.py:410`).
- Runtime patch application uses categorized patch files and game files without introducing a patched-ROM persistence model (`backend/endpoints/roms/patch.py`).

## Key Abstractions

**Protected Route:**

- Purpose: Bind a FastAPI route to authentication and granular scopes.
- Examples: `backend/decorators/auth.py`, `backend/endpoints/roms/files.py:35`
- Pattern: Use `@protected_route(router.<verb>, path, [Scope...])`; apply entity visibility checks in addition to scope checks.

**Database Handler:**

- Purpose: Own transactions, queries, eager-loading profiles, and mutations for an aggregate.
- Examples: `backend/handler/database/roms_handler.py`, `backend/handler/database/platforms_handler.py`
- Pattern: Use `@begin_session` injection; do not open ad hoc sessions inside endpoints.

**Filesystem Handler:**

- Purpose: Constrain I/O to configured roots and translate bytes into domain metadata.
- Examples: `backend/handler/filesystem/base_handler.py`, `backend/handler/filesystem/roms_handler.py`
- Pattern: Validate relative paths before I/O; keep raw file manipulation out of endpoints except response construction.

**Response Schema:**

- Purpose: Define the public API contract independently of ORM loading behavior.
- Examples: `backend/endpoints/responses/rom.py`, `frontend/src/__generated__/models/DetailedRomSchema.ts`
- Pattern: Change backend Pydantic schemas first, then regenerate frontend models.

**Task:**

- Purpose: Run long or recurring operations outside request workers.
- Examples: `backend/tasks/tasks.py`, `backend/tasks/scheduled/scan_library.py`
- Pattern: Put cron-like work in `tasks/scheduled/` and admin-triggered work in `tasks/manual/`.

## Entry Points

**Backend API:**

- Location: `backend/main.py`
- Triggers: Uvicorn/Gunicorn ASGI startup or direct `python main.py` execution.
- Responsibilities: Migrations in direct-run mode, middleware, routers, sockets, app lifecycle.

**Startup Worker Initialization:**

- Location: `backend/startup.py`
- Triggers: Container entrypoint/direct backend startup.
- Responsibilities: Register recurring tasks, enqueue conditional maintenance, seed caches.

**Filesystem Watcher:**

- Location: `backend/watcher.py`
- Triggers: Watcher process configured by deployment.
- Responsibilities: Convert library filesystem changes into scan/update work.

**Sync Watcher:**

- Location: `backend/sync_watcher.py`
- Triggers: Synchronization worker process.
- Responsibilities: Observe and coordinate save synchronization changes.

**Frontend SPA:**

- Location: `frontend/src/main.ts`
- Triggers: Browser loads the Vite bundle.
- Responsibilities: Register plugins, preload session/config/heartbeat state, mount `RomM.vue`.

## Architectural Constraints

- **Concurrency:** FastAPI and filesystem/provider work use async I/O; CPU/blocking hashing and archive work is moved through `asyncio.to_thread`; durable jobs use RQ workers.
- **Global state:** Configuration manager, Redis handlers, metadata handler instances, and socket handlers are module-level shared services under `backend/config/` and `backend/handler/`.
- **Circular imports:** The frontend API client imports the router. `frontend/src/RomM.vue` lazy-loads `BackendStatusBanner` and `frontend/src/v2/router/routes.ts` uses string route keys to avoid bootstrap cycles.
- **Database portability:** ORM and Alembic changes must support MariaDB, MySQL, and PostgreSQL; migrations live only in `backend/alembic/versions/`.
- **Filesystem safety:** All content paths are relative to configured roots and must pass handler validation. Client-supplied download names never select bytes.
- **API contract:** Backend OpenAPI is authoritative; `frontend/src/__generated__/` is generated output, not a hand-maintained model layer.
- **Frontend migration boundary:** `frontend/src/views/`, `frontend/src/components/`, `frontend/src/console/`, and `frontend/src/layouts/` are v1 compatibility code. New UI belongs under `frontend/src/v2/` while shared stores/services/generated types remain canonical.
- **ROM identity:** One logical `Rom` may own many physical files. File extras stay categorized `RomFile` rows; do not introduce separate domain ownership based only on folder names.

## Anti-Patterns

### Business Logic in Endpoints

**What happens:** A route performs raw SQL, provider selection, or scanner persistence itself.
**Why it's wrong:** It bypasses transaction conventions, makes socket/task reuse difficult, and couples HTTP schemas to persistence.
**Do this instead:** Delegate to `backend/handler/database/`, `backend/handler/metadata/`, or `backend/handler/scan_handler.py`, following `backend/endpoints/roms/__init__.py`.

### Parallel ROM-extra Models

**What happens:** DLC, updates, patches, discs, or manuals are modeled as unrelated top-level entities merely because they live in subfolders.
**Why it's wrong:** The scanner, detail UI, download selection, visibility, and hashing all use `Rom.files`; a second ownership path would drift.
**Do this instead:** Extend `RomFileCategory` and the existing category-aware flows in `backend/models/rom.py`, `backend/handler/filesystem/roms_handler.py`, and `frontend/src/v2/components/GameDetails/FilesTab/`.

### Handwritten Frontend API Shapes

**What happens:** A frontend feature invents local DTOs for a backend route or patches files under `frontend/src/__generated__/`.
**Why it's wrong:** The backend contract and client types diverge.
**Do this instead:** Update `backend/endpoints/responses/`, regenerate `frontend/src/__generated__/`, and consume the generated type from `frontend/src/services/api/`.

### New Work in Frozen v1

**What happens:** A new feature or broad refactor is added under `frontend/src/views/` or `frontend/src/components/`.
**Why it's wrong:** The default router is actively gated between two implementations and v1 is a removal-bound compatibility surface.
**Do this instead:** Add views/components under `frontend/src/v2/`, use `frontend/src/v2/lib/` primitives, and reuse shared stores/services.

### Serving Files from Client Paths

**What happens:** A route joins user-controlled path or filename input directly to the library root.
**Why it's wrong:** It creates traversal, content-type confusion, and hidden-ROM disclosure risk.
**Do this instead:** Resolve a database id, enforce parent-ROM visibility, validate its stored path, and serve through `FileRedirectResponse` as in `backend/endpoints/roms/files.py:84`.

## Error Handling

**Strategy:** Raise typed domain/endpoint/filesystem exceptions inside handlers, convert them through FastAPI handlers, and keep external-provider failures isolated during concurrent metadata scans.

**Patterns:**

- Use custom exceptions from `backend/exceptions/` when a typed error exists.
- Use 404 masking for content belonging to a ROM the caller cannot see (`backend/endpoints/roms/files.py:91`).
- Log provider or filesystem failures with context, but allow independent metadata providers to complete (`backend/handler/scan_handler.py`).
- Frontend API failures pass through central Axios response handling, while feature composables/views own user-visible errors (`frontend/src/services/api/index.ts:52`).

## Cross-Cutting Concerns

**Logging:** Structured backend logger under `backend/logger/`; admin log streaming uses Socket.IO and Redis pub/sub.
**Validation:** FastAPI/Pydantic for transport, SQLAlchemy types/constraints for persistence, and `backend/handler/filesystem/base_handler.py` plus `backend/utils/validation.py` for filesystem boundaries.
**Authentication:** Hybrid session/basic/bearer/OIDC/client-token authentication in `backend/handler/auth/`; granular scopes on routes and visibility checks on entities.
**Caching:** Redis caches metadata/query state; resumable multi-file downloads use `backend/utils/zip_cache.py`.
**Observability:** Sentry initializes in `backend/main.py`; OpenTelemetry spans appear in startup and task flows.

---

_Architecture analysis: original mapping 2026-08-04; fork delta verified 2026-10-15_

## Current fork delta (verified 2026-10-15)

This section records the fork-specific capabilities added after the original codebase mapping. The layered RomM core remains the foundation; these features are not part of an unmodified RomM checkout.

### PC library and storage model

- External PC library roots are mounted read-only and assigned to platforms through canonical storage mappings.
- Storage mapping administration and legacy-library reconciliation are exposed through the library-management UI and storage endpoints.
- PC games remain logical ROM records, while base games, installers, updates, DLC, patches, manuals, optional files, and required archives are represented as categorized PC components and ROM files.
- Relevant code: `backend/handler/filesystem/`, `backend/handler/storage/`, `backend/endpoints/storage.py`, `backend/endpoints/roms/pc_metadata.py`, `frontend/src/v2/components/LibraryManagement/`, `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`.

### PC downloads and manifests

- Selected PC components can be downloaded through immutable, hash-backed manifests.
- Browser downloads support progress, pause/resume, retry, cancel, history, and enhanced folder downloads.
- Relevant code: `backend/endpoints/download_manifests.py`, `backend/endpoints/download_transfers.py`, `backend/handler/downloads/`, `frontend/src/v2/components/GameDetails/`, and the generated download API client.

### Metadata and media extensions

- IGDB, Steam, ScreenScraper, SteamGridDB, MobyGames, LaunchBox, Hasheous, and RetroAchievements remain provider adapters under the existing metadata boundary.
- PC-specific Steam identity and DLC enrichment are handled separately from the IGDB relationship and do not replace the ROM aggregate model.
- YouTube video IDs and Steam App IDs are exposed through ROM metadata and editable in the v2 game-details workflow.
- Artwork, screenshots, backgrounds, owned media, and PC DLC media use ROM-owned media records and placement roles; source library files remain unchanged.
- Relevant code: `backend/handler/metadata/`, `backend/models/rom.py`, `backend/endpoints/responses/rom.py`, `frontend/src/v2/components/GameDetails/OverviewTab.vue`, `frontend/src/v2/components/GameDetails/ArtworkSubtab.vue`, and `frontend/src/v2/components/GameDetails/PcDlcMediaTab.vue`.

### Save-data management

- PC save data has dedicated upload, download, deletion, content-hash, migration, and device-sync paths.
- Relevant code: `backend/endpoints/saves.py`, `backend/tasks/pc_save_migration.py`, `backend/tasks/manual/recompute_save_content_hashes.py`, and the v2 save-data tabs.

### Locale-aware descriptions

- Descriptions are resolved per UI locale without mutating the legacy `rom.summary` fallback.
- Manual descriptions, localized provider variants, English fallback, and legacy fallback are handled by the shared metadata description resolver.
- PC games and console ROMs use the same locale-aware contract.
- Relevant code: `backend/handler/metadata/manual_description.py`, `backend/handler/metadata/steam_merge.py`, `backend/handler/metadata/ss_handler.py`, `backend/handler/scan_handler.py`, `backend/endpoints/roms/pc_metadata.py`, and `frontend/src/v2/components/GameDetails/OverviewTab.vue`.

### v2 frontend and fork UI

- New feature work is implemented under `frontend/src/v2/`; the v1 tree remains a frozen compatibility surface.
- The fork adds PC component details, media management, save-data management, localized descriptions, clickable theme/genre filters, role-aware company metadata, and responsive artwork controls.
- Shared v2 primitives, design tokens, locale files, and accessibility patterns are used instead of introducing a second UI architecture.

### Reproducible deployment

- Portainer deployment, persistent library/media/database boundaries, read-only mounts, provider credentials, ScreenScraper user credentials, official-image developer credentials, and source-build secrets are documented in `docs/PORTAINER_INSTALL.md` and `examples/portainer-stack.yml`.
- The official image and source-build credential paths are intentionally distinguished: normal users provide ScreenScraper account credentials; source builds additionally require developer build secrets.

### Documentation status

- This document is an architecture map, not a complete API reference or phase log.
- Phase-specific acceptance criteria, UAT evidence, and deployment procedures remain in `.planning/phases/`, `.planning/quick/`, `docs/`, and `examples/`.
