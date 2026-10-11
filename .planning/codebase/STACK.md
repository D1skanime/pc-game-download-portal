# Technology Stack

**Analysis Date:** 2026-08-04

## Languages

**Primary:**

- Python 3.13 - FastAPI application, persistence, metadata adapters, filesystem operations, background jobs, and tests under `backend/`; the minimum is declared in `pyproject.toml` and pinned for development in `.python-version`.
- TypeScript 5.7 - Vue application, generated API types, stores, services, and tests under `frontend/src/`; the compiler version is declared in `frontend/package.json`.

**Secondary:**

- JavaScript (Node.js 24) - Vite configuration in `frontend/vite.config.js` and the ROM patching subprocess in `backend/utils/rom_patcher/patcher.js`.
- SQL - Alembic migrations under `backend/alembic/versions/` target MariaDB, MySQL, and PostgreSQL through SQLAlchemy.
- Shell - Container startup and build automation in `entrypoint.sh`, `docker/init_scripts/init`, and `docker/init_scripts/docker-entrypoint.sh`.
- HTML/CSS/Vue SFC - UI templates and styling in `frontend/src/**/*.vue`, including the active v2 UI in `frontend/src/v2/`.

## Runtime

**Environment:**

- Python 3.13, served by FastAPI via Uvicorn/Gunicorn; runtime dependencies are declared in `pyproject.toml`.
- Node.js 24.16 builds the frontend and provides the isolated RomPatcher.js runtime; build arguments are in `docker/Dockerfile`.
- Nginx 1.29.5 fronts the production application, serves built frontend/static files, and accelerates library downloads; see `docker/Dockerfile` and `docker/nginx/templates/default.conf.template`.
- Alpine Linux 3.23 is the production container base in `docker/Dockerfile`; the legacy top-level `Dockerfile` uses Ubuntu 22.04.

**Package Manager:**

- uv 0.11.2 manages Python dependencies from `pyproject.toml`.
- Lockfile: `uv.lock` present.
- npm 11.13.0 manages frontend dependencies from `frontend/package.json` and the patcher dependencies from `backend/utils/rom_patcher/package.json`.
- Lockfiles: `frontend/package-lock.json` and `backend/utils/rom_patcher/package-lock.json` present.

## Frameworks

**Core:**

- FastAPI 0.134.x - REST/OpenAPI backend and middleware in `backend/main.py` and `backend/endpoints/`.
- SQLAlchemy 2.0.x - ORM, database engine, and sessions in `backend/models/` and `backend/handler/database/`.
- Alembic 1.16.x - cross-database schema migrations in `backend/alembic/`.
- Vue 3.4+ - frontend application in `frontend/src/`.
- Vuetify 3.9+ - primary UI component framework configured by `frontend/src/plugins/vuetify.ts`.
- Pinia 3.0+ - client state stores in `frontend/src/stores/`.
- Vue Router 4.3+ - browser routing in `frontend/src/router/`.
- Socket.IO - real-time transport using `python-socketio` in the backend and `socket.io-client` in `frontend/src/services/socket.ts`.
- Redis/RQ - session storage, cache, pub/sub, job queues, and scheduled jobs through `backend/utils/cache.py`, `backend/tasks/`, and `backend/startup.py`.

**Testing:**

- pytest 9.x with pytest-asyncio, pytest-xdist, Hypothesis, fakeredis, and pytest-recording for backend tests in `backend/tests/`.
- Vitest 4.1+ with happy-dom and Vue Test Utils for frontend tests configured by `frontend/vitest.config.ts`.
- Playwright 1.61+ for end-to-end browser tests under `frontend/e2e/`.
- Storybook 10.2+ with accessibility checks and interaction tests for v2 primitives under `frontend/src/v2/lib/`.

**Build/Dev:**

- Vite 8 - frontend development server, production build, API/WebSocket proxy, and PWA build in `frontend/vite.config.js`.
- vue-tsc 2.2+ - strict Vue/TypeScript type checking through `npm run typecheck` in `frontend/package.json`.
- openapi-typescript-codegen 0.29 - generates Axios-compatible TypeScript models from backend `/openapi.json` into `frontend/src/__generated__/`.
- Trunk - repository-wide formatting, linting, type checks, and security checks configured under `.trunk/` and enforced by `.github/workflows/trunk-check.yml`.
- Multi-stage Docker BuildKit - produces slim/full/dev images from `docker/Dockerfile`.

## Key Dependencies

**Critical:**

- `aiohttp` 3.14.x and `httpx` 0.27.x - shared asynchronous HTTP clients for metadata, media, OIDC, and other network operations; context-managed clients are exposed by `backend/utils/context.py`.
- `pydantic` 2.11.x - request/response schemas and OpenAPI shapes in `backend/endpoints/responses/`.
- `fastapi-pagination[sqlalchemy]` 0.15.x - paginated API results.
- `redis` 6.2.x, `rq` 2.7.x, and a pinned `rq-scheduler` fork - cache, sessions, background work, and cron-like scheduling in `backend/tasks/` and `backend/startup.py`.
- `authlib` 1.6.x, `joserfc` 1.6.x, `itsdangerous` 2.2.x, `passlib`, `bcrypt`, and `cryptography` - OIDC, JWT, CSRF, session signing, token, and password security in `backend/handler/auth/`.
- `streaming-form-data` 1.19.x - streaming/chunked upload handling in `backend/endpoints/roms/upload.py` and middleware.
- `zstandard`, `zipfile-inflate64`, and filesystem/archive utilities - archive inspection, extraction, and streamed ZIP generation in `backend/utils/archives.py` and `backend/utils/zip_cache.py`.
- `axios` 1.18+ - central browser API client in `frontend/src/services/api/index.ts`.

**Infrastructure:**

- MariaDB Connector, MySQL Connector, and psycopg - SQLAlchemy database drivers selected through `ROMM_DB_DRIVER` in `backend/config/__init__.py` and `backend/config/config_manager.py`.
- Valkey/Redis-compatible server - development service `romm-valkey-dev` in `docker-compose.yml`; production code uses the Redis protocol.
- `sentry-sdk` 2.32+ - optional server error reporting initialized in `backend/main.py` and `backend/startup.py`.
- OpenTelemetry 0.56/1.36 packages - optional OTLP tracing/instrumentation for FastAPI, SQLAlchemy, Redis, aiohttp, and httpx, declared in `pyproject.toml`.
- `asyncssh` 2.23+ - device save/state sync over SSH in `backend/handler/sync/` and `backend/tasks/`.
- Pillow, mutagen, and python-magic - image processing, soundtrack metadata, and MIME detection in `backend/handler/filesystem/` and `backend/utils/`.

## Configuration

**Environment:**

- Environment variables are loaded centrally by `backend/config/__init__.py`; use `env.template` only as the checked-in example and never commit a live `.env`.
- Core runtime configuration includes `ROMM_BASE_URL`, `ROMM_PORT`, `ROMM_BASE_PATH`, database `DB_*`/`ROMM_DB_DRIVER`, Redis `REDIS_*`, and mandatory `ROMM_AUTH_SECRET_KEY`.
- Optional metadata, OIDC, Sentry, scheduling, sync, proxy, upload-limit, and emulator settings are also normalized in `backend/config/__init__.py`.
- Application-level YAML settings are managed by the singleton in `backend/config/config_manager.py` and stored below the configured RomM base path.

**Build:**

- `docker/Dockerfile` is the canonical multi-stage production/development image definition.
- `docker-compose.yml` defines local RomM, MariaDB, Valkey, PostgreSQL, and Authentik development services.
- `frontend/vite.config.js` configures Vue, Vuetify, Tailwind, PWA, HTTPS development, aliases, proxying, and browser targets.
- `frontend/tsconfig.json`, `frontend/vitest.config.ts`, and `.trunk/` define type checking, tests, and repository quality gates.

## Platform Requirements

**Development:**

- Python 3.13 with uv and Node.js 24 with npm 11.10+ are the declared manual-development requirements in `.python-version`, `pyproject.toml`, and `frontend/package.json`.
- Docker Compose is the integrated development path documented in `DEVELOPER_SETUP.md`; services include MariaDB 11.3.2, Valkey 8, optional PostgreSQL 16, and optional Authentik 2024.10.4 in `docker-compose.yml`.
- Native/archive tooling is supplied by the container build in `docker/Dockerfile`, including Nginx and compiled ROM hashing/emulation assets.

**Production:**

- Self-hosted Linux container deployment on port 8080 using the image built from `docker/Dockerfile`.
- Persistent host or volume storage is required for the configured library, resources, assets, cache, sync data, and database; path roots are defined in `backend/config/__init__.py`.
- A SQL database plus Redis-compatible service are required. MariaDB is the default; MySQL and PostgreSQL are supported through `ROMM_DB_DRIVER`.
- For a PC-game module or manifest-based downloader, extend the existing backend/OpenAPI/frontend-service pipeline and the download/filesystem seams in `backend/endpoints/roms/__init__.py`, `backend/endpoints/roms/files.py`, `backend/handler/filesystem/`, and `frontend/src/services/api/rom.ts`; do not create a second transport stack.

---

_Stack analysis: 2026-08-04_
