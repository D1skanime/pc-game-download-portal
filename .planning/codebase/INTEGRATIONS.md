# External Integrations

**Analysis Date:** 2026-08-04

## APIs & External Services

**Game metadata and artwork:**

- IGDB - primary game/platform metadata, covers, screenshots, localization, ratings, and related games.
  - SDK/Client: typed custom `aiohttp` adapter in `backend/adapters/services/igdb.py`, normalized by `backend/handler/metadata/igdb_handler.py`.
  - Auth: Twitch OAuth2 client credentials via `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET`; token exchange is implemented in `backend/handler/metadata/igdb_handler.py`.
  - Endpoint: `https://api.igdb.com/v4`, with `https://id.twitch.tv/oauth2/token` for tokens.
- MobyGames - game metadata, companies, genres, and platform mappings.
  - SDK/Client: rate-limited custom adapter in `backend/adapters/services/mobygames.py`.
  - Auth: `MOBYGAMES_API_KEY` query parameter.
  - Endpoint: `https://api.mobygames.com/v1`.
- ScreenScraper - regional metadata and downloadable covers, screenshots, videos, manuals, marquees, and bezels.
  - SDK/Client: custom adapter and media concurrency controls in `backend/adapters/services/screenscraper.py`; persisted by `backend/handler/filesystem/resources_handler.py`.
  - Auth: `SCREENSCRAPER_USER`, `SCREENSCRAPER_PASSWORD`, plus build-injected `SCREENSCRAPER_DEV_ID` and `SCREENSCRAPER_DEV_PASSWORD`.
  - Endpoint: `https://api.screenscraper.fr/api2`.
- SteamGridDB - grid art, heroes, logos, and icons.
  - SDK/Client: bearer-authenticated adapter in `backend/adapters/services/steamgriddb.py`.
  - Auth: `STEAMGRIDDB_API_KEY`.
  - Endpoint: `https://steamgriddb.com/api/v2`.
- RetroAchievements - ROM identification, achievements, badges, and user progression.
  - SDK/Client: custom API adapter in `backend/adapters/services/retroachievements.py` with platform hashing in `backend/adapters/services/rahasher.py`.
  - Auth: `RETROACHIEVEMENTS_API_KEY`; per-user credentials/profiles are stored through the user model/API flow.
  - Endpoint: `https://retroachievements.org/API`.
- Libretro thumbnails - public thumbnail directory listings and images.
  - SDK/Client: custom adapter in `backend/adapters/services/libretro_thumbnails.py`, used by `backend/handler/metadata/libretro_handler.py`.
  - Auth: none.
- LaunchBox Games Database - remote metadata archive/media plus optional locally mounted LaunchBox XML/media tree.
  - SDK/Client: handler family in `backend/handler/metadata/launchbox_handler/`; scheduled archive retrieval is in `backend/tasks/scheduled/update_launchbox_metadata.py`.
  - Auth: none; enabled with `LAUNCHBOX_API_ENABLED`.
  - Endpoints: `https://gamesdb.launchbox-app.com/Metadata.zip` and `https://images.launchbox-app.com/`.
- Hasheous - hash lookup and metadata proxies for IGDB and RetroAchievements.
  - SDK/Client: custom handler in `backend/handler/metadata/hasheous_handler.py`.
  - Auth: none detected; enabled with `HASHEOUS_API_ENABLED`.
  - Endpoint: `https://hasheous.org/api/v1` or beta endpoint in development mode.
- TheGamesDB - hash and platform lookup.
  - SDK/Client: custom handler in `backend/handler/metadata/tgdb_handler.py`.
  - Auth: none detected; enabled with `TGDB_API_ENABLED`.
  - Endpoint: `https://api.thegamesdb.net/v1`.
- Flashpoint - browser-game metadata and artwork.
  - SDK/Client: custom handler in `backend/handler/metadata/flashpoint_handler.py`.
  - Auth: none detected; enabled with `FLASHPOINT_API_ENABLED`.
  - Endpoints: `https://db-api.unstable.life` and media from `https://infinity.unstable.life`.
- HowLongToBeat - completion-time metadata and cover art.
  - SDK/Client: custom scraper/API handler in `backend/handler/metadata/hltb_handler.py`; its current API path fixture can be refreshed from the RomM GitHub repository.
  - Auth: none detected; enabled with `HLTB_API_ENABLED`.
  - Endpoint: `https://howlongtobeat.com`.
- PlayMatch - hash-based game matching, with a configurable self-hosted target.
  - SDK/Client: custom handler in `backend/handler/metadata/playmatch_handler.py`.
  - Auth: none detected; enabled with `PLAYMATCH_API_ENABLED`.
  - Endpoint: `PLAYMATCH_API_URL`, defaulting in `backend/config/__init__.py` to the hosted PlayMatch v2 API.

**Browser emulation and release information:**

- EmulatorJS - browser emulator runtime bundled during container builds and loaded by both UIs from a configurable CDN-style data path; see `docker/Dockerfile`, `frontend/src/v2/views/Player/EmulatorJS.vue`, and legacy `frontend/src/views/Player/EmulatorJS/`.
  - SDK/Client: browser JavaScript runtime, version pinned by `EMULATORJS_VERSION` in `docker/Dockerfile`.
  - Auth: none.
- Ruffle - Flash emulator bundled in the image with an unpkg fallback in `frontend/src/v2/views/Player/Ruffle.vue`.
  - SDK/Client: `@ruffle-rs/ruffle`, version pinned by `RUFFLE_VERSION` in `docker/Dockerfile`.
  - Auth: none.
- GitHub Releases API - latest-version banner and changelog in `frontend/src/v2/components/Notifications/NewVersionBanner.vue` and `frontend/src/v2/components/Dialogs/ChangelogDialog.vue`.
  - SDK/Client: browser `fetch`.
  - Auth: none.
- Nintendo Switch title database - scheduled metadata JSON retrieval from GitHub in `backend/tasks/scheduled/update_switch_titledb.py`.
  - SDK/Client: shared backend HTTP client.
  - Auth: none.

## Data Storage

**Databases:**

- MariaDB is the default relational database; MySQL and PostgreSQL are supported by the same SQLAlchemy models and Alembic migrations.
  - Connection: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWD`, `DB_NAME`, `DB_QUERY_JSON`, and `ROMM_DB_DRIVER` from `backend/config/__init__.py`.
  - Client: SQLAlchemy 2 engines/session factories in `backend/handler/database/`, with URL construction in `backend/config/config_manager.py`.
  - Development services: MariaDB 11.3.2 and PostgreSQL 16 are defined in `docker-compose.yml`.

**File Storage:**

- Local or mounted filesystem only; no object-storage SDK is detected.
- Library ROMs live under `LIBRARY_BASE_PATH`; metadata media/resources under `RESOURCES_BASE_PATH`; user assets under `ASSETS_BASE_PATH`; ZIP cache under `ZIP_CACHE_PATH`; sync content under `SYNC_BASE_PATH`. All are derived in `backend/config/__init__.py`.
- Chunked upload staging uses `ROM_UPLOAD_TMP_BASE`; filesystem access is implemented in `backend/handler/filesystem/` and upload endpoints in `backend/endpoints/roms/upload.py`.
- Existing download delivery supports direct Starlette `FileResponse`, streamed ZIP generation, and Nginx internal redirects through `backend/endpoints/roms/__init__.py`, `backend/endpoints/roms/files.py`, `backend/utils/zip_cache.py`, and `backend/utils/nginx.py`.
- For manifest-based PC downloads, manifests should reference stable API/file identifiers and reuse these authenticated download routes. Do not expose arbitrary host paths or introduce direct frontend filesystem addressing.

**Caching:**

- Redis-compatible storage is required for application caches, sessions, JWT JTI tracking, metadata fixtures, Socket.IO/pub-sub coordination, RQ queues, job results, and scheduler state.
- Connection: `REDIS_HOST`, `REDIS_PORT`, `REDIS_USERNAME`, `REDIS_PASSWORD`, `REDIS_DB`, and `REDIS_SSL` in `backend/config/__init__.py`.
- Client: `redis`/`rq` in `backend/utils/cache.py`, `backend/tasks/`, `backend/startup.py`, and auth/session handlers.
- Development provider: Valkey 8 service `romm-valkey-dev` in `docker-compose.yml`.

## Authentication & Identity

**Auth Provider:**

- Custom hybrid authentication is canonical in `backend/handler/auth/` and `backend/decorators/auth.py`.
  - Implementation: Redis-backed session cookie, HTTP Basic, HS256 JWT access/refresh tokens, hashed `rmm_` client API tokens stored in SQL, optional kiosk read access, and CSRF cookie/header validation.
  - Secret/config: mandatory `ROMM_AUTH_SECRET_KEY`, token/session lifetime variables, `ROMM_SESSION_SECURE_COOKIE`, and CSRF/download feature flags in `backend/config/__init__.py`.
- Optional generic OpenID Connect integrates external identity providers through Authlib.
  - Implementation: discovery/metadata, authorization callback, role claim mapping, optional automatic login/registration, and RP-initiated logout in `backend/handler/auth/oidc.py` and `backend/endpoints/auth.py`.
  - Config: `OIDC_ENABLED`, `OIDC_PROVIDER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`, `OIDC_SERVER_APPLICATION_URL`, `OIDC_SERVER_METADATA_URL`, role/claim variables, CA certificate path, and logout variables in `backend/config/__init__.py`.
- Authentik server/worker services in `docker-compose.yml` provide the repository's local OIDC development target; RomM remains provider-agnostic.
- External native/PC clients should prefer scoped client API tokens rather than browser session cookies; token creation/exchange routes are in `backend/endpoints/client_tokens.py`.

## Monitoring & Observability

**Error Tracking:**

- Optional Sentry reporting, enabled by `SENTRY_DSN` and initialized in `backend/main.py` and `backend/startup.py` using `sentry-sdk`.

**Logs:**

- Python structured/application logging is centralized under `backend/logger/` with Gunicorn logging configured by `docker/gunicorn/logging.conf`.
- Logs are exposed to authorized clients through `backend/endpoints/logs.py` and live Socket.IO events in `backend/endpoints/sockets/logs.py`.
- OpenTelemetry packages in `pyproject.toml` support OTLP export and automatic instrumentation for FastAPI, SQLAlchemy, Redis, aiohttp, and httpx; runtime collector/exporter configuration is environment-driven rather than hard-coded.

## CI/CD & Deployment

**Hosting:**

- Self-hosted Docker/OCI image built by the multi-stage `docker/Dockerfile`, with Nginx, backend processes, Redis-compatible service support, frontend assets, and optional emulator payloads.
- GitHub Container Registry is used for referenced Authentik development images in `docker-compose.yml`; RomM build/release automation lives in `.github/workflows/build.yml` and `.github/workflows/test-build.yml`.

**CI Pipeline:**

- GitHub Actions workflows under `.github/workflows/` cover frontend tests/builds, type checking, i18n, backend pytest on supported databases, Alembic migrations, end-to-end tests, Docker builds, and Trunk checks.
- No external deployment platform such as Kubernetes, AWS, Azure, or managed PaaS is detected in the repository.

## Environment Configuration

**Required env vars:**

- `ROMM_AUTH_SECRET_KEY` is mandatory at import/startup in `backend/config/__init__.py`.
- A production database requires `DB_HOST`, `DB_USER`, `DB_PASSWD`, `DB_NAME`, and usually `ROMM_DB_DRIVER`; Redis requires the relevant `REDIS_*` connection variables.
- Metadata credentials are optional and provider-specific: `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`, `MOBYGAMES_API_KEY`, `SCREENSCRAPER_USER`, `SCREENSCRAPER_PASSWORD`, `STEAMGRIDDB_API_KEY`, and `RETROACHIEVEMENTS_API_KEY`.
- OIDC requires the `OIDC_*` client/provider variables when enabled; Sentry requires `SENTRY_DSN` when enabled.
- Proxy support follows standard `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY`, detected by `backend/config/__init__.py`.

**Secrets location:**

- Runtime environment variables or container secret injection; `env.template` documents names and placeholders.
- Live `.env` files and mounted sync SSH keys under `SYNC_SSH_KEYS_PATH` are host-local secrets and must not be read or committed.
- No cloud secret manager integration is detected.

## Webhooks & Callbacks

**Incoming:**

- OIDC authorization/logout callbacks are handled by auth routes in `backend/endpoints/auth.py`; exact redirect/public URLs are configured through `OIDC_REDIRECT_URI` and `OIDC_SERVER_APPLICATION_URL`.
- Socket.IO transports use `/ws/socket.io/` for application events and `/netplay` for netplay signaling, configured in `frontend/src/services/socket.ts` and backend socket endpoints under `backend/endpoints/sockets/`.
- Device pairing, token exchange, heartbeat, and sync negotiation are regular authenticated REST/Socket.IO APIs in `backend/endpoints/device_auth.py`, `backend/endpoints/client_tokens.py`, `backend/endpoints/device.py`, and `backend/endpoints/sync.py`, not third-party webhooks.

**Outgoing:**

- No generic outbound webhook delivery subsystem is detected.
- Server-initiated outbound traffic is limited to configured metadata/media providers, OIDC discovery/token flows, optional Sentry/OTLP telemetry, GitHub-hosted update data, device SSH sync, and provider URLs passed through validated media-download logic in `backend/handler/filesystem/resources_handler.py` and `backend/utils/ssrf.py`.

---

_Integration audit: 2026-08-04_
