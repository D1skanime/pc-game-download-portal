from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from handler.metadata.steam_handler import SteamHandler

GERMAN_PARTIAL = {
    "type": "game",
    "name": "Cyberpunk 2077",
    "steam_appid": 1091500,
    "short_description": "",
}
ENGLISH_FULL = {
    "type": "game",
    "name": "Cyberpunk 2077",
    "steam_appid": 1091500,
    "short_description": "An open-world RPG.",
}


@pytest.fixture
def handler():
    with patch("handler.metadata.steam_handler.STEAM_API_ENABLED", True):
        instance = SteamHandler()
        instance.steam_service = MagicMock(
            get_app_details=AsyncMock(side_effect=[GERMAN_PARTIAL, ENGLISH_FULL]),
            get_library_capsule_url=AsyncMock(return_value=None),
        )
        yield instance


async def test_missing_german_summary_falls_back_on_the_same_app_id(handler):
    """A locale fallback cannot resolve a different Steam application."""
    result = await handler.get_rom_by_id(1091500, "win")

    assert result["steam_id"] == 1091500
    assert result["summary"] == "An open-world RPG."
    calls = handler.steam_service.get_app_details.await_args_list
    assert [call.args[0] for call in calls] == [1091500, 1091500]
    assert calls[0].kwargs == {"country": "CH", "language": "de"}
    assert calls[1].kwargs == {"country": "US", "language": "en"}


async def test_fallback_fills_empty_release_and_header_fields_for_the_same_app_id(
    handler,
):
    handler.steam_service.get_app_details = AsyncMock(
        side_effect=[
            {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "header_image": "",
                "release_date": {},
            },
            {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "header_image": "https://cdn.example/header.jpg",
                "release_date": {"date": "10 Dec, 2020", "coming_soon": False},
            },
        ]
    )

    result = await handler.get_rom_by_id(1091500)

    assert result["url_cover"] == "https://cdn.example/header.jpg"
    assert result["steam_metadata"]["release_date"] == {
        "date": "10 Dec, 2020",
        "coming_soon": False,
    }
    assert [
        call.args[0] for call in handler.steam_service.get_app_details.await_args_list
    ] == [
        1091500,
        1091500,
    ]


@pytest.mark.parametrize("platform", ["dos", "win3x", "win9x"])
async def test_excluded_pc_platforms_do_not_name_search(handler, platform):
    handler.steam_service.search_apps = AsyncMock()

    assert await handler.get_rom("Cyberpunk 2077", platform) == {"steam_id": None}
    handler.steam_service.search_apps.assert_not_awaited()


@pytest.mark.parametrize("platform", ["dos", "win3x", "win9x"])
async def test_excluded_pc_platforms_can_resolve_an_explicit_app_id(handler, platform):
    result = await handler.get_rom_by_id(1091500, platform)

    assert result["steam_id"] == 1091500


@pytest.mark.parametrize("platform", ["win", "linux", "mac"])
async def test_eligible_pc_platforms_can_search(handler, platform):
    handler.steam_service.search_apps = AsyncMock(return_value=[])

    assert await handler.get_rom("Cyberpunk 2077", platform) == {"steam_id": None}
    handler.steam_service.search_apps.assert_awaited_once()


async def test_invalid_store_type_and_disabled_provider_return_no_match(handler):
    handler.steam_service.get_app_details = AsyncMock(
        return_value={"type": "bundle", "steam_appid": 1091500}
    )

    assert await handler.get_rom_by_id(1091500) == {"steam_id": None}

    with patch("handler.metadata.steam_handler.STEAM_API_ENABLED", False):
        assert await handler.get_rom_by_id(1091500) == {"steam_id": None}
