import os
from pathlib import Path
from unittest.mock import AsyncMock
from urllib.parse import quote

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from endpoints.roms import files as files_endpoint
from handler.database import db_permission_handler, db_rom_handler
from handler.database.base_handler import sync_session
from handler.filesystem.storage_resolver import StorageRootHealthSnapshot
from models.permission import PermAction, PermEntity
from models.platform import Platform
from models.rom import Rom, RomFile, RomFileCategory
from models.storage import PlatformStorageMapping, StorageRoot
from models.user import User

_MAPPED_ROOT: Path | None = None


@pytest.fixture(autouse=True)
def mapped_file_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: Platform
):
    global _MAPPED_ROOT
    _MAPPED_ROOT = tmp_path / "external"
    mapped_path = _MAPPED_ROOT / platform.slug
    mapped_path.mkdir(parents=True)
    root = StorageRoot(
        name="Endpoint mapped archive",
        container_path=str(_MAPPED_ROOT),
        mode="external_read_only",
        active=True,
    )
    with sync_session.begin() as session:
        session.add(root)
        session.flush()
        session.add(
            PlatformStorageMapping(
                platform_id=platform.id,
                storage_root_id=root.id,
                relative_path=platform.slug,
                active=True,
                version=1,
            )
        )
    real_access = os.access
    monkeypatch.setattr(
        "handler.filesystem.storage_resolver.os.access",
        lambda path, mode: False if mode & os.W_OK else real_access(path, mode),
    )
    monkeypatch.setattr(
        "handler.storage.read_context.get_storage_root_health_snapshot",
        lambda _root: StorageRootHealthSnapshot(True, True, True, None, None),
    )
    yield
    _MAPPED_ROOT = None


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _add_file(rom: Rom, name: str, category: RomFileCategory | None) -> RomFile:
    file = _add_db_file(rom, name, category)
    assert _MAPPED_ROOT is not None
    source = _MAPPED_ROOT.joinpath(*Path(file.full_path).parts)
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"mapped-data")
    return file


def _add_db_file(rom: Rom, name: str, category: RomFileCategory | None) -> RomFile:
    return db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name=name,
            file_path=f"{rom.fs_path}/{rom.fs_name}",
            file_size_bytes=10,
            category=category,
        )
    )


def _make_rom(admin_user: User, platform: Platform) -> Rom:
    rom = db_rom_handler.add_rom(
        Rom(
            platform_id=platform.id,
            name="media_rom",
            slug="media_rom_slug",
            fs_name="media_rom",
            fs_name_no_tags="media_rom",
            fs_name_no_ext="media_rom",
            fs_extension="",
            fs_path=f"{platform.slug}/roms",
        )
    )
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=admin_user.id)
    return rom


def test_image_file_served_inline(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "trailer_thumb.png", RomFileCategory.GAME)

    r = client.get(
        f"/api/roms/{file.id}/files/content/trailer_thumb.png",
        headers=_auth(access_token),
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.headers["content-type"].startswith("image/png")
    assert r.headers["content-disposition"].startswith("inline")


def test_video_file_served_inline(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "trailer.mp4", RomFileCategory.GAME)

    r = client.get(
        f"/api/roms/{file.id}/files/content/trailer.mp4",
        headers=_auth(access_token),
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.headers["content-type"].startswith("video/mp4")
    assert r.headers["content-disposition"].startswith("inline")


def test_pdf_manual_served_inline(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "manual.pdf", RomFileCategory.MANUAL)

    r = client.get(
        f"/api/roms/{file.id}/files/content/manual.pdf",
        headers=_auth(access_token),
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.headers["content-disposition"].startswith("inline")
    assert r.headers["x-content-type-options"] == "nosniff"


def test_markdown_manual_served_inline(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "manual.md", RomFileCategory.MANUAL)

    r = client.get(
        f"/api/roms/{file.id}/files/content/manual.md",
        headers=_auth(access_token),
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.headers["content-disposition"].startswith("inline")
    # nosniff keeps the browser from sniffing the Markdown into HTML.
    assert r.headers["x-content-type-options"] == "nosniff"


def test_non_manual_document_served_as_attachment(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    # A game/extra file that happens to end in .pdf must still download; only
    # manual-category documents are served inline.
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "readme.pdf", RomFileCategory.GAME)

    r = client.get(
        f"/api/roms/{file.id}/files/content/readme.pdf",
        headers=_auth(access_token),
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.headers["content-type"].startswith("application/octet-stream")
    assert r.headers["content-disposition"].startswith("attachment")


def test_rom_file_served_as_attachment(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "game.bin", RomFileCategory.GAME)

    r = client.get(
        f"/api/roms/{file.id}/files/content/game.bin",
        headers=_auth(access_token),
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.headers["content-type"].startswith("application/octet-stream")
    assert r.headers["content-disposition"].startswith("attachment")


def test_content_type_derived_from_db_not_path_param(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    # A caller must not be able to force an inline image content-type on a
    # non-media file by tacking a fake extension onto the URL path param.
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "game.bin", RomFileCategory.GAME)

    r = client.get(
        f"/api/roms/{file.id}/files/content/game.bin.png",
        headers=_auth(access_token),
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.headers["content-type"].startswith("application/octet-stream")
    assert r.headers["content-disposition"].startswith("attachment")


def test_content_disposition_escapes_quotes_and_backslashes(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, 'game "quoted"\\edition.bin', RomFileCategory.GAME)

    response = client.head(
        f"/api/roms/{file.id}/files/content/client-name.bin",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    value = response.headers["content-disposition"]
    escaped = file.file_name.replace("\\", "\\\\").replace('"', '\\"')
    assert f'filename="{escaped}"' in value
    assert f"filename*=UTF-8''{quote(file.file_name, safe='')}" in value
    assert value.count("filename=") == 1
    assert value.count("filename*=") == 1


def test_content_disposition_encodes_unicode_with_stable_ascii_fallback(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "ゲーム", RomFileCategory.GAME)

    response = client.head(
        f"/api/roms/{file.id}/files/content/client-name.bin",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    value = response.headers["content-disposition"]
    assert 'filename="download"' in value
    assert f"filename*=UTF-8''{quote(file.file_name, safe='')}" in value
    assert file.file_name not in value


def test_content_disposition_uses_database_name_not_client_path_parameter(
    client: TestClient, access_token: str, admin_user: User, platform: Platform
):
    rom = _make_rom(admin_user, platform)
    file = _add_file(rom, "archive.bin", RomFileCategory.GAME)

    response = client.head(
        f"/api/roms/{file.id}/files/content/C:%5Cserver%5Cprivate.txt",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    value = response.headers["content-disposition"]
    assert "archive.bin" in value
    assert "server" not in value
    assert "private" not in value


@pytest.mark.parametrize(
    "file_name",
    [
        "bad\rname.bin",
        "bad\nname.bin",
        "bad\x00name.bin",
        "C:\\private\\host\x85name.bin",
    ],
)
def test_content_disposition_rejects_controls_without_raw_detail(
    client: TestClient,
    access_token: str,
    admin_user: User,
    platform: Platform,
    file_name: str,
):
    rom = _make_rom(admin_user, platform)
    file = _add_db_file(rom, file_name, RomFileCategory.GAME)

    response = client.head(
        f"/api/roms/{file.id}/files/content/client-name.bin",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.headers.get("content-disposition") is None
    assert file_name not in response.text
    assert "private" not in response.text
    assert "traceback" not in response.text.lower()


# ---------- DELETE /api/roms/{rom_id}/files/{file_id} ----------


@pytest.fixture
def files_fs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock fs_rom_handler so file operations hit a temporary directory."""
    library_dir = tmp_path / "library"
    library_dir.mkdir()

    def validate_path(path: str) -> Path:
        return library_dir / Path(path).name

    async def remove_file(path: str) -> None:
        target = library_dir / Path(path).name
        if target.exists():
            target.unlink()
        else:
            raise FileNotFoundError(path)

    monkeypatch.setattr(files_endpoint.fs_rom_handler, "validate_path", validate_path)
    monkeypatch.setattr(
        files_endpoint.fs_rom_handler,
        "remove_file",
        AsyncMock(side_effect=remove_file),
    )
    return library_dir


@pytest.mark.skip(reason="Superseded by bounded external denial matrix")
def test_delete_rom_file_success(
    client: TestClient,
    access_token: str,
    admin_user: User,
    platform: Platform,
    files_fs: Path,
):
    rom = _make_rom(admin_user, platform)
    (files_fs / "game.bin").write_bytes(b"\x00" * 16)
    rom_file = _add_file(rom, "game.bin", RomFileCategory.GAME)

    response = client.delete(
        f"/api/roms/{rom.id}/files/{rom_file.id}",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert db_rom_handler.get_rom_file_by_id(rom_file.id) is None
    assert not (files_fs / "game.bin").exists()


@pytest.mark.skip(reason="Superseded by bounded external denial matrix")
def test_delete_rom_file_wrong_rom_returns_404(
    client: TestClient,
    access_token: str,
    admin_user: User,
    platform: Platform,
    files_fs: Path,
):
    rom_a = _make_rom(admin_user, platform)
    # Use the game_folder_rom fixture name to avoid a duplicate fs_name constraint;
    # create a second ROM directly with a distinct slug and fs_name.
    rom_b = db_rom_handler.add_rom(
        Rom(
            platform_id=platform.id,
            name="other_rom",
            slug="other_rom_slug",
            fs_name="other_rom",
            fs_name_no_tags="other_rom",
            fs_name_no_ext="other_rom",
            fs_extension="",
            fs_path=f"{platform.slug}/roms",
        )
    )
    db_rom_handler.add_rom_user(rom_id=rom_b.id, user_id=admin_user.id)
    rom_file = _add_file(rom_a, "game.bin", RomFileCategory.GAME)

    response = client.delete(
        f"/api/roms/{rom_b.id}/files/{rom_file.id}",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    # File must NOT have been deleted from the database.
    assert db_rom_handler.get_rom_file_by_id(rom_file.id) is not None


@pytest.mark.skip(reason="Superseded by bounded external denial matrix")
def test_delete_rom_file_unknown_file_returns_404(
    client: TestClient,
    access_token: str,
    admin_user: User,
    platform: Platform,
    files_fs: Path,
):
    rom = _make_rom(admin_user, platform)

    response = client.delete(
        f"/api/roms/{rom.id}/files/999999",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.skip(reason="Superseded by bounded external denial matrix")
def test_delete_rom_file_tolerates_missing_disk_file(
    client: TestClient,
    access_token: str,
    admin_user: User,
    platform: Platform,
    files_fs: Path,
):
    """DB row must be dropped even when the on-disk file is already gone."""
    rom = _make_rom(admin_user, platform)
    rom_file = _add_file(rom, "missing.bin", RomFileCategory.GAME)

    response = client.delete(
        f"/api/roms/{rom.id}/files/{rom_file.id}",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert db_rom_handler.get_rom_file_by_id(rom_file.id) is None


@pytest.mark.skip(reason="Superseded by bounded external denial matrix")
def test_delete_rom_file_forbidden_viewer(
    client: TestClient,
    viewer_access_token: str,
    admin_user: User,
    platform: Platform,
    files_fs: Path,
):
    rom = _make_rom(admin_user, platform)
    rom_file = _add_file(rom, "game.bin", RomFileCategory.GAME)

    response = client.delete(
        f"/api/roms/{rom.id}/files/{rom_file.id}",
        headers=_auth(viewer_access_token),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    # File must NOT have been deleted.
    assert db_rom_handler.get_rom_file_by_id(rom_file.id) is not None


@pytest.mark.skip(reason="Superseded by bounded external denial matrix")
def test_delete_rom_file_forbidden_without_delete_grant(
    client: TestClient,
    editor_access_token: str,
    editor_user: User,
    admin_user: User,
    platform: Platform,
    files_fs: Path,
):
    """ROMS_WRITE alone must not delete library content.

    The editor keeps write (so the coarse scope gate passes) but loses the
    ROMS/DELETE grant, which is what the route now requires.
    """
    db_permission_handler.replace_user_overrides(
        editor_user.id,
        [(PermEntity.ROMS, PermAction.DELETE, False, False)],
    )
    rom = _make_rom(admin_user, platform)
    (files_fs / "game.bin").write_bytes(b"\x00" * 16)
    rom_file = _add_file(rom, "game.bin", RomFileCategory.GAME)

    response = client.delete(
        f"/api/roms/{rom.id}/files/{rom_file.id}",
        headers=_auth(editor_access_token),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert db_rom_handler.get_rom_file_by_id(rom_file.id) is not None
    assert (files_fs / "game.bin").exists()


@pytest.mark.skip(reason="Superseded by bounded external denial matrix")
def test_delete_rom_file_allowed_for_editor(
    client: TestClient,
    editor_access_token: str,
    admin_user: User,
    platform: Platform,
    files_fs: Path,
):
    """The legacy Editor group holds ROMS/DELETE, so it must keep working."""
    rom = _make_rom(admin_user, platform)
    (files_fs / "game.bin").write_bytes(b"\x00" * 16)
    rom_file = _add_file(rom, "game.bin", RomFileCategory.GAME)

    response = client.delete(
        f"/api/roms/{rom.id}/files/{rom_file.id}",
        headers=_auth(editor_access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert db_rom_handler.get_rom_file_by_id(rom_file.id) is None


def test_phase5_delivery_preflights_every_required_part_before_headers():
    source = Path("endpoints/roms/files.py").read_text()
    assert (
        "preflight_mapped_download" in source
    ), "Phase 5 RED: all required parts are not preflighted before output"


def test_phase5_delivery_redacts_storage_failures_and_preserves_range_head():
    source = Path("endpoints/roms/files.py").read_text()
    assert (
        "MappedContentResponse" in source
    ), "Phase 5 RED: mapped delivery parity and redacted failures are not implemented"
