from unittest.mock import AsyncMock, Mock

import pytest

from handler.metadata.pc_match_handler import PcMetadataMatchHandler


@pytest.mark.asyncio
async def test_collect_candidates_attributes_results_to_their_provider():
    igdb = Mock(is_enabled=Mock(return_value=True))
    igdb.get_matched_roms_by_name = AsyncMock(
        return_value=[
            {
                "igdb_id": 101,
                "name": "Example PC Game",
                "summary": "An example description",
                "url_cover": "https://images.igdb.com/cover.jpg",
            }
        ]
    )
    disabled = Mock(is_enabled=Mock(return_value=False))
    handler = PcMetadataMatchHandler(
        providers={
            "igdb": igdb,
            "moby": disabled,
            "sgdb": disabled,
            "launchbox": disabled,
        }
    )
    rom = Mock(fs_name_no_ext="Example PC Game", platform=Mock(igdb_id=6, moby_id=None))

    results = await handler.collect_candidates(rom)

    assert results["igdb"].available is True
    candidate = results["igdb"].candidates[0]
    assert candidate.provider == "igdb"
    assert candidate.provider_ids == {"igdb_id": 101}
    assert candidate.description_available is True
    assert candidate.media == [
        {"kind": "cover", "url": "https://images.igdb.com/cover.jpg"}
    ]
    assert candidate.id


@pytest.mark.asyncio
async def test_collect_candidates_returns_typed_unavailable_provider_result():
    failing = Mock(is_enabled=Mock(return_value=True))
    failing.get_matched_roms_by_name = AsyncMock(side_effect=RuntimeError("offline"))
    disabled = Mock(is_enabled=Mock(return_value=False))
    handler = PcMetadataMatchHandler(
        providers={
            "igdb": failing,
            "moby": disabled,
            "sgdb": disabled,
            "launchbox": disabled,
        }
    )
    rom = Mock(fs_name_no_ext="Example PC Game", platform=Mock(igdb_id=6, moby_id=None))

    results = await handler.collect_candidates(rom)

    assert results["igdb"].available is False
    assert results["igdb"].reason == "unavailable"
    assert results["igdb"].candidates == []
