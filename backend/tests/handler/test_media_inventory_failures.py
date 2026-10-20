"""Whole provider inventories retain old catalog state across late failure and stop."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError
from tests.handler.media_download_helpers import (
    Body,
)
from tests.handler.media_download_helpers import (
    owned_resource_files as owned_resource_files,
)
from tests.handler.media_download_helpers import (
    png_bytes,
    resource_snapshot,
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
from tests.handler.test_scan_operations import repository
from tests.handler.test_scan_write_fence import context

from endpoints.sockets import scan as scan_module
from handler import scan_handler
from handler.database import db_rom_handler
from handler.database.scan_write_fence import ScanWriteRejected, bind_scan_write_context
from handler.filesystem import fs_resource_handler, fs_rom_handler, use_fs_rom_handler
from handler.metadata.steam_owned_media import reconcile_steam_patch_media
from utils.context import ctx_httpx_client


@pytest.mark.parametrize("family", ["badges", "steam"])
@pytest.mark.parametrize("fault", ["stream", "cancel", "association"])
def test_inventory_late_failure_retains_all_prior_references(
    attempt, rom, platform, admin_user, command, monkeypatch, family, fault
):
    if family == "badges":
        mapping, current = asyncio.run(
            configure_scanner(rom, platform, command, monkeypatch, "badge")
        )
        prior = current.ra_metadata["achievements"]
        desired = badge_inventory(rom, prior[0], 65)
        monkeypatch.setattr(
            scan_handler.meta_ra_handler,
            "get_rom",
            AsyncMock(
                return_value={
                    "ra_id": 201,
                    "ra_metadata": {"achievements": desired},
                }
            ),
        )
        original = db_rom_handler.update_rom

        def associate(*args, **kwargs):
            result = original(*args, **kwargs)
            if (
                fault == "association"
                and len(args[1].get("ra_metadata", {}).get("achievements", [])) == 65
            ):
                raise SQLAlchemyError("deterministic final association fault")
            return result

        monkeypatch.setattr(db_rom_handler, "update_rom", associate)
    else:
        old = seed_steam(rom, 129, png_bytes())
        prior = active_steam(rom)
        current = db_rom_handler.get_rom(rom.id)
        original = db_rom_handler.reconcile_steam_owned_media_inventory

        def associate(*args, **kwargs):
            result = original(*args, **kwargs)
            if fault == "association":
                raise SQLAlchemyError("deterministic final association fault")
            return result

        monkeypatch.setattr(
            db_rom_handler, "reconcile_steam_owned_media_inventory", associate
        )
    before = resource_snapshot(rom)
    paused, release = Event(), Event()
    requests = 0

    def respond(request):
        nonlocal requests
        requests += 1
        if requests == 129:
            paused.set()
            assert release.wait(15)
        return httpx.Response(
            503 if fault == "stream" and requests == 129 else 200,
            headers={"content-type": "image/png"},
            stream=Body([png_bytes()]),
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            token = ctx_httpx_client.set(client)
            try:
                with bind_scan_write_context(context(attempt)):
                    if family == "steam":
                        return await reconcile_steam_patch_media(
                            current, steam_patch(129), force=True
                        )
                    with use_fs_rom_handler(fs_rom_handler.for_mapping(mapping)):
                        return await scan_module._identify_rom(
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
            finally:
                ctx_httpx_client.reset(token)

    stopping = None
    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(lambda: asyncio.run(run()))
        try:
            assert paused.wait(20), "inventory did not reach output 129"
            if family == "steam":
                assert active_steam(rom) == prior
            else:
                assert (
                    db_rom_handler.get_rom(rom.id).ra_metadata["achievements"] == prior
                )
            assert resource_snapshot(rom) != before
            if fault == "cancel":
                start = time.monotonic()
                stopping = repository().request_cancel(
                    attempt.id, admin_user.id, attempt.version, "inventory-cancel"
                )
                assert time.monotonic() - start < 3, "streaming held SQL locks"
        finally:
            release.set()
        if fault == "cancel":
            with pytest.raises(ScanWriteRejected):
                work.result(timeout=30)
        elif fault == "association":
            with pytest.raises(SQLAlchemyError, match="final association"):
                work.result(timeout=30)
        else:
            result = work.result(timeout=30)
            if family == "steam":
                assert result is False
    if family == "steam":
        assert active_steam(rom) == prior
        assert all(read(path) == png_bytes() for path in old)
    else:
        assert db_rom_handler.get_rom(rom.id).ra_metadata["achievements"] == prior
    if stopping:
        repository().confirm_stopped(stopping.id, stopping.version, attempt.attempt_id)
    else:
        stop(attempt, admin_user)
    directory = fs_resource_handler.validate_path(
        f".scan-media-staging/{attempt.id}/{attempt.attempt_id}"
    )
    asyncio.run(drain_until(lambda: not directory.exists()))
    assert (
        resource_snapshot(rom) == before
    ), "inventory leaked new final or private bytes"
