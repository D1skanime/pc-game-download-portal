# Phase 32 Naming Inventory

Inventory is the pre-mutation naming boundary for Plan 32-01.

## Disposition counts

- `rename`: product-owned fresh-install identity and disposable fixtures
- `retain`: compatibility, provenance, runtime paths, schemas, providers, and upstream URLs
- `investigate/stop`: zero unclassified bounded occurrences

The pre-mutation bounded scan covered the Plan 32-01 file list and recorded exact path and line ranges for all 279 matching lines. The full repository scan found 13,578 tracked matches. Relevant untracked files: none.

## Exact-path scan evidence

| Path | Line ranges | Disposition |
| --- | --- | --- |
| `examples/portainer-stack.yml` | 4, 8-15, 29-37, 51-63, 79-91 | `rename` product identity, `retain` `/romm` and runtime keys |
| `examples/portainer.env.example` | 7-12, 17, 23-31, 34, 38-48 | `rename` wrapper surface and paths |
| `examples/docker-compose.example.yml` | 3-8, 12-14, 23-27, 31, 35, 37, 41-42 | `rename` deployment identity, `retain` runtime paths/providers |
| `docker-compose.yml` | 4, 8, 11-12, 22, 26-34, 39-50, 54-56, 62, 64, 69, 76, 78, 83-85, 97-98, 100, 102, 107-109, 118-119, 122 | `rename` disposable dev identity, `retain` `/app/romm` paths |
| `docker-compose.override.yml` | 2, 6, 8, 11, 14, 17, 22, 27 | `rename` disposable dev service references |
| `env.template` | 2-5, 9, 12, 28, 38-39, 113-114, 122 | `rename` product-owned fresh DB default, `retain` canonical runtime |
| `backend/config/__init__.py` | 25-26, 35-43, 47, 52, 83, 85, 186, 211-213, 236, 238, 241-242, 342, 389 | `retain` compatibility runtime and `/romm` |
| `backend/pytest.ini` | 6, 8-9, 11, 20 | `rename` synthetic DB/path, `retain` runtime/auth keys |
| `backend/romm_test/setup.sql` | 1-8 | `rename` synthetic DB bootstrap |
| `backend/docker-compose.test.yml` | 10, 12 | `rename` isolated synthetic test DB |
| `backend/docker-compose.pc-integration-test.yml` | 3, 11-22, 33-64, 69-88, 114-121, 123-142, 170-177, 183-223 | `rename` image/fixture DB identity, `retain` phase labels and `/romm` |
| `backend/docker-compose.immutability-test.yml` | 3, 14-25, 34-81, 86, 97-108, 120-154, 161-209, 213-227 | `rename` image/fixture DB identity, `retain` phase labels and `/romm` |
| `backend/docker-compose.policy-test.yml` | 3, 24 | `rename` disposable image identity |

## Retained-name allowlist

- `ROMM_BASE_PATH`, `ROMM_PORT`, `ROMM_BASE_URL`, `ROMM_DB_DRIVER`, `ROMM_AUTH_SECRET_KEY`, canonical `DB_*`, `REDIS_*` runtime keys.
- `/romm`, `/assets/romm`, `romm_session`, `romm_csrftoken`, `romm-api-cache`, and frontend resource symlinks.
- Schema/table/column/Alembic/model identifiers, including `Rom`, `RomMetadataSchema`, and `RomMWorker`.
- Provider IDs, ScreenScraper `softname=romm`, provider cache keys, user-agent contracts, and external API parameters.
- `rommapp/romm`, `romm.app`, `docs.romm.app`, upstream GitHub release/feed/HLTB URLs, issue references, legal/history attribution, and phase provenance labels.

## D-05 operator wrapper boundary

`PGDP_*` is the sole product-owned operator wrapper surface. Compose translates PGDP project/image/container/path/port/database/password/auth-secret inputs one-way into canonical `DB_*` and retained `ROMM_*` runtime keys. Legacy wrapper aliases such as `ROMM_DB_PASSWORD`, `ROMM_LIBRARY_PATH`, `ROMM_ASSETS_PATH`, `ROMM_CONFIG_PATH`, and `ROMM_HTTP_PORT` are not accepted. No data, media, game directory, database, NAS mount, or existing RomM volume is moved, deleted, or adopted.

## Hard stop

Any new bounded occurrence not matching `rename` or `retain`, any unclassified path, any legacy wrapper alias, or any migration/old-volume-adoption claim stops Plan 32-01 before mutation.

```text
git grep -n -I -i -E 'rommapp|romm' -- ':!*.lock' ':!frontend/src/__generated__/*'
tracked matches: 13,578
relevant untracked files: none
```

