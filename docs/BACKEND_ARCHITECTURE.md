<!-- generated-by: gsd-doc-writer -->

# ZockArchive Backend Architecture

**Analysis Date:** 2026-10-15

## System Overview

```text
Browser/PWA -> Vue Router, v2 views, Pinia, Axios/Socket.IO adapters
           -> /api/* and /ws
FastAPI     -> middleware, auth/session/CSRF, thin routers, Socket.IO mounts
Handlers    -> database | metadata/providers | filesystem/storage | scan/tasks
Storage     -> SQLAlchemy/Alembic | provider APIs | read-only library | Redis/RQ
```

The backend owns catalog state and API shapes. The Vue frontend never accesses the database or library directly. Pydantic response schemas in backend/endpoints/responses/ generate frontend/src/**generated**/.

## Component Responsibilities

| Component         | Responsibility                                                        | File                                                                                            |
| ----------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Application       | FastAPI composition, middleware, routers, WebSocket mounts            | backend/main.py                                                                                 |
| Scan pipeline     | Filesystem scan, ROM/component reconciliation, provider enrichment    | backend/handler/scan_handler.py                                                                 |
| API boundary      | Request validation, scopes, delegation and serialization              | backend/endpoints/                                                                              |
| Catalog aggregate | ROM identity, metadata, files, PC components, media, saves and states | backend/models/rom.py                                                                           |
| Storage boundary  | External read-only versus ZockArchive-owned roots                     | backend/handler/filesystem/storage_composition.py, backend/handler/filesystem/storage_policy.py |
| Metadata          | Provider clients, normalization, merge and priority                   | backend/handler/metadata/, backend/adapters/services/                                           |
| PC automation     | Guarded unique decisions and review queue                             | backend/handler/metadata/pc_automation.py, backend/models/pc_automation.py                      |
| Frontend shell    | Bootstrap, initial auth/config/heartbeat, themes and routes           | frontend/src/main.ts, frontend/src/PGDP.vue                                                     |
| Frontend data     | Pinia state and API/socket adapters                                   | frontend/src/v2/data/adapters/legacy/, frontend/src/stores/                                     |

## Pattern Overview

**Overall:** Layered service architecture with a shared ROM aggregate and explicit storage capabilities.

**Key Characteristics:**

- Thin endpoints delegate to handlers and typed schemas.
- Rom is the catalog aggregate. PC installs add RomComponent children and immutable manifest members.
- The external library is read-only. Generated/uploaded content uses classified owned roots.
- Raw provider metadata is retained and normalized into common fields and provider-qualified facets.
- New frontend behavior belongs in frontend/src/v2/; v1 paths are frozen.

## Layers

**Presentation:** backend/endpoints/ and backend/endpoints/sockets/ contain routers, schemas and realtime events. They depend on auth, database, metadata and filesystem handlers.

**Domain/application:** backend/handler/ contains database CRUD, metadata, filesystem, scan, sync, netplay and Redis handlers. It is used by endpoints and tasks.

**Persistence/integration:** backend/models/, backend/alembic/ and backend/adapters/services/ contain SQLAlchemy models, migrations, typed provider clients and provider types.

**Frontend:** frontend/src/v2/, frontend/src/plugins/router.ts and frontend/src/v2/data/adapters/legacy/ contain routes, feature components, stores, composables and API/socket adapters.

## Data Flow

### Primary Request Path

1. frontend/src/plugins/router.ts loads a route and hydrates currentRom through the ROM API.
2. Axios sends /api/* with CSRF headers. backend/main.py applies CORS, upload limits, CSRF, authentication and Redis sessions.
3. A router validates the request and Scope, then calls a database, metadata or filesystem handler.
4. Handlers use SQLAlchemy, typed providers and explicit storage capabilities. Pydantic schemas form the response.
5. Pinia updates the view. Scan, sync, activity and logs use Socket.IO at /ws; netplay uses /netplay.

### Library Scan and PC Enrichment

1. backend/tasks/scheduled/scan_library.py or scan endpoints create bounded mapped commands.
2. backend/handler/scan_handler.py reads the external root, hashes files, persists Rom/RomFile, and reconciles PC layouts defined in backend/handler/filesystem/roms_handler.py.
3. RomComponent represents base, update, DLC, hotfix, language pack, extra or unresolved entries. RomComponentManifestMember retains relative path, size, SHA-256 and missing-from-filesystem state.
4. pc_steam_enrichment.py resolves guarded Steam patches; pc_match_handler.py collects reviewable candidates.
5. pc_automation.py applies only unique guarded matches. Ambiguity or protected/manual targets enter pc_automation_queue.

### Metadata, Localization and Media

- Parent metadata is provider JSON plus roms_metadata and filter-oriented roms_facets in backend/models/rom.py.
- Components have RomComponentMetadata, preserving DLC/provider identity separately from the parent.
- Manual descriptions remain in `manual_metadata.descriptions`. Steam PC/Windows and ScreenScraper console descriptions retain validated language/source variants. English may be collected alongside the requested language, but stays in its English slot. Scalar legacy summary is retained as historical data and is not an active v2 description fallback.
- `backend/config/scan_language.py` updates the existing shared language priority using administrative permission and compare-and-set checks. `backend/handler/metadata/metadata_locale.py` captures the effective locale into accepted scan commands; queued, scheduled and recovered work retains that snapshot.
- `backend/handler/scan_description_retry.py` shares the existing retry coordinator across unidentified and missing-description work. It selects at most five distinct games per operation and eight existing targets per game. Complete warm targets need no provider request; description-only repair avoids inventory and media work.
- `backend/handler/database/description_state.py` applies narrow provider-text patches with current identity, version/digest and execution-authority checks. Partial provider replies preserve valid variants and all stored manual text. Existing interactive matching and refresh paths use `backend/handler/metadata/manual_description_refresh.py` and the same provider/merge owners.
- Library images are RomComponentLocalMedia; uploaded/provider media is copied to owned resources as RomOwnedMedia or RomComponentOwnedMedia, with roles and placements.
- backend/endpoints/roms/media.py and backend/endpoints/roms/pc_component_resources.py expose owned media. The v2 detail view selects overview, background and audio placements.

### Provider image deletion and placement

Deleting parent provider media keeps its catalog identity as a tombstone with
`operator_suppressed=True`, removes its placements and clears its owned path.
Normal, media-only, COMPLETE and explicit provider refresh preserve this intent.
Automatic inventory disappearance instead uses a tombstone with
`operator_suppressed=False`; that candidate may return with a later inventory.
Uploads retain their separate deletion and placement behavior.

`backend/handler/database/provider_media_suppression.py` shares the persisted
suppression policy between optimistic download filtering and locked reconciliation.
Exact native IDs remain provider-qualified. Identical `url-sha256:` identities
also match across existing provider namespaces, only within the same ROM and role.
The digest comes from the existing normalized HTTPS URL. Native records without
a comparable persisted URL identity cannot be reconstructed or aliased by guessing.

Generic and Steam refresh batch suppression checks before downloading or storing
images, including Steam COMPLETE force updates. Repository reconciliation checks
again under the existing ROM version/parent lock and scan write fence. Legacy
cover/screenshot publication filters attempted downloads without changing stored
metadata URL lists. Filtered screenshots are regenerated together so their returned
paths retain their download order, without reusing paths indexed by the original
unfiltered list. Suppression is rechecked under the publication transaction's parent
lock and fence before staged output publication and again before association.
A deletion during download rejects that attempt; the existing batch abort removes
its private outputs. Publication failures retain the existing recovery protocol.

Removing a placement leaves an active candidate in the catalog. Steam inventory
reconciliation can seed empty overview/background surfaces again, so placement
removal is not a durable hide flag. There is no independent per-media hidden state
or restore endpoint. Explicit refresh does not restore operator-deleted images.

### Saves, States and Downloads

- Save and State are user-owned ROM assets with retained catalog identity, device linkage and visibility. Handlers are backend/handler/database/saves_handler.py and states_handler.py.
- Device save synchronization uses backend/models/device_save_sync.py and backend/models/sync_session.py.
- PC download selection snapshots component evidence in backend/models/download_manifest.py.
- Resumable transfer attempts, item states and event lineage live in backend/models/download_transfer.py; endpoints are backend/endpoints/download_manifests.py and backend/endpoints/download_transfers.py.
- Source changes invalidate manifests/transfers. The frontend consumes them via frontend/src/v2/data/adapters/legacy/services/api/downloadTransfers.ts.

**State Management:** SQLAlchemy and Redis hold backend state. Pinia holds frontend server state, route query parameters hold bookmarkable filters/tabs, and component/store state holds ephemeral UI. Language and UI preferences use frontend stores and useUISettings.

## Key Abstractions

**ROM aggregate with PC components:** A parent Rom owns cascading components, manifest members, metadata, media and notes. See backend/models/rom.py, backend/handler/scan_handler.py and frontend/src/v2/components/GameDetails/PcComponents.vue.

**Storage descriptors and grants:** Composition-owned immutable descriptors authorize operations before path opening. See backend/handler/filesystem/storage_composition.py, storage_access.py and storage_policy.py.

**Provider normalization:** Typed adapter, provider handler, merge/priority policy and response schema preserve raw evidence while exposing common/localized fields. See backend/handler/metadata/steam_merge.py, rom_media.py and backend/models/rom.py.

**Frontend v2 tiers:** Domain-free primitives live in frontend/src/v2/lib/, shared composites in frontend/src/v2/components/shared/, and feature composites in frontend/src/v2/components/GameDetails/ or another feature folder.

## Entry Points

- FastAPI: backend/main.py, invoked by Uvicorn/Gunicorn or direct Python.
- Background work: backend/startup.py, backend/tasks/, backend/handler/redis_handler.py.
- Frontend: frontend/src/main.ts and frontend/src/PGDP.vue.

## Architectural Constraints

- **Threading:** Async FastAPI/Socket.IO coexist with RQ workers; blocking I/O stays in handlers/tasks.
- **Global state:** Provider handlers, config manager, Redis clients, Socket.IO handlers and storage composition are module-level infrastructure.
- **Circular imports:** The Axios client imports the router for 401 redirects. PGDP.vue lazy-loads app-shell pieces to avoid bootstrap cycles. V2 primitives must not import stores, services, router or i18n.
- **Storage safety:** The library root is external/read-only. Never write sidecars, exports or generated media there.
- **API contract:** Backend response schemas are authoritative; changes require OpenAPI regeneration into frontend/src/**generated**/.
- **Compatibility:** Do not refactor frozen v1 paths.

## Anti-Patterns

### Business logic in endpoints

**What happens:** Routes query/mutate catalog state or implement provider/filesystem decisions inline.
**Why it's wrong:** Shared transaction, storage-policy, concurrency and response rules are bypassed.
**Do this instead:** Add a focused handler under backend/handler/database/, metadata/ or filesystem/.

### Treating PC components as independent ROMs

**What happens:** DLC/update paths become unrelated catalog records or files are flattened into the parent.
**Why it's wrong:** Install topology, manifest identity, component media and parent-qualified matching are lost.
**Do this instead:** Use RomComponent and RomComponentManifestMember under the parent Rom.

### Writing to the external library

**What happens:** Covers, uploads, exports or transformations write beside library files.
**Why it's wrong:** The archive must remain unchanged and storage policy rejects external mutations.
**Do this instead:** Use fs_resource_handler and owned storage descriptors.

## Error Handling

**Strategy:** Validate and authorize at the boundary, raise typed domain/storage exceptions, translate at endpoint/middleware boundaries, and preserve optimistic concurrency conflicts.

**Patterns:** protected_route and assert_rom_visible enforce access; guarded mutations return None and endpoints map that to 404 or 409; StoragePolicyDenied remains terminal; failed media mutations clean up owned files and scheduled cleanup retains deletion intents.

## Cross-Cutting Concerns

**Logging:** Structured logging in backend/logger/; admin log lines can be forwarded over Socket.IO.

**Validation:** Pydantic schemas, auth scopes, bounded paths, typed provider data and database constraints.

**Authentication:** backend/handler/auth/hybrid_auth.py supports session, basic, bearer/client-token and OIDC, composed with CSRF/session middleware in backend/main.py.

**Localization:** frontend/src/locales/ loads locale/namespace JSON via frontend/src/locales/index.ts; en_US is source, while provider/manual metadata localization is resolved in v2 composables.

---

_Architecture analysis: 2026-10-15_

## Backend-specific current contracts

### API and download surfaces

The REST routers are included under /api in backend/main.py. Current central areas are /auth and /users, /platforms, /roms, /collections, /search, /music, /saves, /states, /screenshots, /firmware, /devices, /sync, /storage, /tasks, /config, /heartbeat, /stats, /logs, /streaming, /export and /feeds. PC-specific routes are implemented in backend/endpoints/roms/pc_metadata.py, pc_component_resources.py and pc_automation.py. Download manifests are created by POST /api/roms/{rom_id}/download-manifests; member reads are under /api/download-manifests/{manifest_id}/files/{public_id}; transfer sessions are under /api/download-transfer-sessions. Chunked ROM upload is in backend/endpoints/roms/upload.py.

### Auth and permissions

Role is user or admin in backend/models/user.py. Admin bypasses the granular matrix. Users receive PermissionGroup grants and UserPermissionOverride changes for read, write and delete over catalog, assets, devices, playlists, firmware, users, tasks and logs. backend/handler/auth/hybrid_auth.py accepts Redis sessions, Basic, HS256 OAuth bearer tokens, hashed rmm_ client tokens, optional OIDC and optional kiosk read access.

### Database, Redis and storage

MariaDB is the default driver. MySQL and PostgreSQL are supported by backend/config/config_manager.py and Alembic. docker-compose.yml includes MariaDB for ZockArchive and a separate PostgreSQL service for Authentik. The production Portainer stack uses MariaDB 11.3 and Valkey-compatible Redis runtime state.

StorageRoot and PlatformStorageMapping in backend/models/storage.py model external_read_only roots and versioned platform mappings. backend/handler/storage/read_context.py validates mapping revision and root health. backend/handler/filesystem/storage_policy.py permits only resolve/list/stat/read/scan/hash/stream/download on external roots; writes go to classified ZockArchive-owned roots.

### PC models, metadata, DLC and descriptions

RomComponent and RomComponentManifestMember in backend/models/rom.py represent base, update, DLC, hotfix, language_pack, extra and unresolved install components with relative paths, size, SHA-256 and missing-file state. RomComponentMetadata, local media, owned media, placements and notes preserve component-specific catalog data. pc_match_handler.py collects review candidates from IGDB, Steam, MobyGames, SteamGridDB and LaunchBox. pc_steam_enrichment.py applies guarded Steam data. DLC matching is limited to related IGDB expansions or validated Steam DLC. manual_description.py stores locale-keyed descriptions and resolves exact locale, English and provider fallbacks.

### Background work, WebSockets and deployment

RQ tasks are defined under backend/tasks/ and initialized by backend/startup.py, including scans, cleanup, provider updates, media cleanup, save-hash backfill and sync push/pull. /ws uses Socket.IO with Redis coordination for scan, activity, sync and admin log events; /netplay provides room, WebRTC and input relay events.

The Git-based production contract is examples/portainer-stack.yml. It builds docker/Dockerfile, persists MariaDB, resources and Redis data, mounts /romm/library read-only, and mounts operator-owned assets and config as writable paths. Required Portainer secrets include PGDP_DB_PASSWORD, PGDP_DB_ROOT_PASSWORD and PGDP_AUTH_SECRET_KEY. The exact host paths are deployment-specific.

### Configuration and verification

env.template is the canonical environment list. backend/config/**init**.py loads database, Redis, auth, OIDC, provider, Steam language, scan, upload, sync and observability variables. ROMM_AUTH_SECRET_KEY is required at import time. Tests live in backend/tests and cross-dialect/storage checks are in backend/tools.

## Product display and retained identities

The API documentation title and visible log prefix use ZockArchive. Both the API
process and startup task process report Sentry releases as `za@<version>`. This
starts a new release-name series for release-based dashboards and comparisons;
the configured DSN, Sentry project, credentials and capture behavior are unchanged.
The logger remains `romm`, with the existing formatter configuration key `pgdp`,
Redis channels and admin-log transport. Product labels do not rename these
installation or integration identities.

`TINFOIL_WELCOME_MESSAGE` keeps its operator key and configured-value precedence.
Only its fallback welcome is ZockArchive Switch Library. Existing custom and
legacy-branded configured welcomes are not migrated. Configuration warnings and
broker connectivity guidance use the current product name; broker failures keep
their existing HTTP status and session-owner authorization rules.

WebRcade feed titles/descriptions, Kekatsu author metadata and the ES-DE scraper
display name use ZockArchive. Feed routes, serialization fields, scopes and
download URLs are unchanged. FPKGi synthetic title IDs retain the `ROMM` prefix
so related content stays grouped; Pegasus retains `x-romm-id` for round trips.
WebRcade artwork URLs still reference upstream RomM assets pending final supplied
artwork. Metadata-provider User-Agent strings and upstream endpoints retain their
provider-compatible identities. No stored library, operator configuration,
authentication, session, cache, schema or filesystem identifier is migrated.

### Owned identity-transition validation

The rebranding probe in backend/tools/phase38_probe.py composes the existing disposable SQL/Redis runner, snapshot fixtures, target labels and exact cleanup. Its source adapter requires the canonical Linux host, root, feature branch and planning markers plus an authenticated live GitHub numeric/node ID and exact current name/origin pair. Inherited database, Compose and disposable-target overrides fail closed. This adapter does not change CI repository authority. Backend defaults to every existing tracked CI shard; the affected profile is a fixed product-identity test list. Schema uses the existing upgrade/downgrade/re-upgrade and constraint checks. Focused local receipts do not fulfill the final complete dual-SQL CI requirement.
