from typing import NotRequired, TypedDict

from adapters.services.steam import SteamService
from adapters.services.steam_types import SteamAppDetails, SteamPlatforms
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


class SteamMetadata(TypedDict):
    developers: NotRequired[list[str]]
    publishers: NotRequired[list[str]]
    platforms: NotRequired[SteamPlatforms]
    language: NotRequired[str]
    fallback_language: NotRequired[str]


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

        term = self.normalize_search_term(
            fs_rom_handler.get_file_name_with_no_tags(fs_name),
            remove_punctuation=False,
        )
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

    async def _build_rom(
        self, preferred: SteamAppDetails, fallback: SteamAppDetails | None
    ) -> SteamRom:
        app_id = preferred["steam_appid"]
        name = preferred.get("name") or (fallback or {}).get("name", "")
        summary = preferred.get("short_description") or (fallback or {}).get(
            "short_description", ""
        )
        metadata: SteamMetadata = {
            "language": STEAM_API_LANGUAGE,
            "fallback_language": STEAM_API_FALLBACK_LANGUAGE if fallback else "",
        }
        for field in ("developers", "publishers", "platforms"):
            if value := preferred.get(field) or (fallback or {}).get(field):
                metadata[field] = value  # type: ignore[literal-required]
        result = SteamRom(
            steam_id=app_id,
            name=name,
            steam_metadata=metadata,
            url_cover=await self.steam_service.get_library_capsule_url(app_id)
            or preferred.get("header_image", ""),
        )
        if summary:
            result["summary"] = summary
        if screenshots := preferred.get("screenshots") or (fallback or {}).get(
            "screenshots"
        ):
            result["url_screenshots"] = [
                str(item["path_full"]) for item in screenshots if item.get("path_full")
            ]
        return result
