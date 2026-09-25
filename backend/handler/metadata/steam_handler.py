import re
from typing import NotRequired, TypedDict

from adapters.services.steam import SteamService
from adapters.services.steam_types import SteamAppDetails, SteamFullGame, SteamPlatforms
from config import (
    STEAM_API_COUNTRY,
    STEAM_API_ENABLED,
    STEAM_API_FALLBACK_COUNTRY,
    STEAM_API_FALLBACK_LANGUAGE,
    STEAM_API_LANGUAGE,
)

from .base_handler import BaseRom, MetadataHandler
from .base_handler import UniversalPlatformSlug as UPS

STEAM_PLATFORMS = frozenset({UPS.WIN, UPS.LINUX, UPS.MAC})
COMPACT_TITLE_BOUNDARY = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])"
)


class SteamMetadata(TypedDict):
    developers: NotRequired[list[str]]
    publishers: NotRequired[list[str]]
    platforms: NotRequired[SteamPlatforms]
    release_date: NotRequired[dict[str, str | bool]]
    language: NotRequired[str]
    fallback_language: NotRequired[str]
    fallback_fields: NotRequired[list[str]]
    type: NotRequired[str]
    fullgame: NotRequired[SteamFullGame]


class SteamRom(BaseRom):
    steam_id: int | None
    steam_metadata: NotRequired[SteamMetadata]


class SteamHandler(MetadataHandler):
    """Steam Storefront metadata for supported PC platforms."""

    def __init__(self) -> None:
        self.steam_service = SteamService()
        self.min_similarity_score = 0.85

    @classmethod
    def is_enabled(cls) -> bool:
        return STEAM_API_ENABLED

    async def heartbeat(self) -> bool:
        if not self.is_enabled():
            return False
        return bool(
            await self.steam_service.get_app_details(
                220,
                country=STEAM_API_COUNTRY,
                language=STEAM_API_LANGUAGE,
                filters="basic",
            )
        )

    async def get_rom(self, fs_name: str, platform_slug: str) -> SteamRom:
        if not self.is_enabled() or platform_slug not in STEAM_PLATFORMS:
            return SteamRom(steam_id=None)
        from handler.filesystem import fs_rom_handler

        name = fs_rom_handler.get_file_name_with_no_tags(fs_name)
        if " " not in name:
            name = COMPACT_TITLE_BOUNDARY.sub(" ", name)
        term = self.normalize_search_term(name, remove_punctuation=False)
        if not term:
            return SteamRom(steam_id=None)
        apps = await self.steam_service.search_apps(
            term, country=STEAM_API_COUNTRY, language=STEAM_API_LANGUAGE
        )
        apps = [item for item in apps if item.get("type") == "app"]
        match, _ = self.find_best_match(
            term, [item["name"] for item in apps], self.min_similarity_score
        )
        if not match:
            return SteamRom(steam_id=None)
        return await self.get_rom_by_id(
            next(item["id"] for item in apps if item["name"] == match), platform_slug
        )

    async def get_rom_by_id(
        self, steam_id: int, platform_slug: str | None = None
    ) -> SteamRom:
        if not self.is_enabled():
            return SteamRom(steam_id=None)
        preferred = await self.steam_service.get_app_details(
            steam_id, country=STEAM_API_COUNTRY, language=STEAM_API_LANGUAGE
        )
        if (
            not preferred
            or preferred.get("type") not in {"game", "dlc"}
            or not isinstance(preferred.get("steam_appid"), int)
            or isinstance(preferred["steam_appid"], bool)
        ):
            return SteamRom(steam_id=None)
        fallback = None
        if self._needs_fallback(preferred):
            fallback = await self.steam_service.get_app_details(
                steam_id,
                country=STEAM_API_FALLBACK_COUNTRY,
                language=STEAM_API_FALLBACK_LANGUAGE,
            )
        return await self._build_rom(preferred, fallback)

    async def get_matched_roms_by_name(
        self, search_term: str, platform_slug: str
    ) -> list[SteamRom]:
        if not self.is_enabled() or platform_slug not in STEAM_PLATFORMS:
            return []
        apps = await self.steam_service.search_apps(
            search_term, country=STEAM_API_COUNTRY, language=STEAM_API_LANGUAGE
        )
        return [
            SteamRom(steam_id=item["id"], name=item["name"])
            for item in apps
            if item.get("type") == "app"
        ][:15]

    @staticmethod
    def _needs_fallback(details: SteamAppDetails) -> bool:
        return any(
            not details.get(field)
            for field in (
                "name",
                "short_description",
                "header_image",
                "developers",
                "publishers",
                "screenshots",
                "release_date",
            )
        )

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item.strip()]

    @staticmethod
    def _release_date(value: object) -> dict[str, str | bool]:
        if not isinstance(value, dict) or not isinstance(value.get("date"), str):
            return {}
        result: dict[str, str | bool] = {"date": value["date"]}
        if isinstance(value.get("coming_soon"), bool):
            result["coming_soon"] = value["coming_soon"]
        return result

    async def _build_rom(
        self, preferred: SteamAppDetails, fallback: SteamAppDetails | None
    ) -> SteamRom:
        app_id = preferred["steam_appid"]
        fallback_details: SteamAppDetails = fallback or {
            "type": "",
            "name": "",
            "steam_appid": 0,
        }
        name = preferred.get("name") or fallback_details.get("name", "")
        summary = preferred.get("short_description") or fallback_details.get(
            "short_description", ""
        )
        metadata: SteamMetadata = {
            "language": STEAM_API_LANGUAGE,
            "fallback_language": STEAM_API_FALLBACK_LANGUAGE if fallback else "",
        }
        fallback_fields: list[str] = []
        if fallback and not preferred.get("name") and fallback_details.get("name"):
            fallback_fields.append("name")
        if (
            fallback
            and not preferred.get("short_description")
            and fallback_details.get("short_description")
        ):
            fallback_fields.append("summary")
        if fallback_fields:
            metadata["fallback_fields"] = fallback_fields
        if isinstance(preferred.get("type"), str):
            metadata["type"] = preferred["type"]
        if isinstance(preferred.get("fullgame"), dict):
            metadata["fullgame"] = preferred["fullgame"]
        for field in ("developers", "publishers"):
            if value := self._string_list(
                preferred.get(field) or fallback_details.get(field)
            ):
                metadata[field] = value
        if release_date := self._release_date(
            preferred.get("release_date") or fallback_details.get("release_date")
        ):
            metadata["release_date"] = release_date
        if isinstance(preferred.get("platforms"), dict):
            metadata["platforms"] = preferred["platforms"]
        elif isinstance(fallback_details.get("platforms"), dict):
            metadata["platforms"] = fallback_details["platforms"]
        header_image = preferred.get("header_image") or fallback_details.get(
            "header_image", ""
        )
        result = SteamRom(
            steam_id=app_id,
            name=name,
            steam_metadata=metadata,
            url_cover=await self.steam_service.get_library_capsule_url(app_id)
            or header_image,
        )
        if summary:
            result["summary"] = summary
        if screenshots := preferred.get("screenshots") or fallback_details.get(
            "screenshots"
        ):
            result["url_screenshots"] = [
                str(item["path_full"])
                for item in screenshots
                if isinstance(item, dict) and isinstance(item.get("path_full"), str)
            ]
        return result
