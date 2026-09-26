# Phase 18: Steam Metadata Integration for PC Games and DLCs - Pattern Map

**Mapped:** 2026-09-25  
**Files analyzed:** 19  
**Analogs found:** 12 / 12

## File Classification

| New/Modified File                                                                          | Role              | Data Flow        | Closest Analog                                            | Match Quality |
| ------------------------------------------------------------------------------------------ | ----------------- | ---------------- | --------------------------------------------------------- | ------------- |
| `backend/adapters/services/steam.py`                                                       | service           | request-response | existing `steam.py`                                       | exact         |
| `backend/adapters/services/steam_types.py`                                                 | model             | transform        | existing `steam_types.py`                                 | exact         |
| `backend/handler/metadata/steam_handler.py`                                                | service           | request-response | existing `steam_handler.py`                               | exact         |
| `backend/handler/metadata/pc_match_handler.py`                                             | service           | request-response | IGDB/SGDB candidate adapters in the same file             | exact         |
| `backend/handler/scan_handler.py`                                                          | service           | batch            | SGDB enrichment and priority application in the same file | role-match    |
| `backend/endpoints/sockets/scan.py`                                                        | controller        | event-driven     | `_enrich_pc_dlc_from_igdb`                                | exact         |
| `backend/handler/database/roms_handler.py`                                                 | service           | CRUD             | PC candidate and component persistence methods            | exact         |
| `backend/models/rom.py`                                                                    | model             | CRUD             | existing provider ID/metadata columns                     | exact         |
| `backend/alembic/versions/0119_add_steam_metadata.py`                                      | migration         | transform        | `0118_pc_igdb_structured_metadata.py`                     | role-match    |
| `backend/endpoints/roms/pc_metadata.py`                                                    | controller        | request-response | existing candidate selection routes                       | exact         |
| `backend/endpoints/responses/rom.py`                                                       | model             | transform        | `PcComponentMetadataSchema`                               | exact         |
| `backend/watcher.py`, `backend/endpoints/heartbeat.py`, `backend/config/config_manager.py` | config/controller | event-driven     | existing provider registration maps                       | exact         |
| `frontend/src/v2/components/GameDetails/providers.ts`                                      | utility           | transform        | `PROVIDERS` registry entries                              | exact         |
| `frontend/src/v2/views/Settings/MetadataSources.vue`                                       | component         | request-response | flag-only provider tile                                   | exact         |
| `backend/tests/adapters/services/test_steam.py`                                            | test              | request-response | existing locale request test                              | exact         |
| `backend/tests/handler/metadata/test_steam_handler.py`                                     | test              | request-response | existing same-ID fallback test                            | exact         |
| `backend/tests/models/test_pc_igdb_metadata.py`                                            | test              | CRUD             | persistence/migration assertions                          | exact         |
| `backend/tests/endpoints/roms/test_pc_metadata.py`                                         | test              | request-response | manual candidate selection tests                          | exact         |
| `backend/tests/endpoints/sockets/test_scan.py`                                             | test              | event-driven     | trusted DLC enrichment tests                              | exact         |

## Pattern Assignments

### `backend/adapters/services/steam.py` and `steam_types.py` (service/model, request-response)

**Analog:** existing Steam transport, [steam.py](../../../backend/adapters/services/steam.py) lines 28-86, with typed shapes in [steam_types.py](../../../backend/adapters/services/steam_types.py).

**Imports and client lifecycle** (lines 6-25):

```python
from aiohttp.client import ClientTimeout

from utils.context import ctx_aiohttp_session
from utils.rate_limiter import RateLimiter

_rate_limiter = RateLimiter(STEAM_MAX_REQUESTS_PER_SECOND)
```

**Failure-isolated transport** (lines 34-62):

```python
session = ctx_aiohttp_session.get()
for attempt in range(STEAM_MAX_REQUEST_ATTEMPTS):
    await _rate_limiter.acquire()
    try:
        response = await session.get(url, headers={...}, timeout=ClientTimeout(...))
        response.raise_for_status()
        payload = await response.json()
        return payload if isinstance(payload, dict) else {}
    except TimeoutError:
        continue
    except aiohttp.ClientResponseError as exc:
        if exc.status == http.HTTPStatus.TOO_MANY_REQUESTS and attempt < ...:
            await asyncio.sleep(STEAM_RATE_LIMIT_BACKOFF_SECONDS)
            continue
        log.warning("Steam request failed: %s", exc)
        return {}
    except json.JSONDecodeError:
        return {}
return {}
```

Keep the public no-key service and its empty-result degradation. Add defensive typed parsing for `type`, `fullgame`, and media rather than passing remote payloads into persistence unchanged.

### `backend/handler/metadata/steam_handler.py` (metadata service, request-response)

**Analog:** [steam_handler.py](../../../backend/handler/metadata/steam_handler.py) lines 15-136.

**Platform gate and no-result contract** (lines 52-74):

```python
if not self.is_enabled() or platform_slug not in STEAM_PLATFORMS:
    return SteamRom(steam_id=None)
...
apps = [item for item in apps if item.get("type") == "app"]
match, _ = self.find_best_match(term, [item["name"] for item in apps], self.min_similarity_score)
if not match:
    return SteamRom(steam_id=None)
return await self.get_rom_by_id(...)
```

**Same-App-ID fallback and field-level merging** (lines 76-93, 109-135):

```python
preferred = await self.steam_service.get_app_details(steam_id, country=..., language=...)
if not preferred or preferred.get("type") not in {"game", "dlc"}:
    return SteamRom(steam_id=None)
fallback = None
if not preferred.get("name") or not preferred.get("short_description"):
    fallback = await self.steam_service.get_app_details(steam_id, country=..., language=...)
...
name = preferred.get("name") or (fallback or {}).get("name", "")
summary = preferred.get("short_description") or (fallback or {}).get("short_description", "")
```

Do not move fallback to name search. The scan resolver should call `get_rom_by_id(existing_steam_id)` before considering filename matching, including after a rename. Explicit IDs may be resolved on `dos`, `win3x`, and `win9x`; only the `STEAM_PLATFORMS` set permits automatic search.

### `backend/handler/metadata/pc_match_handler.py` (candidate service, request-response)

**Analog:** [pc_match_handler.py](../../../backend/handler/metadata/pc_match_handler.py) lines 53-82 and 190-321.

**Provider registration and outage isolation** (lines 56-62, 197-221):

```python
self.providers = providers or {
    "igdb": meta_igdb_handler,
    "moby": meta_moby_handler,
    "sgdb": meta_sgdb_handler,
    "launchbox": meta_launchbox_handler,
}
...
if not provider.is_enabled():
    results[provider_name] = PcMetadataProviderResult(provider_name, False, [], "disabled")
    continue
try:
    provider_results = await self._lookup(provider_name, provider, rom, title)
except Exception:
    results[provider_name] = PcMetadataProviderResult(provider_name, False, [], "unavailable")
    continue
```

**Candidate identity, allowlist, and media normalization** (lines 243-321): candidate IDs are a SHA-256 fingerprint of provider, provider IDs, title, and media. Extend the allowlist in `_candidate()` with `steam_id` and `steam_metadata`; add `steam` to `_lookup()` using `get_matched_roms_by_name(title, rom.platform_slug)`. Reuse `_media()` so Steam art remains selectable candidate media, not direct selected-artwork writes.

**DLC identity boundary** (lines 84-108, 137-188): build on `fetch_unique_related_igdb_candidate()` and retain its single-candidate guard. Steam DLC lookup must occur only after this hydrates the IGDB candidate, then require a valid DLC type and matching Storefront `fullgame` parent where supplied. Return no enrichment for ambiguous, invalid, wrong-parent, bundle, soundtrack, demo, edition, tool, or unrelated results.

### `backend/handler/scan_handler.py` and `backend/endpoints/sockets/scan.py` (scan service/controller, batch/event-driven)

**Analog:** [scan_handler.py](../../../backend/handler/scan_handler.py) lines 996-1111 and 1189-1249; [test_scan.py](../../../backend/tests/endpoints/sockets/test_scan.py) lines 66-150 documents the DLC scan seam.

**Provider map and priority shape** (scan lines 996-1057):

```python
MetadataSource.IGDB: {
    "handler": igdb_handler_rom,
    "id_field": "igdb_id",
    "metadata_field": "igdb_metadata",
},
```

Add Steam with `steam_id` and `steam_metadata` to this map, source gathering, completeness checks, and priority availability. Preserve the generic priority loop for normal providers, but route PC Steam fields through one dedicated non-empty, manual-safe normalizer instead of allowing the generic loop to overwrite main-game fields or IGDB relationships.

**Artwork safety precedent** (scan lines 1229-1248):

```python
manual_cover_preserved = (
    not newly_added
    and scan_type in (ScanType.UNMATCHED, ScanType.UPDATE)
    and rom.path_cover_s
)
if sgdb_cover and not manual_cover_preserved:
    ...
    if ranked[0] == MetadataSource.SGDB:
        rom_attrs["url_cover"] = sgdb_cover
```

Use the same priority and selected-state principles. Steam can supply candidates only; never replace already selected or manually overridden cover/screenshot paths.

### `backend/handler/database/roms_handler.py`, `models/rom.py`, and `endpoints/responses/rom.py` (persistence/model/schema, CRUD/transform)

**Analog:** [roms_handler.py](../../../backend/handler/database/roms_handler.py) lines 1762-1803 and 1806-1872; [rom.py](../../../backend/models/rom.py) lines 324-347, 568-657, 1068-1103; [responses/rom.py](../../../backend/endpoints/responses/rom.py) lines 308-329.

**Optimistic manual selection write** (handler lines 1762-1780):

```python
result = session.execute(
    update(Rom)
    .where(and_(Rom.id == id, Rom.updated_at == expected_updated_at))
    .values(**data)
    .execution_options(synchronize_session="evaluate")
)
if result.rowcount != 1:
    return None
session.flush()
session.expire_all()
return session.query(Rom).filter_by(id=id).one()
```

The main automatic path and manual selected-candidate path must call the same Steam normalizer before this persistence boundary. The normalizer must write only non-empty Steam title, summary, developer, publisher, release, IDs, metadata and candidate URLs, and protect manual title, summary, release date, and selected artwork independently.

**Component mutation pattern** (handler lines 1839-1869): create `RomComponentMetadata` lazily, allowlist fields, set `metadata_source`, retain provider metadata, then update `component.updated_at` and flush. Add `steam_id` and `steam_metadata` to this explicit component allowlist. Do not add a uniqueness constraint: the model intentionally permits shared component App IDs.

**Schema/coverage mirrors:** maintain the `Rom`, `RomFacets`, `METADATA_SOURCE_COLUMNS`, `METADATA_SOURCE_FACET_COLUMNS`, component schema, and response serialization as one unit. Steam is already shown in these current locations, which makes them the source of truth for any corrections.

### `backend/alembic/versions/0119_add_steam_metadata.py` (migration, transform)

**Analog:** [0119_add_steam_metadata.py](../../../backend/alembic/versions/0119_add_steam_metadata.py) lines 17-34, and cross-dialect view handling in [0118_pc_igdb_structured_metadata.py](../../../backend/alembic/versions/0118_pc_igdb_structured_metadata.py) lines 19-89.

```python
op.add_column("roms", sa.Column("steam_id", sa.Integer(), nullable=True))
op.add_column("roms", sa.Column("steam_metadata", sa.JSON(), nullable=True))
op.add_column("roms_facets", sa.Column("steam_id", sa.Integer(), nullable=True))
op.add_column("rom_component_metadata", sa.Column("steam_id", sa.Integer(), nullable=True))
...
op.drop_column("rom_component_metadata", "steam_metadata")
```

Keep nullable columns and exact reverse-order downgrade. If the migration needs view/generated-column work, branch on `is_postgresql(op.get_bind())` as `0118` does. Verify upgrade, downgrade one revision, and re-upgrade on the supported dialects.

### Registration and v2 display (config/controller/component, event-driven/transform)

**Analogs:** [watcher.py](../../../backend/watcher.py) lines 63-78; [heartbeat.py](../../../backend/endpoints/heartbeat.py) lines 151-189; [providers.ts](../../../frontend/src/v2/components/GameDetails/providers.ts) lines 22-93; [MetadataSources.vue](../../../frontend/src/v2/views/Settings/MetadataSources.vue) lines 28-59 and 61-148.

**Registration pattern:** every provider has an enabled-handler entry in the watcher map, a `MetadataSource` match arm in heartbeat, and the config-priority slug in `VALID_SCAN_PRIORITY_SOURCES`. Import the existing singleton `meta_steam_handler`, never instantiate a separate handler.

**Provider card pattern:** model Steam as `requiresKey: false`, read `STEAM_API_ENABLED` from `METADATA_SOURCES`, give it a Storefront URL, add `steam: undefined` in local heartbeat state, and use the existing disabled/connection status machinery. Add a provider registry entry keyed by `steam_id` with `https://store.steampowered.com/app/${id}`. Keep `sgdb` unchanged and separate.

### Tests (test, request-response/CRUD/event-driven)

**Analogs:** [test_steam.py](../../../backend/tests/adapters/services/test_steam.py) lines 8-36; [test_steam_handler.py](../../../backend/tests/handler/metadata/test_steam_handler.py) lines 21-41; [test_pc_igdb_metadata.py](../../../backend/tests/models/test_pc_igdb_metadata.py) lines 65-81; [test_scan.py](../../../backend/tests/endpoints/sockets/test_scan.py) lines 66-150; [test_pc_metadata.py](../../../backend/tests/endpoints/roms/test_pc_metadata.py).

**Mocked locale assertion:**

```python
calls = handler.steam_service.get_app_details.await_args_list
assert [call.args[0] for call in calls] == [1091500, 1091500]
assert calls[0].kwargs == {"country": "CH", "language": "de"}
assert calls[1].kwargs == {"country": "US", "language": "en"}
```

Add focused tests for stored-ID refresh after rename, platform gate, malformed/429/unavailable degradation, candidate/provider registration, normalized non-empty merge and each manual protection, Steam component persistence without App-ID uniqueness, parent/missing-parent DLC criteria, invalid product types, no component creation, and selected artwork preservation. Keep tests mocked, no live Storefront dependency.

## Shared Patterns

### Authentication and optimistic concurrency

**Source:** [pc_metadata.py](../../../backend/endpoints/roms/pc_metadata.py) lines 70-99 and 420-466.

Routes use `@protected_route` with `Scope.ROMS_READ` or `Scope.ROMS_WRITE`, retrieve the ROM, call `assert_rom_visible`, re-collect the candidate server-side, and return `422` for unknown candidates or `409` for stale `expected_version`. Steam must use this existing manual candidate flow, not a Steam-only route.

### Error handling and logging

**Source:** [steam.py](../../../backend/adapters/services/steam.py) lines 34-62 and [pc_match_handler.py](../../../backend/handler/metadata/pc_match_handler.py) lines 201-215.

An external-provider fault becomes `{}` or an unavailable provider result, never a failed scan or destructive write. Log bounded structured context only: provider, platform, query, App ID, language, confidence, and fallback outcome. Do not log Storefront payloads or secrets.

### Media ownership

**Source:** [pc_metadata.py](../../../backend/endpoints/roms/pc_metadata.py) lines 148-207.

Only candidate media selected by the user is downloaded through `fs_resource_handler.store_pc_component_provider_image`, then persisted with provider origin and a current version. Reuse the same owned-media path for DLC imports; do not write selected cover/screenshot paths directly from Steam lookup results.

## No Analog Found

| File/Concern                        | Role    | Data Flow    | Reason                                                                                                                                                                        |
| ----------------------------------- | ------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Steam-specific PC normalizer        | utility | transform    | Existing generic scan merge cannot express the required independent manual-field and IGDB-relationship protections. Implement as a small, isolated helper with focused tests. |
| Steam-after-IGDB DLC safety matcher | service | event-driven | Existing automatic DLC enrichment is IGDB-only. Extend its narrow seam, retaining the unique hydrated IGDB candidate guard.                                                   |

## Metadata

**Analog search scope:** `backend/adapters/services`, `backend/handler`, `backend/endpoints`, `backend/models`, `backend/alembic`, `backend/tests`, `frontend/src/v2`  
**Files scanned:** 19  
**Pattern extraction date:** 2026-09-25
