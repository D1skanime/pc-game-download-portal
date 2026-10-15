# Architecture

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
| Storage boundary  | External read-only versus RomM-owned roots                            | backend/handler/filesystem/storage_composition.py, backend/handler/filesystem/storage_policy.py |
| Metadata          | Provider clients, normalization, merge and priority                   | backend/handler/metadata/, backend/adapters/services/                                           |
| PC automation     | Guarded unique decisions and review queue                             | backend/handler/metadata/pc_automation.py, backend/models/pc_automation.py                      |
| Frontend shell    | Bootstrap, initial auth/config/heartbeat, themes and routes           | frontend/src/main.ts, frontend/src/RomM.vue                                                     |
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
- Manual descriptions live in manual_metadata; Steam/ScreenScraper variants are resolved by exact locale, language base, English fallback and legacy summary in frontend/src/v2/composables/useManualDescription/index.ts.
- Library images are RomComponentLocalMedia; uploaded/provider media is copied to owned resources as RomOwnedMedia or RomComponentOwnedMedia, with roles and placements.
- backend/endpoints/roms/media.py and backend/endpoints/roms/pc_component_resources.py expose owned media. The v2 detail view selects overview, background and audio placements.

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
- Frontend: frontend/src/main.ts and frontend/src/RomM.vue.

## Architectural Constraints

- **Threading:** Async FastAPI/Socket.IO coexist with RQ workers; blocking I/O stays in handlers/tasks.
- **Global state:** Provider handlers, config manager, Redis clients, Socket.IO handlers and storage composition are module-level infrastructure.
- **Circular imports:** The Axios client imports the router for 401 redirects. RomM.vue lazy-loads app-shell pieces to avoid bootstrap cycles. V2 primitives must not import stores, services, router or i18n.
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
