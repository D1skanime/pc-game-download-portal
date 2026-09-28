from types import SimpleNamespace
from typing import cast
from unittest.mock import ANY, AsyncMock, patch

import pytest

from handler.scan_handler import (
    MetadataSource,
    ScanType,
    _apply_metadata_handler_fields,
    _is_steam_only_windows_igdb_recovery,
    _steam_artwork_handler,
    _windows_igdb_lookup_name,
    resolve_steam_scan_metadata,
    scan_rom,
)
from models.platform import Platform
from models.rom import Rom


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


def test_steam_media_enters_the_existing_artwork_priority_handler():
    assert _steam_artwork_handler(
        {
            "steam_id": 1903340,
            "media": {
                "cover": ["https://cdn.example/cover.jpg"],
                "screenshots": ["https://cdn.example/shot.jpg"],
            },
        }
    ) == {
        "steam_id": 1903340,
        "url_cover": "https://cdn.example/cover.jpg",
        "url_screenshots": ["https://cdn.example/shot.jpg"],
    }


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
async def test_stored_steam_id_refreshes_directly_after_filename_change():
    direct = AsyncMock(return_value={"steam_id": 1091500, "name": "Steam title"})
    search = AsyncMock()
    with (
        patch("handler.scan_handler.meta_steam_handler.get_rom_by_id", direct),
        patch("handler.scan_handler.meta_steam_handler.get_rom", search),
    ):
        updates = await resolve_steam_scan_metadata(
            cast("Rom", _rom(steam_id=1091500)),
            cast("Platform", _platform("win")),
            "Renamed game.exe",
            [MetadataSource.STEAM],
        )

    direct.assert_awaited_once_with(1091500, "win")
    search.assert_not_awaited()
    assert updates["steam_id"] == 1091500


@pytest.mark.asyncio
async def test_stored_steam_id_rejects_a_different_resolved_app_id():
    direct = AsyncMock(return_value={"steam_id": 1091501, "name": "Other game"})
    with patch("handler.scan_handler.meta_steam_handler.get_rom_by_id", direct):
        updates = await resolve_steam_scan_metadata(
            cast("Rom", _rom(steam_id=1091500)),
            cast("Platform", _platform("win")),
            "Renamed game.exe",
            [MetadataSource.STEAM],
        )

    direct.assert_awaited_once_with(1091500, "win")
    assert updates == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("platform_slug", ["win", "linux", "mac"])
async def test_eligible_pc_platforms_search_steam_only_without_a_stored_id(
    platform_slug: str,
):
    direct = AsyncMock()
    search = AsyncMock(return_value={"steam_id": 1091500})
    with (
        patch("handler.scan_handler.meta_steam_handler.get_rom_by_id", direct),
        patch("handler.scan_handler.meta_steam_handler.get_rom", search),
    ):
        await resolve_steam_scan_metadata(
            cast("Rom", _rom()),
            cast("Platform", _platform(platform_slug)),
            "Game.exe",
            [MetadataSource.STEAM],
        )

    direct.assert_not_awaited()
    search.assert_awaited_once_with("Game.exe", platform_slug)


@pytest.mark.asyncio
@pytest.mark.parametrize("platform_slug", ["dos", "win3x", "win9x"])
async def test_excluded_pc_platforms_use_only_an_explicit_stored_steam_id(
    platform_slug: str,
):
    direct = AsyncMock(return_value={"steam_id": 1091500})
    search = AsyncMock()
    with (
        patch("handler.scan_handler.meta_steam_handler.get_rom_by_id", direct),
        patch("handler.scan_handler.meta_steam_handler.get_rom", search),
    ):
        await resolve_steam_scan_metadata(
            cast("Rom", _rom(steam_id=1091500)),
            cast("Platform", _platform(platform_slug)),
            "Game.exe",
            [MetadataSource.STEAM],
        )
        await resolve_steam_scan_metadata(
            cast("Rom", _rom()),
            cast("Platform", _platform(platform_slug)),
            "Game.exe",
            [MetadataSource.STEAM],
        )

    direct.assert_awaited_once_with(1091500, platform_slug)
    search.assert_not_awaited()


@pytest.mark.asyncio
async def test_classic_roms_never_call_steam():
    direct = AsyncMock()
    search = AsyncMock()
    with (
        patch("handler.scan_handler.meta_steam_handler.get_rom_by_id", direct),
        patch("handler.scan_handler.meta_steam_handler.get_rom", search),
    ):
        updates = await resolve_steam_scan_metadata(
            cast("Rom", _rom(steam_id=1091500)),
            cast("Platform", _platform("snes")),
            "Game.sfc",
            [MetadataSource.STEAM],
        )

    assert updates == {}
    direct.assert_not_awaited()
    search.assert_not_awaited()


@pytest.mark.asyncio
async def test_steam_failure_is_empty_and_preserves_existing_state():
    with patch(
        "handler.scan_handler.meta_steam_handler.get_rom_by_id",
        AsyncMock(side_effect=TimeoutError()),
    ):
        updates = await resolve_steam_scan_metadata(
            cast("Rom", _rom(steam_id=1091500)),
            cast("Platform", _platform("win")),
            "Game.exe",
            [MetadataSource.STEAM],
        )

    assert updates == {}
