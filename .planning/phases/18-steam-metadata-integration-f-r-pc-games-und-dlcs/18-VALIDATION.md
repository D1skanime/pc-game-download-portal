# Phase 18 Validation Matrix

## Required evidence

| Area                   | Required proof                                                                                                                                                                            | Owning plan         |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| Steam service          | Mocked `de/CH` details, same-App-ID `en/US` field fallback, timeout, 429, region-miss, malformed-payload degradation                                                                      | 18-01               |
| Provider boundary      | `steam` priority/heartbeat/registry wiring is independent from `sgdb`                                                                                                                     | 18-03               |
| Persistence            | One Alembic head, nullable ROM/facet/component Steam fields, no component App-ID uniqueness                                                                                               | 18-02               |
| Portable migrations    | Upgrade, downgrade one revision, and re-upgrade for MariaDB plus a ready disposable PostgreSQL verifier container on the canonical Compose network                                        | 18-02, 18-08        |
| Generated API contract | Regenerated `PcComponentMetadataSchema.ts`, `RomSchema.ts`, and `DetailedRomSchema.ts` match backend response schemas and typecheck                                                       | 18-02               |
| Manual safety          | Independent title, summary, release date, and selected-artwork protections, with explicit `manual_metadata` provenance and legacy populated-field preservation                            | 18-04               |
| Main-game flow         | Persisted ID direct refresh after rename, supported platform search, excluded platform direct-ID-only behavior, non-PC no-call, non-fatal IGDB/Moby/LaunchBox fallback                    | 18-04               |
| DLC safety             | Unique hydrated IGDB identity before Steam, valid DLC type, normalized `fullgame.appid` parent check, unique high-confidence parentless path, all rejection paths preserve component data | 18-05               |
| v2 UAT                 | Steam tile/App-ID link verified at 320px, 768px, and 1440px in light/dark themes with mouse, touch, keyboard, gamepad, and accessibility-tree/screen-reader evidence                      | 18-03               |
| Frontend production    | Generated types, focused provider test, `npm run typecheck`, and `npm run build`                                                                                                          | 18-03, 18-06, 18-08 |

## Container-context migration commands

Run these commands from `/home/d1sk/romm`. They use only the canonical Linux
Compose network. PostgreSQL is verified by a uniquely named, disposable
container and database, never the shared `romm-postgres-dev` or Authentik
database.

```bash
docker compose exec -T romm-dev bash -lc 'cd /app/backend && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-db-dev DB_PORT=3306 ROMM_DB_DRIVER=mariadb uv run alembic heads && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-db-dev DB_PORT=3306 ROMM_DB_DRIVER=mariadb uv run alembic upgrade head && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-db-dev DB_PORT=3306 ROMM_DB_DRIVER=mariadb uv run alembic downgrade -1 && ROMM_AUTH_SECRET_KEY=phase18-migration DB_HOST=romm-db-dev DB_PORT=3306 ROMM_DB_DRIVER=mariadb uv run alembic upgrade head'
backend/tools/verify_phase18_postgres_migration.sh
```

The verifier derives PostgreSQL credentials from `docker compose config
--environment`, starts its own canonical-network `postgres:16-alpine`
container, waits for `pg_isready`, and uses an EXIT trap that preserves the
first failing status while removing that container. A service availability error
is not permission to weaken migration or test requirements.

## Completion gate

Do not mark Phase 18 complete until all rows have command or browser evidence,
the targeted backend suite passes, generated TypeScript artifacts are committed,
`npm run typecheck` and `npm run build` pass, the responsive/accessibility v2
UAT is approved, and `trunk fmt && trunk check` passes.
