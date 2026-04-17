from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from endpoints.roms import soundtrack as soundtrack_endpoint
from handler.database import db_rom_handler
from models.platform import Platform
from models.rom import Rom, RomFile, RomFileCategory
from models.user import User

MP3_BYTES = b"ID3\x03\x00\x00\x00\x00\x00\x21fake mp3 payload"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def multi_file_rom(admin_user: User, platform: Platform) -> Rom:
    rom = Rom(
        platform_id=platform.id,
        name="multi_rom",
        slug="multi_rom_slug",
        fs_name="multi_rom",
        fs_name_no_tags="multi_rom",
        fs_name_no_ext="multi_rom",
        fs_extension="",
        fs_path=f"{platform.slug}/roms",
    )
    rom = db_rom_handler.add_rom(rom)
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=admin_user.id)
    file_path = f"{platform.slug}/roms/multi_rom"
    db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name="game.bin",
            file_path=file_path,
            file_size_bytes=10,
            category=RomFileCategory.GAME,
        )
    )
    db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name="readme.txt",
            file_path=file_path,
            file_size_bytes=5,
            category=RomFileCategory.GAME,
        )
    )
    return db_rom_handler.get_rom(rom.id)


@pytest.fixture
def soundtrack_fs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    folder_dir = tmp_path / "library"
    folder_dir.mkdir()

    def validate_path(path: str) -> Path:
        return folder_dir / Path(path).name

    async def remove_file(path: str) -> None:
        target = folder_dir / Path(path).name
        if target.exists():
            target.unlink()
        else:
            raise FileNotFoundError(path)

    monkeypatch.setattr(
        soundtrack_endpoint.fs_rom_handler, "validate_path", validate_path
    )
    monkeypatch.setattr(
        soundtrack_endpoint.fs_rom_handler,
        "make_directory",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        soundtrack_endpoint.fs_rom_handler,
        "remove_file",
        AsyncMock(side_effect=remove_file),
    )
    return folder_dir


# ---------- POST /api/roms/{id}/soundtracks ----------


def test_upload_soundtrack_success(
    client: TestClient,
    access_token: str,
    multi_file_rom: Rom,
    soundtrack_fs: Path,
):
    response = client.post(
        f"/api/roms/{multi_file_rom.id}/soundtracks",
        headers={**_auth(access_token), "x-upload-filename": "track1.mp3"},
        files={"track1.mp3": ("track1.mp3", MP3_BYTES, "audio/mpeg")},
    )

    assert response.status_code == status.HTTP_200_OK
    written = soundtrack_fs / "track1.mp3"
    assert written.exists()
    assert written.read_bytes() == MP3_BYTES

    rom_after = db_rom_handler.get_rom(multi_file_rom.id)
    soundtracks = [
        f for f in rom_after.files if f.category == RomFileCategory.SOUNDTRACK
    ]
    assert len(soundtracks) == 1
    assert soundtracks[0].file_name == "track1.mp3"
    assert soundtracks[0].file_path == f"{multi_file_rom.full_path}/soundtrack"
    assert soundtracks[0].file_size_bytes == len(MP3_BYTES)


def test_upload_soundtrack_upserts_on_reupload(
    client: TestClient,
    access_token: str,
    multi_file_rom: Rom,
    soundtrack_fs: Path,
):
    for _ in range(2):
        response = client.post(
            f"/api/roms/{multi_file_rom.id}/soundtracks",
            headers={**_auth(access_token), "x-upload-filename": "track1.mp3"},
            files={"track1.mp3": ("track1.mp3", MP3_BYTES, "audio/mpeg")},
        )
        assert response.status_code == status.HTTP_200_OK

    rom_after = db_rom_handler.get_rom(multi_file_rom.id)
    soundtracks = [
        f for f in rom_after.files if f.category == RomFileCategory.SOUNDTRACK
    ]
    assert len(soundtracks) == 1


def test_upload_soundtrack_rejects_single_file_rom(
    client: TestClient,
    access_token: str,
    rom: Rom,
    soundtrack_fs: Path,
):
    db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name=rom.fs_name,
            file_path=rom.fs_path,
            file_size_bytes=1,
            category=RomFileCategory.GAME,
        )
    )

    response = client.post(
        f"/api/roms/{rom.id}/soundtracks",
        headers={**_auth(access_token), "x-upload-filename": "track1.mp3"},
        files={"track1.mp3": ("track1.mp3", MP3_BYTES, "audio/mpeg")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "folder-based" in response.json()["detail"]


def test_upload_soundtrack_rejects_invalid_extension(
    client: TestClient,
    access_token: str,
    multi_file_rom: Rom,
    soundtrack_fs: Path,
):
    response = client.post(
        f"/api/roms/{multi_file_rom.id}/soundtracks",
        headers={**_auth(access_token), "x-upload-filename": "notes.txt"},
        files={"notes.txt": ("notes.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unsupported audio file type" in response.json()["detail"]


# ---------- DELETE /api/roms/{id}/soundtracks/{file_id} ----------


def test_delete_soundtrack_success(
    client: TestClient,
    access_token: str,
    multi_file_rom: Rom,
    soundtrack_fs: Path,
):
    (soundtrack_fs / "track1.mp3").write_bytes(MP3_BYTES)
    track = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=multi_file_rom.id,
            file_name="track1.mp3",
            file_path=f"{multi_file_rom.full_path}/soundtrack",
            file_size_bytes=len(MP3_BYTES),
            category=RomFileCategory.SOUNDTRACK,
        )
    )

    response = client.delete(
        f"/api/roms/{multi_file_rom.id}/soundtracks/{track.id}",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert db_rom_handler.get_rom_file_by_id(track.id) is None
    assert not (soundtrack_fs / "track1.mp3").exists()


def test_delete_soundtrack_wrong_rom_returns_404(
    client: TestClient,
    access_token: str,
    multi_file_rom: Rom,
    rom: Rom,
    soundtrack_fs: Path,
):
    track = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=multi_file_rom.id,
            file_name="track1.mp3",
            file_path=f"{multi_file_rom.full_path}/soundtrack",
            file_size_bytes=len(MP3_BYTES),
            category=RomFileCategory.SOUNDTRACK,
        )
    )

    response = client.delete(
        f"/api/roms/{rom.id}/soundtracks/{track.id}",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_soundtrack_wrong_category_returns_404(
    client: TestClient,
    access_token: str,
    multi_file_rom: Rom,
    soundtrack_fs: Path,
):
    not_soundtrack = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=multi_file_rom.id,
            file_name="english.pdf",
            file_path=f"{multi_file_rom.full_path}/manual",
            file_size_bytes=10,
            category=RomFileCategory.MANUAL,
        )
    )

    response = client.delete(
        f"/api/roms/{multi_file_rom.id}/soundtracks/{not_soundtrack.id}",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
