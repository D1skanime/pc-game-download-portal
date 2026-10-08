from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from adapters.services.steam import SteamService
from adapters.services.steam_types import SteamAppDetails, SteamFullGame


def _response(payload: object) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value=payload)
    return response


@pytest.fixture
def session():
    mock_session = AsyncMock()
    with patch("adapters.services.steam.ctx_aiohttp_session") as context:
        context.get.return_value = mock_session
        yield mock_session


async def test_app_details_sends_the_requested_locale(session):
    """A localized Steam request must use the configured storefront locale."""
    session.get.return_value = _response(
        {"1091500": {"success": True, "data": {"type": "game"}}}
    )

    details = await SteamService().get_app_details(1091500, country="CH", language="de")

    assert details == {"type": "game"}
    request_url = str(session.get.await_args.args[0])
    assert "cc=CH" in request_url
    assert "l=de" in request_url


async def test_app_details_accepts_a_matching_payload_from_an_unexpected_envelope_key(
    session,
):
    """Steam occasionally caches a valid payload under a stale response key."""
    session.get.return_value = _response(
        {
            "stale-cache-key": {
                "success": True,
                "data": {"steam_appid": 1091500, "type": "game"},
            }
        }
    )

    assert await SteamService().get_app_details(1091500) == {
        "steam_appid": 1091500,
        "type": "game",
    }


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError(),
        aiohttp.ClientConnectionError(),
        ValueError("malformed payload"),
    ],
)
async def test_storefront_failures_degrade_to_empty_results(session, failure):
    session.get.side_effect = failure

    assert (
        await SteamService().search_apps("Cyberpunk", country="CH", language="de") == []
    )


async def test_malformed_storefront_envelopes_degrade_to_empty_results(session):
    session.get.return_value = _response(["not", "an", "object"])

    assert (
        await SteamService().search_apps("Cyberpunk", country="CH", language="de") == []
    )
    assert (
        await SteamService().get_app_details(1091500, country="CH", language="de")
        is None
    )


async def test_rate_limit_retries_are_bounded_then_degrade(session):
    response = MagicMock()
    response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        MagicMock(), (), status=429
    )
    session.get.return_value = response

    with (
        patch("adapters.services.steam._rate_limiter.acquire", new=AsyncMock()),
        patch("adapters.services.steam.asyncio.sleep", new=AsyncMock()),
    ):
        assert (
            await SteamService().search_apps("Cyberpunk", country="CH", language="de")
            == []
        )

    assert session.get.await_count == 3


def test_dlc_fullgame_transport_contract_keeps_only_the_parent_identity():
    annotations = SteamFullGame.__annotations__

    assert annotations["appid"] == int | str
    assert str(annotations["name"]) == "typing.NotRequired[str]"
    assert SteamAppDetails.__annotations__["fullgame"].__args__[0] is SteamFullGame


def test_parse_storefront_results_filters_invalid_candidates() -> None:
    payload = {"results_html": """
        <a data-ds-appid="123" href="#"><span class="title">Valid &amp; DLC</span></a>
        <a data-ds-appid="bad,0,456" href="#"><span class="title">Second</span></a>
        <a data-ds-appid="789" href="#"><span class="title">   </span></a>
        """}

    assert SteamService._parse_storefront_results(payload) == [
        {"type": "app", "id": 123, "name": "Valid & DLC"},
        {"type": "app", "id": 456, "name": "Second"},
    ]


@pytest.mark.asyncio
async def test_search_apps_prefers_primary_storesearch(monkeypatch) -> None:
    service = SteamService()
    calls: list[str] = []

    async def request(url: str) -> dict:
        calls.append(url)
        return {"items": [{"type": "app", "id": 292030, "name": "The Witcher 3"}]}

    monkeypatch.setattr(service, "_request", request)

    result = await service.search_apps("The Witcher 3")

    assert result == [{"type": "app", "id": 292030, "name": "The Witcher 3"}]
    assert len(calls) == 1
    assert "/api/storesearch" in calls[0]
