"""Connected suppression contracts against disposable SQL."""

# Bounded local file checks instrument publication and cleanup.
# ruff: noqa: ASYNC240

from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_media_publication import command as command
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


@pytest.mark.parametrize("different", ["role", "url", "rom", "native-provider"])
def test_suppression_identity_boundaries(rom, platform, different):
    from tests.conftest import session

    from models.rom import Rom

    current, media_id = suppress(rom, "provider", RomOwnedMediaRole.SCREENSHOT)
    item = candidate("igdb", RomOwnedMediaRole.SCREENSHOT)
    target = current
    if different == "role":
        item = candidate("igdb", RomOwnedMediaRole.ARTWORK)
    elif different == "url":
        item = candidate(
            "igdb", RomOwnedMediaRole.SCREENSHOT, "https://fixture.invalid/other.png"
        )
    elif different == "rom":
        target = db_rom_handler.add_rom(
            Rom(
                platform_id=platform.id,
                name="other",
                fs_name="other.zip",
                fs_path=rom.fs_path,
            )
        )
    else:
        with session.begin() as db:
            from models.rom import RomOwnedMedia

            db.get(RomOwnedMedia, media_id).provider_media_id = "native-1"
        item = rom_media.discover_provider_media(
            "igdb", {"url_screenshots": [{"id": "native-1", "url": URL}]}
        )[0]
    applied = db_rom_handler.reconcile_provider_owned_media(
        target.id,
        target.updated_at,
        item.provider,
        item.provider_media_id,
        item.role,
        item.display_label,
        "image/png",
        f"{target.fs_resources_path}/owned-media/allowed.png",
    )
    assert applied is not None


@pytest.mark.asyncio
async def test_suppression_legacy_delete_during_publication(rom, attempt, monkeypatch):
    from handler.filesystem.scan_media_publication import require_scan_media_batch

    added = seed(rom, "provider", RomOwnedMediaRole.ARTWORK)
    current = db_rom_handler.update_rom(
        rom.id, {"url_cover": URL, "url_screenshots": []}
    )
    outputs = []

    async def cover(*args):
        unit = require_scan_media_batch()
        output = unit.prepare(f"{rom.fs_resources_path}/cover/big.png")
        output.file.write(b"attempt image")
        unit.finish(output)
        outputs.append(output.path)
        assert (
            db_rom_handler.delete_owned_media(
                rom.id, added.media.id, current.updated_at
            )
            is not None
        )
        return output.path, output.path

    monkeypatch.setattr(fs_resource_handler, "get_cover", cover)
    monkeypatch.setattr(fs_resource_handler, "get_manual", AsyncMock(return_value=""))
    with bind_scan_write_context(context(attempt)):
        with pytest.raises(ValueError, match="suppressed during publication"):
            await publish_rom_resources(
                fs_resource_handler, current, current, complete=True
            )
    assert_suppressed(rom.id, added.media.id)
    persisted = db_rom_handler.get_rom(rom.id)
    assert persisted.path_cover_l != outputs[0]
    assert not fs_resource_handler.validate_path(outputs[0]).exists()


@pytest.mark.asyncio
async def test_suppression_legacy_roles_are_independent(rom, attempt, monkeypatch):
    current, _ = suppress(rom, "provider", RomOwnedMediaRole.SCREENSHOT)
    current = db_rom_handler.update_rom(
        rom.id, {"url_cover": URL, "url_screenshots": [URL]}
    )
    cover = AsyncMock(return_value=("", ""))
    shots = AsyncMock(return_value=[])
    monkeypatch.setattr(fs_resource_handler, "get_cover", cover)
    monkeypatch.setattr(fs_resource_handler, "get_manual", AsyncMock(return_value=""))
    monkeypatch.setattr(fs_resource_handler, "get_rom_screenshots", shots)
    with bind_scan_write_context(context(attempt)):
        await publish_rom_resources(
            fs_resource_handler, current, current, complete=True
        )
    cover.assert_awaited_once()
    shots.assert_not_awaited()
