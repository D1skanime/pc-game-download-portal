# Phase 19: Fix PC quick-scan IGDB matching and safe DLC/expansion enrichment - Pattern Map

**Mapped:** 2026-09-28
**Files analyzed:** 5 new or modified files
**Analogs found:** 5 / 5

## File Classification

| New/Modified File                              | Role       | Data Flow              | Closest Analog                                                              | Match Quality |
| ---------------------------------------------- | ---------- | ---------------------- | --------------------------------------------------------------------------- | ------------- |
| `backend/handler/scan_handler.py`              | service    | request-response       | `backend/handler/metadata/steam_handler.py` and its existing IGDB dispatch  | exact         |
| `backend/endpoints/sockets/scan.py`            | controller | batch, event-driven    | existing `should_scan_rom()` and Windows enrichment branch in the same file | exact         |
| `backend/tests/handler/test_scan_handler.py`   | test       | request-response       | existing Steam eligibility/provider-dispatch tests in the same file         | exact         |
| `backend/tests/endpoints/sockets/test_scan.py` | test       | batch, event-driven    | existing fail-closed component-enrichment tests in the same file            | exact         |
| `backend/tests/handler/test_fastapi.py`        | test       | request-response, CRUD | existing scan result and PC component persistence tests in the same file    | role-match    |

## Pattern Assignments

### `backend/handler/scan_handler.py` (service, request-response)

**Analogs:** `backend/handler/metadata/steam_handler.py`, `backend/handler/scan_handler.py`

**Imports and compact-title boundary pattern** (`backend/handler/metadata/steam_handler.py:1-20`):

```python
import re

from .base_handler import BaseRom, MetadataHandler
from .base_handler import UniversalPlatformSlug as UPS

STEAM_PLATFORMS = frozenset({UPS.WIN, UPS.LINUX, UPS.MAC})
COMPACT_TITLE_BOUNDARY = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])"
)
```

**PC-only presentation adaptation** (`backend/handler/metadata/steam_handler.py:63-85`):

```python
name = fs_rom_handler.get_file_name_with_no_tags(fs_name)
if " " not in name:
    name = COMPACT_TITLE_BOUNDARY.sub(" ", name)
term = self.normalize_search_term(name, remove_punctuation=False)
if not term:
    return SteamRom(steam_id=None)
```

Copy the tag-removal plus boundary-only transformation, but invoke it only for the Windows IGDB name-search fallback. Keep it out of `IGDBHandler`, preserving classic platform filename handling and existing IGDB matching thresholds.

**Provider eligibility and ID-refresh versus name-search branch** (`backend/handler/scan_handler.py:668-719`):

```python
if (
    MetadataSource.IGDB in metadata_sources
    and platform.igdb_id
    and (
        newly_added
        or scan_type == ScanType.COMPLETE
        or (scan_type == ScanType.UPDATE and rom.igdb_id)
        or (
            scan_type == ScanType.UNMATCHED
            and (not rom.igdb_id or not rom.igdb_metadata)
            and rom.platform_slug in IGDB_PLATFORM_LIST
        )
    )
):
    ...
    if scan_type == ScanType.UPDATE and rom.igdb_id:
        return await meta_igdb_handler.get_rom_by_id(rom, rom.igdb_id)
    else:
        return await meta_igdb_handler.get_rom(
            rom,
            rom_attrs["fs_name"],
            main_platform_igdb_id or platform.igdb_id,
        )
```

Add the narrow Steam-present, IGDB-absent, Windows, IGDB-selected recovery predicate to this outer condition. Do not replace the persisted-IGDB refresh branch: the exception must reach the existing name-search fallback, while records with `igdb_id` remain ID-refreshed.

**Provider-error isolation** (`backend/handler/scan_handler.py:1023-1045`):

```python
# Run metadata fetches concurrently. One provider raising must not discard the
# others' results for this ROM, so each failure falls back to an empty match.
provider_fetches: tuple[tuple[Any, Any], ...] = (
    (
        fetch_igdb_rom(playmatch_hash_match, hasheous_hash_match),
        IGDBRom(igdb_id=None),
    ),
    ...
    (fetch_steam_updates(), {}),
)
```

Leave concurrency and failure fallback unchanged. The phase changes only IGDB input presentation and the narrow update gate.

---

### `backend/endpoints/sockets/scan.py` (controller, batch/event-driven)

**Analog:** existing scan selection and Windows parent-to-component enrichment in this file.

**Update selection gate** (`backend/endpoints/sockets/scan.py:371-422`):

```python
if roms_ids:
    return bool(rom and rom.id in roms_ids)

should_scan = bool(
    rom is None
    or scan_type in [ScanType.QUICK, ScanType.COMPLETE]
    or (
        rom
        and (
            (
                scan_type == ScanType.UPDATE
                and rom.is_identified
                and any(
                    getattr(rom, f"{source}_id", None)
                    for source in metadata_sources
                )
            )
            or (...)
        )
    )
)
```

Add the same narrowly-scoped Steam-only Windows recovery predicate as a sibling of the normal UPDATE condition. Do not change `Rom.is_identified` and do not make Steam IDs generally eligible.

**Post-persist parent enrichment, then components** (`backend/endpoints/sockets/scan.py:632-650`):

```python
_added_rom = db_rom_handler.add_rom(scanned_rom)

if platform.slug == UPS.WIN and isinstance(_added_rom.igdb_metadata, dict):
    enriched_parent = db_rom_handler.apply_pc_igdb_enrichment(
        _added_rom.id,
        _added_rom.updated_at,
        {
            "igdb_id": _added_rom.igdb_id,
            "name": _added_rom.name,
            "summary": _added_rom.summary,
            "igdb_metadata": _added_rom.igdb_metadata,
        },
    )
    if enriched_parent is not None:
        _added_rom = enriched_parent
    scan_target = db_rom_handler.get_rom(_added_rom.id)
    if scan_target is not None:
        for component in scan_target.components:
            await _enrich_pc_dlc_from_igdb(scan_target, component)
```

Preserve this order. It makes the current IGDB relation data durable before components are inspected, and it keeps the original parent row identity through `add_rom()`.

**Automatic component safety sequence** (`backend/endpoints/sockets/scan.py:118-164`):

```python
candidate = await pc_metadata_match_handler.fetch_unique_related_igdb_candidate(
    rom, component
)
if candidate is None:
    return

saved_component = db_rom_handler.apply_pc_component_metadata_candidate(
    rom.id, component.id, component.updated_at, candidate.provider, candidate.fields
)
if saved_component is None:
    return

steam_candidate = await pc_metadata_match_handler.fetch_validated_steam_dlc(
    rom, candidate
)
```

No generic component name search belongs in automatic scan code. The IGDB relation must be exactly one candidate and hydrate successfully before any optional Steam lookup.

---

### `backend/tests/handler/test_scan_handler.py` (test, request-response)

**Analog:** `backend/tests/handler/test_scan_handler.py:73-190`.

Follow its async unit-test style: create a minimal Windows platform/ROM, patch the provider method using `AsyncMock`, call `scan_rom()`, and assert exact await arguments. Add focused cases for `EuroTruckSimulator2` being passed to IGDB as `Euro Truck Simulator 2`, a normal spaced Windows name staying unchanged, and a classic ROM retaining its raw IGDB lookup name. Add the Steam-only Windows UPDATE case here if the direct `scan_rom()` provider call is easiest to isolate.

**Provider dispatch assertion convention** (`backend/tests/handler/test_scan_handler.py:109-156`):

```python
await scan_rom(...)

steam.get_rom.assert_awaited_once_with("Test Game", UPS.WIN)
```

Assert the exact IGDB lookup argument and that an unselected IGDB provider is never invoked. This protects the PC-only scope and matching-threshold boundary.

---

### `backend/tests/endpoints/sockets/test_scan.py` (test, batch/event-driven)

**Analog:** `backend/tests/endpoints/sockets/test_scan.py:82-184`.

**Fail-closed enrichment test setup** (`backend/tests/endpoints/sockets/test_scan.py:134-145`):

```python
matcher.fetch_unique_related_igdb_candidate = AsyncMock(return_value=None)
matcher.fetch_validated_steam_dlc = AsyncMock(return_value=None)

await scan_module._enrich_pc_dlc_from_igdb(rom, component)

db.apply_pc_component_metadata_candidate.assert_not_called()
matcher.fetch_validated_steam_dlc.assert_not_awaited()
```

Extend, do not weaken, this style for both related DLC and expansion fixtures. Cover an exact single related candidate that persists, plus ambiguous or unrelated records that produce neither a component write nor Steam call.

Add pure `should_scan_rom()` tests adjacent to scan selection tests for all four conditions: Windows, `steam_id`, missing `igdb_id`, UPDATE, and IGDB selected means `True`; each excluded condition means `False` unless the pre-existing normal rule applies.

---

### `backend/tests/handler/test_fastapi.py` (test, request-response/CRUD)

**Analog:** `backend/tests/handler/test_fastapi.py:269-304`.

**Minimal persistence expectation** (`backend/tests/handler/test_fastapi.py:269-304`):

```python
auto_link_pc_dlc_components(rom, [component])

apply.assert_called_once_with(
    1,
    7,
    "2026-09-02T00:00:00+00:00",
    "igdb",
    candidate.fields,
)
```

Use the existing scan fixture seam to model a persisted Steam-only Windows ROM refreshed through IGDB. Assert its existing primary key is preserved, its IGDB parent relation is persisted, and no second ROM is created. Keep the assertion at persistence effects rather than testing provider fuzzy matching a second time.

## Shared Patterns

### Compact PC title normalization

**Source:** `backend/handler/metadata/steam_handler.py:63-85`
**Apply to:** Windows IGDB name-search fallback only.

Strip filesystem tags first, then split only lower-to-upper and letter-to-digit boundaries when the title has no spaces. Do not alter the shared IGDB handler or generic classic-ROM parsing.

### Narrow update recovery

**Sources:** `backend/endpoints/sockets/scan.py:371-422`, `backend/handler/scan_handler.py:668-719`
**Apply to:** both gates, identically.

The eligibility predicate must require all of: `UPS.WIN`, a present Steam ID, absent IGDB ID, `ScanType.UPDATE`, and selected IGDB metadata source. Its purpose is recovery, not a new definition of identified metadata.

### IGDB-first, fail-closed component enrichment

**Sources:** `backend/endpoints/sockets/scan.py:118-164`, `backend/handler/metadata/pc_match_handler.py:88-120`, `backend/handler/metadata/pc_match_handler.py:137-196`
**Apply to:** all automatic DLC/expansion paths.

```python
candidate = self.find_unique_related_igdb_candidate(rom, component)
if candidate is None:
    return None
...
try:
    details = await get_by_id(rom, candidate.provider_ids["igdb_id"])
except Exception:
    return None
```

The matcher requires exactly one related IGDB identity, confirms it by ID, then the scan socket persists optimistically. Steam is optional enrichment only after this point, and validates type, title similarity, and parent app relation.

### Explicit manual selection remains review-only

**Source:** `backend/endpoints/roms/pc_metadata.py:72-161`
**Apply to:** preserve current API behavior; no new UI/API code is planned.

```python
results = await pc_metadata_match_handler.collect_component_candidates(
    rom, component, selection.query
)
candidate = next(... if item.id == selection.candidate_id, None)
if candidate is None:
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, ...)
```

Candidate collection writes nothing. A subsequent POST must supply an ID present in freshly recomputed results and an optimistic version.

### Optimistic persistence

**Source:** `backend/handler/database/roms_handler.py:1792-1813`
**Apply to:** parent IGDB relation persistence.

```python
igdb_metadata = data.get("igdb_metadata")
if not isinstance(igdb_metadata, dict):
    return None
values = {"igdb_metadata": igdb_metadata}
for field in ("igdb_id", "name", "summary"):
    if field in data:
        values[field] = data[field]
return self.apply_pc_metadata_candidate(
    id=id,
    expected_updated_at=expected_updated_at,
    data=values,
    session=session,
)
```

## No Analog Found

None. Every planned change has an established source or test analog. The PC-specific IGDB helper is new but directly mirrors the existing Steam boundary transformation.

## Metadata

**Analog search scope:** `backend/handler/`, `backend/endpoints/sockets/`, `backend/endpoints/roms/`, `backend/tests/handler/`, `backend/tests/endpoints/`
**Files scanned:** 11
**Pattern extraction date:** 2026-09-28
