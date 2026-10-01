from unittest.mock import AsyncMock, patch

import pytest

from handler.metadata.pc_steam_enrichment import (
    SteamPcEnrichmentRequest,
    resolve_steam_pc_enrichment,
)


def _request(**overrides):
    values = {
        "scan_context": "targeted-selection",
        "current": {
            "name": "",
            "summary": "",
            "manual_metadata": {},
            "steam_metadata": {},
            "metadata": {},
        },
        "platform_slug": "win",
        "fs_name": "The Witcher 3.exe",
        "metadata_sources": ["steam"],
        "explicit_steam_id": None,
    }
    values.update(overrides)
    return SteamPcEnrichmentRequest(**values)


@pytest.mark.asyncio
async def test_d01_persisted_id_refreshes_after_rename_without_name_search():
    get_by_id = AsyncMock(return_value={"steam_id": 1091500, "name": "The Witcher 3"})
    get_by_name = AsyncMock()
    with (
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
            get_by_id,
        ),
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom",
            get_by_name,
        ),
    ):
        patch_fields = await resolve_steam_pc_enrichment(
            _request(current={"steam_id": 1091500, "manual_metadata": {}})
        )

    assert patch_fields["steam_id"] == 1091500
    get_by_id.assert_awaited_once_with(1091500, "win")
    get_by_name.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("platform_slug", ["win", "linux", "mac"])
async def test_d02_eligible_platforms_use_one_name_lookup(platform_slug):
    get_by_id = AsyncMock()
    get_by_name = AsyncMock(return_value={"steam_id": 1091500, "name": "The Witcher 3"})
    with (
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
            get_by_id,
        ),
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom",
            get_by_name,
        ),
    ):
        patch_fields = await resolve_steam_pc_enrichment(
            _request(platform_slug=platform_slug)
        )

    assert patch_fields["steam_id"] == 1091500
    get_by_id.assert_not_awaited()
    get_by_name.assert_awaited_once_with("The Witcher 3.exe", platform_slug)


@pytest.mark.asyncio
@pytest.mark.parametrize("platform_slug", ["dos", "win3x", "win9x", "snes"])
async def test_d05_excluded_platforms_never_name_search(platform_slug):
    get_by_id = AsyncMock()
    get_by_name = AsyncMock()
    with (
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
            get_by_id,
        ),
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom",
            get_by_name,
        ),
    ):
        patch_fields = await resolve_steam_pc_enrichment(
            _request(platform_slug=platform_slug)
        )

    assert patch_fields == {}
    get_by_id.assert_not_awaited()
    get_by_name.assert_not_awaited()


@pytest.mark.asyncio
async def test_d01_explicit_id_rejects_mismatched_result_without_name_search():
    get_by_id = AsyncMock(return_value={"steam_id": 1091501, "name": "Other game"})
    get_by_name = AsyncMock()
    with (
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
            get_by_id,
        ),
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom",
            get_by_name,
        ),
    ):
        patch_fields = await resolve_steam_pc_enrichment(
            _request(explicit_steam_id=1091500)
        )

    assert patch_fields == {}
    get_by_id.assert_awaited_once_with(1091500, "win")
    get_by_name.assert_not_awaited()


@pytest.mark.asyncio
async def test_d06_ambiguous_or_malformed_name_results_return_empty_without_retry():
    get_by_name = AsyncMock(side_effect=[{"steam_id": None}, {}])
    with patch(
        "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom", get_by_name
    ):
        patch_fields = await resolve_steam_pc_enrichment(_request())

    assert patch_fields == {}
    get_by_name.assert_awaited_once_with("The Witcher 3.exe", "win")


@pytest.mark.asyncio
async def test_d10_rate_limited_provider_returns_empty_without_second_lookup():
    get_by_id = AsyncMock(side_effect=TimeoutError("rate limited"))
    get_by_name = AsyncMock()
    with (
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
            get_by_id,
        ),
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom",
            get_by_name,
        ),
    ):
        patch_fields = await resolve_steam_pc_enrichment(
            _request(current={"steam_id": 1091500, "manual_metadata": {}})
        )

    assert patch_fields == {}
    get_by_id.assert_awaited_once_with(1091500, "win")
    get_by_name.assert_not_awaited()


@pytest.mark.asyncio
async def test_d06_selected_source_gate_makes_no_provider_request():
    get_by_id = AsyncMock()
    get_by_name = AsyncMock()
    with (
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
            get_by_id,
        ),
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom",
            get_by_name,
        ),
    ):
        patch_fields = await resolve_steam_pc_enrichment(
            _request(metadata_sources=["igdb"])
        )

    assert patch_fields == {}
    get_by_id.assert_not_awaited()
    get_by_name.assert_not_awaited()
