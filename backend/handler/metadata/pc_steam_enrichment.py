"""Pure Steam PC metadata resolution shared by scan and selection paths."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from config import STEAM_API_TEXT_LANGUAGES
from handler.metadata import meta_steam_handler
from handler.metadata.description_completeness import assess_description_completeness
from handler.metadata.steam_descriptions import (
    accepted_text_variants,
    valid_steam_provenance,
)
from handler.metadata.steam_handler import STEAM_PLATFORMS
from handler.metadata.steam_merge import normalize_steam


@dataclass(frozen=True, slots=True)
class SteamPcEnrichmentRequest:
    """Inputs needed to resolve one guarded Steam PC metadata patch."""

    scan_context: str
    current: Mapping[str, Any]
    platform_slug: str
    fs_name: str
    metadata_sources: Collection[str]
    explicit_steam_id: int | None = None
    metadata_locale: str | None = None
    descriptions_only: bool = False
    text_languages: tuple[str, ...] | None = None


async def resolve_steam_pc_enrichment(
    request: SteamPcEnrichmentRequest,
) -> dict[str, Any]:
    """Return a normalized Steam patch without ORM or session mutation."""
    if not _steam_selected(request.metadata_sources):
        return {}

    explicit_id = request.explicit_steam_id
    if explicit_id is not None and _positive_int(explicit_id) is None:
        return {}
    steam_id = _positive_int(explicit_id)
    if steam_id is None:
        steam_id = _positive_int(request.current.get("steam_id"))

    missing_languages: tuple[str, ...] = ()
    if request.descriptions_only:
        if steam_id is None or (
            request.current.get("steam_id") is not None
            and request.current.get("steam_id") != steam_id
        ):
            return {}
        configured = (
            STEAM_API_TEXT_LANGUAGES
            if request.text_languages is None
            else request.text_languages
        )
        completeness = assess_description_completeness(
            request.current,
            configured,
            request.metadata_locale,
        )
        if completeness.complete:
            return {}
        missing_languages = completeness.missing_locales

    try:
        if request.descriptions_only and steam_id is not None:
            result = await meta_steam_handler.get_rom_by_id(
                steam_id,
                request.platform_slug,
                metadata_locale=request.metadata_locale,
                descriptions_only=True,
                text_languages=missing_languages,
            )
        elif steam_id is not None:
            if request.metadata_locale is None:
                result = await meta_steam_handler.get_rom_by_id(
                    steam_id, request.platform_slug
                )
            else:
                result = await meta_steam_handler.get_rom_by_id(
                    steam_id,
                    request.platform_slug,
                    metadata_locale=request.metadata_locale,
                )
        elif request.platform_slug in STEAM_PLATFORMS:
            if request.metadata_locale is None:
                result = await meta_steam_handler.get_rom(
                    request.fs_name, request.platform_slug
                )
            else:
                result = await meta_steam_handler.get_rom(
                    request.fs_name,
                    request.platform_slug,
                    metadata_locale=request.metadata_locale,
                )
        else:
            return {}
    except Exception:
        return {}

    if not isinstance(result, Mapping):
        return {}
    resolved_id = _positive_int(result.get("steam_id"))
    if resolved_id is None or (steam_id is not None and resolved_id != steam_id):
        return {}
    if request.descriptions_only:
        incoming = result.get("steam_metadata")
        if not isinstance(incoming, Mapping) or not valid_steam_provenance(
            incoming, resolved_id
        ):
            return {}
        variants = accepted_text_variants(
            incoming.get("text_variants"), app_id=resolved_id
        )
        if not variants:
            return {}
        normalized = normalize_steam(
            {"steam_id": resolved_id, "steam_metadata": {"text_variants": variants}},
            request.current,
        )["steam_metadata"]
        existing = request.current.get("steam_metadata")
        return {
            "steam_metadata": {
                **(dict(existing) if isinstance(existing, Mapping) else {}),
                "app_id": resolved_id,
                "source": "storefront",
                "text_variants": normalized["text_variants"],
            }
        }
    return normalize_steam(result, request.current)


def _steam_selected(metadata_sources: Collection[str]) -> bool:
    return any(
        getattr(source, "value", source) == "steam" for source in metadata_sources
    )


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) and value > 0 else None
