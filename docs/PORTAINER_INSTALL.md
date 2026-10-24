# ZockArchive Portainer installation

This guide covers PC and console libraries using the Git-source [stack](../examples/portainer-stack.yml) and [environment template](../examples/portainer.env.example). Keep filled environment files and secrets outside Git.

## Storage and prerequisites

Use a Docker host with Portainer support for Git-based Compose stacks, enough build/database storage, and three existing absolute host directories.

| Input               | Container target  | Access                            |
| ------------------- | ----------------- | --------------------------------- |
| `PGDP_LIBRARY_PATH` | `/romm/library`   | Read-only source archive          |
| `PGDP_ASSETS_PATH`  | `/romm/assets`    | Writable assets, saves and states |
| `PGDP_CONFIG_PATH`  | `/romm/config`    | Writable configuration            |
| `pgdp_resources`    | `/romm/resources` | Persistent managed resources      |
| `pgdp_redis_data`   | `/redis-data`     | Persistent Redis/Valkey state     |
| `pgdp_mysql_data`   | `/var/lib/mysql`  | Persistent MariaDB catalog        |

Paths must exist on the Docker host, not only on an administrator workstation. Keep the source archive outside Git and separate from writable application targets.

Synology example paths, not universal defaults:

```text
/volume1/Games
/volume1/docker/pc-downloadportal/assets
/volume1/docker/pc-downloadportal/config
```

For QNAP use actual storage-pool/share paths exposed to its Docker daemon. Linux examples are `/srv/pgdp/library`, `/srv/pgdp/assets` and `/srv/pgdp/config`. Confirm ownership and read/write access before deploying. Existing paths remain valid under the ZockArchive name.

## Create the Git stack

1. Open **Stacks > Add stack > Git repository**.
2. Use repository <https://github.com/D1skanime/zockarchive.git>.
3. Select `main` or a reviewed tag/commit.
4. Set Compose path to `examples/portainer-stack.yml`.
5. Copy the template into the protected stack environment.
6. Replace required placeholders and host paths.
7. Confirm the library mount has `:ro` and writable targets are separate.
8. Review the revision and storage settings, then deploy.

Build context `..` resolves from `examples/` to the repository root. The stack builds `docker/Dockerfile`, target `full-image`. `PGDP_IMAGE` defaults to `pc-game-download-portal:portainer`, the local tag for that build. Preserve existing overrides. A deliberate prebuilt-image deployment requires separate provenance/version verification.

## Existing installations and Git URL changes

Update the existing stack's Git URL to <https://github.com/D1skanime/zockarchive.git> during an authorized maintenance window. Retain reference, Compose path, project/container overrides, environment values, host paths and volumes. Review the revision before rebuilding.

A source rename does not move the canonical development checkout `/home/d1sk/pc-game-download-portal` or migrate registry packages and Docker storage. Do not create a differently named replacement stack and assume it reuses the same data. Portainer changes are operator actions, not performed by reading this guide.

## Retained operator settings

All `PGDP_*` and `ROMM_*` keys retain their exact names and values.

| Setting                  | Existing default or purpose                          |
| ------------------------ | ---------------------------------------------------- |
| `PGDP_PROJECT_NAME`      | `pgdp`, Compose project                              |
| `PGDP_CONTAINER_NAME`    | `pgdp`, application container                        |
| `PGDP_DB_CONTAINER_NAME` | `pgdp-db`, database container                        |
| `PGDP_IMAGE`             | `pc-game-download-portal:portainer`, local build tag |
| `PGDP_DB_NAME`           | `pgdp`                                               |
| `PGDP_DB_USER`           | `pgdp-user`                                          |
| `PGDP_HTTP_PORT`         | `8080`, internal port remains 8080                   |
| `PGDP_TZ`                | `UTC`                                                |
| `PGDP_DB_PASSWORD`       | Required application database password               |
| `PGDP_DB_ROOT_PASSWORD`  | Required separate MariaDB root password              |
| `PGDP_AUTH_SECRET_KEY`   | Required persistent authentication secret            |

Services remain `pgdp` and `pgdp-db`. Keep `pgdp_mysql_data`, `pgdp_resources` and `pgdp_redis_data`. Compose may prefix actual volumes with the project name. Do not recreate them to change branding.

For a fresh installation generate separate strong values, for example using `openssl rand -hex 32`. Existing installations retain authentication secrets and database credentials unless following a separate credential-rotation procedure. Never paste secrets into issues, screenshots or logs.

## Optional providers

Portainer inputs use the `PGDP_` prefix and map to existing runtime keys. Empty credentials leave that provider unavailable while base library/login operation remains usable.

- `PGDP_SCREENSCRAPER_USER` and `PGDP_SCREENSCRAPER_PASSWORD`: personal credentials.
- `PGDP_SCREENSCRAPER_DEV_ID` and `PGDP_SCREENSCRAPER_DEV_PASSWORD`: source-build application credentials, passed to Docker build arguments. Store in the protected stack environment or a secret store, and rebuild after changes.
- `PGDP_RETROACHIEVEMENTS_API_KEY`: RetroAchievements access.
- `PGDP_STEAMGRIDDB_API_KEY`: personal SteamGridDB API key.
- `PGDP_IGDB_CLIENT_ID` and `PGDP_IGDB_CLIENT_SECRET`: Twitch developer application credentials for IGDB.
- `PGDP_HASHEOUS_API_ENABLED`: optional Hasheous integration switch.

Upstream RomM images and embedded application credentials belong to upstream. Do not assume they are available in this source build. ScreenScraper may reject an unconfigured source build with HTTP 403.

Get credentials from each provider's account/developer portal. IGDB uses a Twitch developer application. ZockArchive renews tokens internally using client ID/secret. See [IGDB documentation](https://api-docs.igdb.com/) and [SteamGridDB API documentation](https://www.steamgriddb.com/api/v2).

## Startup and a bounded check

1. Wait for `pgdp-db`, then `pgdp`, to become healthy.
2. Open the configured host port, such as `http://<NAS-IP>:8080`.
3. Complete first-user setup or sign in.
4. Check a platform mapping beneath the read-only library root.
5. Scan a small authorized test library and check metadata.
6. Test configured providers, DLC presentation and a small download.
7. Compare source contents and directory structure before and after.

The entrypoint prepares the environment and applies migrations. Ordinary startup needs no manual schema command. If startup fails, check required variables and writable target permissions. Access times can change during reads; see [read-only operations](external-read-only-library-operations.md).

## Updates, backups and rollback

Back up catalog and managed state using your database-aware backup procedure:

- Actual project-prefixed `pgdp_mysql_data`, `pgdp_resources` and `pgdp_redis_data` volumes.
- `PGDP_ASSETS_PATH` and `PGDP_CONFIG_PATH`.
- Stack settings, path overrides and secrets in a secure recovery store.

The source archive follows your separate NAS backup policy. Never delete, replace or copy it into Git during updates.

Select the reviewed revision, rebuild and redeploy the existing stack with the same identities/storage. Recheck health, login, library and a small download. For rollback select the previous known revision and reuse state only where schema compatibility permits. Code rollback is not database rollback. Restore a matching backup using a version-compatible procedure when required.

## Image publication and support ownership

Release automation retains full/slim aliases `d1skanime/pc-game-download-portal` and `ghcr.io/d1skanime/pc-game-download-portal`. Preview automation retains `pc-game-download-portal-testing` in the selected registry/credential namespace. These are configured destinations, not proof of publication or access.

Package accessibility is **unverified**: inventory returned HTTP 403 without `read:packages`. No new public ZockArchive GHCR/Docker Hub alias is advertised. Repository redirects do not establish registry redirects or package migration. This guide uses Git-source builds.

Use [ZockArchive issues](https://github.com/D1skanime/zockarchive/issues), [releases](https://github.com/D1skanime/zockarchive/releases) and repository docs. [Upstream RomM](https://github.com/rommapp/romm) remains the origin. Its docs, community and donation accounts belong to upstream.

## Troubleshooting and verification limits

- Required variable missing: check exact keys and replace placeholders.
- Empty library: check host path and read permissions.
- Failed mapping/scan: check the authorized relative platform folder.
- Unwritable assets/config: check separate writable host directories.
- Unhealthy database: check matching credentials and persistent volume.
- Missing metadata: check selected provider credentials and container DNS/HTTPS.
- Old version: check Git revision and whether the application was rebuilt.

Run `bash scripts/verify-portainer-stack.sh` in the canonical Linux checkout to render and inspect the template. It does not deploy. Static/synthetic checks do not establish live Synology, QNAP, production Portainer, NAS or physical hardware acceptance. Supplied artwork and platform-specific installer proof remain separate work.
