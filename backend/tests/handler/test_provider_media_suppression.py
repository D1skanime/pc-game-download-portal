"""Connected suppression contracts against disposable SQL."""

from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from tests.handler.test_scan_media_publication import attempt, command
from tests.handler.test_scan_write_fence import context

from handler.database import db_rom_handler
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import publish_rom_resources
from handler.metadata import rom_media, steam_owned_media
from models.rom import RomOwnedMediaRole, RomOwnedMediaState
from utils.context import ctx_httpx_client

URL = "https://fixture.invalid/image.png?a=1&b=2"


def candidate(provider, role, url=URL):
    key = "url_screenshots" if role == RomOwnedMediaRole.SCREENSHOT else "url_artworks"
    return rom_media.discover_provider_media(provider, {key: [url]})[0]


def seed(rom, provider, role):
    item = candidate(provider, role)
    result = db_rom_handler.reconcile_provider_owned_media(
        rom.id,
        rom.updated_at,
        provider,
        item.provider_media_id,
        role,
        item.display_label,
        "image/png",
        f"{rom.fs_resources_path}/owned-media/seed.png",
    )
    assert result is not None
    return result


def suppress(rom, provider, role):
    added = seed(rom, provider, role)
    deleted = db_rom_handler.delete_owned_media(
        rom.id, added.media.id, added.rom.updated_at
    )
    assert deleted is not None
    return db_rom_handler.get_rom(rom.id), added.media.id


def assert_suppressed(rom_id, media_id):
    current = db_rom_handler.get_rom(rom_id)
    item = next(item for item in current.owned_media if item.id == media_id)
    assert item.operator_suppressed
    assert item.state == RomOwnedMediaState.TOMBSTONED
    assert item.owned_path is None
    assert item.placements == []
    assert len(current.owned_media) == 1


@pytest.mark.parametrize(
    "role", [RomOwnedMediaRole.SCREENSHOT, RomOwnedMediaRole.ARTWORK]
)
@pytest.mark.parametrize("mode", ["normal", "complete", "media-only", "explicit"])
@pytest.mark.asyncio
async def test_suppression_update_modes_repeat(rom, attempt, role, mode):
    rom, media_id = suppress(rom, "provider", role)
    rom = db_rom_handler.update_rom(
        rom.id,
        {
            "url_cover": URL if role == RomOwnedMediaRole.ARTWORK else "",
            "url_screenshots": [URL] if role == RomOwnedMediaRole.SCREENSHOT else [],
        },
    )
    image = Path("/phase34/owned/library/PC/soundtracks/cover.png").read_bytes()
    requests = []

    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200, content=image)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        token = ctx_httpx_client.set(client)
        try:
            for _ in range(2):
                current = db_rom_handler.get_rom(rom.id)
                if mode == "explicit":
                    await rom_media.refresh_provider_owned_media(
                        current, current.updated_at, "provider"
                    )
                else:
                    with bind_scan_write_context(context(attempt)):
                        if mode == "complete":
                            assert await steam_owned_media.reconcile_steam_patch_media(
                                current,
                                {
                                    "media": {
                                        "cover": (
                                            [URL]
                                            if role == RomOwnedMediaRole.ARTWORK
                                            else []
                                        ),
                                        "screenshots": (
                                            [URL]
                                            if role == RomOwnedMediaRole.SCREENSHOT
                                            else []
                                        ),
                                    }
                                },
                                force=True,
                            )
                        else:
                            await rom_media.refresh_provider_owned_media(
                                current, current.updated_at, "igdb"
                            )
                assert_suppressed(rom.id, media_id)
        finally:
            ctx_httpx_client.reset(token)
    assert requests == [], "suppression must prevent network and storage work"


@pytest.mark.parametrize(
    "role", [RomOwnedMediaRole.SCREENSHOT, RomOwnedMediaRole.ARTWORK]
)
@pytest.mark.parametrize("provider", ["steam", "igdb", "provider"])
def test_suppression_locked_alias_guard(rom, role, provider):
    rom, media_id = suppress(rom, "provider", role)
    item = candidate(
        provider, role, "https://FIXTURE.invalid/image.png?b=2&a=1#fragment"
    )
    for _ in range(2):
        assert (
            db_rom_handler.reconcile_provider_owned_media(
                rom.id,
                rom.updated_at,
                provider,
                item.provider_media_id,
                role,
                item.display_label,
                "image/png",
                f"{rom.fs_resources_path}/owned-media/new.png",
            )
            is None
        )
    assert_suppressed(rom.id, media_id)


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.asyncio
async def test_suppression_steam_skips_before_force(rom, force, monkeypatch):
    rom, media_id = suppress(rom, "steam", RomOwnedMediaRole.SCREENSHOT)
    download = AsyncMock(
        return_value=(f"{rom.fs_resources_path}/owned-media/new.png", "image/png")
    )
    monkeypatch.setattr(steam_owned_media, "_download_candidate", download)
    assert await steam_owned_media.reconcile_steam_patch_media(
        rom, {"media": {"cover": [], "screenshots": [URL]}}, force=force
    )
    assert_suppressed(rom.id, media_id)
    download.assert_not_awaited()


@pytest.mark.asyncio
async def test_suppression_generic_delete_during_download(rom, monkeypatch):
    added = seed(rom, "igdb", RomOwnedMediaRole.SCREENSHOT)
    current = db_rom_handler.update_rom(
        rom.id, {"url_screenshots": [URL], "url_cover": ""}
    )
    path = f"{rom.fs_resources_path}/owned-media/attempt.png"

    async def download(*args):
        assert (
            db_rom_handler.delete_owned_media(
                rom.id, added.media.id, current.updated_at
            )
            is not None
        )
        return path, "image/png"

    remove = AsyncMock()
    monkeypatch.setattr(rom_media, "_download_provider_image", download)
    monkeypatch.setattr(fs_resource_handler, "remove_file", remove)
    await rom_media.refresh_provider_owned_media(current, current.updated_at, "igdb")
    assert_suppressed(rom.id, added.media.id)
    remove.assert_awaited_once_with(path)


@pytest.mark.parametrize("complete", [False, True])
@pytest.mark.asyncio
async def test_suppression_legacy_publication_filters_without_shifting(
    rom, attempt, complete, monkeypatch
):
    rom, media_id = suppress(rom, "provider", RomOwnedMediaRole.SCREENSHOT)
    urls = [URL, "https://fixture.invalid/keep.png"]
    rom = db_rom_handler.update_rom(rom.id, {"url_screenshots": urls, "url_cover": ""})
    received = []

    async def screenshots(current, force, values):
        received.extend(values)
        return [f"{rom.fs_resources_path}/screenshots/keep.png"] if values else []

    monkeypatch.setattr(
        fs_resource_handler, "get_cover", AsyncMock(return_value=("", ""))
    )
    monkeypatch.setattr(fs_resource_handler, "get_manual", AsyncMock(return_value=""))
    monkeypatch.setattr(fs_resource_handler, "get_rom_screenshots", screenshots)
    with bind_scan_write_context(context(attempt)):
        await publish_rom_resources(fs_resource_handler, rom, rom, complete=complete)
    current = db_rom_handler.get_rom(rom.id)
    assert current.url_screenshots == urls
    assert received == [urls[1]]
    assert current.path_screenshots == [f"{rom.fs_resources_path}/screenshots/keep.png"]
    assert_suppressed(rom.id, media_id)
