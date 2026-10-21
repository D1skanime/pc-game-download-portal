from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from handler.metadata.pc_steam_enrichment import (
    SteamPcEnrichmentRequest,
    resolve_steam_pc_enrichment,
)


def _request(**overrides):
    values: dict[str, Any] = {
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
async def test_requested_metadata_locale_reaches_steam_name_lookup():
    get_by_name = AsyncMock(return_value={"steam_id": 1091500, "name": "The Witcher 3"})
    with patch(
        "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom", get_by_name
    ):
        await resolve_steam_pc_enrichment(_request(metadata_locale="fr-FR"))

    get_by_name.assert_awaited_once_with(
        "The Witcher 3.exe", "win", metadata_locale="fr-FR"
    )


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


@pytest.mark.asyncio
async def test_text_only_request_preserves_protected_fields_and_merges_slots():
    from copy import deepcopy

    from endpoints.responses.rom import SteamMetadataSchema

    current = {
        "steam_id": 1091500,
        "name": "Manual title",
        "summary": "Legacy scalar",
        "manual_metadata": {"descriptions": {"en": "Manual English", "de": "Manuell"}},
        "steam_metadata": {
            "app_id": 1091500,
            "source": "storefront",
            "developers": ["Saved studio"],
            "fields": ["name"],
            "text_variants": {
                "de": {"source_language": "german", "summary": "Gespeichert"},
            },
        },
    }
    before = deepcopy(current)
    fetched = {
        "steam_id": 1091500,
        "name": "Unwanted title",
        "summary": "Unwanted scalar",
        "url_cover": "http://unwanted",
        "metadata": {"genres": ["unwanted"]},
        "steam_metadata": {
            "developers": ["Unwanted studio"],
            "text_variants": {
                "fr": {
                    "source_language": "french",
                    "summary": "Texte francais",
                    "requested_language": "french",
                    "language_evidence": "provider_slot",
                },
                "en": {
                    "source_language": "english",
                    "summary": "English text",
                    "requested_language": "english",
                    "language_evidence": "provider_slot",
                },
            },
        },
    }
    with patch(
        "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
        AsyncMock(return_value=fetched),
    ) as fetch:
        result = await resolve_steam_pc_enrichment(
            _request(
                current=current,
                metadata_locale="fr-FR",
                descriptions_only=True,
                text_languages=("de", "en"),
            )
        )
    assert set(result) == {"steam_metadata"}
    assert result["steam_metadata"]["developers"] == ["Saved studio"]
    assert set(result["steam_metadata"]["text_variants"]) == {"de", "fr", "en"}
    assert current == before
    assert fetch.await_args is not None
    assert fetch.await_args.kwargs["descriptions_only"] is True
    assert fetch.await_args.kwargs["metadata_locale"] == "fr-FR"
    serialized = SteamMetadataSchema.model_validate(
        result["steam_metadata"]
    ).model_dump()
    assert serialized["text_variants"]["fr"]["requested_language"] == "french"
    assert serialized["text_variants"]["en"]["language_evidence"] == "provider_slot"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "values",
    [
        {"current": {}},
        {"metadata_sources": ["igdb"]},
        {
            "current": {
                "steam_id": 1091500,
                "manual_metadata": {
                    "descriptions": {"fr": "Manuel", "en": "Manual", "de": "Manuell"}
                },
            }
        },
    ],
)
async def test_text_only_ineligible_or_complete_never_searches_or_fetches(values):
    with (
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
            AsyncMock(),
        ) as fetch,
        patch(
            "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom",
            AsyncMock(),
        ) as search,
    ):
        result = await resolve_steam_pc_enrichment(
            _request(
                descriptions_only=True,
                metadata_locale="fr",
                text_languages=("de", "en"),
                **values,
            )
        )
    assert result == {}
    fetch.assert_not_awaited()
    search.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fetched",
    [
        {
            "steam_id": 42,
            "steam_metadata": {
                "text_variants": {
                    "fr": {"source_language": "french", "summary": "Wrong app"}
                }
            },
        },
        {
            "steam_id": 1091500,
            "steam_metadata": {
                "app_id": 42,
                "text_variants": {
                    "fr": {"source_language": "french", "summary": "Wrong provenance"}
                },
            },
        },
        {"steam_id": 1091500, "steam_metadata": {"text_variants": {}}},
    ],
)
async def test_text_only_empty_or_invalid_result_never_becomes_completeness(fetched):
    with patch(
        "handler.metadata.pc_steam_enrichment.meta_steam_handler.get_rom_by_id",
        AsyncMock(return_value=fetched),
    ):
        result = await resolve_steam_pc_enrichment(
            _request(
                current={"steam_id": 1091500},
                metadata_locale="fr",
                descriptions_only=True,
            )
        )
    assert result == {}
