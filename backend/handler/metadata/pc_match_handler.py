"""Review-only metadata candidate collection for PC library entries."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from handler.metadata import (
    meta_igdb_handler,
    meta_launchbox_handler,
    meta_moby_handler,
    meta_sgdb_handler,
)
from models.rom import Rom, RomComponent

COMPACT_TITLE_BOUNDARY = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])"
)


class PcMetadataProvider(Protocol):
    def is_enabled(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class PcMetadataCandidate:
    id: str
    provider: str
    title: str
    provider_ids: dict[str, int | str]
    description_available: bool
    media: list[dict[str, str]]
    fields: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PcMetadataProviderResult:
    provider: str
    available: bool
    candidates: list[PcMetadataCandidate]
    reason: str | None = None


class PcMetadataMatchHandler:
    """Adapt configured providers into reviewable, non-persisted candidates."""

    def __init__(self, providers: dict[str, PcMetadataProvider] | None = None) -> None:
        self.providers = providers or {
            "igdb": meta_igdb_handler,
            "moby": meta_moby_handler,
            "sgdb": meta_sgdb_handler,
            "launchbox": meta_launchbox_handler,
        }

    async def collect_candidates(self, rom: Rom) -> dict[str, PcMetadataProviderResult]:
        title = rom.fs_name_no_ext or rom.fs_name
        if " " not in title:
            title = COMPACT_TITLE_BOUNDARY.sub(" ", title)
        return await self._collect_for_title(rom, title)

    async def collect_component_candidates(
        self, rom: Rom, component: RomComponent
    ) -> dict[str, PcMetadataProviderResult]:
        base_title = rom.name or rom.fs_name_no_ext or rom.fs_name
        component_title = component.relative_path.rsplit("/", 1)[-1]
        component_title = component_title.replace("-", " ").replace("_", " ")
        title = f"{base_title} {component_title}".strip()
        return await self._collect_for_title(rom, title)

    async def _collect_for_title(
        self, rom: Rom, title: str
    ) -> dict[str, PcMetadataProviderResult]:
        results: dict[str, PcMetadataProviderResult] = {}
        for provider_name, provider in self.providers.items():
            if not provider.is_enabled():
                results[provider_name] = PcMetadataProviderResult(
                    provider_name, False, [], "disabled"
                )
                continue

            try:
                provider_results = await self._lookup(
                    provider_name, provider, rom, title
                )
            except Exception:
                results[provider_name] = PcMetadataProviderResult(
                    provider_name, False, [], "unavailable"
                )
                continue

            results[provider_name] = PcMetadataProviderResult(
                provider_name,
                True,
                [self._candidate(provider_name, item) for item in provider_results],
            )
        return results

    async def _lookup(
        self, provider_name: str, provider: PcMetadataProvider, rom: Rom, title: str
    ) -> list[dict[str, Any]]:
        if provider_name == "igdb":
            return await provider.get_matched_roms_by_name(  # type: ignore[attr-defined]
                rom, title, rom.platform.igdb_id
            )
        if provider_name == "moby":
            return await provider.get_matched_roms_by_name(  # type: ignore[attr-defined]
                title, rom.platform.moby_id
            )
        if provider_name == "sgdb":
            return await provider.get_details(title)  # type: ignore[attr-defined]
        if provider_name == "launchbox":
            return await provider.get_matched_roms_by_name(  # type: ignore[attr-defined]
                title, rom.platform_slug
            )
        return []

    @staticmethod
    def _candidate(provider: str, item: dict[str, Any]) -> PcMetadataCandidate:
        provider_ids = {
            key: value
            for key, value in item.items()
            if key.endswith("_id") and value is not None
        }
        title = str(item.get("name") or "")
        media = PcMetadataMatchHandler._media(provider, item)
        fingerprint = json.dumps(
            {"provider": provider, "ids": provider_ids, "title": title, "media": media},
            sort_keys=True,
            separators=(",", ":"),
        )
        candidate_id = hashlib.sha256(fingerprint.encode()).hexdigest()
        fields = {
            key: value
            for key, value in item.items()
            if key
            in {
                "igdb_id",
                "moby_id",
                "sgdb_id",
                "launchbox_id",
                "name",
                "summary",
                "igdb_metadata",
                "moby_metadata",
                "launchbox_metadata",
            }
        }
        return PcMetadataCandidate(
            id=candidate_id,
            provider=provider,
            title=title,
            provider_ids=provider_ids,
            description_available=bool(item.get("summary")),
            media=media,
            fields=fields,
        )

    @staticmethod
    def _media(provider: str, item: dict[str, Any]) -> list[dict[str, str]]:
        media: list[dict[str, str]] = []
        if cover := item.get("url_cover"):
            media.append({"kind": "cover", "url": str(cover)})
        for screenshot in item.get("url_screenshots", []):
            media.append({"kind": "screenshot", "url": str(screenshot)})
        if provider == "sgdb":
            for resource in item.get("resources", []):
                if url := resource.get("url"):
                    media.append({"kind": "cover", "url": str(url)})
        if provider == "launchbox":
            metadata = item.get("launchbox_metadata", {})
            for image in metadata.get("images", []):
                url = image.get("url")
                image_type = image.get("type", "").lower()
                if not url:
                    continue
                if "logo" in image_type:
                    kind = "logo"
                elif "screenshot" in image_type:
                    kind = "screenshot"
                elif "fanart" in image_type:
                    kind = "fan_art"
                elif "box" in image_type or "cover" in image_type:
                    kind = "cover"
                else:
                    continue
                media.append({"kind": kind, "url": str(url)})
            if video := metadata.get("video_url") or metadata.get("video_path"):
                media.append({"kind": "video", "url": str(video)})
        return media


pc_metadata_match_handler = PcMetadataMatchHandler()
