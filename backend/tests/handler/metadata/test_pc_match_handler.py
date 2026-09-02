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
    assert "url_cover" not in candidate.fields
    assert candidate.id


@pytest.mark.asyncio
async def test_collect_candidates_uses_a_spaced_search_title_for_compact_folder_names():
    igdb = Mock(is_enabled=Mock(return_value=True))
    igdb.get_matched_roms_by_name = AsyncMock(
        return_value=[
            {
                "igdb_id": 1453,
                "name": "Cyberpunk 2077",
                "summary": "An open-world action role-playing game.",
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
    rom = Mock(fs_name_no_ext="Cyberpunk2077", platform=Mock(igdb_id=6))

    results = await handler.collect_candidates(rom)

    assert results["igdb"].candidates[0].title == "Cyberpunk 2077"
    igdb.get_matched_roms_by_name.assert_awaited_once_with(rom, "Cyberpunk 2077", 6)


@pytest.mark.asyncio
async def test_collect_component_candidates_derives_a_dlc_title_from_setup_files():
    igdb = Mock(is_enabled=Mock(return_value=True))
    igdb.get_matched_roms_by_name = AsyncMock(return_value=[])
    disabled = Mock(is_enabled=Mock(return_value=False))
    handler = PcMetadataMatchHandler(
        providers={
            "igdb": igdb,
            "moby": disabled,
            "sgdb": disabled,
            "launchbox": disabled,
        }
    )
    rom = Mock(fs_name_no_ext="Cyberpunk2077", platform=Mock(igdb_id=6))
    rom.name = "Cyberpunk 2077"
    component = Mock(
        relative_path="dlc",
        manifest_members=[
            Mock(
                relative_path=(
                    "dlc/setup_cyberpunk_2077_phantom_liberty_2.31a_(64bit)_(85116)-1.bin"
                )
            ),
            Mock(
                relative_path=(
                    "dlc/setup_cyberpunk_2077_phantom_liberty_2.31a_(64bit)_(85116).exe"
                )
            ),
        ],
    )

    await handler.collect_component_candidates(rom, component)

    igdb.get_matched_roms_by_name.assert_awaited_once_with(
        rom, "Cyberpunk 2077 Phantom Liberty", 6
    )


@pytest.mark.asyncio
async def test_collect_component_candidates_offers_a_matching_parent_expansion():
    igdb = Mock(is_enabled=Mock(return_value=True))
    igdb.get_matched_roms_by_name = AsyncMock(return_value=[])
    disabled = Mock(is_enabled=Mock(return_value=False))
    handler = PcMetadataMatchHandler(
        providers={
            "igdb": igdb,
            "moby": disabled,
            "sgdb": disabled,
            "launchbox": disabled,
        }
    )
    rom = Mock(fs_name_no_ext="Cyberpunk2077", platform=Mock(igdb_id=6))
    rom.name = "Cyberpunk 2077"
    rom.igdb_metadata = {
        "expansions": [
            {
                "id": 215769,
                "name": "Cyberpunk 2077: Phantom Liberty",
                "cover_url": "https://images.igdb.com/phantom-liberty.jpg",
            }
        ]
    }
    component = Mock(
        relative_path="dlc",
        manifest_members=[
            Mock(
                relative_path=(
                    "dlc/setup_cyberpunk_2077_phantom_liberty_2.31a_(64bit)_(85116).exe"
                )
            )
        ],
    )

    results = await handler.collect_component_candidates(rom, component)

    candidate = results["igdb"].candidates[0]
    assert candidate.title == "Cyberpunk 2077: Phantom Liberty"
    assert candidate.provider_ids == {"igdb_id": 215769}
    igdb.get_matched_roms_by_name.assert_not_awaited()


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


def test_launchbox_candidate_only_exposes_eligible_media_descriptors():
    candidate = PcMetadataMatchHandler._candidate(
        "launchbox",
        {
            "launchbox_id": 88,
            "name": "Local PC Game",
            "summary": "Local description",
            "launchbox_metadata": {
                "images": [
                    {"type": "Box - Front", "url": "file:///cover.png"},
                    {"type": "Fanart - Background", "url": "file:///fanart.png"},
                    {"type": "Clear Logo", "url": "file:///logo.png"},
                    {"type": "Screenshot - Gameplay", "url": "file:///shot.png"},
                    {"type": "Manual", "url": "file:///manual.pdf"},
                ],
                "video_path": "file:///video.mp4",
            },
        },
    )

    assert candidate.description_available is True
    assert candidate.media == [
        {"kind": "cover", "url": "file:///cover.png"},
        {"kind": "fan_art", "url": "file:///fanart.png"},
        {"kind": "logo", "url": "file:///logo.png"},
        {"kind": "screenshot", "url": "file:///shot.png"},
        {"kind": "video", "url": "file:///video.mp4"},
    ]
