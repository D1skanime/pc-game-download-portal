"""A failed optional refresh must keep the exact prior public paths and bytes."""

from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from PIL import Image
from tests.handler.media_download_helpers import (
    owned_resource_files as owned_resource_files,
)
from tests.handler.media_download_helpers import (
    png_bytes,
    provider_response,
    resource_snapshot,
    seed_primary,
)
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_operations import command as command

from handler.database import db_rom_handler
from handler.filesystem import fs_resource_handler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "family,failure",
    [
        (family, failure)
        for family in ("cover", "manual", "screenshot")
        for failure in ("status", "mime", "read", "timeout", "content")
        if (family, failure) != ("manual", "content")
    ],
)
async def test_nonscan_replacement_preserves_old(rom, family, failure):
    paths = await seed_primary(rom)
    current = db_rom_handler.update_rom(rom.id, paths)
    before = resource_snapshot(rom)
    async with provider_response(
        failure=failure,
        data=b"invalid image" if failure == "content" else None,
        mime="application/pdf" if family == "manual" else "image/png",
    ):
        if family == "cover":
            result = await fs_resource_handler.get_cover(
                current, True, "https://fixture.invalid/cover"
            )
            assert result == (paths["path_cover_s"], paths["path_cover_l"])
        elif family == "manual":
            result = await fs_resource_handler.get_manual(
                current, True, "https://fixture.invalid/manual"
            )
            assert result == paths["path_manual"]
        else:
            result = await fs_resource_handler.get_rom_screenshots(
                current, True, ["https://fixture.invalid/screenshot"]
            )
            assert result == paths["path_screenshots"]
    assert resource_snapshot(rom) == before


@pytest.mark.asyncio
async def test_nonscan_success_converts_before_replacement(rom, monkeypatch):
    from handler.filesystem import scan_media_publication

    monkeypatch.setattr("config.ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP", True)
    paths = await seed_primary(rom)
    current = db_rom_handler.update_rom(rom.id, paths)
    async with provider_response():
        small, large = await scan_media_publication.store_resource(
            fs_resource_handler,
            "https://fixture.invalid/cover",
            paths["path_cover_s"],
            ("image/",),
            cover_size="small",
        ), await scan_media_publication.store_resource(
            fs_resource_handler,
            "https://fixture.invalid/cover",
            paths["path_cover_l"],
            ("image/",),
            cover_size="big",
        )
    for path, dimensions in ((small, (8, 12)), (large, (20, 30))):
        assert path.endswith(".png")
        with Image.open(
            BytesIO(fs_resource_handler.validate_path(path).read_bytes())
        ) as image:
            assert image.format == "PNG"
            assert image.size == dimensions
        with Image.open(
            fs_resource_handler.validate_path(path).with_suffix(".webp")
        ) as image:
            assert image.format == "WEBP"
            assert image.size == dimensions
    assert current.path_cover_l == paths["path_cover_l"]


@pytest.mark.asyncio
async def test_pc_selection_keeps_authoritative_cover_paths(
    rom, monkeypatch, admin_user
):
    from starlette.requests import Request
    from tests.endpoints.roms.test_pc_metadata import _candidate, _candidate_results

    from endpoints.roms import pc_metadata as endpoint
    from endpoints.roms.pc_metadata import PcMetadataSelectionRequest

    paths = await seed_primary(rom)
    current = db_rom_handler.update_rom(rom.id, paths)
    monkeypatch.setattr(
        endpoint.pc_metadata_match_handler,
        "collect_candidates",
        AsyncMock(return_value=_candidate_results()),
    )
    request = Request({"type": "http", "user": admin_user, "session": {}})
    selection = PcMetadataSelectionRequest(
        candidate_id=_candidate().id,
        query="Synthetic",
        expected_version=current.updated_at,
        selected_media_ids=[
            endpoint._candidate_media_id(_candidate(), _candidate().media[0])
        ],
    )
    before = resource_snapshot(rom)
    async with provider_response(failure="status"):
        await endpoint.select_pc_metadata_candidate.__wrapped__(
            request, rom.id, selection
        )
    saved = db_rom_handler.get_rom(rom.id)
    assert saved.path_cover_s == paths["path_cover_s"]
    assert saved.path_cover_l == paths["path_cover_l"]
    assert resource_snapshot(rom) == before


@pytest.mark.asyncio
async def test_replacement_collision_preserves_another_writers_private_file(rom):
    import os

    from handler.filesystem.scan_media_publication import store_resource

    paths = await seed_primary(rom)
    path = paths["path_cover_l"]
    final = fs_resource_handler.validate_path(path)
    private = final.with_name(f".{final.name}.{os.getpid()}.tmp")
    private.write_bytes(b"another writer owns this private file")
    async with provider_response():
        result = await store_resource(
            fs_resource_handler,
            "https://fixture.invalid/cover",
            path,
            ("image/",),
            cover_size="big",
        )
    assert result is None
    assert final.read_bytes() == b"prior good bytes"
    assert private.read_bytes() == b"another writer owns this private file"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["status", "mime", "read"])
async def test_nonscan_screenshot_failure_returns_committed_generation(
    attempt, rom, failure
):
    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import bind_scan_write_context
    from handler.filesystem.scan_media_publication import ScanMediaBatch

    with bind_scan_write_context(context(attempt)):
        with ScanMediaBatch(
            rom.id, rom.platform_id, fs_resource_handler.storage
        ) as unit:
            async with provider_response():
                path = await fs_resource_handler._store_screenshot(
                    rom, "https://fixture.invalid/screenshot", 0
                )
            unit.publish_and_associate(
                lambda session: db_rom_handler.update_rom(
                    rom.id, {"path_screenshots": [path]}, session=session
                )
            )
    current = db_rom_handler.get_rom(rom.id)
    before = resource_snapshot(rom)
    async with provider_response(failure=failure):
        paths = await fs_resource_handler.get_rom_screenshots(
            current, True, ["https://fixture.invalid/screenshot"]
        )
    assert paths == [path]
    assert resource_snapshot(rom) == before
