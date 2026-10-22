"""Interactive text repair through canonical provider and persistence owners."""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from fastapi import HTTPException

from handler.database import db_rom_handler
from handler.database.scan_inventory_state import _digest
from handler.metadata import meta_ss_handler
from handler.metadata.description_completeness import assess_description_completeness
from handler.metadata.pc_steam_enrichment import (
    SteamPcEnrichmentRequest,
    resolve_steam_pc_enrichment,
)


def text_snapshot(metadata, provider):
    return {
        provider + "_id": getattr(metadata, provider + "_id", None),
        provider
        + "_metadata": deepcopy(getattr(metadata, provider + "_metadata", None)),
        "manual_metadata": deepcopy(getattr(metadata, "manual_metadata", None)),
    }


async def refresh_manual_descriptions(
    rom, provider, locale, expected_version, component=None
):
    target = component or rom
    metadata = component.component_metadata if component else rom
    current = text_snapshot(metadata, provider)
    provider_id = current[provider + "_id"]
    if not provider_id:
        return target
    if target.updated_at != expected_version:
        raise HTTPException(
            status_code=409, detail="The metadata changed before confirmation"
        )
    digest = _digest(current)
    data: Mapping[str, Any] = {}
    if not assess_description_completeness(
        current, (), locale, provider=provider
    ).complete:
        if provider == "ss":
            data = await meta_ss_handler.get_rom_by_id(
                rom,
                provider_id,
                metadata_locale=locale,
                descriptions_only=True,
            )
        else:
            data = await resolve_steam_pc_enrichment(
                SteamPcEnrichmentRequest(
                    scan_context="targeted-selection",
                    current=current,
                    platform_slug=rom.platform_slug,
                    fs_name=rom.fs_name,
                    metadata_sources=["steam"],
                    explicit_steam_id=provider_id,
                    metadata_locale=locale,
                    descriptions_only=True,
                    text_languages=(),
                )
            )
    updated = db_rom_handler.apply_interactive_description_patch(
        rom_id=rom.id,
        component_id=component.id if component else None,
        incarnation=rom.incarnation_token,
        provider=provider,
        provider_id=provider_id,
        expected_updated_at=expected_version,
        expected_text_digest=digest,
        data=data,
    )
    if updated is None:
        raise HTTPException(
            status_code=409, detail="The metadata changed before confirmation"
        )
    return updated
