"""Contracts for parent-owned media discovery, storage, and mutation responses."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from handler.database import db_rom_handler
from handler.metadata.rom_media import discover_provider_media
from models.rom import (
    Rom,
    RomFile,
    RomFileCategory,
    RomOwnedMediaRole,
    RomOwnedMediaSurface,
)


def test_provider_discovery_normalizes_https_url_and_uses_digest_identity() -> None:
    candidates = discover_provider_media(
        "igdb",
        {"url_screenshots": ["https://images.igdb.com/a.png?b=2&a=1#fragment"]},
    )

    assert len(candidates) == 1
    assert candidates[0].url == "https://images.igdb.com/a.png?a=1&b=2"
    assert candidates[0].provider_media_id == (
        "url-sha256:631703e43d3d497a541d2759ae5e2e7e4452558ef853995586db11e59798ac92"
    )


def test_provider_discovery_rejects_non_https_urls() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        discover_provider_media(
            "igdb", {"url_screenshots": ["http://invalid/image.png"]}
        )


def test_setting_media_placement_returns_a_hydrated_detailed_rom(
    client: TestClient, access_token: str, rom: Rom
) -> None:
    media = db_rom_handler.create_owned_upload_media(
        rom.id,
        rom.updated_at,
        RomOwnedMediaRole.ARTWORK,
        "test-artwork.webp",
        "image/webp",
        "roms/1/media/upload/test-artwork.webp",
    )
    assert media is not None

    response = client.post(
        f"/api/roms/{rom.id}/media/placements",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "media_id": media.media.id,
            "expected_version": media.rom.updated_at.isoformat(),
            "surface": RomOwnedMediaSurface.OVERVIEW.value,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == rom.id


def test_replace_local_background_audio_requires_same_rom_soundtrack(
    client: TestClient, access_token: str, rom: Rom
) -> None:
    soundtrack = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name="track.mp3",
            file_path=f"{rom.fs_path}/OST",
            category=RomFileCategory.SOUNDTRACK,
        )
    )

    response = client.put(
        f"/api/roms/{rom.id}/media/local-background-audio",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "file_ids": [soundtrack.id],
            "expected_version": rom.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["local_background_audio_file_ids"] == [soundtrack.id]


def test_replace_owned_background_audio_returns_hydrated_selection(
    client: TestClient, access_token: str, rom: Rom
) -> None:
    track = db_rom_handler.create_owned_upload_media(
        rom.id,
        rom.updated_at,
        RomOwnedMediaRole.SOUNDTRACK,
        "track.mp3",
        "audio/mpeg",
        "roms/1/media/upload/track.mp3",
    )
    assert track is not None

    response = client.put(
        f"/api/roms/{rom.id}/media/owned-background-audio",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "media_ids": [track.media.id],
            "expected_version": track.rom.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["owned_background_audio_media_ids"] == [track.media.id]
