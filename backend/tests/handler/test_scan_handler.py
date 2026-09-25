from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from handler.scan_handler import MetadataSource, resolve_steam_scan_metadata
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
