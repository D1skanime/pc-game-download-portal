# Steam Metadata Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add upstream Steam Storefront metadata to PC games and safely identified DLC components, with German-first metadata and non-regressive IGDB integration.

**Architecture:** Port upstream Steam transport and handler code, then add a small locale layer that can fetch fallback details only for the already resolved App ID. Register Steam normally, but route scans and manual PC choices through one normalized, manual-safe merge function. IGDB remains the DLC relationship source and SteamGridDB remains artwork-only.

**Tech Stack:** Python 3.13, aiohttp, SQLAlchemy 2, Alembic, FastAPI/Pydantic, pytest, Vue 3, TypeScript, Vitest, uv, Trunk.

**Spec:** `docs/superpowers/specs/2026-09-24-steam-metadata-integration-design.md`

## Global Constraints

- Preserve `sgdb` as SteamGridDB artwork-only. `steam` is Steam Storefront metadata.
- Steam requires only `STEAM_API_ENABLED=true`, defaults to `de/CH`, and only falls back to `en/US` for missing fields on the same App ID.
- Automatic name lookup is only for `win`, `linux`, and `mac`. `dos`, `win3x`, and `win9x` resolve explicit App IDs only.
- A persisted App ID refreshes by ID, never by a filename rematch.
- Steam cannot clear existing fields, bypass manual values or selected artwork, or create a ROM/component.
- DLC automation requires one hydrated IGDB-related DLC, one high-confidence Steam DLC, rejection of non-DLC product types, and parent confirmation when Steam exposes it.
- Steam timeouts, 429s, regional misses, and malformed payloads are non-fatal to other providers.

## Review Focus

- A partly translated response fills only absent text fields from `en/US` for the exact same App ID. Covered in Task 1.
- A renamed game with a stored App ID calls only the ID endpoint. Covered in Task 3.
- Explicitly selected cover artwork cannot be changed by Steam detail application. Covered in Task 3.
- Bundles, soundtracks, demos, tools, ambiguous DLC hits, and mismatched parents do not enrich a component. Covered in Task 4.
- Steam unavailable with successful IGDB/Moby/LaunchBox preserves the pre-Steam usable scan result. Covered in Task 3.

---

### Task 1: Port the localized Steam service and handler

**Files:**

- Create: `backend/adapters/services/steam.py`
- Create: `backend/adapters/services/steam_types.py`
- Create: `backend/handler/metadata/steam_handler.py`
- Modify: `backend/config/__init__.py`
- Modify: `backend/handler/metadata/__init__.py`
- Modify: `env.template`
- Test: `backend/tests/adapters/services/test_steam.py`
- Test: `backend/tests/handler/metadata/test_steam_handler.py`

**Interfaces:**

- Produces `SteamService.search_apps(term, *, country, language)` and `get_app_details(app_id, *, country, language, filters=None)`.
- Produces `SteamHandler.get_rom(fs_name, platform_slug)`, `get_rom_by_id(steam_id, platform_slug=None)`, and `get_matched_roms_by_name(search_term, platform_slug)`.
- Returns normalized `SteamRom` mappings with `steam_id`, `steam_metadata`, `name`, `summary`, `url_cover`, and `url_screenshots`.

- [ ] **Step 1: Write the failing service and handler tests**

```python
async def test_details_uses_requested_locale(session):
    session.get.return_value = _response({"400": {"success": True, "data": {}}})
    await SteamService().get_app_details(400, country="CH", language="de")
    assert "cc=CH" in str(session.get.await_args.args[0])
    assert "l=de" in str(session.get.await_args.args[0])

async def test_partial_german_falls_back_by_same_app_id_only(handler, service):
    service.get_app_details.side_effect = [GERMAN_PARTIAL, ENGLISH_FULL]
    rom = await handler.get_rom_by_id(1091500, "win")
    assert rom["summary"] == ENGLISH_FULL["short_description"]
    assert [call.args[0] for call in service.get_app_details.await_args_list] == [1091500, 1091500]
```

- [ ] **Step 2: Run the tests and confirm failure**

Run: `cd backend && uv run pytest tests/adapters/services/test_steam.py tests/handler/metadata/test_steam_handler.py -q`

Expected: FAIL because the Steam modules do not exist.

- [ ] **Step 3: Port upstream transport and types**

Copy the current upstream `steam.py` and `steam_types.py` as the baseline. Retain the 0.6 request-per-second limiter, three attempts, 429 backoff, timeouts, JSON guards, empty-result degradation, and capsule/header probes. Add only optional typed DLC-parent data when exposed by Storefront details.

```python
async def get_app_details(self, app_id: int, *, country: str, language: str,
                          filters: str | None = None) -> SteamAppDetails | None:
    query = {"appids": str(app_id), "cc": country, "l": language}
    if filters:
        query["filters"] = filters
    # Return None for failed, malformed, missing, or region-locked results.
```

- [ ] **Step 4: Add configuration and provider registration**

```python
STEAM_API_ENABLED: Final[bool] = safe_str_to_bool(_get_env("STEAM_API_ENABLED"))
STEAM_API_LANGUAGE: Final[str] = _get_env("STEAM_API_LANGUAGE", "de")
STEAM_API_COUNTRY: Final[str] = _get_env("STEAM_API_COUNTRY", "CH")
STEAM_API_FALLBACK_LANGUAGE: Final[str] = _get_env("STEAM_API_FALLBACK_LANGUAGE", "en")
STEAM_API_FALLBACK_COUNTRY: Final[str] = _get_env("STEAM_API_FALLBACK_COUNTRY", "US")
```

Document these in `env.template`; instantiate `meta_steam_handler`. Do not change any SGDB name, key, handler, or asset.

- [ ] **Step 5: Implement PC eligibility and strict App-ID locale fallback**

Port upstream `STEAM_PLATFORMS = {win, linux, mac}`, similarity threshold, app/product validation, heartbeat, and cover resolution. Make `get_rom_by_id` permit an explicit ID on excluded PC slugs but make `get_rom` skip their name search.

```python
async def get_localized_rom_by_id(self, steam_id: int) -> SteamRom:
    preferred = await self.steam_service.get_app_details(
        steam_id, country=STEAM_API_COUNTRY, language=STEAM_API_LANGUAGE
    )
    if not preferred:
        return SteamRom(steam_id=None)
    fallback = await self.steam_service.get_app_details(
        steam_id, country=STEAM_API_FALLBACK_COUNTRY,
        language=STEAM_API_FALLBACK_LANGUAGE,
    ) if self._needs_text_fallback(preferred) else None
    return await self._build_localized_rom(preferred, fallback)
```

Choose each text field from non-empty German then non-empty English. Store language provenance only in `steam_metadata`; never make it another display source.

- [ ] **Step 6: Run tests and commit**

Run: `cd backend && uv run pytest tests/adapters/services/test_steam.py tests/handler/metadata/test_steam_handler.py -q && cd .. && trunk fmt -- backend/adapters/services/steam.py backend/adapters/services/steam_types.py backend/handler/metadata/steam_handler.py backend/config/__init__.py`

Expected: PASS for disabled state, timeouts/429s, `win/linux/mac`, excluded-platform no-search, and exact-ID fallback.

```bash
git add backend/adapters/services/steam.py backend/adapters/services/steam_types.py backend/handler/metadata/steam_handler.py backend/handler/metadata/__init__.py backend/config/__init__.py env.template backend/tests/adapters/services/test_steam.py backend/tests/handler/metadata/test_steam_handler.py
git commit -m "feat: add localized Steam metadata provider"
```

### Task 2: Add Steam persistence, migration, and response schemas

**Files:**

- Modify: `backend/models/rom.py`
- Create: `backend/alembic/versions/0119_add_steam_metadata.py`
- Modify: `backend/endpoints/responses/rom.py`
- Modify: `backend/endpoints/roms/__init__.py`
- Test: `backend/tests/models/test_rom.py`
- Test: `backend/tests/models/test_pc_igdb_metadata.py`

**Interfaces:**

- Produces nullable `Rom.steam_id`, JSON `Rom.steam_metadata`, nullable `RomComponentMetadata.steam_id`, and JSON `RomComponentMetadata.steam_metadata`.
- Produces corresponding response fields for frontend generation.

- [ ] **Step 1: Write failing persistence and migration tests**

```python
def test_component_steam_ids_are_not_globally_unique():
    first = RomComponentMetadata(component_id=1, steam_id=123)
    second = RomComponentMetadata(component_id=2, steam_id=123)
    assert first.steam_id == second.steam_id == 123

def test_steam_migration_adds_rom_and_component_columns():
    migration = Path("alembic/versions/0119_add_steam_metadata.py").read_text()
    assert '"roms"' in migration and '"rom_component_metadata"' in migration
    assert "UniqueConstraint" not in migration
```

- [ ] **Step 2: Run the tests and confirm failure**

Run: `cd backend && uv run pytest tests/models/test_rom.py tests/models/test_pc_igdb_metadata.py -q`

Expected: FAIL because the fields and migration do not exist.

- [ ] **Step 3: Implement model, API, and migration changes**

```python
steam_id: Mapped[int | None] = mapped_column(Integer(), default=None)
steam_metadata: Mapped[dict[str, Any] | None] = mapped_column(CustomJSON(), default=dict)
```

Add fields to both models and needed Rom facets/provider mappings. Migration adds and drops both fields on both tables using existing cross-dialect conventions. Add response schema fields and `RomUpdateForm.steam_id` only where existing provider IDs are manually editable. Do not add a Steam App-ID uniqueness constraint or index unless the current model has an equivalent non-global provider convention.

- [ ] **Step 4: Verify migration and commit**

Run: `cd backend && uv run pytest tests/models/test_rom.py tests/models/test_pc_igdb_metadata.py -q && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`

Expected: PASS and a reversible migration.

```bash
git add backend/models/rom.py backend/alembic/versions/0119_add_steam_metadata.py backend/endpoints/responses/rom.py backend/endpoints/roms/__init__.py backend/tests/models/test_rom.py backend/tests/models/test_pc_igdb_metadata.py
git commit -m "feat: persist Steam metadata for PC entries"
```

### Task 3: Register Steam and implement one safe PC main-game merge path

**Files:**

- Create: `backend/handler/metadata/steam_merge.py`
- Modify: `backend/handler/scan_handler.py`
- Modify: `backend/config/config_manager.py`
- Modify: `backend/watcher.py`
- Modify: `backend/tasks/scheduled/scan_library.py`
- Modify: `backend/endpoints/heartbeat.py`
- Modify: `backend/endpoints/responses/heartbeat.py`
- Modify: `backend/handler/database/roms_handler.py`
- Modify: `backend/endpoints/roms/pc_metadata.py`
- Test: `backend/tests/handler/metadata/test_steam_merge.py`
- Test: `backend/tests/handler/test_resolve_steam_rom.py`
- Test: `backend/tests/config/test_config_loader.py`
- Test: `backend/tests/endpoints/test_heartbeat.py`

**Interfaces:**

- Produces `MetadataSource.STEAM`, heartbeat `STEAM_API_ENABLED`, `resolve_steam_rom(...)`, and `normalize_steam_application(existing, steam, *, manual_fields)`.

- [ ] **Step 1: Write failing source, scan, and merge tests**

```python
def test_steam_is_valid_priority_source():
    assert MetadataSource.STEAM.value == "steam"
    assert VALID_SCAN_PRIORITY_SOURCES == {source.value for source in MetadataSource}

async def test_renamed_rom_with_steam_id_refreshes_only_that_id(lookups):
    await resolve_steam_rom(rom=_rom(steam_id=1091500), fs_name="renamed", platform_slug="win", scan_type=ScanType.UPDATE)
    lookups.by_id.assert_awaited_once_with(1091500, "win")
    lookups.by_name.assert_not_awaited()

def test_merge_preserves_manual_text_release_and_selected_artwork():
    merged = normalize_steam_application(MANUAL_ROM, STEAM_ROM, manual_fields={"name", "summary", "pc_release_date", "artwork"})
    assert {key: merged[key] for key in ("name", "summary", "pc_release_date", "path_cover_l")} == MANUAL_VALUES
```

- [ ] **Step 2: Run the tests and confirm failure**

Run: `cd backend && uv run pytest tests/handler/metadata/test_steam_merge.py tests/handler/test_resolve_steam_rom.py tests/config/test_config_loader.py tests/endpoints/test_heartbeat.py -q`

Expected: FAIL because Steam registration and the shared merge function do not exist.

- [ ] **Step 3: Register Steam in every central provider path**

Add enum/allowlist/availability-map/heartbeat/metadata-handler entries with `steam_id` and `steam_metadata`. Add the heartbeat switch case. Preserve SGDB mapping to `sgdb_id`. Add `steam` to priority parsing without placing it in an artwork-specific override.

```python
async def resolve_steam_rom(*, rom: Rom, fs_name: str, platform_slug: str, scan_type: ScanType) -> SteamRom:
    if rom.steam_id and (scan_type == ScanType.UPDATE or (scan_type == ScanType.UNMATCHED and not rom.steam_metadata)):
        return await meta_steam_handler.get_rom_by_id(rom.steam_id, platform_slug)
    if platform_slug not in STEAM_PLATFORMS:
        return SteamRom(steam_id=None)
    return await meta_steam_handler.get_rom(fs_name, platform_slug)
```

Call this only for selected Steam scans. An exception must become an empty Steam result, leaving concurrent IGDB/Moby/LaunchBox results intact.

- [ ] **Step 4: Implement the common normalizer and guarded application**

```python
def normalize_steam_application(existing: Mapping[str, Any], steam: Mapping[str, Any], *, manual_fields: frozenset[str]) -> dict[str, Any]:
    updates = {"steam_id": steam["steam_id"], "steam_metadata": steam["steam_metadata"]}
    for field in ("name", "summary", "main_developer", "publishers", "pc_release_date"):
        if steam.get(field) not in (None, "", []) and field not in manual_fields:
            updates[field] = steam[field]
    return updates
```

Determine manual protection from existing source/override semantics. Never write Steam into IGDB themes, franchise, relationships, or selected artwork. Both automatic scan output and a manually selected Steam candidate must use this normalizer before persistence.

- [ ] **Step 5: Add outage and non-PC regression tests, then verify**

```python
async def test_steam_timeout_does_not_discard_igdb_success(mocker):
    mocker.patch("handler.scan_handler.meta_steam_handler.get_rom", side_effect=TimeoutError)
    assert (await scan_with_igdb_success())["igdb_id"] == 42
```

Run: `cd backend && uv run pytest tests/handler/metadata/test_steam_merge.py tests/handler/test_resolve_steam_rom.py tests/config/test_config_loader.py tests/endpoints/test_heartbeat.py tests/handler/test_fastapi.py -q`

Expected: PASS for strict ID refresh, no SNES/DOS/Win3x/Win9x automatic call, Steam failure isolation, and independent manual protection.

- [ ] **Step 6: Commit**

```bash
git add backend/handler/metadata/steam_merge.py backend/handler/scan_handler.py backend/config/config_manager.py backend/watcher.py backend/tasks/scheduled/scan_library.py backend/endpoints/heartbeat.py backend/endpoints/responses/heartbeat.py backend/handler/database/roms_handler.py backend/endpoints/roms/pc_metadata.py backend/tests
git commit -m "feat: integrate Steam PC metadata safely"
```

### Task 4: Add Steam PC candidates and conservative DLC enrichment

**Files:**

- Modify: `backend/handler/metadata/pc_match_handler.py`
- Modify: `backend/handler/metadata/steam_handler.py`
- Modify: `backend/handler/database/roms_handler.py`
- Test: `backend/tests/handler/metadata/test_pc_match_handler.py`
- Test: `backend/tests/endpoints/roms/test_pc_metadata.py`

**Interfaces:**

- Produces `SteamHandler.get_matched_dlc_by_identity(title, parent_steam_id) -> SteamRom | None`.
- Produces Steam candidates containing `steam_id` and `steam_metadata`; application reuses Task 3's normalizer.

- [ ] **Step 1: Write failing candidate and safety tests**

```python
async def test_igdb_resolved_dlc_gets_one_safe_steam_candidate(handler, rom, component):
    results = await handler.collect_component_candidates(rom, component)
    assert results["igdb"].candidates[0].provider_ids == {"igdb_id": 215769}
    assert results["steam"].candidates[0].provider_ids == {"steam_id": 2138330}

@pytest.mark.parametrize("hit", [BUNDLE, SOUNDTRACK, DEMO, TOOL])
async def test_non_dlc_product_never_enriches_related_dlc(steam, hit):
    steam.search_apps.return_value = [hit]
    assert await steam.get_matched_dlc_by_identity("Known DLC", 1091500) is None
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd backend && uv run pytest tests/handler/metadata/test_pc_match_handler.py tests/endpoints/roms/test_pc_metadata.py -q`

Expected: FAIL because no Steam candidate or DLC identity resolver exists.

- [ ] **Step 3: Add the Steam candidate provider**

Add `meta_steam_handler` immediately after IGDB in the PC matcher. Dispatch main-game lookup with `get_matched_roms_by_name(title, rom.platform_slug)`; add `steam_id` and `steam_metadata` to candidate fields. Keep SGDB media code untouched.

- [ ] **Step 4: Implement DLC filtering, confidence, and parent verification**

```python
async def get_matched_dlc_by_identity(self, title: str, parent_steam_id: int | None) -> SteamRom | None:
    hits = await self.steam_service.search_apps(title, country=STEAM_API_COUNTRY, language=STEAM_API_LANGUAGE)
    dlcs = [hit for hit in hits if hit.get("type") == "dlc"]
    match, _ = self.find_best_match(title, [hit["name"] for hit in dlcs], min_similarity_score=self.min_similarity_score)
    if not match or sum(hit["name"] == match for hit in dlcs) != 1:
        return None
    steam_id = next(hit["id"] for hit in dlcs if hit["name"] == match)
    result = await self.get_localized_rom_by_id(steam_id)
    return result if self._is_valid_dlc_parent(result, parent_steam_id) else None
```

Require one already hydrated IGDB related candidate before calling this. Reject zero/multiple candidates and any known mismatched parent relation. When Steam exposes no parent relation, only the unique threshold-passing result tied to that IGDB identity can apply. Never add folder-name-only matching.

- [ ] **Step 5: Verify tests and commit**

Run: `cd backend && uv run pytest tests/handler/metadata/test_pc_match_handler.py tests/handler/metadata/test_steam_handler.py tests/endpoints/roms/test_pc_metadata.py -q`

Expected: PASS for German DLC fallback, no match preserving IGDB, ambiguity/product-type/parent rejection, and no component duplicate.

```bash
git add backend/handler/metadata/pc_match_handler.py backend/handler/metadata/steam_handler.py backend/handler/database/roms_handler.py backend/tests/handler/metadata/test_pc_match_handler.py backend/tests/handler/metadata/test_steam_handler.py backend/tests/endpoints/roms/test_pc_metadata.py
git commit -m "feat: enrich verified PC DLCs from Steam"
```

### Task 5: Expose Steam separately in the v2 UI and verify the whole change

**Files:**

- Modify: `frontend/src/stores/heartbeat.ts`
- Modify: `frontend/src/v2/components/Dialogs/RefreshMetadataDialog.vue`
- Modify: `frontend/src/v2/components/Scan/ScanInfoDialog.vue`
- Modify: `frontend/src/v2/components/Auth/SetupStepMetadata.vue`
- Modify: `frontend/src/v2/components/GameDetails/providers.ts`
- Modify: `frontend/src/v2/tokens/index.ts`
- Modify: `frontend/src/locales/en_US/{setup,rom}.json`
- Modify: `frontend/src/locales/de_DE/{setup,rom}.json`
- Create: `frontend/assets/scrappers/steam.png`
- Regenerate: `frontend/src/__generated__/models/MetadataSourcesDict.ts`
- Create: `docs/UPSTREAM_STEAM_METADATA_PORT.md`
- Test: affected Vitest and backend suites

**Interfaces:**

- Consumes `STEAM_API_ENABLED` and `steam_id`; produces a `steam` UI option and `https://store.steampowered.com/app/{id}` link.

- [ ] **Step 1: Write the failing distinct-provider test**

```ts
it("shows Steam and SteamGridDB as separate enabled providers", () => {
  heartbeat.value.METADATA_SOURCES.STEAM_API_ENABLED = true;
  const keys = heartbeat.getEnabledMetadataOptions().map(({ value }) => value);
  expect(keys).toContain("steam");
  expect(keys).toContain("sgdb");
});
```

- [ ] **Step 2: Run the test and confirm failure**

Run: `cd frontend && npm run test -- heartbeat.test.ts`

Expected: FAIL because Steam is absent from the generated heartbeat type and option list.

- [ ] **Step 3: Implement UI representation and port documentation**

Copy upstream `frontend/assets/scrappers/steam.png`. Add a Steam icon/token/label/setup text that states it requires no key, a refresh/scan option gated by `STEAM_API_ENABLED`, and a provider link for `steam_id`. Do not rename or alter SteamGridDB controls. Record upstream commit `eaba9c70d1ef462022c7b4a1ab9846ddb214b66c`, directly ported files, and fork-only locale/PC/DLC code in `docs/UPSTREAM_STEAM_METADATA_PORT.md`.

- [ ] **Step 4: Generate types and run full verification**

Run: `cd frontend && npm run generate && npm run typecheck && npm run test && cd ../backend && uv run alembic upgrade head && uv run pytest -q && cd .. && trunk fmt && trunk check && git diff --check`

Expected: all commands exit 0. Regenerate types after any backend OpenAPI shape change before the typecheck.

- [ ] **Step 5: Commit**

```bash
git add frontend/src docs/UPSTREAM_STEAM_METADATA_PORT.md
git commit -m "feat: expose Steam metadata provider"
```
