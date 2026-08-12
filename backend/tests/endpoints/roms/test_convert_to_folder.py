from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from handler.database import db_rom_handler
from handler.filesystem import fs_rom_handler
from models.platform import Platform
from models.rom import Rom, RomFile, RomFileCategory
from models.user import User

MP3_BYTES = b"ID3\x03\x00\x00\x00\x00\x00\x21fake mp3 payload"
PDF_BYTES = b"%PDF-1.4 fake pdf payload"
PNG_BYTES = b"\x89PNG\r\n\x1a\n fake png payload"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def real_library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point fs_rom_handler at a real temp library so FS moves actually happen."""
    lib = tmp_path / "library"
    lib.mkdir()
    monkeypatch.setattr(fs_rom_handler, "base_path", lib.resolve())
    return lib


def _single_file_rom(
    platform: Platform,
    admin_user: User,
    lib: Path,
    *,
    fs_name: str,
    fs_name_no_ext: str,
    fs_extension: str,
) -> Rom:
    """A simple single-file ROM with its lone file present on disk."""
    rom = Rom(
        platform_id=platform.id,
        name=fs_name_no_ext,
        slug=f"{fs_name}_slug",
        fs_name=fs_name,
        fs_name_no_tags=fs_name_no_ext,
        fs_name_no_ext=fs_name_no_ext,
        fs_extension=fs_extension,
        fs_path=f"{platform.slug}/roms",
    )
    rom = db_rom_handler.add_rom(rom)
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=admin_user.id)
    db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name=fs_name,
            file_path=rom.fs_path,
            file_size_bytes=10,
            last_modified=1700000000.0,
            category=RomFileCategory.GAME,
        )
    )
    disk = lib / rom.fs_path / fs_name
    disk.parent.mkdir(parents=True, exist_ok=True)
    disk.write_bytes(b"romdata")
    return db_rom_handler.get_rom(rom.id)


def _source_manifest(root: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


@pytest.mark.parametrize(
    ("fs_name", "fs_name_no_ext", "fs_extension", "existing_target"),
    [
        ("test_rom.zip", "test_rom", "zip", False),
        ("test_rom.zip", "test_rom", "zip", False),
        ("test_rom.zip", "test_rom", "zip", True),
        ("test_rom", "test_rom", "", False),
        ("test_rom", "test_rom", "", True),
    ],
    ids=[
        "single-file",
        "already-folder-request",
        "folder-collision",
        "extensionless",
        "extensionless-collision",
    ],
)
def test_convert_to_folder_denied_without_source_mutation(
    client: TestClient,
    access_token: str,
    platform: Platform,
    admin_user: User,
    real_library: Path,
    fs_name: str,
    fs_name_no_ext: str,
    fs_extension: str,
    existing_target: bool,
):
    rom = _single_file_rom(
        platform,
        admin_user,
        real_library,
        fs_name=fs_name,
        fs_name_no_ext=fs_name_no_ext,
        fs_extension=fs_extension,
    )
    source = real_library / rom.fs_path / fs_name
    if existing_target:
        if source.name == fs_name_no_ext:
            source.unlink()
        target = real_library / rom.fs_path / fs_name_no_ext
        target.mkdir(parents=True, exist_ok=True)
        (target / "already_here.txt").write_text("keep me")

    before = _source_manifest(real_library)
    response = client.post(
        f"/api/roms/{rom.id}/convert-to-folder", headers=_auth(access_token)
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "external_storage_operation_denied"
    assert _source_manifest(real_library) == before


def test_convert_to_folder_denial_precedes_database_work(
    client: TestClient,
    access_token: str,
    platform: Platform,
    admin_user: User,
    real_library: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    rom = _single_file_rom(
        platform,
        admin_user,
        real_library,
        fs_name="test_rom",
        fs_name_no_ext="test_rom",
        fs_extension="",
    )

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(db_rom_handler, "convert_rom_to_folder", boom)
    before = _source_manifest(real_library)
    response = client.post(
        f"/api/roms/{rom.id}/convert-to-folder", headers=_auth(access_token)
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "external_storage_operation_denied"
    assert _source_manifest(real_library) == before


@pytest.mark.parametrize(
    ("route", "filename", "payload", "media_type"),
    [
        ("soundtracks", "track1.mp3", MP3_BYTES, "audio/mpeg"),
        ("manuals/files", "manual.pdf", PDF_BYTES, "application/pdf"),
        ("screenshots", "shot1.png", PNG_BYTES, "image/png"),
    ],
)
def test_child_upload_denied_without_source_mutation(
    client: TestClient,
    access_token: str,
    platform: Platform,
    admin_user: User,
    real_library: Path,
    route: str,
    filename: str,
    payload: bytes,
    media_type: str,
):
    rom = _single_file_rom(
        platform,
        admin_user,
        real_library,
        fs_name="test_rom.zip",
        fs_name_no_ext="test_rom",
        fs_extension="zip",
    )
    before = _source_manifest(real_library)
    response = client.post(
        f"/api/roms/{rom.id}/{route}",
        headers={**_auth(access_token), "x-upload-filename": filename},
        files={filename: (filename, payload, media_type)},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"]["code"] == "external_storage_operation_denied"
    assert _source_manifest(real_library) == before
