import asyncio
import http
import json
from typing import Final, cast

import aiohttp
import yarl
from aiohttp.client import ClientTimeout

from adapters.services.steam_types import (
    SteamAppDetails,
    SteamStoreSearchItem,
)
from logger.logger import log
from utils import get_version
from utils.context import ctx_aiohttp_session
from utils.rate_limiter import RateLimiter

STEAM_MAX_REQUESTS_PER_SECOND: Final[float] = 0.6
STEAM_MAX_REQUEST_ATTEMPTS: Final[int] = 3
STEAM_RATE_LIMIT_BACKOFF_SECONDS: Final[float] = 5
STEAM_LIBRARY_CAPSULE_URL = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{app_id}/library_600x900.jpg"
_rate_limiter = RateLimiter(STEAM_MAX_REQUESTS_PER_SECOND)


class SteamService:
    """Resilient client for the public Steam Storefront endpoints."""

    def __init__(self, base_url: str | None = None) -> None:
        self.url = yarl.URL(base_url or "https://store.steampowered.com/api")

    async def _request(self, url: str, request_timeout: int = 120) -> dict:
        session = ctx_aiohttp_session.get()
        for attempt in range(STEAM_MAX_REQUEST_ATTEMPTS):
            await _rate_limiter.acquire()
            try:
                response = await session.get(
                    url,
                    headers={"user-agent": f"RomM/{get_version()}"},
                    timeout=ClientTimeout(total=request_timeout),
                )
                response.raise_for_status()
                payload = await response.json()
                return payload if isinstance(payload, dict) else {}
            except TimeoutError:
                continue
            except aiohttp.ClientResponseError as exc:
                if (
                    exc.status == http.HTTPStatus.TOO_MANY_REQUESTS
                    and attempt < STEAM_MAX_REQUEST_ATTEMPTS - 1
                ):
                    await asyncio.sleep(STEAM_RATE_LIMIT_BACKOFF_SECONDS)
                    continue
                log.warning("Steam request failed: %s", exc)
                return {}
            except (aiohttp.ClientError, json.JSONDecodeError, ValueError) as exc:
                log.warning("Steam request failed: %s", exc)
                return {}
        return {}

    async def search_apps(
        self, term: str, *, country: str = "US", language: str = "en"
    ) -> list[SteamStoreSearchItem]:
        url = self.url.joinpath("storesearch").with_query(
            term=term, cc=country, l=language
        )
        response = await self._request(str(url))
        items = response.get("items", [])
        if not isinstance(items, list):
            return []
        return [
            cast(SteamStoreSearchItem, item)
            for item in items
            if isinstance(item, dict)
            and item.get("type") == "app"
            and isinstance(item.get("id"), int)
            and not isinstance(item["id"], bool)
            and isinstance(item.get("name"), str)
            and item["name"].strip()
        ]

    async def get_app_details(
        self,
        app_id: int,
        *,
        country: str = "US",
        language: str = "en",
        filters: str | None = None,
    ) -> SteamAppDetails | None:
        query = {"appids": str(app_id), "cc": country, "l": language}
        if filters:
            query["filters"] = filters
        response = await self._request(
            str(self.url.joinpath("appdetails").with_query(query))
        )
        envelope = response.get(str(app_id))
        if not isinstance(envelope, dict):
            envelope = next(
                (
                    candidate
                    for candidate in response.values()
                    if isinstance(candidate, dict)
                    and candidate.get("success") is True
                    and isinstance(candidate.get("data"), dict)
                    and candidate["data"].get("steam_appid") == app_id
                ),
                None,
            )
        if not isinstance(envelope, dict) or envelope.get("success") is not True:
            return None
        details = envelope.get("data")
        if not isinstance(details, dict):
            return None
        return cast(SteamAppDetails, details)

    async def get_library_capsule_url(self, app_id: int) -> str | None:
        url = STEAM_LIBRARY_CAPSULE_URL.format(app_id=app_id)
        try:
            response = await ctx_aiohttp_session.get().head(
                url,
                headers={"user-agent": f"RomM/{get_version()}"},
                timeout=ClientTimeout(total=15),
                allow_redirects=True,
            )
        except (aiohttp.ClientError, TimeoutError):
            return None
        return url if response.status == 200 else None
