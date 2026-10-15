# Codebase Structure

**Analysis Date:** 2026-10-15

## Directory Layout

```text
pc-game-download-portal/
├── backend/                 # FastAPI, models, handlers, adapters and tasks
│   ├── endpoints/           # REST routers, schemas and Socket.IO events
│   ├── handler/             # database, metadata, filesystem and orchestration
│   ├── models/              # catalog, PC components, assets and transfers
│   ├── adapters/services/   # typed external provider clients
│   ├── alembic/             # database migrations
│   ├── tasks/               # scheduled and manual RQ jobs
│   └── tests/               # backend tests by layer
├── frontend/src/            # Vue bootstrap, plugins, stores, services and v2
│   ├── v2/                  # active rewrite: views, features, primitives, data
│   ├── services/api/        # shared Axios modules
│   ├── stores/              # shared Pinia stores
│   └── locales/             # locale/namespace JSON and validators
├── frontend/e2e/            # Playwright flows
├── desktop/                 # Tauri/Rust desktop shell
├── docker/                  # container, Nginx and init assets
├── docs/                    # architecture, setup, provider and design docs
├── scripts/                 # repository utilities
├── tests/                   # root fixtures and cross-cutting tests
└── .planning/               # GSD state, phases, reports and codebase maps
```

## Directory Purposes

**backend/endpoints/:** HTTP/realtime presentation. ROM-specific routes are under backend/endpoints/roms/, including pc_metadata.py, pc_component_resources.py and media.py. Download routes are backend/endpoints/download_manifests.py and download_transfers.py.

**backend/handler/:** Application logic independent of HTTP serialization. Important boundaries are backend/handler/database/, backend/handler/metadata/, backend/handler/filesystem/, backend/handler/scan_handler.py and backend/handler/redis_handler.py.

**backend/models/:** SQLAlchemy domain schema. backend/models/rom.py owns the parent ROM, files, PC components, component manifest members, provider metadata, local/owned media and placements. backend/models/assets.py owns saves, states and screenshots. Download and storage models are separate modules.

**backend/handler/filesystem/:** All library and owned-file I/O. storage_composition.py and storage_policy.py classify roots and operations; resources_handler.py owns generated/uploaded media; roms_handler.py reads and hashes the external library.

**backend/alembic/versions/:** Ordered schema evolution. PC component/media, localized/provider metadata, download manifest/transfer and immutable storage changes are represented by migrations such as 0116, 0118, 0119, 0128 and 0138.

**frontend/src/v2/:** Active frontend rewrite. GameDetails contains ROM, DLC, metadata, media, saves and downloads. MatchRom contains provider matching. Settings contains scan, storage and PC automation administration. data/adapters/legacy/ bridges v2 to canonical shared API/store modules.

**frontend/src/services/api/ and frontend/src/stores/:** Shared compatibility data boundary used by v2 adapters and remaining v1 surfaces. ROM, save, state, media and download APIs live here beside auth/config/task stores.

**frontend/src/locales/:** Locale and namespace JSON. en_US is the source; parity and sorted-key scripts enforce the catalog.

## Key File Locations

**Entry Points:**

- backend/main.py: FastAPI composition, middleware, routers and WebSocket mounts.
- backend/startup.py: startup initialization and task registration.
- frontend/src/main.ts: Vue bootstrap, initial heartbeat/auth/config loading and router mount.
- frontend/src/RomM.vue: root shell, theme scope and global connection banner.

**Configuration:**

- backend/config/**init**.py: environment-backed runtime configuration.
- backend/config/config_manager.py: YAML-backed configuration singleton.
- frontend/package.json, frontend/vite.config.js and frontend/tsconfig.json: frontend build/type configuration.
- .github/workflows/: CI for backend, frontend, migrations and i18n.

**Core Logic:**

- backend/handler/scan_handler.py: scan and metadata pipeline.
- backend/models/rom.py: ROM/PC/media aggregate.
- backend/handler/database/roms_handler.py: catalog mutations and hydration.
- backend/handler/metadata/: provider normalization and PC matching.
- frontend/src/v2/components/GameDetails/: user-facing ROM/DLC detail composition.

**Testing:**

- backend/tests/handler/, backend/tests/endpoints/, backend/tests/models/: backend tests by layer.
- backend/tests/integration/: storage and scan guarantees.
- frontend/src/v2/**/*.test.ts: colocated v2 tests.
- frontend/e2e/: browser-level tests.
- frontend/src/v2/**/*.stories.ts: Storybook coverage for primitives/components.

## Naming Conventions

**Files:** Python modules use snake_case, for example pc_steam_enrichment.py. Vue feature files use PascalCase, for example PcComponents.vue and DownloadManager.vue. API modules and stores use domain names such as rom.ts, downloadTransfers.ts and pcAutomation.ts. Tests use test_*.py, *.test.ts or *.stories.ts.

**Directories:** Backend directories are lower-case by layer/domain. V2 feature directories are PascalCase. V2 primitive directories use one R* component per folder under frontend/src/v2/lib/.

## Where to Add New Code

**New backend feature:** Add a route under backend/endpoints/, focused logic under backend/handler/database/, metadata/ or filesystem/, models/migration under backend/models/ and backend/alembic/versions/, response types under backend/endpoints/responses/, and mirrored tests under backend/tests/.

**New PC catalog behavior:** Extend backend/models/rom.py and its migration; use backend/handler/metadata/pc_match_handler.py and pc_automation.py for candidate/review behavior; use backend/endpoints/roms/pc_metadata.py or pc_component_resources.py for routes. Add frontend behavior under frontend/src/v2/components/GameDetails/, MatchRom/ or Settings/.

**New media/assets:** Parent media belongs in backend/endpoints/roms/media.py and backend/handler/metadata/rom_media.py. Component media belongs in backend/endpoints/roms/pc_component_resources.py. Saves, states and screenshots use their dedicated endpoint/database-handler modules. Store bytes through owned resource storage.

**New download behavior:** Manifest selection belongs in backend/endpoints/download_manifests.py and backend/handler/database/download_manifests_handler.py. Transfer lifecycle belongs in backend/endpoints/download_transfers.py and its handler. The UI belongs in frontend/src/v2/components/GameDetails/Download*.vue and the download adapter/store.

**New frontend feature/component:** Route views go in frontend/src/v2/views/ and route registration in frontend/src/v2/router/routes.ts or frontend/src/plugins/router.ts. Feature composites go in frontend/src/v2/components/<Feature>/. Shared composites go in components/shared/. Domain-free primitives go in frontend/src/v2/lib/<RName>/ with component, index and Storybook story.

**Utilities:** Backend shared helpers go in backend/utils/; frontend behavior goes in frontend/src/v2/composables/ or frontend/src/v2/utils/. User-visible strings belong in every frontend/src/locales/<locale>/ namespace, with en_US as source.

## Special Directories

**frontend/src/**generated**/:** OpenAPI-generated TypeScript types. Generated and committed. Regenerate after backend contract changes; do not hand-edit.

**frontend/dist/:** Vite production output. Generated; source changes belong under frontend/src/.

**backend/**pycache**/, frontend/node_modules/, .pytest_cache/:** Generated runtime/dependency/test caches. Not implementation source and not committed.

**romm_mock/:** Repository fixture library and owned-resource fixtures for development/tests, not the production library.

**.planning/:** GSD project state, phase plans, reports and codebase references. Mapper documents under .planning/codebase/ feed planning and execution.

---

_Structure analysis: 2026-10-15_
