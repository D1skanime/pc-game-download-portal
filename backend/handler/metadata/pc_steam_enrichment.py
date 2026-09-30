"""Pure Steam PC metadata resolution shared by scan and selection paths."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from handler.metadata import meta_steam_handler
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

    try:
        if steam_id is not None:
            result = await meta_steam_handler.get_rom_by_id(
                steam_id, request.platform_slug
            )
        elif request.platform_slug in STEAM_PLATFORMS:
            result = await meta_steam_handler.get_rom(
                request.fs_name, request.platform_slug
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
    return normalize_steam(result, request.current)


def _steam_selected(metadata_sources: Collection[str]) -> bool:
    return any(
        getattr(source, "value", source) == "steam" for source in metadata_sources
    )


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) and value > 0 else None
