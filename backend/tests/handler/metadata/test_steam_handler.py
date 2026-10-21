from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from handler.metadata import steam_handler
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
    result = await handler.get_rom_by_id(1091500, "win", metadata_locale="de")

    assert result["steam_id"] == 1091500
    assert result["summary"] == "An open-world RPG."
    assert result["steam_metadata"]["fallback_fields"] == ["summary"]
    calls = handler.steam_service.get_app_details.await_args_list
    assert [call.args[0] for call in calls] == [1091500, 1091500]
    assert calls[0].kwargs == {"country": "CH", "language": "german"}
    assert calls[1].kwargs == {"country": "US", "language": "english"}


async def test_requested_ui_locale_selects_mapped_steam_language_and_keeps_variants(
    handler,
):
    handler.steam_service.get_app_details = AsyncMock(
        side_effect=[
            {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "short_description": "Un jeu de rôle.",
            },
            {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "short_description": "Ein Rollenspiel.",
            },
            {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "short_description": "An RPG.",
            },
        ]
    )

    with patch.object(
        steam_handler,
        "STEAM_API_TEXT_LANGUAGES",
        ("german", "english"),
        create=True,
    ):
        result = await handler.get_rom_by_id(1091500, metadata_locale="fr-FR")

    assert result["steam_metadata"]["language"] == "french"
    assert result["steam_metadata"]["text_variants"] == {
        "fr": {
            "source_language": "french",
            "requested_language": "french",
            "language_evidence": "provider_slot",
            "name": "Cyberpunk 2077",
            "summary": "Un jeu de rôle.",
        },
        "de": {
            "source_language": "german",
            "requested_language": "german",
            "language_evidence": "provider_slot",
            "name": "Cyberpunk 2077",
            "summary": "Ein Rollenspiel.",
        },
        "en": {
            "source_language": "english",
            "requested_language": "english",
            "language_evidence": "provider_slot",
            "name": "Cyberpunk 2077",
            "summary": "An RPG.",
        },
    }
    assert [
        call.kwargs["language"]
        for call in handler.steam_service.get_app_details.await_args_list
    ] == ["french", "german", "english"]


async def test_missing_requested_locale_records_selected_provider_language(handler):
    handler.steam_service.get_app_details = AsyncMock(
        side_effect=[
            None,
            {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "short_description": "Ein Rollenspiel.",
            },
            {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "short_description": "An RPG.",
            },
        ]
    )

    with patch.object(
        steam_handler,
        "STEAM_API_TEXT_LANGUAGES",
        ("german", "english"),
        create=True,
    ):
        result = await handler.get_rom_by_id(1091500, metadata_locale="fr-FR")

    assert result["steam_metadata"]["language"] == "german"
    assert result["steam_metadata"]["fallback_language"] == "english"
    assert result["steam_metadata"]["text_variants"] == {
        "de": {
            "source_language": "german",
            "requested_language": "german",
            "language_evidence": "provider_slot",
            "name": "Cyberpunk 2077",
            "summary": "Ein Rollenspiel.",
        },
        "en": {
            "source_language": "english",
            "requested_language": "english",
            "language_evidence": "provider_slot",
            "name": "Cyberpunk 2077",
            "summary": "An RPG.",
        },
    }


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

    result = await handler.get_rom_by_id(1091500, metadata_locale="de")

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


async def test_store_details_keep_localized_genres_categories_and_dlc_ids(handler):
    handler.steam_service.get_app_details = AsyncMock(
        return_value={
            "type": "game",
            "name": "Cyberpunk 2077",
            "steam_appid": 1091500,
            "genres": [{"id": "3", "description": "Rollenspiel"}],
            "categories": [
                {"id": 2, "description": "Einzelspieler"},
                {"id": 29, "description": "Steam-Cloud"},
            ],
            "dlc": [2138330, "bad", 0],
        }
    )

    result = await handler.get_rom_by_id(1091500, metadata_locale="de")

    assert result["steam_metadata"] == {
        "language": "german",
        "fallback_language": "english",
        "text_variants": {
            "de": {
                "source_language": "german",
                "requested_language": "german",
                "language_evidence": "provider_slot",
                "name": "Cyberpunk 2077",
            },
            "en": {
                "source_language": "english",
                "requested_language": "english",
                "language_evidence": "provider_slot",
                "name": "Cyberpunk 2077",
            },
        },
        "type": "game",
        "genres": ["Rollenspiel"],
        "categories": ["Einzelspieler", "Steam-Cloud"],
        "dlc_ids": [2138330],
    }


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


async def test_filesystem_pc_slug_does_not_search_steam(handler):
    handler.steam_service.search_apps = AsyncMock()

    result = await handler.get_rom("Dwarf Fortress", "pc")

    assert result == {"steam_id": None}
    handler.steam_service.search_apps.assert_not_awaited()


async def test_compact_pc_filename_is_split_before_steam_search(handler):
    handler.steam_service.search_apps = AsyncMock(
        return_value=[
            {"id": 1903340, "name": "Clair Obscur: Expedition 33", "type": "app"}
        ]
    )
    handler.steam_service.get_app_details = AsyncMock(
        return_value={
            "type": "game",
            "name": "Clair Obscur: Expedition 33",
            "steam_appid": 1903340,
        }
    )

    result = await handler.get_rom("ClairObscurExpedition33.exe", "win")

    assert result["steam_id"] == 1903340
    handler.steam_service.search_apps.assert_awaited_once_with(
        "clair obscur expedition 33", country="US", language="english"
    )


async def test_name_search_skips_soundtrack_and_uses_next_valid_game(handler):
    """A better fuzzy soundtrack match must not hide the actual game."""
    handler.steam_service.search_apps = AsyncMock(
        return_value=[
            {
                "id": 292031,
                "name": "The Witcher 3: Wild Hunt Soundtrack",
                "type": "app",
            },
            {
                "id": 292030,
                "name": "The Witcher 3: Wild Hunt - Complete Edition",
                "type": "app",
            },
        ]
    )

    def details(steam_id, **_kwargs):
        if steam_id == 292031:
            return {"type": "music", "steam_appid": steam_id}
        return {
            "type": "game",
            "name": "The Witcher 3: Wild Hunt",
            "steam_appid": steam_id,
        }

    handler.steam_service.get_app_details = AsyncMock(side_effect=details)

    result = await handler.get_rom("TheWitcher3WildHunt", "win")

    assert result["steam_id"] == 292030
    assert [
        call.args[0] for call in handler.steam_service.get_app_details.await_args_list
    ] == [292031, 292031, 292030, 292030]


async def test_invalid_store_type_and_disabled_provider_return_no_match(handler):
    handler.steam_service.get_app_details = AsyncMock(
        return_value={"type": "bundle", "steam_appid": 1091500}
    )

    assert await handler.get_rom_by_id(1091500, metadata_locale="de") == {
        "steam_id": None
    }

    with patch("handler.metadata.steam_handler.STEAM_API_ENABLED", False):
        assert await handler.get_rom_by_id(1091500, metadata_locale="de") == {
            "steam_id": None
        }


async def test_default_languages_retain_german_and_english_text_variants(handler):
    handler.steam_service.get_app_details = AsyncMock(
        side_effect=[
            {
                "type": "game",
                "steam_appid": 1091500,
                "name": "Cyberpunk 2077",
                "short_description": "Ein Open-World-Rollenspiel.",
            },
            {
                "type": "game",
                "steam_appid": 1091500,
                "name": "Cyberpunk 2077",
                "short_description": "An open-world RPG.",
            },
        ]
    )

    result = await handler.get_rom_by_id(1091500, metadata_locale="de")

    assert result["name"] == "Cyberpunk 2077"
    assert result["summary"] == "Ein Open-World-Rollenspiel."
    assert result["steam_metadata"]["text_variants"] == {
        "de": {
            "source_language": "german",
            "requested_language": "german",
            "language_evidence": "provider_slot",
            "name": "Cyberpunk 2077",
            "summary": "Ein Open-World-Rollenspiel.",
        },
        "en": {
            "source_language": "english",
            "requested_language": "english",
            "language_evidence": "provider_slot",
            "name": "Cyberpunk 2077",
            "summary": "An open-world RPG.",
        },
    }
    assert [
        call.args[0] for call in handler.steam_service.get_app_details.await_args_list
    ] == [1091500, 1091500]


async def test_configured_supported_language_adds_one_same_app_text_variant(handler):
    handler.steam_service.get_app_details = AsyncMock(
        side_effect=[
            {
                "type": "game",
                "steam_appid": 1091500,
                "name": "Cyberpunk 2077",
                "short_description": "Ein Open-World-Rollenspiel.",
            },
            {
                "type": "game",
                "steam_appid": 1091500,
                "name": "Cyberpunk 2077",
                "short_description": "Un jeu de rôle en monde ouvert.",
            },
            {
                "type": "game",
                "steam_appid": 1091500,
                "name": "Cyberpunk 2077",
                "short_description": "An open-world RPG.",
            },
        ]
    )

    with patch.object(
        steam_handler,
        "STEAM_API_TEXT_LANGUAGES",
        ("german", "french", "english"),
        create=True,
    ):
        result = await handler.get_rom_by_id(1091500, metadata_locale="de")

    assert result["steam_metadata"]["text_variants"]["fr"] == {
        "source_language": "french",
        "requested_language": "french",
        "language_evidence": "provider_slot",
        "name": "Cyberpunk 2077",
        "summary": "Un jeu de rôle en monde ouvert.",
    }
    assert [
        call.args[0] for call in handler.steam_service.get_app_details.await_args_list
    ] == [1091500, 1091500, 1091500]


def test_text_language_configuration_is_canonicalized_and_bounded():
    from config import parse_steam_api_text_languages

    assert parse_steam_api_text_languages(
        " german, english, german, french, unsupported, , ENGLISH "
    ) == ("german", "english", "french")
    assert parse_steam_api_text_languages("de, en, de") == ("german", "english")


async def test_invalid_localized_responses_do_not_discard_valid_text_variants(handler):
    handler.steam_service.get_app_details = AsyncMock(
        side_effect=[
            {
                "type": "game",
                "steam_appid": 1091500,
                "name": " Cyberpunk 2077 ",
                "short_description": " Ein Open-World-Rollenspiel. ",
            },
            {"type": "game", "steam_appid": 999, "name": "Wrong game"},
            {
                "type": "game",
                "steam_appid": 1091500,
                "name": "   ",
                "short_description": "",
            },
            None,
        ]
    )

    with patch.object(
        steam_handler,
        "STEAM_API_TEXT_LANGUAGES",
        ("german", "english", "french", "spanish"),
        create=True,
    ):
        result = await handler.get_rom_by_id(1091500, metadata_locale="de")

    assert result["name"] == " Cyberpunk 2077 "
    assert result["summary"] == " Ein Open-World-Rollenspiel. "
    assert result["steam_metadata"]["text_variants"] == {
        "de": {
            "source_language": "german",
            "requested_language": "german",
            "language_evidence": "provider_slot",
            "name": "Cyberpunk 2077",
            "summary": "Ein Open-World-Rollenspiel.",
        }
    }
    assert [
        call.args[0] for call in handler.steam_service.get_app_details.await_args_list
    ] == [1091500, 1091500, 1091500, 1091500]


async def test_name_search_hydrates_candidates_with_review_media(handler):
    handler.steam_service.search_apps = AsyncMock(
        return_value=[
            {
                "id": 456,
                "name": "The Witcher 3: Wild Hunt - Blood and Wine Soundtrack",
                "type": "app",
            },
            {
                "id": 123,
                "name": "The Witcher 3: Wild Hunt - Blood and Wine",
                "type": "app",
            },
        ]
    )

    async def get_rom_by_id(steam_id, _platform_slug):
        if steam_id == 456:
            return {"steam_id": None}
        return {
            "type": "dlc",
            "name": "The Witcher 3: Wild Hunt - Blood and Wine",
            "steam_id": 123,
            "summary": "A major expansion.",
            "url_cover": "https://cdn.example/header.jpg",
            "url_screenshots": ["https://cdn.example/screenshot.jpg"],
        }

    handler.get_rom_by_id = AsyncMock(side_effect=get_rom_by_id)

    results = await handler.get_matched_roms_by_name("The Witcher 3: Wild Hunt", "win")

    assert results[0]["steam_id"] == 123
    assert results[0]["url_cover"] == "https://cdn.example/header.jpg"
    assert results[0]["url_screenshots"] == ["https://cdn.example/screenshot.jpg"]
    assert len(results) == 1
    assert [call.args[0] for call in handler.get_rom_by_id.await_args_list] == [
        456,
        123,
    ]


async def test_text_only_collects_bounded_requested_and_english_without_artwork(
    handler,
):
    handler.steam_service.get_app_details = AsyncMock(
        side_effect=lambda app_id, **kwargs: {
            "steam_appid": app_id,
            "type": "game",
            "name": "Title",
            "short_description": {
                "french": "Description francaise.",
                "german": "Deutsche Beschreibung.",
                "english": "English description.",
            }[kwargs["language"]],
        }
    )
    handler.steam_service.search_apps = AsyncMock()
    result = await handler.get_rom_by_id(
        1091500,
        "win",
        metadata_locale="fr_FR",
        descriptions_only=True,
        text_languages=("fr", "de", "en", "unsupported") * 100,
    )
    assert set(result) == {"steam_id", "steam_metadata"}
    assert set(result["steam_metadata"]) == {"text_variants"}
    variants = result["steam_metadata"]["text_variants"]
    assert set(variants) == {"fr", "de", "en"}
    assert variants["fr"]["summary"] == "Description francaise."
    assert variants["en"]["summary"] == "English description."
    assert all(v["language_evidence"] == "provider_slot" for v in variants.values())
    assert variants["fr"]["requested_language"] == "french"
    calls = handler.steam_service.get_app_details.await_args_list
    assert [c.kwargs["language"] for c in calls] == ["french", "german", "english"]
    assert [c.kwargs["country"] for c in calls] == ["US", "CH", "US"]
    handler.steam_service.get_library_capsule_url.assert_not_awaited()
    handler.steam_service.search_apps.assert_not_awaited()


async def test_text_only_english_default_and_ambiguous_slot_are_honest(handler):
    handler.steam_service.get_app_details = AsyncMock(return_value=ENGLISH_FULL)
    result = await handler.get_rom_by_id(
        1091500,
        descriptions_only=True,
    )
    assert (
        handler.steam_service.get_app_details.await_args_list[0].kwargs["language"]
        == "english"
    )
    variants = result["steam_metadata"]["text_variants"]
    assert variants["en"]["summary"] == ENGLISH_FULL["short_description"]
    assert "summary" not in variants.get("de", {})
    handler.steam_service.get_library_capsule_url.assert_not_awaited()


@pytest.mark.parametrize("app_id", [True, 0, -1, "1091500"])
async def test_text_only_rejects_invalid_identity_before_transport(handler, app_id):
    result = await handler.get_rom_by_id(app_id, descriptions_only=True)
    assert result == {"steam_id": None}
    handler.steam_service.get_app_details.assert_not_awaited()
    handler.steam_service.get_library_capsule_url.assert_not_awaited()


async def test_text_only_rejects_wrong_app_and_preserves_partial_slots(handler):
    handler.steam_service.get_app_details = AsyncMock(
        side_effect=[
            {**ENGLISH_FULL, "steam_appid": 42},
            ENGLISH_FULL,
        ]
    )
    result = await handler.get_rom_by_id(
        1091500,
        metadata_locale="fr",
        descriptions_only=True,
        text_languages=("fr",),
    )
    assert set(result["steam_metadata"]["text_variants"]) == {"en"}
    handler.steam_service.get_library_capsule_url.assert_not_awaited()


async def test_text_only_uses_real_adapter_urls_and_counts_each_attempt(handler):
    from urllib.parse import parse_qs, urlsplit

    from adapters.services.steam import SteamService

    observed = []

    async def response(url, **kwargs):
        parsed = urlsplit(url)
        assert parsed.path == "/api/appdetails"
        query = parse_qs(parsed.query)
        observed.append(query)
        language = query["l"][0]
        payload = {
            "1091500": {
                "success": True,
                "data": {
                    "steam_appid": 1091500,
                    "type": "game",
                    "short_description": {
                        "french": "Texte francais",
                        "english": "English text",
                    }[language],
                },
            }
        }
        result = MagicMock()
        result.json = AsyncMock(return_value=payload)
        return result

    session = MagicMock(get=AsyncMock(side_effect=response))
    handler.steam_service = SteamService(base_url="http://127.0.0.1:12345/api")
    with (
        patch("adapters.services.steam.ctx_aiohttp_session") as context,
        patch("adapters.services.steam._rate_limiter.acquire", AsyncMock()),
        patch("utils.scan_provider_observation.mark_provider_invoked") as invoked,
    ):
        context.get.return_value = session
        result = await handler.get_rom_by_id(
            1091500,
            metadata_locale="fr",
            descriptions_only=True,
            text_languages=("fr",),
        )
    assert observed == [
        {"appids": ["1091500"], "cc": ["US"], "l": ["french"]},
        {"appids": ["1091500"], "cc": ["US"], "l": ["english"]},
    ]
    assert invoked.call_count == 2
    assert (
        result["steam_metadata"]["text_variants"]["fr"]["summary"] == "Texte francais"
    )


async def test_text_only_timeout_reports_fault_without_artwork(handler):
    from adapters.services.steam import SteamService
    from utils.provider_diagnostics import bind_provider_diagnostics

    faults: list[Exception] = []
    handler.steam_service = SteamService(base_url="http://127.0.0.1:12345/api")
    with (
        patch("adapters.services.steam.ctx_aiohttp_session") as context,
        patch("adapters.services.steam._rate_limiter.acquire", AsyncMock()),
        patch("utils.scan_provider_observation.mark_provider_invoked") as invoked,
        bind_provider_diagnostics(faults.append),
    ):
        context.get.return_value = MagicMock(get=AsyncMock(side_effect=TimeoutError()))
        result = await handler.get_rom_by_id(
            1091500,
            descriptions_only=True,
            text_languages=(),
        )
    assert result["steam_metadata"]["text_variants"] == {}
    assert invoked.call_count == 3
    assert len(faults) == 1 and isinstance(faults[0], TimeoutError)
