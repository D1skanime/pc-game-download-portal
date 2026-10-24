# ZockArchive branding and compatibility contract

ZockArchive is the current product name, abbreviated ZA, for the PC and console
archive. The source repository is [D1skanime/zockarchive](https://github.com/D1skanime/zockarchive).
Current HTML, manifests, project links and operator guides use this identity.
The naming and Portainer verifiers consume this tracked document and tracked
source files, so an installation proof needs no planning or research directory.

## Retained compatibility

`PGDP_*` operator inputs, `ROMM_*` runtime inputs, pgdp services, databases and volumes,
the local pc-game-download-portal:portainer image, /romm runtime paths and browser
keys retain their existing meanings. A repository rename does not move the
canonical /home/d1sk/pc-game-download-portal checkout or publish a registry image.
Native RomM Desktop packaging retains its installation identity until a separately
verified migration exists. Display names do not authorize data or auth migrations.

RomM provenance, licenses, copyright and provider/upstream names belong to their
original owners. Historical planning records, receipts and decision documents are
history and are outside current display assertions. ROM remains a domain term.
There is deliberately no global prohibition on raw RomM or PGDP text.

## Current source assertions

Records below are parsed as literal, pipe-delimited lines. Surface records bound
the residual-name audit to reviewed current owners. Require records assert
current identity. Retain records allow only the exact reviewed path and full line,
including technical syntax, compatibility guidance or upstream attribution.
A new residual occurrence requires classification and review of this contract.
Legal files, historical records and other upstream domain owners are not rewritten.

```text
surface|frontend/index.html|
surface|frontend/public/site.webmanifest|
surface|frontend/src/PGDP.vue|
surface|frontend/src/v2/config/project.ts|
surface|README.md|
surface|docs/PORTAINER_INSTALL.md|
surface|examples/README.md|
surface|examples/portainer-stack.yml|
surface|examples/portainer.env.example|
surface|examples/docker-compose.example.yml|
surface|frontend/package.json|
surface|frontend/src/main.ts|
surface|backend/config/__init__.py|
surface|backend/pytest.ini|
surface|backend/romm_test/setup.sql|
require|frontend/index.html|<title>ZockArchive</title>
require|frontend/public/site.webmanifest|"name": "ZockArchive"
require|frontend/public/site.webmanifest|"short_name": "ZA"
require|frontend/src/v2/config/project.ts|D1skanime/zockarchive
require|README.md|# ZockArchive
require|README.md|https://github.com/D1skanime/zockarchive
require|docs/PORTAINER_INSTALL.md|# ZockArchive
require|docs/PORTAINER_INSTALL.md|https://github.com/D1skanime/zockarchive.git
require|examples/README.md|https://github.com/D1skanime/zockarchive.git
require|examples/portainer-stack.yml|# ZockArchive
require|examples/portainer.env.example|# ZockArchive
retain|frontend/src/PGDP.vue|// Lazy-loaded: PGDP.vue is the first module main.ts evaluates, and the banner
retain|frontend/src/PGDP.vue|// import TDZ during bootstrap (PGDP.vue is the first module main.ts loads).
retain|README.md|Portainer builds the selected Git revision with `docker/Dockerfile`. The local image tag remains `pc-game-download-portal:portainer` and can be overridden with `PGDP_IMAGE`. This local build tag is not evidence of a published registry image. Registry aliases and external accessibility are described in the installation guide.
retain|README.md|Keep the original archive mounted at `/romm/library:ro`. Store database, resources, Redis data, assets and configuration separately. Preserve existing stack names, host paths and volumes when updating.
retain|README.md|The product name is ZockArchive, abbreviated ZA. Existing `PGDP_*` and `ROMM_*` keys, `pgdp` services/project defaults, database names, persistent volumes, storage paths, browser/session/cache keys and native desktop identifiers remain compatibility contracts.
retain|README.md|The canonical development checkout remains `/home/d1sk/pc-game-download-portal` on `team4s-linux`. A repository URL change does not move that directory or migrate packages, credentials, data or Portainer settings.
retain|README.md|ZockArchive derives from [upstream RomM](https://github.com/rommapp/romm), a self-hosted ROM manager and player. Upstream documentation and provider integrations remain attributed to their owners. Upstream donation and community accounts do not belong to ZockArchive.
retain|docs/PORTAINER_INSTALL.md|| `PGDP_LIBRARY_PATH` | `/romm/library`   | Read-only source archive          |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_ASSETS_PATH`  | `/romm/assets`    | Writable assets, saves and states |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_CONFIG_PATH`  | `/romm/config`    | Writable configuration            |
retain|docs/PORTAINER_INSTALL.md|| `pgdp_resources`    | `/romm/resources` | Persistent managed resources      |
retain|docs/PORTAINER_INSTALL.md|| `pgdp_redis_data`   | `/redis-data`     | Persistent Redis/Valkey state     |
retain|docs/PORTAINER_INSTALL.md|| `pgdp_mysql_data`   | `/var/lib/mysql`  | Persistent MariaDB catalog        |
retain|docs/PORTAINER_INSTALL.md|For QNAP use actual storage-pool/share paths exposed to its Docker daemon. Linux examples are `/srv/pgdp/library`, `/srv/pgdp/assets` and `/srv/pgdp/config`. Confirm ownership and read/write access before deploying. Existing paths remain valid under the ZockArchive name.
retain|docs/PORTAINER_INSTALL.md|Build context `..` resolves from `examples/` to the repository root. The stack builds `docker/Dockerfile`, target `full-image`. `PGDP_IMAGE` defaults to `pc-game-download-portal:portainer`, the local tag for that build. Preserve existing overrides. A deliberate prebuilt-image deployment requires separate provenance/version verification.
retain|docs/PORTAINER_INSTALL.md|A source rename does not move the canonical development checkout `/home/d1sk/pc-game-download-portal` or migrate registry packages and Docker storage. Do not create a differently named replacement stack and assume it reuses the same data. Portainer changes are operator actions, not performed by reading this guide.
retain|docs/PORTAINER_INSTALL.md|All `PGDP_*` and `ROMM_*` keys retain their exact names and values.
retain|docs/PORTAINER_INSTALL.md|| `PGDP_PROJECT_NAME`      | `pgdp`, Compose project                              |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_CONTAINER_NAME`    | `pgdp`, application container                        |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_DB_CONTAINER_NAME` | `pgdp-db`, database container                        |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_IMAGE`             | `pc-game-download-portal:portainer`, local build tag |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_DB_NAME`           | `pgdp`                                               |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_DB_USER`           | `pgdp-user`                                          |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_HTTP_PORT`         | `8080`, internal port remains 8080                   |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_TZ`                | `UTC`                                                |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_DB_PASSWORD`       | Required application database password               |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_DB_ROOT_PASSWORD`  | Required separate MariaDB root password              |
retain|docs/PORTAINER_INSTALL.md|| `PGDP_AUTH_SECRET_KEY`   | Required persistent authentication secret            |
retain|docs/PORTAINER_INSTALL.md|Services remain `pgdp` and `pgdp-db`. Keep `pgdp_mysql_data`, `pgdp_resources` and `pgdp_redis_data`. Compose may prefix actual volumes with the project name. Do not recreate them to change branding.
retain|docs/PORTAINER_INSTALL.md|Portainer inputs use the `PGDP_` prefix and map to existing runtime keys. Empty credentials leave that provider unavailable while base library/login operation remains usable.
retain|docs/PORTAINER_INSTALL.md|- `PGDP_SCREENSCRAPER_USER` and `PGDP_SCREENSCRAPER_PASSWORD`: personal credentials.
retain|docs/PORTAINER_INSTALL.md|- `PGDP_SCREENSCRAPER_DEV_ID` and `PGDP_SCREENSCRAPER_DEV_PASSWORD`: source-build application credentials, passed to Docker build arguments. Store in the protected stack environment or a secret store, and rebuild after changes.
retain|docs/PORTAINER_INSTALL.md|- `PGDP_RETROACHIEVEMENTS_API_KEY`: RetroAchievements access.
retain|docs/PORTAINER_INSTALL.md|- `PGDP_STEAMGRIDDB_API_KEY`: personal SteamGridDB API key.
retain|docs/PORTAINER_INSTALL.md|- `PGDP_IGDB_CLIENT_ID` and `PGDP_IGDB_CLIENT_SECRET`: Twitch developer application credentials for IGDB.
retain|docs/PORTAINER_INSTALL.md|- `PGDP_HASHEOUS_API_ENABLED`: optional Hasheous integration switch.
retain|docs/PORTAINER_INSTALL.md|Upstream RomM images and embedded application credentials belong to upstream. Do not assume they are available in this source build. ScreenScraper may reject an unconfigured source build with HTTP 403.
retain|docs/PORTAINER_INSTALL.md|1. Wait for `pgdp-db`, then `pgdp`, to become healthy.
retain|docs/PORTAINER_INSTALL.md|- Actual project-prefixed `pgdp_mysql_data`, `pgdp_resources` and `pgdp_redis_data` volumes.
retain|docs/PORTAINER_INSTALL.md|- `PGDP_ASSETS_PATH` and `PGDP_CONFIG_PATH`.
retain|docs/PORTAINER_INSTALL.md|Release automation retains full/slim aliases `d1skanime/pc-game-download-portal` and `ghcr.io/d1skanime/pc-game-download-portal`. Preview automation retains `pc-game-download-portal-testing` in the selected registry/credential namespace. These are configured destinations, not proof of publication or access.
retain|docs/PORTAINER_INSTALL.md|Use [ZockArchive issues](https://github.com/D1skanime/zockarchive/issues), [releases](https://github.com/D1skanime/zockarchive/releases) and repository docs. [Upstream RomM](https://github.com/rommapp/romm) remains the origin. Its docs, community and donation accounts belong to upstream.
retain|examples/README.md|The stack builds the selected Git revision using `docker/Dockerfile`. `PGDP_IMAGE` defaults to the existing local tag `pc-game-download-portal:portainer`. It is not an advertised public image. Preserve project, service, database, volume and host-path overrides.
retain|examples/README.md|`docker-compose.example.yml` is a manual prebuilt-image example. Its local `pc-game-download-portal:latest` tag must already be built or supplied by an operator who verified its provenance. It is not a verified registry publication.
retain|examples/README.md|Optional provider credentials may remain blank. ScreenScraper source builds need the two `PGDP_SCREENSCRAPER_DEV_*` build inputs as well as personal credentials.
retain|examples/portainer-stack.yml|name: ${PGDP_PROJECT_NAME:-pgdp}
retain|examples/portainer-stack.yml|  pgdp_mysql_data:
retain|examples/portainer-stack.yml|  pgdp_resources:
retain|examples/portainer-stack.yml|  pgdp_redis_data:
retain|examples/portainer-stack.yml|  pgdp:
retain|examples/portainer-stack.yml|        SCREENSCRAPER_DEV_ID: ${PGDP_SCREENSCRAPER_DEV_ID:-}
retain|examples/portainer-stack.yml|        SCREENSCRAPER_DEV_PASSWORD: ${PGDP_SCREENSCRAPER_DEV_PASSWORD:-}
retain|examples/portainer-stack.yml|    image: ${PGDP_IMAGE:-pc-game-download-portal:portainer}
retain|examples/portainer-stack.yml|    container_name: ${PGDP_CONTAINER_NAME:-pgdp}
retain|examples/portainer-stack.yml|      DB_HOST: pgdp-db
retain|examples/portainer-stack.yml|      DB_NAME: ${PGDP_DB_NAME:-pgdp}
retain|examples/portainer-stack.yml|      DB_USER: ${PGDP_DB_USER:-pgdp-user}
retain|examples/portainer-stack.yml|      DB_PASSWD: ${PGDP_DB_PASSWORD:?Set PGDP_DB_PASSWORD in Portainer}
retain|examples/portainer-stack.yml|      ROMM_AUTH_SECRET_KEY: ${PGDP_AUTH_SECRET_KEY:?Set PGDP_AUTH_SECRET_KEY in Portainer}
retain|examples/portainer-stack.yml|      TZ: ${PGDP_TZ:-UTC}
retain|examples/portainer-stack.yml|      SCREENSCRAPER_USER: ${PGDP_SCREENSCRAPER_USER:-}
retain|examples/portainer-stack.yml|      SCREENSCRAPER_PASSWORD: ${PGDP_SCREENSCRAPER_PASSWORD:-}
retain|examples/portainer-stack.yml|      RETROACHIEVEMENTS_API_KEY: ${PGDP_RETROACHIEVEMENTS_API_KEY:-}
retain|examples/portainer-stack.yml|      STEAMGRIDDB_API_KEY: ${PGDP_STEAMGRIDDB_API_KEY:-}
retain|examples/portainer-stack.yml|      IGDB_CLIENT_ID: ${PGDP_IGDB_CLIENT_ID:-}
retain|examples/portainer-stack.yml|      IGDB_CLIENT_SECRET: ${PGDP_IGDB_CLIENT_SECRET:-}
retain|examples/portainer-stack.yml|      HASHEOUS_API_ENABLED: ${PGDP_HASHEOUS_API_ENABLED:-true}
retain|examples/portainer-stack.yml|      - pgdp_resources:/romm/resources
retain|examples/portainer-stack.yml|      - pgdp_redis_data:/redis-data
retain|examples/portainer-stack.yml|      - ${PGDP_LIBRARY_PATH:?Set PGDP_LIBRARY_PATH in Portainer}:/romm/library:ro
retain|examples/portainer-stack.yml|      - ${PGDP_ASSETS_PATH:?Set PGDP_ASSETS_PATH in Portainer}:/romm/assets
retain|examples/portainer-stack.yml|      - ${PGDP_CONFIG_PATH:?Set PGDP_CONFIG_PATH in Portainer}:/romm/config
retain|examples/portainer-stack.yml|      # Change only the host-side port in PGDP_HTTP_PORT if 8080 is occupied.
retain|examples/portainer-stack.yml|      - "${PGDP_HTTP_PORT:-8080}:8080"
retain|examples/portainer-stack.yml|      pgdp-db:
retain|examples/portainer-stack.yml|  pgdp-db:
retain|examples/portainer-stack.yml|    container_name: ${PGDP_DB_CONTAINER_NAME:-pgdp-db}
retain|examples/portainer-stack.yml|      MARIADB_ROOT_PASSWORD: ${PGDP_DB_ROOT_PASSWORD:?Set PGDP_DB_ROOT_PASSWORD in Portainer}
retain|examples/portainer-stack.yml|      MARIADB_DATABASE: ${PGDP_DB_NAME:-pgdp}
retain|examples/portainer-stack.yml|      MARIADB_USER: ${PGDP_DB_USER:-pgdp-user}
retain|examples/portainer-stack.yml|      MARIADB_PASSWORD: ${PGDP_DB_PASSWORD:?Set PGDP_DB_PASSWORD in Portainer}
retain|examples/portainer-stack.yml|      - pgdp_mysql_data:/var/lib/mysql
retain|examples/portainer.env.example|PGDP_PROJECT_NAME=pgdp
retain|examples/portainer.env.example|PGDP_IMAGE=pc-game-download-portal:portainer
retain|examples/portainer.env.example|PGDP_CONTAINER_NAME=pgdp
retain|examples/portainer.env.example|PGDP_DB_CONTAINER_NAME=pgdp-db
retain|examples/portainer.env.example|PGDP_TZ=UTC
retain|examples/portainer.env.example|PGDP_HTTP_PORT=8080
retain|examples/portainer.env.example|# PGDP_LIBRARY_PATH=/volume1/Games
retain|examples/portainer.env.example|# PGDP_ASSETS_PATH=/volume1/docker/pc-downloadportal/assets
retain|examples/portainer.env.example|# PGDP_CONFIG_PATH=/volume1/docker/pc-downloadportal/config
retain|examples/portainer.env.example|PGDP_LIBRARY_PATH=/srv/pgdp/library
retain|examples/portainer.env.example|PGDP_ASSETS_PATH=/srv/pgdp/assets
retain|examples/portainer.env.example|PGDP_CONFIG_PATH=/srv/pgdp/config
retain|examples/portainer.env.example|PGDP_DB_NAME=pgdp
retain|examples/portainer.env.example|PGDP_DB_USER=pgdp-user
retain|examples/portainer.env.example|PGDP_DB_PASSWORD=replace-with-a-long-random-password
retain|examples/portainer.env.example|# Required. Use a different unique long value from PGDP_DB_PASSWORD.
retain|examples/portainer.env.example|PGDP_DB_ROOT_PASSWORD=replace-with-a-different-long-random-password
retain|examples/portainer.env.example|PGDP_AUTH_SECRET_KEY=replace-with-openssl-rand-hex-32
retain|examples/portainer.env.example|PGDP_SCREENSCRAPER_USER=
retain|examples/portainer.env.example|PGDP_SCREENSCRAPER_PASSWORD=
retain|examples/portainer.env.example|PGDP_SCREENSCRAPER_DEV_ID=
retain|examples/portainer.env.example|PGDP_SCREENSCRAPER_DEV_PASSWORD=
retain|examples/portainer.env.example|PGDP_RETROACHIEVEMENTS_API_KEY=
retain|examples/portainer.env.example|PGDP_STEAMGRIDDB_API_KEY=
retain|examples/portainer.env.example|PGDP_IGDB_CLIENT_ID=
retain|examples/portainer.env.example|PGDP_IGDB_CLIENT_SECRET=
retain|examples/portainer.env.example|PGDP_HASHEOUS_API_ENABLED=true
retain|examples/docker-compose.example.yml|  pgdp_mysql_data:
retain|examples/docker-compose.example.yml|  pgdp_resources:
retain|examples/docker-compose.example.yml|  pgdp_redis_data:
retain|examples/docker-compose.example.yml|  pgdp:
retain|examples/docker-compose.example.yml|    image: pc-game-download-portal:latest
retain|examples/docker-compose.example.yml|    container_name: pgdp
retain|examples/docker-compose.example.yml|      - DB_HOST=pgdp-db
retain|examples/docker-compose.example.yml|      - DB_NAME=pgdp # Should match MARIADB_DATABASE in mariadb
retain|examples/docker-compose.example.yml|      - DB_USER=pgdp-user # Should match MARIADB_USER in mariadb
retain|examples/docker-compose.example.yml|      - ROMM_AUTH_SECRET_KEY= # Generate a key with `openssl rand -hex 32`
retain|examples/docker-compose.example.yml|      - SCREENSCRAPER_PASSWORD= # Upstream RomM reference: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#screenscraper
retain|examples/docker-compose.example.yml|      - RETROACHIEVEMENTS_API_KEY= # Upstream RomM reference: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#retroachievements
retain|examples/docker-compose.example.yml|      - STEAMGRIDDB_API_KEY= # Upstream RomM reference: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#steamgriddb
retain|examples/docker-compose.example.yml|      - HASHEOUS_API_ENABLED=true # Upstream RomM reference: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#hasheous
retain|examples/docker-compose.example.yml|      - pgdp_resources:/romm/resources # Resources fetched from IGDB (covers, screenshots, etc.)
retain|examples/docker-compose.example.yml|      - pgdp_redis_data:/redis-data # Cached data for background tasks
retain|examples/docker-compose.example.yml|      - /path/to/library:/romm/library:ro # Upstream RomM reference: Your game library. Check https://docs.romm.app/latest/Getting-Started/Folder-Structure/ for more details.
retain|examples/docker-compose.example.yml|      - /path/to/assets:/romm/assets # Uploaded saves, states, etc.
retain|examples/docker-compose.example.yml|      - /path/to/config:/romm/config # (Optional) Path where config.yml is stored
retain|examples/docker-compose.example.yml|      pgdp-db:
retain|examples/docker-compose.example.yml|  pgdp-db:
retain|examples/docker-compose.example.yml|    container_name: pgdp-db
retain|examples/docker-compose.example.yml|      - MARIADB_DATABASE=pgdp
retain|examples/docker-compose.example.yml|      - MARIADB_USER=pgdp-user
retain|examples/docker-compose.example.yml|      - pgdp_mysql_data:/var/lib/mysql
retain|frontend/src/main.ts|import App from "@/PGDP.vue";
retain|frontend/src/main.ts|const CHUNK_RELOAD_KEY = "romm-chunk-reload-at";
retain|backend/config/__init__.py|ROMM_BASE_URL: Final[str] = _get_env("ROMM_BASE_URL", "http://0.0.0.0")
retain|backend/config/__init__.py|ROMM_PORT: Final[int] = safe_int(_get_env("ROMM_PORT"), 8080)
retain|backend/config/__init__.py|ROMM_BASE_PATH: Final[str] = _get_env("ROMM_BASE_PATH", "/romm")
retain|backend/config/__init__.py|ROMM_TMP_PATH: Final[str | None] = _get_env("ROMM_TMP_PATH")
retain|backend/config/__init__.py|LIBRARY_BASE_PATH: Final[str] = f"{ROMM_BASE_PATH}/library"
retain|backend/config/__init__.py|RESOURCES_BASE_PATH: Final[str] = f"{ROMM_BASE_PATH}/resources"
retain|backend/config/__init__.py|ASSETS_BASE_PATH: Final[str] = f"{ROMM_BASE_PATH}/assets"
retain|backend/config/__init__.py|ZIP_CACHE_PATH: Final[str] = f"{ROMM_BASE_PATH}/cache/zips"
retain|backend/config/__init__.py|DATABASE_BASE_PATH: Final[str] = f"{ROMM_BASE_PATH}/database"
retain|backend/config/__init__.py|CONFIG_BASE_PATH: Final[str] = f"{ROMM_BASE_PATH}/config"
retain|backend/config/__init__.py|CACHE_BASE_PATH: Final[str] = f"{ROMM_BASE_PATH}/cache"
retain|backend/config/__init__.py|FRONTEND_RESOURCES_PATH: Final[str] = "/assets/romm/resources"
retain|backend/config/__init__.py|    Path(ROMM_TMP_PATH) if ROMM_TMP_PATH else Path(RESOURCES_BASE_PATH)
retain|backend/config/__init__.py|DB_NAME: Final[str] = _get_env("DB_NAME", "pgdp")
retain|backend/config/__init__.py|ROMM_DB_DRIVER: Final[str] = _get_env("ROMM_DB_DRIVER", "mariadb")
retain|backend/config/__init__.py|LAUNCHBOX_BASE_PATH: Final[str] = f"{ROMM_BASE_PATH}/launchbox"
retain|backend/config/__init__.py|ROMM_AUTH_SECRET_KEY: Final[str] = _get_env("ROMM_AUTH_SECRET_KEY", "")
retain|backend/config/__init__.py|if not ROMM_AUTH_SECRET_KEY:
retain|backend/config/__init__.py|    raise ValueError("ROMM_AUTH_SECRET_KEY environment variable is not set!")
retain|backend/config/__init__.py|ROMM_CORS_ALLOWED_ORIGINS: Final[list[str]] = [
retain|backend/config/__init__.py|    for o in (_get_env("ROMM_CORS_ALLOWED_ORIGINS", "*")).split(",")
retain|backend/config/__init__.py|ROMM_SESSION_SECURE_COOKIE: Final[bool] = safe_str_to_bool(
retain|backend/config/__init__.py|    _get_env("ROMM_SESSION_SECURE_COOKIE")
retain|backend/config/__init__.py|SYNC_BASE_PATH: Final[str] = f"{ROMM_BASE_PATH}/sync"
retain|backend/pytest.ini|   ROMM_AUTH_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
retain|backend/romm_test/setup.sql|CREATE DATABASE IF NOT EXISTS pgdp_test;
retain|backend/romm_test/setup.sql|CREATE USER IF NOT EXISTS 'pgdp_test'@'%' IDENTIFIED BY 'passwd';
retain|backend/romm_test/setup.sql|-- Grant on the `pgdp_test%` namespace (the base DB plus the per-worker
retain|backend/romm_test/setup.sql|-- `pgdp_test_gw0`, ... databases created under pytest-xdist). A database-level
retain|backend/romm_test/setup.sql|GRANT ALL PRIVILEGES ON `pgdp\_test%`.* TO 'pgdp_test'@'%' WITH GRANT OPTION;
```

## Verification authority

CI accepts only the exact D1skanime/zockarchive origin and matching Actions
repository/workspace, with optional .git suffix normalization. Inherited SQL, Redis,
Compose, pytest and run-token overrides fail before provisioning. The canonical
Linux checkout path is unchanged. Historical scan and description probes retain
their own branch, host and planning identities with the current source URL; a
current-phase runner composes their fixture/client functions through the existing
disposable target authority instead of widening those historical entrypoints.

## Disposable evidence

Fresh installation receipts belong only to the generated run directory under
Phase 38 evidence/install. The proof retains exact project labels, temporary paths
and owned Compose cleanup. Historical Phase 32 summaries and inventory are never
outputs. A fresh proof does not establish production NAS, hardware, upgrade or
registry availability.
