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
    STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG,
    STEAM_API_TEXT_LANGUAGES,
)

from .base_handler import BaseRom, MetadataHandler
from .base_handler import UniversalPlatformSlug as UPS

STEAM_PLATFORMS = frozenset({UPS.WIN, UPS.LINUX, UPS.MAC})
COMPACT_TITLE_BOUNDARY = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])"
)


class SteamTextVariant(TypedDict):
    source_language: str
    name: NotRequired[str]
    summary: NotRequired[str]


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
    genres: NotRequired[list[str]]
    categories: NotRequired[list[str]]
    dlc_ids: NotRequired[list[int]]
    text_variants: NotRequired[dict[str, SteamTextVariant]]


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

    @staticmethod
    def _requested_language(metadata_locale: str | None) -> str:
        if isinstance(metadata_locale, str) and metadata_locale.strip():
            base_tag = metadata_locale.replace("_", "-").split("-", 1)[0].lower()
            for language, tag in STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG.items():
                if tag == base_tag:
                    return language
        return STEAM_API_LANGUAGE

    @staticmethod
    def _country_for_language(language: str) -> str:
        return (
            STEAM_API_COUNTRY
            if language == STEAM_API_LANGUAGE
            else STEAM_API_FALLBACK_COUNTRY
        )

    async def get_rom(
        self,
        fs_name: str,
        platform_slug: str,
        metadata_locale: str | None = None,
    ) -> SteamRom:
        if not self.is_enabled() or platform_slug not in STEAM_PLATFORMS:
            return SteamRom(steam_id=None)
        from handler.filesystem import fs_rom_handler

        name = fs_rom_handler.get_file_name_with_no_tags(fs_name)
        if " " not in name:
            name = COMPACT_TITLE_BOUNDARY.sub(" ", name)
        term = self.normalize_search_term(name, remove_punctuation=False)
        if not term:
            return SteamRom(steam_id=None)
        requested_language = self._requested_language(metadata_locale)
        apps = await self.steam_service.search_apps(
            term,
            country=self._country_for_language(requested_language),
            language=requested_language,
        )
        remaining_apps = [item for item in apps if item.get("type") == "app"]
        while remaining_apps:
            match, _ = self.find_best_match(
                term,
                [item["name"] for item in remaining_apps],
                self.min_similarity_score,
            )
            if not match:
                break
            app_index = next(
                index
                for index, item in enumerate(remaining_apps)
                if item["name"] == match
            )
            app = remaining_apps.pop(app_index)
            rom = await self.get_rom_by_id(
                app["id"], platform_slug, metadata_locale=metadata_locale
            )
            if rom["steam_id"] is not None:
                return rom
        return SteamRom(steam_id=None)

    async def get_rom_by_id(
        self,
        steam_id: int,
        platform_slug: str | None = None,
        metadata_locale: str | None = None,
    ) -> SteamRom:
        if not self.is_enabled():
            return SteamRom(steam_id=None)
        localized_details: dict[str, SteamAppDetails] = {}
        requested_language = self._requested_language(metadata_locale)
        text_languages = tuple(
            dict.fromkeys((requested_language, *STEAM_API_TEXT_LANGUAGES))
        )
        for language in text_languages:
            details = await self.steam_service.get_app_details(
                steam_id,
                country=self._country_for_language(language),
                language=language,
            )
            if validated_details := self._valid_app_details(details, steam_id):
                localized_details[language] = validated_details
        selected = (
            (requested_language, localized_details[requested_language])
            if requested_language in localized_details
            else next(iter(localized_details.items()), None)
        )
        if selected is None:
            return SteamRom(steam_id=None)
        actual_language, preferred = selected
        fallback: SteamAppDetails | None = None
        if self._needs_fallback(preferred):
            fallback = localized_details.get(STEAM_API_FALLBACK_LANGUAGE)
        return await self._build_rom(
            preferred,
            fallback,
            self._text_variants(localized_details),
            actual_language,
        )

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
    def _valid_app_details(
        details: SteamAppDetails | None, steam_id: int
    ) -> SteamAppDetails | None:
        if (
            not details
            or details.get("type") not in {"game", "dlc"}
            or not isinstance(details.get("steam_appid"), int)
            or isinstance(details["steam_appid"], bool)
            or details["steam_appid"] != steam_id
        ):
            return None
        return details

    @staticmethod
    def _text_variants(
        localized_details: dict[str, SteamAppDetails],
    ) -> dict[str, SteamTextVariant]:
        variants: dict[str, SteamTextVariant] = {}
        for language, details in localized_details.items():
            base_tag = STEAM_API_TEXT_LANGUAGE_TO_UI_BASE_TAG[language]
            variant: SteamTextVariant = {"source_language": language}
            if isinstance(details.get("name"), str) and details["name"].strip():
                variant["name"] = details["name"].strip()
            if (
                isinstance(details.get("short_description"), str)
                and details["short_description"].strip()
            ):
                variant["summary"] = details["short_description"].strip()
            if len(variant) > 1:
                variants[base_tag] = variant
        return variants

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

    @staticmethod
    def _store_labels(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [
            item["description"].strip()
            for item in value
            if isinstance(item, dict)
            and isinstance(item.get("description"), str)
            and item["description"].strip()
        ]

    @staticmethod
    def _positive_ids(value: object) -> list[int]:
        if not isinstance(value, list):
            return []
        return [
            item
            for item in value
            if isinstance(item, int) and not isinstance(item, bool) and item > 0
        ]

    async def _build_rom(
        self,
        preferred: SteamAppDetails,
        fallback: SteamAppDetails | None,
        text_variants: dict[str, SteamTextVariant],
        preferred_language: str,
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
            "language": preferred_language,
            "fallback_language": STEAM_API_FALLBACK_LANGUAGE if fallback else "",
        }
        if text_variants:
            metadata["text_variants"] = text_variants
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
        for field in ("genres", "categories"):
            if value := self._store_labels(
                preferred.get(field) or fallback_details.get(field)
            ):
                metadata[field] = value
        if dlc_ids := self._positive_ids(preferred.get("dlc")):
            metadata["dlc_ids"] = dlc_ids
        if developers := self._string_list(
            preferred.get("developers") or fallback_details.get("developers")
        ):
            metadata["developers"] = developers
        if publishers := self._string_list(
            preferred.get("publishers") or fallback_details.get("publishers")
        ):
            metadata["publishers"] = publishers
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
