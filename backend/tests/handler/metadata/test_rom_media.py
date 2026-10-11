from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from handler.metadata import rom_media


def _rom():
    return SimpleNamespace(
        id=73,
        updated_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
        url_cover="https://cdn.example/cover.webp",
        url_screenshots=["https://cdn.example/shot.webp"],
    )


@pytest.mark.asyncio
async def test_refresh_uses_explicit_provider_and_keeps_sibling_after_download_failure(
    monkeypatch,
):
    rom = _rom()
    download = AsyncMock(
        side_effect=[
            ValueError("cover unavailable"),
            ("roms/73/shot.webp", "image/webp"),
        ]
    )
    reconcile = MagicMock(
        side_effect=lambda *args: SimpleNamespace(
            rom=SimpleNamespace(id=73, updated_at=args[1]),
        )
    )
    monkeypatch.setattr(rom_media, "_download_provider_image", download)
    monkeypatch.setattr(
        rom_media.db_rom_handler, "reconcile_provider_owned_media", reconcile
    )
    monkeypatch.setattr(rom_media.fs_resource_handler, "remove_file", AsyncMock())

    refreshed, failures = await rom_media.refresh_provider_owned_media(
        rom, rom.updated_at, "steam"
    )

    assert refreshed.id == 73
    assert len(failures) == 1
    assert download.await_count == 2
    assert all(call.args[1].provider == "steam" for call in download.await_args_list)
    assert reconcile.call_count == 1
    assert reconcile.call_args.args[2] == "steam"


@pytest.mark.asyncio
async def test_refresh_does_not_swallow_programming_errors(monkeypatch):
    rom = _rom()
    monkeypatch.setattr(
        rom_media,
        "_download_provider_image",
        AsyncMock(side_effect=RuntimeError("bug")),
    )

    with pytest.raises(RuntimeError, match="bug"):
        await rom_media.refresh_provider_owned_media(rom, rom.updated_at, "steam")


def test_discovery_does_not_read_rom_metadata_source():
    assert (
        rom_media.discover_provider_media(
            "selected-provider",
            {"url_screenshots": [], "url_artworks": []},
        )
        == []
    )
