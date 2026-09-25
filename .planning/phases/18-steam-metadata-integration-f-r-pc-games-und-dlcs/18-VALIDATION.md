# Phase 18 Validation Matrix

## Required evidence

| Area                   | Required proof                                                                                                                                                                            | Owning plan |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| Steam service          | Mocked `de/CH` details, same-App-ID `en/US` field fallback, timeout, 429, region-miss, malformed-payload degradation                                                                      | 18-01       |
| Provider boundary      | `steam` priority/heartbeat/registry wiring is independent from `sgdb`                                                                                                                     | 18-03       |
| Persistence            | One Alembic head, nullable ROM/facet/component Steam fields, no component App-ID uniqueness                                                                                               | 18-02       |
| Portable migrations    | Upgrade, downgrade one revision, and re-upgrade in the project Docker network for MariaDB and a disposable PostgreSQL database                                                            | 18-02       |
| Generated API contract | Regenerated `PcComponentMetadataSchema.ts`, `RomSchema.ts`, and `DetailedRomSchema.ts` match backend response schemas and typecheck                                                       | 18-02       |
| Manual safety          | Independent title, summary, release date, and selected-artwork protections, with explicit `manual_metadata` provenance and legacy populated-field preservation                            | 18-04       |
| Main-game flow         | Persisted ID direct refresh after rename, supported platform search, excluded platform direct-ID-only behavior, non-PC no-call, non-fatal IGDB/Moby/LaunchBox fallback                    | 18-04       |
| DLC safety             | Unique hydrated IGDB identity before Steam, valid DLC type, normalized `fullgame.appid` parent check, unique high-confidence parentless path, all rejection paths preserve component data | 18-05       |
| v2 UAT                 | Steam tile/App-ID link separately verified in light and dark themes with mouse, touch, keyboard, and gamepad                                                                              | 18-03       |

## Container-context migration commands

Run these commands exactly from `/home/d1sk/romm`. They use only the canonical
Linux Compose network. PostgreSQL uses the disposable
`romm_phase18_migration` database, never the Authentik database.

```bash
docker compose exec -T romm-dev bash -lc 'cd /app/backend && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-db-dev DB_PORT=3306 ROMM_DB_DRIVER=mariadb uv run alembic heads && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-db-dev DB_PORT=3306 ROMM_DB_DRIVER=mariadb uv run alembic upgrade head && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-db-dev DB_PORT=3306 ROMM_DB_DRIVER=mariadb uv run alembic downgrade -1 && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-db-dev DB_PORT=3306 ROMM_DB_DRIVER=mariadb uv run alembic upgrade head'
docker compose exec -T romm-postgres-dev sh -lc 'dropdb --if-exists -U "$POSTGRES_USER" romm_phase18_migration && createdb -U "$POSTGRES_USER" romm_phase18_migration'
docker compose exec -T romm-dev bash -lc 'cd /app/backend && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-postgres-dev DB_PORT=5432 DB_NAME=romm_phase18_migration DB_USER=romm DB_PASSWD=authentik ROMM_DB_DRIVER=postgresql uv run alembic upgrade head && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-postgres-dev DB_PORT=5432 DB_NAME=romm_phase18_migration DB_USER=romm DB_PASSWD=authentik ROMM_DB_DRIVER=postgresql uv run alembic downgrade -1 && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-postgres-dev DB_PORT=5432 DB_NAME=romm_phase18_migration DB_USER=romm DB_PASSWD=authentik ROMM_DB_DRIVER=postgresql uv run alembic upgrade head'
docker compose exec -T romm-postgres-dev sh -lc 'dropdb --if-exists -U "$POSTGRES_USER" romm_phase18_migration'
```

If a command fails, record its exact output and run the final PostgreSQL drop
command. A service availability error is not permission to weaken migration or
test requirements.

## Completion gate

Do not mark Phase 18 complete until all rows have command or browser evidence,
the targeted backend suite passes, generated TypeScript artifacts are committed,
`npm run typecheck` passes, and `trunk fmt && trunk check` passes.
