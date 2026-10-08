from types import SimpleNamespace
from typing import cast
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest

from handler.database import db_platform_handler, db_rom_handler
from handler.scan_handler import (
    MetadataSource,
    ScanType,
    _apply_metadata_handler_fields,
    _is_steam_only_windows_igdb_recovery,
    _windows_igdb_lookup_name,
    auto_link_pc_dlc_components,
    scan_rom,
)
from models.platform import Platform
from models.rom import Rom, RomComponent, RomComponentKind


def _rom(*, steam_id: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        steam_id=steam_id,
        steam_metadata={},
        manual_metadata={},
        name="Existing title",
        summary="Existing summary",
        pc_release_date=1_600_000_000,
        main_developer=None,
        publishers=[],
        path_cover_s="roms/1/selected-cover.webp",
        path_screenshots=["roms/1/selected-shot.webp"],
        metadatum=None,
    )


def _platform(slug: str) -> SimpleNamespace:
    return SimpleNamespace(slug=slug)


def _igdb_scan_fixture(
    *,
    platform_slug: str = "win",
    igdb_id: int | None = None,
    steam_id: int | None = None,
    igdb_metadata: dict | None = None,
) -> tuple[Platform, Rom]:
    platform = Platform(
        id=1,
        name=platform_slug,
        slug=platform_slug,
        fs_slug=platform_slug,
        igdb_id=6,
    )
    rom = Rom(
        id=1,
        platform_id=platform.id,
        fs_name="EuroTruckSimulator2",
        fs_name_no_tags="EuroTruckSimulator2",
        fs_name_no_ext="EuroTruckSimulator2",
        fs_extension="",
        fs_path=platform_slug,
        regions=[],
        languages=[],
        tags=[],
        igdb_id=igdb_id,
        igdb_metadata=igdb_metadata or {},
        steam_id=steam_id,
    )
    return platform, rom


async def _scan_igdb_name_fallback(
    *,
    platform_slug: str = "win",
    fs_name: str = "EuroTruckSimulator2",
    scan_type: ScanType = ScanType.QUICK,
    newly_added: bool = True,
    igdb_id: int | None = None,
    steam_id: int | None = None,
):
    platform, rom = _igdb_scan_fixture(
        platform_slug=platform_slug, igdb_id=igdb_id, steam_id=steam_id
    )
    name_lookup = AsyncMock(
        return_value={"igdb_id": 3070, "name": "Euro Truck Simulator 2"}
    )
    id_lookup = AsyncMock(
        return_value={"igdb_id": igdb_id, "name": "Euro Truck Simulator 2"}
    )
    with (
        patch(
            "handler.scan_handler.db_rom_handler.add_rom", side_effect=lambda item: item
        ),
        patch(
            "handler.scan_handler.meta_playmatch_handler.is_enabled", return_value=False
        ),
        patch("handler.scan_handler.meta_igdb_handler.get_rom", name_lookup),
        patch("handler.scan_handler.meta_igdb_handler.get_rom_by_id", id_lookup),
        patch(
            "handler.scan_handler.fs_rom_handler.get_pico8_cover_url", return_value=None
        ),
    ):
        await scan_rom(
            scan_type=scan_type,
            platform=platform,
            rom=rom,
            fs_rom={
                "fs_name": fs_name,
                "flat": True,
                "nested": False,
                "files": [],
                "crc_hash": "",
                "md5_hash": "",
                "sha1_hash": "",
                "ra_hash": "",
            },
            metadata_sources=[MetadataSource.IGDB],
            newly_added=newly_added,
        )
    return name_lookup, id_lookup


def test_derived_igdb_artworks_are_not_passed_to_the_rom_model():
    rom_attrs = {"name": "Existing"}

    _apply_metadata_handler_fields(
        rom_attrs,
        {
            "igdb_id": 1877,
            "url_screenshots": ["https://cdn.example/artwork.jpg"],
            "url_artworks": ["https://cdn.example/artwork.jpg"],
        },
    )

    assert rom_attrs == {
        "name": "Existing",
        "igdb_id": 1877,
        "url_screenshots": ["https://cdn.example/artwork.jpg"],
    }


def test_auto_link_pc_dlc_adds_igdb_to_a_component_already_identified_by_steam():
    rom = SimpleNamespace(id=41)
    component = SimpleNamespace(
        id=7,
        kind=RomComponentKind.DLC,
        updated_at="version",
        component_metadata=SimpleNamespace(steam_id=123, igdb_id=None),
    )
    candidate = SimpleNamespace(provider="igdb", fields={"igdb_id": 456})

    with (
        patch(
            "handler.scan_handler.pc_metadata_match_handler.find_unique_related_igdb_candidate",
            return_value=candidate,
        ) as find_candidate,
        patch(
            "handler.scan_handler.db_rom_handler.apply_pc_component_metadata_candidate"
        ) as apply_candidate,
    ):
        auto_link_pc_dlc_components(cast(Rom, rom), [cast(RomComponent, component)])

    find_candidate.assert_called_once_with(rom, component)
    apply_candidate.assert_called_once_with(41, 7, "version", "igdb", {"igdb_id": 456})


@pytest.mark.parametrize(
    ("fs_name", "expected"),
    [
        ("EuroTruckSimulator2", "Euro Truck Simulator 2"),
        ("Euro Truck Simulator 2", "Euro Truck Simulator 2"),
        ("EuroTruckSimulator2 (USA)", "Euro Truck Simulator 2"),
    ],
)
def test_windows_igdb_lookup_name_normalizes_only_compact_titles(
    fs_name: str, expected: str
):
    assert _windows_igdb_lookup_name(fs_name) == expected


@pytest.mark.parametrize(
    (
        "platform_slug",
        "steam_id",
        "igdb_id",
        "scan_type",
        "metadata_sources",
        "expected",
    ),
    [
        ("win", 227300, None, ScanType.UPDATE, [MetadataSource.IGDB], True),
        ("linux", 227300, None, ScanType.UPDATE, [MetadataSource.IGDB], False),
        ("win", None, None, ScanType.UPDATE, [MetadataSource.IGDB], False),
        ("win", -1, None, ScanType.UPDATE, [MetadataSource.IGDB], False),
        ("win", 227300, 3070, ScanType.UPDATE, [MetadataSource.IGDB], False),
        ("win", 227300, None, ScanType.QUICK, [MetadataSource.IGDB], False),
        ("win", 227300, None, ScanType.UPDATE, [], False),
    ],
)
def test_steam_only_windows_igdb_recovery_requires_all_fields(
    platform_slug: str,
    steam_id: int | None,
    igdb_id: int | None,
    scan_type: ScanType,
    metadata_sources: list[MetadataSource],
    expected: bool,
):
    assert (
        _is_steam_only_windows_igdb_recovery(
            platform_slug,
            steam_id,
            igdb_id,
            scan_type,
            metadata_sources,
        )
        is expected
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("platform_slug", "fs_name", "expected_lookup_name"),
    [
        ("win", "EuroTruckSimulator2", "Euro Truck Simulator 2"),
        ("win", "Euro Truck Simulator 2", "Euro Truck Simulator 2"),
        ("snes", "EuroTruckSimulator2", "EuroTruckSimulator2"),
    ],
)
async def test_igdb_name_search_applies_compact_title_normalization_only_to_windows(
    platform_slug: str, fs_name: str, expected_lookup_name: str
):
    name_lookup, id_lookup = await _scan_igdb_name_fallback(
        platform_slug=platform_slug, fs_name=fs_name
    )

    name_lookup.assert_awaited_once_with(
        ANY,
        expected_lookup_name,
        6,
    )
    id_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_igdb_update_with_persisted_id_uses_id_refresh():
    name_lookup, id_lookup = await _scan_igdb_name_fallback(
        scan_type=ScanType.UPDATE,
        newly_added=False,
        igdb_id=3070,
    )

    name_lookup.assert_not_awaited()
    id_lookup.assert_awaited_once_with(ANY, 3070)


@pytest.mark.asyncio
async def test_steam_only_windows_update_recovers_igdb_by_normalized_name():
    name_lookup, id_lookup = await _scan_igdb_name_fallback(
        scan_type=ScanType.UPDATE,
        newly_added=False,
        steam_id=227300,
    )

    name_lookup.assert_awaited_once_with(
        ANY,
        "Euro Truck Simulator 2",
        6,
    )
    id_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def _scan_steam_patch(
    *,
    scan_type: ScanType,
    newly_added: bool,
    platform_slug: str = "win",
    steam_id: int | None = 292030,
    metadata_sources: list[str] | None = None,
    patch_data: dict | None = None,
    igdb_metadata: dict | None = None,
    metadata_only: bool = False,
):
    platform, rom = _igdb_scan_fixture(
        platform_slug=platform_slug,
        steam_id=steam_id,
        igdb_metadata=igdb_metadata,
    )
    resolver = AsyncMock(
        return_value=(
            patch_data
            if patch_data is not None
            else {
                "steam_id": 292030,
                "steam_metadata": {"app_id": 292030, "source": "storefront"},
                "name": "The Witcher",
                "media": {"cover": ["https://cdn.example/witcher.jpg"]},
            }
        )
    )
    reconcile = AsyncMock(return_value=True)
    persist_igdb_metadata = Mock(return_value=None)
    persist_candidate_metadata = Mock(return_value=None)
    with (
        patch(
            "handler.scan_handler.db_rom_handler.add_rom", side_effect=lambda item: item
        ),
        patch(
            "handler.scan_handler.meta_playmatch_handler.is_enabled", return_value=False
        ),
        patch("handler.scan_handler.resolve_steam_pc_enrichment", resolver),
        patch("handler.scan_handler.reconcile_steam_patch_media", reconcile),
        patch("handler.scan_handler.db_rom_handler.get_rom", return_value=None),
        patch(
            "handler.scan_handler.db_rom_handler.apply_pc_igdb_enrichment",
            persist_igdb_metadata,
        ),
        patch(
            "handler.scan_handler.db_rom_handler.apply_pc_metadata_candidate",
            persist_candidate_metadata,
        ),
        patch(
            "handler.scan_handler.fs_rom_handler.get_pico8_cover_url", return_value=None
        ),
    ):
        result = await scan_rom(
            scan_type=scan_type,
            platform=platform,
            rom=rom,
            fs_rom={
                "fs_name": "The Witcher.exe",
                "flat": True,
                "nested": False,
                "files": [],
                "crc_hash": "",
                "md5_hash": "",
                "sha1_hash": "",
                "ra_hash": "",
            },
            metadata_sources=(
                metadata_sources
                if metadata_sources is not None
                else [MetadataSource.STEAM.value]
            ),
            newly_added=newly_added,
            metadata_only=metadata_only,
        )
    return (
        resolver,
        reconcile,
        result,
        persist_igdb_metadata,
        persist_candidate_metadata,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scan_type", "newly_added", "steam_id"),
    [
        (ScanType.NEW_PLATFORMS, True, None),
        (ScanType.UPDATE, False, 292030),
        (ScanType.COMPLETE, False, 292030),
    ],
)
@pytest.mark.parametrize("platform_slug", ["win", "linux", "mac"])
async def test_admin_pc_scans_use_the_shared_steam_patch(
    scan_type: ScanType,
    newly_added: bool,
    steam_id: int | None,
    platform_slug: str,
):
    resolver, reconcile, result, _, _ = await _scan_steam_patch(
        scan_type=scan_type,
        newly_added=newly_added,
        platform_slug=platform_slug,
        steam_id=steam_id,
    )

    resolver.assert_awaited_once()
    request = resolver.await_args.args[0]
    assert request.scan_context == scan_type.value
    assert request.platform_slug == platform_slug
    assert request.fs_name == "The Witcher.exe"
    assert result.name == "The Witcher"
    reconcile.assert_awaited_once_with(result, resolver.return_value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scan_type", "newly_added", "platform_slug", "metadata_sources"),
    [
        (ScanType.QUICK, True, "win", [MetadataSource.STEAM]),
        (ScanType.HASHES, False, "win", [MetadataSource.STEAM]),
        (ScanType.UPDATE, False, "snes", [MetadataSource.STEAM]),
        (ScanType.UPDATE, False, "win", [MetadataSource.IGDB]),
    ],
)
async def test_non_parity_scan_paths_do_not_call_steam(
    scan_type: ScanType,
    newly_added: bool,
    platform_slug: str,
    metadata_sources: list[str],
):
    resolver, reconcile, _, _, _ = await _scan_steam_patch(
        scan_type=scan_type,
        newly_added=newly_added,
        platform_slug=platform_slug,
        metadata_sources=metadata_sources,
    )

    resolver.assert_not_awaited()
    reconcile.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("patch_data", [{}, {"steam_id": 292030}])
async def test_empty_or_text_only_steam_patch_never_reconciles_media(patch_data: dict):
    resolver, reconcile, _, _, _ = await _scan_steam_patch(
        scan_type=ScanType.COMPLETE,
        newly_added=False,
        patch_data=patch_data,
    )

    resolver.assert_awaited_once()
    reconcile.assert_not_awaited()


@pytest.mark.asyncio
async def test_steam_media_reconciliation_uses_the_persisted_rom_timestamp():
    platform, rom = _igdb_scan_fixture(platform_slug="win", steam_id=292030)
    persisted = SimpleNamespace(id=rom.id, updated_at="stale-in-memory-timestamp")
    refreshed = SimpleNamespace(id=rom.id, updated_at="database-timestamp")
    resolver = AsyncMock(
        return_value={
            "steam_id": 292030,
            "steam_metadata": {"app_id": 292030, "source": "storefront"},
            "media": {"cover": ["https://cdn.example/witcher.jpg"]},
        }
    )
    reconcile = AsyncMock(return_value=True)

    with (
        patch("handler.scan_handler.db_rom_handler.add_rom", return_value=persisted),
        patch("handler.scan_handler.db_rom_handler.get_rom", return_value=refreshed),
        patch(
            "handler.scan_handler.meta_playmatch_handler.is_enabled", return_value=False
        ),
        patch("handler.scan_handler.resolve_steam_pc_enrichment", resolver),
        patch("handler.scan_handler.reconcile_steam_patch_media", reconcile),
        patch(
            "handler.scan_handler.fs_rom_handler.get_pico8_cover_url", return_value=None
        ),
    ):
        await scan_rom(
            scan_type=ScanType.COMPLETE,
            platform=platform,
            rom=rom,
            fs_rom={
                "fs_name": "The Witcher.exe",
                "flat": True,
                "nested": False,
                "files": [],
                "crc_hash": "",
                "md5_hash": "",
                "sha1_hash": "",
                "ra_hash": "",
            },
            metadata_sources=[MetadataSource.STEAM.value],
            newly_added=False,
        )

    reconcile.assert_awaited_once_with(refreshed, resolver.return_value)


@pytest.mark.asyncio
async def test_metadata_only_keeps_text_metadata_but_skips_artwork_side_effects(mocker):
    sgdb_lookup = mocker.patch(
        "handler.scan_handler.meta_sgdb_handler.get_details_by_names",
        new_callable=AsyncMock,
    )
    resolver, reconcile, result, _, _ = await _scan_steam_patch(
        scan_type=ScanType.COMPLETE,
        newly_added=False,
        metadata_sources=[MetadataSource.STEAM, MetadataSource.SGDB],
        metadata_only=True,
        patch_data={
            "steam_id": 292030,
            "steam_metadata": {"app_id": 292030, "source": "storefront"},
            "summary": "Updated text metadata",
            "media": {"cover": ["https://cdn.example/witcher.jpg"]},
        },
    )

    assert result.summary == "Updated text metadata"
    resolver.assert_awaited_once()
    reconcile.assert_not_awaited()
    sgdb_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_metadata_only_refreshes_existing_pc_component_steam_metadata(mocker):
    auto_link_igdb = mocker.patch("handler.scan_handler.auto_link_pc_dlc_components")
    auto_link_steam = mocker.patch(
        "handler.scan_handler.auto_link_parent_listed_steam_dlc_components",
        new_callable=AsyncMock,
    )

    await _scan_steam_patch(
        scan_type=ScanType.COMPLETE,
        newly_added=False,
        metadata_only=True,
        patch_data={
            "steam_id": 292030,
            "steam_metadata": {"app_id": 292030, "source": "storefront"},
        },
    )

    auto_link_igdb.assert_not_called()
    auto_link_steam.assert_awaited_once_with(mocker.ANY, link_missing=False)


@pytest.mark.asyncio
async def test_steam_structured_metadata_persists_through_rom_not_metadata_view():
    structured_steam_metadata = {
        "main_developer": "CD Projekt RED",
        "publishers": ["CD Projekt RED"],
        "pc_release_date": 1_432_080_000,
    }
    _, _, _, persist_igdb_metadata, persist_candidate_metadata = (
        await _scan_steam_patch(
            scan_type=ScanType.COMPLETE,
            newly_added=False,
            igdb_metadata={"themes": ["Fantasy"], "franchises": ["The Witcher"]},
            patch_data={
                "steam_id": 292030,
                "steam_metadata": {"app_id": 292030, "source": "storefront"},
                "metadata": structured_steam_metadata,
                "media": {"cover": ["https://cdn.example/witcher.jpg"]},
            },
        )
    )

    persist_igdb_metadata.assert_called_once()
    assert persist_igdb_metadata.call_args.args[2] == {
        "igdb_metadata": {
            "themes": ["Fantasy"],
            "franchises": ["The Witcher"],
            **structured_steam_metadata,
        }
    }
    persist_candidate_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_steam_scan_defers_automation_until_the_final_scan_write():
    """The caller owns automation after all scan-side writes are durable."""
    platform, rom = _igdb_scan_fixture(platform_slug="win")
    persisted = SimpleNamespace(id=rom.id, updated_at="initial-version")
    after_structured_overlay = SimpleNamespace(id=rom.id, updated_at="overlay-version")
    resolver = AsyncMock(
        return_value={
            "steam_id": 1091500,
            "steam_metadata": {
                "app_id": 1091500,
                "language": "german",
                "fallback_fields": [],
            },
            "summary": "Deutsche Zusammenfassung",
            "metadata": {"main_developer": "CD PROJEKT RED"},
        }
    )
    process_parent = AsyncMock()

    with (
        patch(
            "handler.scan_handler.db_rom_handler.add_rom", return_value=persisted
        ) as add_rom,
        patch(
            "handler.scan_handler.db_rom_handler.get_rom",
            side_effect=[
                after_structured_overlay,
                after_structured_overlay,
            ],
        ),
        patch(
            "handler.scan_handler.db_rom_handler.apply_pc_igdb_enrichment",
            return_value=after_structured_overlay,
        ),
        patch(
            "handler.scan_handler.meta_playmatch_handler.is_enabled", return_value=False
        ),
        patch("handler.scan_handler.resolve_steam_pc_enrichment", resolver),
        patch(
            "handler.scan_handler.pc_automation_handler.process_parent", process_parent
        ),
        patch(
            "handler.scan_handler.fs_rom_handler.get_pico8_cover_url", return_value=None
        ),
    ):
        await scan_rom(
            scan_type=ScanType.NEW_PLATFORMS,
            platform=platform,
            rom=rom,
            fs_rom={
                "fs_name": "Cyberpunk 2077.exe",
                "flat": True,
                "nested": False,
                "files": [],
                "crc_hash": "",
                "md5_hash": "",
                "sha1_hash": "",
                "ra_hash": "",
            },
            metadata_sources=[MetadataSource.STEAM],
            newly_added=True,
        )

    process_parent.assert_not_awaited()
    assert add_rom.call_args_list[-1].args[0].summary == "Deutsche Zusammenfassung"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("steam_id", "german_summary"),
    [
        (1091500, "Cyberpunk 2077 ist ein Open-World-Action-Adventure."),
        (2138330, "Phantom Liberty ist eine Spionage-Thriller-Erweiterung."),
    ],
)
async def test_update_scan_persists_german_steam_summary_to_the_durable_catalog(
    steam_id: int, german_summary: str
):
    windows = db_platform_handler.add_platform(
        Platform(name="Windows", slug="win", fs_slug="win")
    )
    rom = db_rom_handler.add_rom(
        Rom(
            platform_id=windows.id,
            name="English catalog title",
            summary="English catalog summary",
            fs_name=f"Steam-{steam_id}.exe",
            fs_name_no_tags=f"Steam-{steam_id}",
            fs_name_no_ext=f"Steam-{steam_id}",
            fs_extension="exe",
            fs_path="win",
            steam_id=steam_id,
            steam_metadata={
                "app_id": steam_id,
                "language": "german",
                "fallback_fields": [],
                "fields": ["summary"],
            },
        )
    )
    resolver = AsyncMock(
        return_value={
            "steam_id": steam_id,
            "steam_metadata": {
                "app_id": steam_id,
                "language": "german",
                "fallback_fields": [],
                "fields": ["summary"],
            },
            "summary": german_summary,
        }
    )

    with (
        patch(
            "handler.scan_handler.meta_playmatch_handler.is_enabled", return_value=False
        ),
        patch("handler.scan_handler.resolve_steam_pc_enrichment", resolver),
        patch(
            "handler.scan_handler.fs_rom_handler.get_pico8_cover_url", return_value=None
        ),
    ):
        await scan_rom(
            scan_type=ScanType.UPDATE,
            platform=windows,
            rom=rom,
            fs_rom={
                "fs_name": rom.fs_name,
                "flat": True,
                "nested": False,
                "files": [],
                "crc_hash": "",
                "md5_hash": "",
                "sha1_hash": "",
                "ra_hash": "",
            },
            metadata_sources=[MetadataSource.STEAM],
            newly_added=False,
        )

    durable_rom = db_rom_handler.get_rom(rom.id)
    assert durable_rom is not None
    assert durable_rom.summary == german_summary
    assert durable_rom.steam_metadata["language"] == "german"
    assert "summary" not in durable_rom.steam_metadata["fallback_fields"]
