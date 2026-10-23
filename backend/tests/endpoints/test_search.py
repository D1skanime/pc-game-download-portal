from unittest.mock import AsyncMock

import pytest

from endpoints import search
from handler.database import db_rom_handler


@pytest.mark.parametrize("locale", ["de-DE", "fr-FR", "en"])
@pytest.mark.parametrize("mode", ["name", "id"])
def test_ss_search_captures_locale_and_preview(
    client, access_token, rom, monkeypatch, locale, mode
):
    for name in (
        "igdb",
        "moby",
        "flashpoint",
        "launchbox",
        "steam",
        "sgdb",
        "libretro",
    ):
        handler = getattr(search, "meta_" + name + "_handler")
        for method in (
            "get_matched_rom_by_id",
            "get_matched_roms_by_name",
            "get_rom_by_id",
        ):
            if hasattr(handler, method):
                monkeypatch.setattr(
                    type(handler),
                    method,
                    AsyncMock(return_value=None if mode == "id" else []),
                )
    monkeypatch.setattr(
        type(search.meta_sgdb_handler),
        "get_details_by_names",
        AsyncMock(return_value={"sgdb_id": None}),
    )
    monkeypatch.setattr(
        type(search.meta_libretro_handler),
        "get_rom",
        AsyncMock(return_value={"libretro_id": None}),
    )
    monkeypatch.setattr(type(search.meta_ss_handler), "is_enabled", lambda self: True)
    ss = {
        "ss_id": 33333,
        "name": "Localized game",
        "ss_metadata": {
            "text_variants": {
                locale[:2]: {
                    "source_language": locale[:2],
                    "summary": "Localized preview",
                }
            }
        },
    }
    call = AsyncMock(return_value=ss if mode == "id" else [ss])
    monkeypatch.setattr(
        type(search.meta_ss_handler),
        "get_matched_rom_by_id" if mode == "id" else "get_matched_roms_by_name",
        call,
    )
    response = client.get(
        "/api/search/roms",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "rom_id": rom.id,
            "search_term": "33333" if mode == "id" else "Game",
            "search_by": mode,
            "metadata_locale": locale,
        },
    )
    assert response.status_code == 200, response.text
    assert call.await_args is not None
    assert call.await_args.kwargs["metadata_locale"] == locale[:2]
    assert (
        response.json()[0]["ss_metadata"]["text_variants"][locale[:2]]["summary"]
        == "Localized preview"
    )
    assert db_rom_handler.get_rom(rom.id).ss_id == rom.ss_id


def test_steam_id_search_returns_localized_provider_preview(
    client, access_token, rom, monkeypatch
):
    for name in ("igdb", "moby", "ss", "launchbox"):
        handler = getattr(search, "meta_" + name + "_handler")
        monkeypatch.setattr(
            type(handler), "get_matched_rom_by_id", AsyncMock(return_value=None)
        )
    monkeypatch.setattr(
        type(search.meta_steam_handler), "is_enabled", lambda self: True
    )
    result = {
        "steam_id": 700,
        "name": "Steam identity",
        "steam_metadata": {
            "app_id": 700,
            "source": "storefront",
            "text_variants": {
                "fr": {
                    "source_language": "french",
                    "requested_language": "french",
                    "language_evidence": "provider_slot",
                    "summary": "Texte français",
                },
                "en": {"source_language": "english", "summary": "English preview"},
            },
        },
    }
    fetch = AsyncMock(return_value=result)
    monkeypatch.setattr(type(search.meta_steam_handler), "get_rom_by_id", fetch)
    monkeypatch.setattr(
        type(search.meta_sgdb_handler),
        "get_details_by_names",
        AsyncMock(return_value={"sgdb_id": None}),
    )
    monkeypatch.setattr(
        type(search.meta_libretro_handler),
        "get_rom",
        AsyncMock(return_value={"libretro_id": None}),
    )
    response = client.get(
        "/api/search/roms",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "rom_id": rom.id,
            "search_by": "id",
            "search_term": "700",
            "metadata_locale": "fr-FR",
        },
    )
    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["steam_id"] == 700
    assert (
        response.json()[0]["steam_metadata"]["text_variants"]["fr"]["source_language"]
        == "french"
    )
    assert fetch.await_args is not None
    assert fetch.await_args.kwargs["metadata_locale"] == "fr"
