"""Accepted provider inventories must publish completely in one catalog transaction."""

import json
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
from tests.handler.media_inventory_helpers import (
    active_steam,
    badge_inventory,
    seed_steam,
    steam_patch,
)
from tests.handler.media_recovery_helpers import drain_until
from tests.handler.test_media_download_transport import configure_scanner, fs_input
from tests.handler.test_media_recovery_validation import stop
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_media_publication import read
from tests.handler.test_scan_operations import command as command
from tests.handler.test_scan_write_fence import context

from endpoints.sockets import scan as scan_module
from handler import scan_handler
from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler, fs_rom_handler, use_fs_rom_handler
from handler.filesystem.scan_media_publication import (
    MAX_MANIFEST_BYTES,
    MAX_OUTPUTS,
    parse_manifest,
)
from handler.metadata.steam_owned_media import reconcile_steam_patch_media
from models.owned_media_cleanup import OwnedMediaCleanupIntent


def assert_bounded_receipts(attempt):
    directory = fs_resource_handler.validate_path(
        f".scan-media-staging/{attempt.id}/{attempt.attempt_id}"
    )
    count = 0
    for batch in directory.iterdir():
        for receipt in batch.glob("receipt-*.json"):
            content = receipt.read_bytes()
            assert len(content) <= MAX_MANIFEST_BYTES
            document = parse_manifest(
                content, str(batch.relative_to(directory.parents[2]))
            )
            assert len(document["outputs"]) <= MAX_OUTPUTS
        count += 1
    return count


@pytest.mark.asyncio
async def test_scanner_publishes_65_complete_two_badge_achievements(
    attempt, rom, platform, command, monkeypatch
):
    mapping, current = await configure_scanner(
        rom, platform, command, monkeypatch, "badge"
    )
    achievements = badge_inventory(rom, current.ra_metadata["achievements"][0], 65)
    monkeypatch.setattr(
        scan_handler.meta_ra_handler,
        "get_rom",
        AsyncMock(
            return_value={
                "ra_id": 201,
                "ra_metadata": {"achievements": achievements},
            }
        ),
    )
    async with provider_response():
        with use_fs_rom_handler(
            fs_rom_handler.for_mapping(mapping)
        ), bind_scan_write_context(context(attempt)):
            await scan_module._identify_rom(
                mapping.platform,
                fs_input(),
                current,
                scan_handler.ScanType.COMPLETE,
                [],
                ["ra"],
                False,
                False,
                AsyncMock(),
                scan_module.ScanStats(),
            )
    saved = db_rom_handler.get_rom(rom.id)
    actual = saved.ra_metadata["achievements"]
    assert len(actual) == 65
    assert [item["ra_id"] for item in actual] == list(range(10, 75))
    paths = [item[key] for item in actual for key in ("badge_path", "badge_path_lock")]
    assert len(set(paths)) == 130
    assert all(".scan-" in path and read(path) == png_bytes() for path in paths)
    assert assert_bounded_receipts(attempt) >= 2


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [129, 1000])
async def test_complete_steam_inventory_replaces_large_prior_atomically(
    attempt, rom, admin_user, count, monkeypatch
):
    from traceback import extract_tb

    from handler.filesystem.scan_media_inventory import ScanMediaInventory

    failures = []
    original_exit = ScanMediaInventory.__exit__

    def record_failure(unit, kind, error, trace):
        if error is not None:
            failures.append(
                (
                    type(error).__name__,
                    getattr(error.__cause__, "errno", None),
                    str(error),
                    extract_tb(trace)[-2:],
                )
            )
        return original_exit(unit, kind, error, trace)

    monkeypatch.setattr(ScanMediaInventory, "__exit__", record_failure)
    old = seed_steam(rom, count, png_bytes())
    if count == 1000:
        assert len(json.dumps(old).encode()) > MAX_MANIFEST_BYTES
    current = db_rom_handler.get_rom(rom.id)
    async with provider_response():
        with bind_scan_write_context(context(attempt)):
            result = await reconcile_steam_patch_media(
                current, steam_patch(count), force=True
            )
    assert result is True, ("accepted complete Steam inventory was rejected", failures)
    inventory = active_steam(rom)
    assert len(inventory) == count
    assert set(inventory.values()).isdisjoint(old)
    assert all(read(path) == png_bytes() for path in inventory.values())
    assert all(read(path) == png_bytes() for path in old)
    with sync_session.begin() as session:
        retired = set(session.scalars(select(OwnedMediaCleanupIntent.owned_path)))
    assert set(old) <= retired
    assert assert_bounded_receipts(attempt) >= 2
    stop(attempt, admin_user)
    await drain_until(
        lambda: all(
            not fs_resource_handler.validate_path(path).exists() for path in old
        )
    )
    assert all(read(path) == png_bytes() for path in inventory.values())
