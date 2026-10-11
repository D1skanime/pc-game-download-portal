# Codebase Structure

**Analysis Date:** 2026-08-04

## Directory Layout

```text
RomM/
├── backend/                    # FastAPI application, domain, persistence, workers
│   ├── adapters/services/       # Typed external metadata/API clients
│   ├── alembic/versions/        # Ordered cross-database schema migrations
│   ├── config/                  # Environment and YAML configuration
│   ├── decorators/              # Route protection and DB session injection
│   ├── endpoints/               # REST and Socket.IO presentation layer
│   │   ├── responses/          # Pydantic/OpenAPI response contracts
│   │   ├── roms/               # ROM CRUD, files, uploads, manuals, patching
│   │   └── sockets/            # Scan/activity/log/netplay/sync events
│   ├── handler/                 # Business and data-access layers
│   │   ├── auth/               # Authentication, scopes, middleware
│   │   ├── database/           # Per-entity SQLAlchemy handlers
│   │   ├── filesystem/         # Rooted filesystem operations
│   │   └── metadata/           # Provider normalization and matching
│   ├── models/                  # SQLAlchemy ORM domain models
│   ├── tasks/                   # RQ scheduled and manual jobs
│   ├── tests/                   # Backend tests mirroring runtime packages
│   ├── tools/                   # Standalone developer/test utilities
│   ├── utils/                   # Cross-cutting helpers
│   ├── main.py                  # ASGI composition root
│   ├── startup.py               # Startup task/cache initialization
│   ├── watcher.py               # Library filesystem watcher
│   └── sync_watcher.py          # Save synchronization watcher
├── frontend/                   # Vue 3 SPA and client tooling
│   ├── src/__generated__/       # Generated OpenAPI TypeScript client models
│   ├── src/services/api/        # Shared domain API wrappers
│   ├── src/stores/              # Canonical shared Pinia stores
│   ├── src/plugins/             # Router, Pinia, i18n, Vuetify registration
│   ├── src/locales/             # Feature-namespaced translations
│   ├── src/views/               # Frozen v1 views
│   ├── src/components/          # Frozen v1 components
│   ├── src/v2/                  # Active v2 application
│   │   ├── components/         # Shared and feature composites
│   │   ├── composables/        # Typed v2 behavior hooks
│   │   ├── layouts/            # App/auth/settings route shells
│   │   ├── lib/                # Reusable R* design-system primitives
│   │   ├── router/             # v2 named-view registry
│   │   ├── stores/             # v2-only UI state
│   │   ├── styles/             # v2 tokens and global styles
│   │   ├── tokens/             # Theme token source
│   │   ├── utils/              # Pure v2 utilities
│   │   └── views/              # Lazy-loaded route views
│   ├── src/main.ts              # Browser entry point
│   └── src/RomM.vue             # v1/v2 root gate
├── docker/                     # Container runtime configuration
├── docs/                       # Architecture and contributor references
├── examples/                   # Deployment examples
├── .github/workflows/          # CI checks, builds, migrations, tests
├── pyproject.toml               # Python project and tool dependencies
├── docker-compose.yml           # Default multi-service deployment
└── Dockerfile                   # Production image build
```

## Directory Purposes

**`backend/endpoints/`:**

- Purpose: Public REST and socket presentation boundary.
- Contains: FastAPI routers, Pydantic response schemas, request forms, Socket.IO handlers.
- Key files: `backend/endpoints/roms/__init__.py`, `backend/endpoints/roms/files.py`, `backend/endpoints/responses/rom.py`, `backend/endpoints/sockets/scan.py`
- Add request parsing and serialization here; put reusable behavior in a handler.

**`backend/handler/`:**

- Purpose: Application services and data access.
- Contains: Scan orchestration plus `auth/`, `database/`, `filesystem/`, `metadata/`, and Redis/socket handlers.
- Key files: `backend/handler/scan_handler.py`, `backend/handler/database/roms_handler.py`, `backend/handler/filesystem/roms_handler.py`, `backend/handler/redis_handler.py`
- Add domain behavior to the narrowest existing handler package. Preserve endpoint-to-handler direction.

**`backend/models/`:**

- Purpose: Relational domain and persistence model.
- Contains: SQLAlchemy models for ROMs, platforms, users, collections, assets, permissions, devices, music, and sync.
- Key files: `backend/models/rom.py`, `backend/models/platform.py`, `backend/models/assets.py`, `backend/models/collection.py`, `backend/models/base.py`
- Add columns/relationships here and pair schema changes with a new file in `backend/alembic/versions/`.

**`backend/tasks/`:**

- Purpose: Durable background and recurring work.
- Contains: `scheduled/` cron-like tasks, `manual/` admin-triggered tasks, and shared task abstractions.
- Key files: `backend/tasks/tasks.py`, `backend/tasks/scheduled/scan_library.py`, `backend/tasks/manual/sync_folder_scan.py`
- Add long-running work here and call handlers rather than duplicating scanner or database logic.

**`backend/adapters/services/`:**

- Purpose: Isolate external API protocols and provider-specific types.
- Contains: Provider clients and companion typed payload modules.
- Key files: `backend/adapters/services/igdb.py`, `backend/adapters/services/screenscraper.py`, `backend/adapters/services/retroachievements.py`
- Add a provider client here and normalize it through a corresponding file in `backend/handler/metadata/`.

**`backend/alembic/`:**

- Purpose: Reproducible schema evolution across MariaDB/MySQL/PostgreSQL.
- Contains: Alembic environment plus ordered revision files.
- Key files: `backend/alembic/env.py`, `backend/alembic/versions/`
- Add a new revision; do not edit an applied historical revision.

**`backend/tests/`:**

- Purpose: Backend unit, handler, endpoint, task, and adapter coverage.
- Contains: Directory structure paralleling runtime packages, VCR cassettes, fixture databases and files.
- Key files: `backend/tests/conftest.py`, `backend/tests/endpoints/roms/`, `backend/tests/handler/filesystem/test_roms_handler.py`, `backend/tests/tasks/test_scan_library.py`

**`frontend/src/services/api/`:**

- Purpose: Stable, domain-oriented wrappers around the central Axios instance.
- Contains: API modules for ROMs, platforms, users, collections, assets, tasks, and related features.
- Key files: `frontend/src/services/api/index.ts`, `frontend/src/services/api/rom.ts`, `frontend/src/services/api/platform.ts`
- Put browser transport details here; views and components should not duplicate URL building or CSRF behavior.

**`frontend/src/__generated__/`:**

- Purpose: Generated TypeScript representation of backend OpenAPI.
- Contains: Request/response models and generated index exports.
- Key files: `frontend/src/__generated__/index.ts`, `frontend/src/__generated__/models/DetailedRomSchema.ts`, `frontend/src/__generated__/models/RomFileSchema.ts`
- Regenerate from the backend; never hand-edit.

**`frontend/src/stores/`:**

- Purpose: Canonical state shared by both frontend versions.
- Contains: Auth, config, users, ROM/gallery filters, upload, task, and media state.
- Key files: `frontend/src/stores/auth.ts`, `frontend/src/stores/config.ts`, `frontend/src/stores/upload.ts`, `frontend/src/stores/roms.ts`
- Extend additively when both versions need the state. Keep v2-only interaction state under `frontend/src/v2/stores/`.

**`frontend/src/v2/lib/`:**

- Purpose: Domain-free reusable design-system primitives.
- Contains: `R*` primitives grouped by forms, media, menus, overlays, data, and structural behavior.
- Key files: `frontend/src/v2/lib/index.ts`, `frontend/src/v2/lib/forms/RDropzone/RDropzone.vue`, `frontend/src/v2/lib/data/RTable/RTable.vue`
- Add one primitive per folder with `RFoo.vue`, `RFoo.stories.ts`, and `index.ts`; export it from the lib barrel.

**`frontend/src/v2/components/`:**

- Purpose: Shared and feature-owned UI composites.
- Contains: App shell, Gallery, GameDetails, Dialogs, Scan, Settings, Auth, Soundtrack, and shared components.
- Key files: `frontend/src/v2/components/GameDetails/FilesTab/FilesTab.vue`, `frontend/src/v2/components/Gallery/GalleryShell.vue`, `frontend/src/v2/components/shared/GameCover.vue`
- Add domain UI to the owning feature folder. Put only cross-feature composites in `components/shared/`.

**`frontend/src/v2/views/`:**

- Purpose: Route-level orchestration and lazy-loading boundary.
- Contains: Thin views for home, galleries, details, players, scan/upload, auth, and settings.
- Key files: `frontend/src/v2/views/GameDetails.vue`, `frontend/src/v2/views/Player/EmulatorJS.vue`, `frontend/src/v2/views/Scan.vue`
- Keep reusable UI in components and behavior in composables; views compose route state.

**`frontend/src/views/`, `frontend/src/components/`, `frontend/src/console/`, `frontend/src/layouts/`:**

- Purpose: Frozen v1 compatibility UI.
- Contains: Default named-view implementations still selected for v1 users.
- Key files: `frontend/src/views/GameDetails.vue`, `frontend/src/components/Details/`, `frontend/src/console/`
- Do not place new features or broad refactors here. Critical compatibility fixes only.

## Key File Locations

**Entry Points:**

- `backend/main.py`: FastAPI/Socket.IO application composition and direct-run server startup.
- `backend/startup.py`: Cache and scheduled-job initialization.
- `backend/watcher.py`: Library filesystem watcher entry.
- `backend/sync_watcher.py`: Save synchronization watcher entry.
- `frontend/src/main.ts`: Vue application bootstrap.
- `frontend/src/RomM.vue`: Runtime v1/v2 rendering gate and root theme scope.

**Configuration:**

- `backend/config/__init__.py`: Environment-driven runtime configuration.
- `backend/config/config_manager.py`: YAML library/scan configuration singleton.
- `backend/alembic.ini`: Migration runner configuration.
- `frontend/vite.config.js`: Frontend build, aliases, proxy, and plugins.
- `frontend/tsconfig.json`: TypeScript compiler/alias configuration.
- `frontend/src/plugins/router.ts`: Shared route tree, layouts, permission guards, and named views.
- `docker-compose.yml`: Default application, database, Redis, and worker topology.
- `env.template`: Documented environment names only; runtime secret files must not be read or committed.

**Core Logic:**

- `backend/handler/scan_handler.py`: ROM/platform scanning and provider aggregation.
- `backend/handler/filesystem/roms_handler.py`: Filesystem ROM discovery, category assignment, hashing, and archive manifests.
- `backend/handler/database/roms_handler.py`: ROM queries, persistence, filters, file rows, and folder conversion.
- `backend/models/rom.py`: Logical ROM, physical file, metadata, per-user state, notes, and sibling modeling.
- `backend/endpoints/roms/__init__.py`: ROM CRUD and single/bulk download surface.
- `backend/endpoints/roms/files.py`: Individual `RomFile` retrieval, content, and deletion.
- `backend/endpoints/roms/manual.py`: Provider manual caching and ROM-owned manual file operations.
- `backend/endpoints/roms/patch.py`: Runtime patch application.
- `frontend/src/services/api/rom.ts`: Browser ROM CRUD, uploads, selection downloads, and bulk downloads.
- `frontend/src/v2/components/GameDetails/FilesTab/`: Categorized file management UI.
- `frontend/src/v2/views/Player/EmulatorJS.vue`: Player setup and disc selection.

**Testing:**

- `backend/tests/endpoints/roms/`: ROM route, file, manual, upload, soundtrack, screenshot, patch-adjacent behavior.
- `backend/tests/handler/filesystem/test_roms_handler.py`: Filesystem scanning/hash/category behavior.
- `backend/tests/models/test_rom.py`: ROM model computed behavior.
- `frontend/test/`: Frontend smoke and Storybook composition tests.
- `frontend/src/v2/**/*.test.ts`: Co-located v2 utility/store/view/component tests.
- `frontend/e2e/`: Browser end-to-end tests when present.

**Documentation:**

- `CLAUDE.md`: Repository-wide contributor rules and stack overview.
- `docs/BACKEND_ARCHITECTURE.md`: Backend reference, endpoints, data model, auth, tasks.
- `docs/FRONTEND_ARCHITECTURE.md`: Frontend routing, state, services, theming, tooling.
- `.claude/skills/backend-development/SKILL.md`: Backend placement and workflow constraints.
- `.claude/skills/frontend-v2-components/SKILL.md`: v2 component tiers and file placement.

## Naming Conventions

**Files:**

- Python modules use `snake_case.py`: `scan_handler.py`, `roms_handler.py`.
- Backend domain packages use plural entity names when they expose aggregate handlers/endpoints: `endpoints/roms/`, `database/roms_handler.py`.
- Vue route and composite components use `PascalCase.vue`: `GameDetails.vue`, `FilesTab.vue`.
- v2 primitives use an `R` prefix and a same-named directory: `frontend/src/v2/lib/forms/RDropzone/RDropzone.vue`.
- TypeScript utilities/stores use `camelCase.ts`: `playerDisc.ts`, `galleryRoms.ts`.
- Tests use `test_*.py` in Python and `*.test.ts` beside frontend code.
- Generated models mirror backend schema names in `PascalCase.ts` under `frontend/src/__generated__/models/`.

**Directories:**

- Backend packages use lowercase singular functional names (`handler`, `models`) and lowercase plural domain groupings (`endpoints/roms`).
- v2 feature folders use `PascalCase` (`GameDetails`, `Gallery`, `Settings`); generic layer folders remain lowercase (`components`, `composables`, `utils`).
- Locale folders use locale codes and namespace JSON files: `frontend/src/locales/en_US/rom.json`.

## Where to Add New Code

**New Backend Feature:**

- Router/request boundary: `backend/endpoints/<domain>.py` or `backend/endpoints/<domain>/`
- Public response contract: `backend/endpoints/responses/<domain>.py`
- Business logic: `backend/handler/<domain>_handler.py` or the existing `database/`, `filesystem/`, `metadata/`, or `auth/` subpackage
- Persistence: `backend/models/<domain>.py`
- Migration: new revision under `backend/alembic/versions/`
- Tests: matching path under `backend/tests/`

**New ROM/File Capability:**

- ROM aggregate/category: `backend/models/rom.py`
- Database query/mutation: `backend/handler/database/roms_handler.py`
- Scanner/filesystem recognition: `backend/handler/filesystem/roms_handler.py` and `backend/handler/scan_handler.py`
- HTTP route: existing module under `backend/endpoints/roms/`
- Response schema: `backend/endpoints/responses/rom.py`
- Client wrapper: `frontend/src/services/api/rom.ts`
- Active UI: owning subfolder under `frontend/src/v2/components/GameDetails/`
- Tests: `backend/tests/endpoints/roms/`, `backend/tests/handler/filesystem/`, and co-located `frontend/src/v2/**/*.test.ts`

**New Metadata Provider:**

- Typed client: `backend/adapters/services/<provider>.py` plus provider type module
- Normalization/matching: `backend/handler/metadata/<provider>_handler.py`
- Scan composition: `backend/handler/scan_handler.py`
- Configuration: `backend/config/` and documented template keys
- Tests: `backend/tests/adapters/services/` and `backend/tests/handler/metadata/`

**New Background Task:**

- Recurring: `backend/tasks/scheduled/<task>.py`
- Admin/on-demand: `backend/tasks/manual/<task>.py`
- Initialization/registration: `backend/startup.py` or existing task endpoint registry
- Tests: `backend/tests/tasks/test_<task>.py`

**New v2 Feature:**

- Route view: `frontend/src/v2/views/<Feature>.vue`
- Feature composites: `frontend/src/v2/components/<Feature>/`
- Feature behavior: `frontend/src/v2/composables/use<Behavior>/index.ts`
- v2-only state: `frontend/src/v2/stores/<state>.ts`
- Shared API/state: extend `frontend/src/services/api/` or `frontend/src/stores/` additively
- Route registration: `frontend/src/v2/router/routes.ts` and shared route shell in `frontend/src/plugins/router.ts`
- Tests: co-located `*.test.ts`; primitive stories under the primitive folder

**New Component/Module:**

- Domain-free primitive: `frontend/src/v2/lib/<category>/RFoo/`
- Cross-feature composite: `frontend/src/v2/components/shared/`
- Feature composite: `frontend/src/v2/components/<Feature>/`
- Do not add new components under frozen `frontend/src/components/`.

**Utilities:**

- Backend cross-domain helper: `backend/utils/`; standalone executable developer tooling: `backend/tools/`.
- Shared frontend helper used by both versions: `frontend/src/utils/`.
- v2-only pure helper: `frontend/src/v2/utils/`.
- Avoid a utility when the behavior belongs to a handler, service, store, or composable.

## Special Directories

**`frontend/src/__generated__/`:**

- Purpose: OpenAPI-derived frontend contract.
- Generated: Yes, by the frontend generation command against the running backend.
- Committed: Yes.

**`frontend/src/v2/styles/tokens.css`:**

- Purpose: Generated CSS custom properties for v2 themes.
- Generated: Yes, from `frontend/src/v2/tokens/index.ts`.
- Committed: Yes.

**`backend/alembic/versions/`:**

- Purpose: Immutable ordered schema history.
- Generated: Initial skeleton may be generated, but every revision requires manual review.
- Committed: Yes.

**`backend/handler/metadata/fixtures/`:**

- Purpose: Static provider/platform indexes used during matching.
- Generated: Some fixture data is maintained or refreshed by project tooling.
- Committed: Yes.

**`backend/romm_test/`:**

- Purpose: Mock library and database bootstrap assets for backend tests/development.
- Generated: No.
- Committed: Yes.

**`frontend/src/locales/`:**

- Purpose: Per-locale, per-feature translation dictionaries and parity validators.
- Generated: No.
- Committed: Yes.

**`.planning/codebase/`:**

- Purpose: GSD codebase reference documents.
- Generated: Yes, by mapping workflows.
- Committed: Workflow-dependent.

---

_Structure analysis: 2026-08-04_
