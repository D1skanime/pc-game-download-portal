"""Exercise the actual adapters' terminal catches without external requests."""

import json
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from fastapi import HTTPException

from adapters.services import (
    igdb,
    libretro_thumbnails,
    mobygames,
    retroachievements,
    screenscraper,
    steam,
    steamgriddb,
)
from handler.scan_metadata_result import (
    bind_metadata_results,
    observe_provider_fetch,
    resolve_provider_fetch,
)
from utils.context import ctx_aiohttp_session


def adapter(provider, monkeypatch, error):
    module = {
        "igdb": igdb,
        "ra": retroachievements,
        "steam": steam,
        "moby": mobygames,
        "ss": screenscraper,
        "sgdb": steamgriddb,
    }[provider]
    monkeypatch.setattr(
        module, "_rate_limiter", SimpleNamespace(acquire=AsyncMock()), raising=False
    )
    response = SimpleNamespace(
        raise_for_status=Mock(), json=AsyncMock(), text=AsyncMock(return_value="{}")
    )
    if isinstance(error, json.JSONDecodeError):
        response.json.side_effect = error
    elif isinstance(error, aiohttp.ClientResponseError):
        response.raise_for_status.side_effect = error
    request = AsyncMock(return_value=response)
    if isinstance(error, (aiohttp.ClientConnectionError, aiohttp.ServerTimeoutError)):
        request.side_effect = error
    session = SimpleNamespace(get=request, post=request)
    service: Any
    if provider == "igdb":
        service = igdb.IGDBService(
            cast(Any, SimpleNamespace(_update_twitch_token=AsyncMock()))
        )
    elif provider == "ra":
        service = retroachievements.RetroAchievementsService()
    elif provider == "steam":
        service = steam.SteamService()
    elif provider == "moby":
        service = mobygames.MobyGamesService()
    elif provider == "ss":
        monkeypatch.setattr(screenscraper._state, "daily_quota_exhausted", False)
        service = screenscraper.ScreenScraperService()
    else:
        service = steamgriddb.SteamGridDBService()
    return service, session


def response_error(status):
    return aiohttp.ClientResponseError(
        SimpleNamespace(real_url="https://provider.invalid"),
        (),
        status=status,
        message="Synthetic provider fault",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["igdb", "ra", "steam", "moby", "ss", "sgdb"])
@pytest.mark.parametrize(
    "kind, cause",
    [
        ("malformed", "malformed_provider_response"),
        ("unavailable", "metadata_provider_unavailable"),
        ("timeout", "metadata_timeout"),
    ],
)
async def test_actual_terminal_catches_report_per_game(
    provider, kind, cause, monkeypatch
):
    error = {
        "malformed": json.JSONDecodeError("Synthetic invalid JSON", "", 0),
        "unavailable": response_error(503),
        "timeout": aiohttp.ServerTimeoutError(),
    }[kind]
    service, session = adapter(provider, monkeypatch, error)
    token = ctx_aiohttp_session.set(session)
    try:
        with bind_metadata_results() as results:
            await resolve_provider_fetch(
                provider,
                service._request("https://provider.invalid"),
                "Affected.bin",
                {},
            )
        assert any(
            item["provider"] == provider
            and item["auxiliary_path"] == "Affected.bin"
            and item["cause_code"] == cause
            for item in results
        )
    finally:
        ctx_aiohttp_session.reset(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["igdb", "ra", "steam", "moby", "ss", "sgdb"])
async def test_actual_auth_catch_is_terminal_only_in_observed_scan(
    provider, monkeypatch
):
    service, session = adapter(provider, monkeypatch, response_error(403))
    token = ctx_aiohttp_session.set(session)
    try:
        assert await service._request("https://provider.invalid") in ([], {})
        with bind_metadata_results() as results:
            with pytest.raises(aiohttp.ClientResponseError):
                await observe_provider_fetch(
                    provider,
                    service._request("https://provider.invalid"),
                    "Affected.bin",
                )
        assert results == []
    finally:
        ctx_aiohttp_session.reset(token)


@pytest.mark.asyncio
async def test_igdb_invalid_credentials_remain_terminal(monkeypatch):
    service, session = adapter("igdb", monkeypatch, response_error(503))
    session.post.side_effect = igdb.IGDBInvalidCredentialsException()
    token = ctx_aiohttp_session.set(session)
    try:
        with pytest.raises(HTTPException):
            await service._request("https://provider.invalid")
        with bind_metadata_results():
            with pytest.raises(igdb.IGDBInvalidCredentialsException):
                await observe_provider_fetch(
                    "igdb", service._request("https://provider.invalid"), "Affected.bin"
                )
    finally:
        ctx_aiohttp_session.reset(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["hasheous", "playmatch", "flashpoint", "hltb"])
@pytest.mark.parametrize(
    "kind, cause",
    [
        ("malformed", "malformed_provider_response"),
        ("unavailable", "metadata_provider_unavailable"),
        ("timeout", "metadata_timeout"),
    ],
)
async def test_actual_httpx_handler_catches_are_observable(
    provider, kind, cause, monkeypatch
):
    import httpx

    from handler.metadata import (
        flashpoint_handler,
        hasheous_handler,
        hltb_handler,
        playmatch_handler,
    )
    from utils.context import ctx_httpx_client

    modules = {
        "hasheous": hasheous_handler,
        "playmatch": playmatch_handler,
        "flashpoint": flashpoint_handler,
        "hltb": hltb_handler,
    }
    module = modules[provider]
    monkeypatch.setattr(
        module, "_rate_limiter", SimpleNamespace(acquire=AsyncMock()), raising=False
    )
    constructors = {
        "hasheous": hasheous_handler.HasheousHandler,
        "playmatch": playmatch_handler.PlaymatchHandler,
        "flashpoint": flashpoint_handler.FlashpointHandler,
        "hltb": hltb_handler.HLTBHandler,
    }
    service: Any = cast(Any, constructors[provider])()
    service.security_token, service.hp_key, service.hp_val = "synthetic", "key", "value"
    request = httpx.Request("GET", "https://provider.invalid")
    response = httpx.Response(
        503 if kind == "unavailable" else 200,
        request=request,
        content=b"invalid-json" if kind == "malformed" else b"{}",
    )
    fetch = AsyncMock(return_value=response)
    if kind == "timeout":
        fetch.side_effect = httpx.ReadTimeout("Synthetic provider timeout")
    client = SimpleNamespace(request=fetch, get=fetch, post=fetch)
    token = ctx_httpx_client.set(client)
    try:
        coroutine = (
            service._request("https://provider.invalid")
            if provider == "hasheous"
            else service._request("https://provider.invalid", {})
        )
        with bind_metadata_results() as results:
            await resolve_provider_fetch(provider, coroutine, "Affected.bin", {})
        assert any(
            item["cause_code"] == cause and item["provider"] == provider
            for item in results
        )
    finally:
        ctx_httpx_client.reset(token)


@pytest.mark.asyncio
async def test_libretro_actual_listing_failure_reports_game(monkeypatch):
    from adapters.services.libretro_thumbnails_types import LibretroArtType

    monkeypatch.setattr(
        libretro_thumbnails,
        "async_cache",
        SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock()),
    )
    response = SimpleNamespace(raise_for_status=Mock(side_effect=response_error(503)))
    token = ctx_aiohttp_session.set(
        SimpleNamespace(get=AsyncMock(return_value=response))
    )
    try:
        with bind_metadata_results() as results:
            await observe_provider_fetch(
                "libretro",
                libretro_thumbnails.LibretroThumbnailsService().fetch_listing(
                    "Synthetic", LibretroArtType.BOX_ART
                ),
                "Affected.bin",
            )
        assert results[0]["cause_code"] == "metadata_provider_unavailable"
    finally:
        ctx_aiohttp_session.reset(token)


@pytest.mark.asyncio
async def test_launchbox_missing_cache_is_not_a_successful_nomatch(monkeypatch):
    from handler.metadata.launchbox_handler import remote_source

    monkeypatch.setattr(
        remote_source,
        "async_cache",
        SimpleNamespace(exists=AsyncMock(return_value=False)),
    )
    with bind_metadata_results() as results:
        assert (
            await observe_provider_fetch(
                "launchbox",
                remote_source.RemoteSource().get_rom("Affected.bin", "win"),
                "Affected.bin",
            )
            is None
        )
    assert results[0]["cause_code"] == "metadata_provider_unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["igdb", "ra", "steam", "moby", "ss", "sgdb"])
async def test_actual_404_remains_nomatch_without_warning(provider, monkeypatch):
    service, session = adapter(provider, monkeypatch, response_error(404))
    token = ctx_aiohttp_session.set(session)
    try:
        with bind_metadata_results() as results:
            assert await resolve_provider_fetch(
                provider,
                service._request("https://provider.invalid"),
                "Affected.bin",
                {},
            ) in ([], {})
        assert not results
    finally:
        ctx_aiohttp_session.reset(token)
