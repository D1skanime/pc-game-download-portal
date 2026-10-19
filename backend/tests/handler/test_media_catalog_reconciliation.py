"""Component invalidation must survive COMPLETE provider lookup and catalog merge."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from tests.handler.media_download_helpers import (
    owned_resource_files as owned_resource_files,
)
from tests.handler.media_download_helpers import (
    png_bytes,
    provider_response,
)
from tests.handler.test_media_download_transport import configure_scanner, fs_input
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_media_publication import batch, prepare, read
from tests.handler.test_scan_operations import command as command
from tests.handler.test_scan_write_fence import context

from endpoints.sockets import scan as scan_module
from handler import scan_handler
from handler.database import db_rom_handler, db_storage_handler
from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler, fs_rom_handler, use_fs_rom_handler
from handler.metadata.base_handler import UniversalPlatformSlug as UPS
from models.owned_media_cleanup import OwnedMediaCleanupIntent
from models.rom import (
    RomComponent,
    RomComponentKind,
    RomComponentLocalMedia,
    RomComponentLocalMediaRole,
    RomComponentManifestMember,
)
from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task


@pytest.mark.parametrize("cleanup", [False, True])
@pytest.mark.parametrize("source_change", ["changed", "removed"])
def test_complete_keeps_reconciled_local_cover_detached(
    attempt, rom, platform, command, monkeypatch, cleanup, source_change
):
    mapping, original = asyncio.run(
        configure_scanner(rom, platform, command, monkeypatch, "special")
    )
    with sync_session.begin() as session:
        session.get(type(platform), platform.id).slug = UPS.WIN
    db_rom_handler.update_rom(rom.id, {"fs_name": "soundtracks", "fs_path": "PC"})
    asyncio.run(fs_resource_handler.remove_file(original.path_cover_l))
    asyncio.run(fs_resource_handler.remove_file(original.path_cover_s))
    member_path = "cover.png" if source_change == "changed" else "removed-cover.png"
    old_hash = "a" * 64
    with bind_scan_write_context(context(attempt)):
        with batch(rom) as unit:
            components = unit.publish_and_associate(
                lambda session: db_rom_handler.sync_rom_components(
                    rom.id,
                    [
                        RomComponent(
                            relative_path="base",
                            kind=RomComponentKind.BASE,
                            manifest_members=[
                                RomComponentManifestMember(
                                    relative_path=member_path,
                                    size_bytes=99,
                                    sha256=old_hash,
                                )
                            ],
                        )
                    ],
                    session=session,
                )
            )
        component = components[0]
        member = component.manifest_members[0]
        with batch(rom) as unit:
            large = prepare(unit, rom, png_bytes())
            small = unit.prepare(f"{rom.fs_resources_path}/cover/small.png")
            small.file.write(png_bytes())
            unit.finish(small)
            unit.publish_and_associate(
                lambda session: db_rom_handler.apply_pc_local_media(
                    rom.id,
                    db_rom_handler.get_rom(rom.id, session=session).updated_at,
                    component.id,
                    member.id,
                    RomComponentLocalMediaRole.COVER,
                    large.path,
                    "image/png",
                    old_hash,
                    small.path,
                    session=session,
                )
            )
    current = db_rom_handler.get_rom(rom.id)
    assert current.path_cover_l == large.path and read(large.path) == png_bytes()
    paused, release = Event(), Event()

    async def lookup(*args, **kwargs):
        paused.set()
        assert release.wait(10)
        return (
            {
                "ss_id": 101,
                "name": "Synthetic",
                "ss_metadata": {
                    "video_path": f"{rom.fs_resources_path}/video/new.mp4",
                    "video_url": "https://fixture.invalid/video",
                },
                "url_cover": "",
                "url_screenshots": [],
                "url_manual": "",
            },
            False,
        )

    monkeypatch.setattr(scan_handler.meta_ss_handler, "lookup_rom", lookup)
    mapping = db_storage_handler.get_mapping(command["commands"][0]["mapping_id"])

    async def scan():
        async with provider_response(data=b"complete new video", mime="video/mp4"):
            with use_fs_rom_handler(
                fs_rom_handler.for_mapping(mapping)
            ), bind_scan_write_context(context(attempt)):
                source = fs_input("soundtracks")
                source.update(nested=True, flat=False)
                await scan_module._identify_rom(
                    mapping.platform,
                    source,
                    current,
                    scan_handler.ScanType.COMPLETE,
                    [],
                    ["ss"],
                    False,
                    False,
                    AsyncMock(),
                    scan_module.ScanStats(),
                )

    with ThreadPoolExecutor(max_workers=1) as pool:
        worker = pool.submit(lambda: asyncio.run(scan()))
        try:
            assert paused.wait(12), "provider lookup was not reached"
            reconciled = db_rom_handler.get_rom(rom.id)
            assert not reconciled.path_cover_l and not reconciled.path_cover_s
            with sync_session.begin() as session:
                assert session.scalar(select(RomComponentLocalMedia.id)) is None
                retired = set(
                    session.scalars(select(OwnedMediaCleanupIntent.owned_path))
                )
                assert {large.path, small.path} <= retired
            if cleanup:
                asyncio.run(owned_media_cleanup_task.run())
                assert not fs_resource_handler.validate_path(large.path).exists()
                assert not fs_resource_handler.validate_path(small.path).exists()
            else:
                assert read(large.path) == png_bytes()
        finally:
            release.set()
        worker.result(timeout=20)
    saved = db_rom_handler.get_rom(rom.id)
    assert (
        not saved.path_cover_l and not saved.path_cover_s
    ), "retired cover was resurrected"
    assert saved.path_manual == original.path_manual
    assert saved.path_screenshots == original.path_screenshots
    assert read(saved.ss_metadata["video_path"]) == b"complete new video"
    assert saved.ss_metadata["video_path"] != original.ss_metadata["video_path"]


def test_final_merge_preserves_current_references_with_stale_session(attempt, rom):
    from handler.filesystem.scan_media_publication import merge_scan_rom
    from models.rom import Rom

    with bind_scan_write_context(context(attempt)):
        with batch(rom) as unit:
            old = prepare(unit, rom, png_bytes())
            unit.publish_and_associate(
                lambda session: db_rom_handler.update_rom(
                    rom.id, {"path_cover_l": old.path}, session=session
                )
            )
        with batch(rom) as unit:
            new = prepare(unit, rom, png_bytes())
            unit.publish_and_associate(lambda session: None)
    scanned = Rom(
        id=rom.id,
        ss_metadata={
            "video_url": "https://fixture.invalid/new",
            "video_path": f"{rom.fs_resources_path}/video/new.mp4",
        },
    )
    with sync_session.begin() as session:
        stale = session.get(Rom, rom.id)
        assert stale.path_cover_l == old.path
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(
                db_rom_handler.update_rom, rom.id, {"path_cover_l": new.path}
            ).result(timeout=10)
        with bind_scan_write_context(context(attempt)):
            merge_scan_rom(scanned, session=session)
    saved = db_rom_handler.get_rom(rom.id)
    assert saved.path_cover_l == new.path
    assert scanned._pending_scan_media["ss_metadata"]["video_path"].endswith("new.mp4")
