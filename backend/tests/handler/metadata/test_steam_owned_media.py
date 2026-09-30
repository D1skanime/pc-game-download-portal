from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from handler.database.roms_handler import ReconciledSteamOwnedMediaInventory
from handler.metadata.rom_media import ProviderMediaCandidate
from handler.metadata.steam_owned_media import (
    _IMAGE_LIMIT,
    _download_candidate,
    reconcile_steam_patch_media,
)
from models.rom import RomOwnedMediaRole, RomOwnedMediaState


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Keep this handler-only suite independent from a database service."""
    yield


@pytest.fixture(autouse=True)
def clear_database():
    """Override the integration fixture because every dependency is mocked."""
    yield


def _rom():
    return SimpleNamespace(id=73, updated_at=datetime(2026, 9, 30, tzinfo=timezone.utc))


def _patch(*, cover="https://cdn.example/Cover.webp", screenshots=None):
    return {
        "media": {
            "cover": [cover] if cover is not None else [],
            "screenshots": (
                screenshots
                if screenshots is not None
                else ["https://cdn.example/shot.webp"]
            ),
        }
    }


class _Response:
    def __init__(self, status_code, chunks):
        self.status_code = status_code
        self._chunks = chunks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class _Client:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def stream(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


@pytest.mark.asyncio
async def test_reconcile_steam_patch_media_canonicalizes_and_reuses_active_paths(
    monkeypatch,
):
    rom = _rom()
    active_cover = SimpleNamespace(
        role=RomOwnedMediaRole.ARTWORK,
        state=RomOwnedMediaState.ACTIVE,
        owned_path="roms/1/73/owned-media/cover.webp",
        mime_type="image/webp",
    )
    active_shot = SimpleNamespace(
        role=RomOwnedMediaRole.SCREENSHOT,
        state=RomOwnedMediaState.ACTIVE,
        owned_path="roms/1/73/owned-media/shot.webp",
        mime_type="image/webp",
    )
    inventory = {
        "url-sha256:eb6bf8ab82750ccd0984f537ca27fdc2322256755a8e3cf08a39c50568bf85b6": active_cover,
        "url-sha256:e54b35c18b54904b1bd7d0c9c3031cf592fa9ea050d0253c0dd4ffabd328f459": active_shot,
    }
    get_inventory = MagicMock(return_value=inventory)
    reconcile = MagicMock(return_value=ReconciledSteamOwnedMediaInventory(rom, []))
    store = AsyncMock()
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.get_steam_owned_media_inventory",
        get_inventory,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.reconcile_steam_owned_media_inventory",
        reconcile,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media._download_candidate",
        store,
    )

    assert await reconcile_steam_patch_media(rom, _patch()) is True
    assert await reconcile_steam_patch_media(rom, _patch()) is True

    assert store.await_count == 0
    assert reconcile.call_count == 2
    assert get_inventory.call_args_list[0].args[0] == rom.id
    assert set(get_inventory.call_args_list[0].args[1]) == set(inventory)
    first_inventory = reconcile.call_args_list[0].args[2]
    assert [item.owned_path for item in first_inventory] == [
        active_shot.owned_path,
        active_cover.owned_path,
    ]


@pytest.mark.asyncio
async def test_reconcile_steam_patch_media_rejects_invalid_or_incomplete_inventory(
    monkeypatch,
):
    reconcile = MagicMock()
    get_inventory = MagicMock()
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.get_steam_owned_media_inventory",
        get_inventory,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.reconcile_steam_owned_media_inventory",
        reconcile,
    )

    assert (
        await reconcile_steam_patch_media(_rom(), _patch(cover="http://bad.example/x"))
        is False
    )
    assert await reconcile_steam_patch_media(_rom(), {"media": {"cover": []}}) is False
    assert await reconcile_steam_patch_media(_rom(), {}) is False

    get_inventory.assert_not_called()
    reconcile.assert_not_called()


@pytest.mark.asyncio
async def test_download_candidate_rejects_http_and_oversized_responses(monkeypatch):
    candidate = ProviderMediaCandidate(
        "steam",
        "cover-1",
        RomOwnedMediaRole.ARTWORK,
        "https://cdn.example/cover.webp",
        "cover.webp",
    )
    store = AsyncMock()
    client = _Client(_Response(502, [b"unavailable"]))
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.ctx_httpx_client",
        SimpleNamespace(get=lambda: client),
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.fs_resource_handler.store_owned_media_image",
        store,
    )

    with pytest.raises(ValueError, match="could not be downloaded"):
        await _download_candidate(_rom(), candidate)

    client.response = _Response(200, [b"x" * (_IMAGE_LIMIT + 1)])
    with pytest.raises(ValueError, match="10 MiB"):
        await _download_candidate(_rom(), candidate)

    assert client.calls == [
        (("GET", candidate.url), {"timeout": 30}),
        (("GET", candidate.url), {"timeout": 30}),
    ]
    store.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconcile_steam_patch_media_cleans_only_current_attempt_on_storage_failure(
    monkeypatch,
):
    rom = _rom()
    store = AsyncMock(
        side_effect=[
            ("roms/1/73/owned-media/shot.webp", "image/webp"),
            ValueError("invalid image"),
        ]
    )
    remove = AsyncMock()
    reconcile = MagicMock()
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.get_steam_owned_media_inventory",
        MagicMock(return_value={}),
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.reconcile_steam_owned_media_inventory",
        reconcile,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media._download_candidate",
        store,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.fs_resource_handler.remove_file",
        remove,
    )

    assert await reconcile_steam_patch_media(rom, _patch()) is False

    reconcile.assert_not_called()
    remove.assert_awaited_once_with("roms/1/73/owned-media/shot.webp")


@pytest.mark.asyncio
async def test_reconcile_steam_patch_media_cleans_uncommitted_paths_on_lock_conflict(
    monkeypatch,
):
    rom = _rom()
    store = AsyncMock(
        side_effect=[
            ("roms/1/73/owned-media/shot.webp", "image/webp"),
            ("roms/1/73/owned-media/cover.webp", "image/webp"),
        ]
    )
    remove = AsyncMock()
    reconcile = MagicMock(return_value=None)
    cleanup = MagicMock()
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.get_steam_owned_media_inventory",
        MagicMock(return_value={}),
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.reconcile_steam_owned_media_inventory",
        reconcile,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.create_owned_media_cleanup_intent",
        cleanup,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media._download_candidate",
        store,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.fs_resource_handler.remove_file",
        remove,
    )

    assert await reconcile_steam_patch_media(rom, _patch()) is False

    reconcile.assert_called_once()
    assert sorted(call.args[0] for call in remove.await_args_list) == [
        "roms/1/73/owned-media/cover.webp",
        "roms/1/73/owned-media/shot.webp",
    ]
    cleanup.assert_not_called()


@pytest.mark.asyncio
async def test_reconcile_steam_patch_media_reconciles_complete_empty_inventory(
    monkeypatch,
):
    rom = _rom()
    reconcile = MagicMock(
        return_value=ReconciledSteamOwnedMediaInventory(
            rom, ["roms/1/73/owned-media/retired.webp"]
        )
    )
    cleanup = MagicMock()
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.get_steam_owned_media_inventory",
        MagicMock(return_value={}),
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.reconcile_steam_owned_media_inventory",
        reconcile,
    )
    monkeypatch.setattr(
        "handler.metadata.steam_owned_media.db_rom_handler.create_owned_media_cleanup_intent",
        cleanup,
    )

    assert (
        await reconcile_steam_patch_media(rom, _patch(cover=None, screenshots=[]))
        is True
    )

    reconcile.assert_called_once_with(rom.id, rom.updated_at, [])
    cleanup.assert_called_once_with(rom.id, 0, "roms/1/73/owned-media/retired.webp")
