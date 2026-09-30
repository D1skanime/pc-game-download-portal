# Phase 21: Unify admin PC scans with German Steam metadata and media - Pattern Map

**Mapped:** 2026-09-30
**Files analyzed:** 10 planned new or modified files
**Analogs found:** 10 / 10

## File Classification

| New/Modified File                                    | Role                       | Data Flow                   | Closest Analog                                                       | Match Quality         |
| ---------------------------------------------------- | -------------------------- | --------------------------- | -------------------------------------------------------------------- | --------------------- |
| `backend/handler/metadata/pc_steam_enrichment.py`    | service / utility          | transform, request-response | `backend/handler/scan_handler.py::resolve_steam_scan_metadata`       | exact seam extraction |
| `backend/handler/scan_handler.py`                    | scan orchestrator          | batch, request-response     | its `fetch_steam_updates()` provider coroutine                       | exact                 |
| `backend/endpoints/roms/pc_metadata.py`              | protected endpoint         | request-response            | `select_pc_metadata_candidate()`                                     | exact                 |
| `backend/handler/metadata/steam_merge.py`            | pure metadata utility      | transform                   | `normalize_steam()`                                                  | exact                 |
| `backend/handler/metadata/rom_media.py`              | provider candidate utility | transform                   | `discover_provider_media()`                                          | exact                 |
| `backend/handler/metadata/steam_owned_media.py`      | service                    | file-I/O, batch             | `backend/endpoints/roms/media.py::refresh_media`                     | role-match            |
| `backend/handler/database/roms_handler.py`           | repository                 | CRUD, batch                 | `reconcile_provider_owned_media()` and `set_owned_media_placement()` | exact                 |
| `backend/tests/handler/test_scan_handler.py`         | test                       | async request-response      | existing `resolve_steam_scan_metadata` tests at lines 268-379        | exact                 |
| `backend/tests/handler/metadata/test_steam_merge.py` | test                       | transform                   | existing `normalize_steam` tests at lines 4-150                      | exact                 |
| `backend/tests/handler/database/test_rom_media.py`   | test                       | CRUD, batch                 | existing reconciliation and placement tests at lines 274-472         | exact                 |

No frontend files, routes, schemas, or migrations are expected. Phase 20 already exposes the owned-media catalog and selected placements through the v2 Media UI. Preserve that transport and model rather than introducing scan-specific frontend state.

## Pattern Assignments

### `backend/handler/metadata/pc_steam_enrichment.py` (new service, transform/request-response)

**Analog:** `backend/handler/scan_handler.py:191-220`, `backend/handler/metadata/steam_merge.py:14-70`

Extract the current scan lookup into a metadata-layer function that accepts a lightweight current-state mapping and returns a normalized patch. It must not receive a `Session` or write a `Rom`.

**Persisted-ID-first gate and error isolation** (`scan_handler.py:191-220`):

```python
if (
    MetadataSource.STEAM not in metadata_sources
    or platform.slug not in STEAM_EXPLICIT_ID_PLATFORMS
):
    return {}

try:
    if isinstance(rom.steam_id, int) and not isinstance(rom.steam_id, bool):
        result = await meta_steam_handler.get_rom_by_id(rom.steam_id, platform.slug)
        if result.get("steam_id") != rom.steam_id:
            return {}
    elif platform.slug in STEAM_PLATFORMS:
        result = await meta_steam_handler.get_rom(fs_name, platform.slug)
    else:
        return {}
except Exception:
    log.warning("Steam metadata lookup failed", extra={...})
    return {}

return normalize_steam(result, current)
```

Keep this order exactly: selected-and-enabled provider gate, persisted valid App ID, one normalized-name lookup only for supported platforms, same-ID validation, then `normalize_steam()`. The catch returns `{}` so unavailable, malformed, ambiguous, and rate-limited responses cannot trigger persistence or inventory removal.

**Same-App-ID locale primitive** (`backend/handler/metadata/steam_handler.py:97-124`):

```python
preferred = await self.steam_service.get_app_details(
    steam_id, country=STEAM_API_COUNTRY, language=STEAM_API_LANGUAGE
)
if not preferred or preferred.get("type") not in {"game", "dlc"}:
    return SteamRom(steam_id=None)
fallback = None
if self._needs_fallback(preferred):
    fallback = await self.steam_service.get_app_details(
        steam_id,
        country=STEAM_API_FALLBACK_COUNTRY,
        language=STEAM_API_FALLBACK_LANGUAGE,
    )
return await self._build_rom(preferred, fallback)
```

Do not duplicate locale merging or issue a second broad search. `SteamHandler.get_rom_by_id()` owns the German-first, English-only-for-missing-fields behavior.

### `backend/handler/scan_handler.py` (scan orchestrator, batch/request-response)

**Analog:** `scan_handler.py:1051-1149`

Keep Steam as a coroutine in the existing `asyncio.gather(..., return_exceptions=True)` tuple. Replace the local lookup implementation with the shared enrichment boundary, retain the existing provider failure fallback, and consume the returned patch only after the ROM has a durable identity.

```python
async def fetch_steam_updates() -> dict[str, Any]:
    return await resolve_steam_scan_metadata(
        rom, platform, rom_attrs["fs_name"], metadata_sources
    )

provider_fetches = (..., (fetch_steam_updates(), {}))
fetch_results = await asyncio.gather(
    *(coro for coro, _ in provider_fetches), return_exceptions=True
)
```

Do not retain `_steam_artwork_handler()` as the owned-media persistence contract. Its `url_cover` and `url_screenshots` projection (`scan_handler.py:223-235`) is legacy display-field behavior and cannot preserve provider origin, tombstones, owned bytes, or manual placements.

### `backend/endpoints/roms/pc_metadata.py` (endpoint, request-response)

**Analog:** `pc_metadata.py:423-529`

Retain the protected route, candidate validation, and conflict response. Delegate Steam details-to-patch construction to the same shared boundary/helper used by scanning. Keep endpoint code limited to request selection and existing `apply_pc_metadata_candidate()` persistence.

```python
@protected_route(router.post, "/{id}/pc-metadata-selection", [Scope.ROMS_WRITE])
async def select_pc_metadata_candidate(...):
    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)
    assert_rom_visible(request, rom)
    ...
    updated = db_rom_handler.apply_pc_metadata_candidate(
        id, selection.expected_version, candidate_fields
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=...)
```

Preserve the public selection API and its 422 behavior for an unknown/unavailable Steam candidate. Do not call a socket route or database session from the shared patch helper.

### `backend/handler/metadata/steam_merge.py` (utility, transform)

**Analog:** `steam_merge.py:8-70, 157-176`

Extend `MANUAL_FIELDS` to cover the locked manual developer and publisher fields, then continue to build a non-empty patch from provenance rather than applying ORM changes.

```python
for field, value in values.items():
    if value is None or _is_manual(manual_metadata, field):
        continue
    current_value = ...
    if _can_replace(current_value, field in steam_fields ...):
        if field in {"name", "summary"}:
            updates[field] = value
        else:
            structured_updates[field] = value
        applied_fields.append(field)
```

Use `_is_manual()` and `_can_replace()` rather than assigning strings directly. This preserves manually entered data and permits only fields already recorded in Steam provenance to refresh non-empty provider data.

### `backend/handler/metadata/rom_media.py` (utility, transform)

**Analog:** `rom_media.py:18-74`

Use `ProviderMediaCandidate`, `normalize_provider_url()`, and `discover_provider_media()` unchanged as the input validation and stable identity boundary for Steam cover/screenshots.

```python
url = normalize_provider_url(raw_url)
identity = (
    str(native_id)
    if native_id not in (None, "")
    else f"url-sha256:{sha256(url.encode()).hexdigest()}"
)
return ProviderMediaCandidate(provider, identity[:450], role, url, label)
```

The reconciliation service should translate the Steam patch media into the existing keys, `url_artworks` for cover and `url_screenshots` for screenshots, then call `discover_provider_media("steam", source)`. Do not compare raw URLs or permit non-HTTPS media.

### `backend/handler/metadata/steam_owned_media.py` (new service, file-I/O/batch)

**Analog:** `backend/endpoints/roms/media.py:89-123`

Move the non-HTTP portions of the existing explicit refresh flow into a scan-owned handler. Reuse its bounded provider download and `fs_resource_handler.store_owned_media_image()` pattern, but do not import or call endpoint-private `_download_provider_image()` from scan orchestration.

```python
for candidate in discover_provider_media(provider, source):
    path: str | None = None
    try:
        path, mime_type = await _download_provider_image(rom, candidate)
        applied = db_rom_handler.reconcile_provider_owned_media(
            id, expected_version, candidate.provider, candidate.provider_media_id,
            candidate.role, candidate.display_label, mime_type, path,
        )
        if applied is None:
            raise ValueError("Media catalog changed")
        expected_version = applied.rom.updated_at
    except ValueError:
        if path is not None:
            await fs_resource_handler.remove_file(path)
        raise
```

Adapt the failure policy for scans: candidate download or validation failure must leave the prior inventory and placements intact, clean only newly stored owned bytes, and return without propagating a scan failure. Batch tombstoning must run only after the complete validated Steam inventory is available. It must filter `origin=PROVIDER` and `provider="steam"`; it must never touch uploads.

### `backend/handler/database/roms_handler.py` (repository, CRUD/batch)

**Analog:** `roms_handler.py:653-772`

Add a narrow locked batch companion to `reconcile_provider_owned_media()`, or extend it without changing explicit refresh semantics. Follow the lock, validation, optimistic version update, and `session.flush()` behavior.

```python
@begin_session
def reconcile_provider_owned_media(..., session: Session = None) -> AppliedOwnedMedia | None:
    rom = self._get_locked_owned_media_rom(session, rom_id, expected_updated_at)
    if rom is None or not provider or not provider_media_id or ...:
        return None
    media = next(
        (item for item in rom.owned_media
         if item.provider == provider and item.provider_media_id == provider_media_id),
        None,
    )
    ...
    rom.updated_at = datetime.now(timezone.utc)
    session.flush()
```

**Manual-placement safety analog** (`roms_handler.py:735-772`):

```python
current = [
    item for item in rom.owned_media_placements if item.surface == surface
]
placement = next((item for item in current if item.media_id == media_id), None)
if selected and placement is None:
    session.add(RomOwnedMediaPlacement(
        rom_id=rom.id, media_id=media.id, surface=surface, position=len(current)
    ))
```

For automatic scan placement, inspect `current` first. Add only when the surface has no placement at all, using the established compatible role and append position. Do not call `replace_owned_media_placements()` (`roms_handler.py:775-824`), because it deletes and rebuilds all placements and can reorder operator choices.

### Test files (pytest, focused unit and database behavior)

**Scan test analog:** `backend/tests/handler/test_scan_handler.py:268-379`

Existing tests patch the provider methods with `AsyncMock` and invoke the narrow async helper directly:

```python
with patch("handler.scan_handler.meta_steam_handler.get_rom_by_id", direct):
    updates = await resolve_steam_scan_metadata(
        cast("Rom", _rom(steam_id=1091500)),
        cast("Platform", _platform("win")),
        "Game", [MetadataSource.STEAM],
    )
```

Extend this fixture style to compare administrator, update, complete, and targeted entry points against one shared normalized patch. Parametrize Windows, Linux, and macOS, then retain excluded-platform and provider-not-selected negative cases.

**Merge test analog:** `backend/tests/handler/metadata/test_steam_merge.py:4-150`

Use plain mapping inputs and exact patch assertions. Add manual `main_developer` and `publishers`, plus German-first/fallback-only-missing assertions, without a database fixture.

**Owned-media test analog:** `backend/tests/handler/database/test_rom_media.py:274-472`

Use the existing ORM `rom` fixture and carry `applied.rom.updated_at` to each subsequent operation. Cover idempotent Steam inventory, tombstoning only stale Steam provider rows after a successful full inventory, no-op on failed inventory, upload preservation, and unclaimed-only overview/background insertion.

**Targeted endpoint test analog:** `backend/tests/endpoints/roms/test_pc_metadata.py:909-968`

Use the authenticated `client`, `access_token`, `rom`, and `monkeypatch` fixture pattern. Assert that a Steam selection consumes the same patch helper and preserves the existing 422 and stale-version contract.

## Shared Patterns

### Layering and transaction ownership

**Sources:** `.claude/skills/backend-development/SKILL.md`, `backend/handler/database/roms_handler.py:653-824`

Endpoints validate/authenticate and call handlers. The shared enrichment helper is pure and has no session. Database mutations live only in `DBRomsHandler` methods decorated with `@begin_session`; file bytes live only in owned storage helpers. No raw SQL, endpoint-private downloader, or external source-library path is allowed in the scan path.

### Failure isolation

**Sources:** `backend/handler/scan_handler.py:191-220, 1051-1149`; `backend/handler/metadata/steam_merge.py:14-70`

An invalid Steam result is `{}`. An empty patch is not an empty remote inventory. Only a complete, validated candidate inventory may cause a Steam-provider tombstone update. Text patch persistence and media download failures have independent blast radii.

### Provider identity and source safety

**Sources:** `backend/handler/metadata/rom_media.py:26-74`; `backend/models/rom.py:520-621`

Canonical HTTPS URL plus provider origin is the candidate identity. Store downloaded bytes in RomM-owned resources, keep uploads as `RomOwnedMediaOrigin.UPLOAD`, and preserve them during Steam refresh. The model's placement uniqueness and order constraints are the source of truth.

### Manual placement protection

**Sources:** `backend/handler/database/roms_handler.py:735-824`; Phase 21 Context D-08

Automatic placement may append a compatible active Steam candidate only to an empty `OVERVIEW` or `BACKGROUND` surface. It may not replace, remove, or reorder existing placements, whether they are uploads, manual provider selections, or prior choices.

### Focused validation

**Sources:** `.claude/skills/backend-development/SKILL.md`; `21-RESEARCH.md:305-336`

Run changed pytest modules first, then the focused Phase 21 suite:

```bash
cd backend && uv run pytest \
  tests/handler/test_scan_handler.py \
  tests/handler/metadata/test_steam_handler.py \
  tests/handler/metadata/test_steam_merge.py \
  tests/handler/database/test_rom_media.py \
  tests/endpoints/roms/test_pc_metadata.py \
  tests/endpoints/roms/test_media.py \
  tests/endpoints/sockets/test_scan.py -x
```

Database-backed tests require an authorized MariaDB test environment. Browser UAT remains the isolated Witcher-style fixture and must not assume dev and UAT data are identical.

## No Analog Found

| File                                              | Role              | Data Flow                   | Guidance                                                                                                                                                                      |
| ------------------------------------------------- | ----------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/handler/metadata/pc_steam_enrichment.py` | service / utility | transform, request-response | New name only. Extract the proven pure portion of `resolve_steam_scan_metadata()` and call `normalize_steam()`; do not introduce a new provider abstraction.                  |
| `backend/handler/metadata/steam_owned_media.py`   | service           | file-I/O, batch             | New scan-specific boundary. Compose existing provider candidate validation, managed download/storage, and locked repository methods. Do not copy endpoint auth/HTTP behavior. |

## Metadata

**Analog search scope:** `backend/handler/`, `backend/endpoints/roms/`, `backend/models/`, and matching `backend/tests/` modules

**Files scanned:** 18

**Pattern extraction date:** 2026-09-30
