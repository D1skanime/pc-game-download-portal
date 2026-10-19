"""Optional transport faults through the actual scan and DLC entries."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from tests.handler.media_download_helpers import (
    provider_response,
    resource_snapshot,
    seed_primary,
)
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_operations import command as command
from tests.handler.test_scan_write_fence import context

from config.config_manager import MetadataMediaType
from endpoints.sockets import scan as scan_module
from handler import scan_handler
from handler.database import db_rom_handler, db_storage_handler
from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler, fs_rom_handler, use_fs_rom_handler
from handler.metadata.pc_match_handler import PcMetadataCandidate
from models.rom import RomComponent, RomComponentKind, RomComponentOwnedMedia


def fs_input(name="Phase34-Synthetic.bin"):
    return dict(
        fs_name=name,
        files=[],
        nested=False,
        flat=True,
        crc_hash="",
        md5_hash="",
        sha1_hash="",
        ra_hash="",
    )


async def configure_scanner(rom, platform, command, monkeypatch, family):
    paths = await seed_primary(rom)
    special = f"{rom.fs_resources_path}/video/fixture.mp4"
    badge = f"{rom.fs_resources_path}/retroachievements/badges/1.png"
    for path in (special, badge):
        directory, filename = path.rsplit("/", 1)
        await fs_resource_handler.write_file(b"prior good bytes", directory, filename)
    db_rom_handler.update_rom(
        rom.id,
        dict(
            paths,
            fs_name="Phase34-Synthetic.bin",
            fs_path="PC",
            ss_metadata={"video_path": special},
            ra_metadata={"achievements": [{"id": 1, "badge_path": badge}]},
        ),
    )
    desired = (
        {"video_path": special, "video_url": "https://fixture.invalid/video"}
        if family == "special"
        else {}
    )
    response = dict(
        ss_id=101,
        name="Synthetic",
        ss_metadata=desired,
        url_cover="https://fixture.invalid/cover" if family == "primary" else "",
        url_screenshots=(
            ["https://fixture.invalid/screenshot"] if family == "parent" else []
        ),
        url_manual="",
    )
    monkeypatch.setattr(
        scan_handler.meta_ss_handler, "get_rom", AsyncMock(return_value=response)
    )
    monkeypatch.setattr(
        scan_handler.meta_ss_handler,
        "lookup_rom",
        AsyncMock(return_value=(response, False)),
    )
    monkeypatch.setattr(
        scan_module, "get_preferred_media_types", lambda: [MetadataMediaType.VIDEO]
    )
    monkeypatch.setattr(
        scan_handler.meta_ra_handler,
        "get_rom",
        AsyncMock(
            return_value={
                "ra_id": 201,
                "ra_metadata": {
                    "achievements": [
                        {
                            "id": 1,
                            "badge_url": "https://fixture.invalid/badge",
                            "badge_path": badge,
                        }
                    ]
                },
            }
        ),
    )
    with sync_session.begin() as session:
        row = session.get(type(platform), platform.id)
        row.ss_id, row.ra_id = 1, 1
    mapping = db_storage_handler.get_mapping(command["commands"][0]["mapping_id"])
    return mapping, db_rom_handler.get_rom(rom.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["connect", "timeout", "read"])
@pytest.mark.parametrize("family", ["primary", "special", "badge", "parent"])
async def test_actual_scanner_optional_transport_keeps_old_and_indexes_next(
    attempt, rom, platform, command, monkeypatch, family, failure
):
    mapping, current = await configure_scanner(
        rom, platform, command, monkeypatch, family
    )
    before = resource_snapshot(rom)
    stats = scan_module.ScanStats()
    sources = ["ss", "ra"] if family == "badge" else ["ss"]
    async with provider_response(
        failure=failure, mime="video/mp4" if family == "special" else "image/png"
    ):
        with use_fs_rom_handler(
            fs_rom_handler.for_mapping(mapping)
        ), bind_scan_write_context(context(attempt)):
            await scan_module._identify_rom(
                mapping.platform,
                fs_input(),
                current,
                scan_handler.ScanType.COMPLETE,
                [],
                sources,
                False,
                False,
                AsyncMock(),
                stats,
            )
            second = fs_input("soundtracks")
            second.update(nested=True, flat=False)
            await scan_module._identify_rom(
                mapping.platform,
                second,
                None,
                scan_handler.ScanType.COMPLETE,
                [],
                [],
                False,
                False,
                AsyncMock(),
                stats,
            )
    saved = db_rom_handler.get_rom(rom.id)
    assert saved.path_cover_l == current.path_cover_l
    assert saved.path_cover_s == current.path_cover_s
    assert saved.path_manual == current.path_manual
    assert saved.path_screenshots == current.path_screenshots
    assert saved.ss_metadata.get("video_path") == current.ss_metadata["video_path"]
    assert (
        saved.ra_metadata["achievements"][0]["badge_path"]
        == current.ra_metadata["achievements"][0]["badge_path"]
    )
    assert resource_snapshot(rom) == before
    assert saved.files and saved.files[0].file_size_bytes == len(
        b"phase34 synthetic fixture\n"
    )
    assert stats.scanned_roms == 2 and stats.new_roms == 1
    with sync_session.begin() as session:
        from models.rom import Rom

        other = session.scalar(select(Rom).where(Rom.fs_name == "soundtracks"))
        assert other is not None and len(other.files) == 3


def configure_dlc(rom, monkeypatch):
    with sync_session.begin() as session:
        component = RomComponent(
            rom_id=rom.id, relative_path="DLC/Synthetic", kind=RomComponentKind.DLC
        )
        session.add(component)
        session.flush()
        session.refresh(component)
    candidate = PcMetadataCandidate(
        "fixture",
        "igdb",
        "Synthetic DLC",
        {"igdb_id": 101},
        False,
        [{"kind": "cover", "url": "https://fixture.invalid/dlc.png"}],
        {"igdb_id": 101, "name": "Synthetic DLC"},
    )
    monkeypatch.setattr(
        scan_module.pc_metadata_match_handler,
        "fetch_unique_related_igdb_candidate",
        AsyncMock(return_value=candidate),
    )
    monkeypatch.setattr(
        scan_module.pc_metadata_match_handler,
        "fetch_validated_steam_dlc",
        AsyncMock(return_value=None),
    )
    return component


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["connect", "timeout", "read"])
async def test_actual_dlc_optional_transport_retains_prior(
    attempt, rom, monkeypatch, failure
):
    component = configure_dlc(rom, monkeypatch)
    with bind_scan_write_context(context(attempt)):
        async with provider_response():
            await scan_module._enrich_pc_dlc_from_igdb(rom, component)
        with sync_session.begin() as session:
            prior = session.scalars(
                select(RomComponentOwnedMedia).where(
                    RomComponentOwnedMedia.component_id == component.id
                )
            ).all()
        assert len(prior) == 1
        before = resource_snapshot(rom)
        current = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
        async with provider_response(failure=failure):
            await scan_module._enrich_pc_dlc_from_igdb(rom, current)
    with sync_session.begin() as session:
        retained = session.scalars(
            select(RomComponentOwnedMedia).where(
                RomComponentOwnedMedia.component_id == component.id
            )
        ).all()
    assert [(item.id, item.owned_path) for item in retained] == [
        (item.id, item.owned_path) for item in prior
    ]
    assert resource_snapshot(rom) == before
