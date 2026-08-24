import os
from io import BytesIO
from pathlib import Path
from unittest import mock

import pytest
from fastapi import status
from pydantic import ValidationError
from sqlalchemy import select

from config import ASSETS_BASE_PATH
from endpoints.responses.assets import ScreenshotSchema, UserScreenshotSchema
from endpoints.storage_policy import authorize_api_storage_operation
from handler.database import db_screenshot_handler
from handler.database.base_handler import sync_session
from handler.filesystem import fs_asset_handler
from models.assets import Screenshot
from models.permission import HiddenEntity, PermEntity
from models.platform import Platform
from models.rom import Rom
from models.user import User


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _hide(entity: PermEntity, entity_id: int, user_id: int) -> None:
    with sync_session.begin() as s:
        s.add(HiddenEntity(entity=entity, entity_id=entity_id, user_id=user_id))


def _asset_manifest():
    root = Path(ASSETS_BASE_PATH).resolve()
    if not root.exists():
        return False, ()

    entries = []
    for path in sorted(root.rglob("*")):
        stat = path.lstat()
        content: bytes | str | None
        if path.is_symlink():
            content = os.readlink(path)
        elif path.is_file():
            content = path.read_bytes()
        else:
            content = None
        entries.append(
            (path.relative_to(root).as_posix(), stat.st_mode, stat.st_size, content)
        )
    return True, tuple(entries)


def _screenshot_ids_for_rom(rom_id: int) -> tuple[int, ...]:
    with sync_session() as session:
        return tuple(
            session.scalars(
                select(Screenshot.id)
                .where(Screenshot.rom_id == rom_id)
                .order_by(Screenshot.id)
            ).all()
        )


def _screenshot_row_state(
    screenshot_id: int,
) -> tuple[tuple[str, object], ...] | None:
    with sync_session() as session:
        screenshot = session.get(Screenshot, screenshot_id)
        if screenshot is None:
            return None
        return tuple(
            (column.name, getattr(screenshot, column.name))
            for column in Screenshot.__table__.columns
        )


@pytest.mark.parametrize("schema", (ScreenshotSchema, UserScreenshotSchema))
def test_screenshot_schema_requires_live_rom_ownership(schema) -> None:
    json_schema = schema.model_json_schema()

    assert "rom_id" in json_schema["required"]
    assert json_schema["properties"]["rom_id"] == {"title": "Rom Id", "type": "integer"}
    assert "retained_catalog_id" not in json_schema["properties"]


def test_screenshot_schema_rejects_missing_or_null_rom_owner(
    screenshot: Screenshot,
) -> None:
    payload = {
        field: getattr(screenshot, field)
        for field in ScreenshotSchema.model_fields
        if field != "rom_id"
    }

    with pytest.raises(ValidationError):
        ScreenshotSchema.model_validate(payload)
    with pytest.raises(ValidationError):
        ScreenshotSchema.model_validate({**payload, "rom_id": None})


# ---------- POST /api/screenshots ----------


@mock.patch(
    "endpoints.screenshots.fs_asset_handler.write_file", new_callable=mock.AsyncMock
)
@mock.patch("endpoints.screenshots.scan_screenshot", new_callable=mock.AsyncMock)
def test_upload_gallery_screenshot_sets_flags(
    mock_scan,
    _mock_write,
    client,
    access_token: str,
    rom: Rom,
    platform: Platform,
    admin_user: User,
):
    mock_scan.return_value = Screenshot(
        file_name="shot1.png",
        file_name_no_tags="shot1",
        file_name_no_ext="shot1",
        file_extension="png",
        file_path=f"{platform.slug}/screenshots",
        file_size_bytes=100,
    )

    response = client.post(
        f"/api/screenshots?rom_id={rom.id}",
        files={"screenshotFile": ("shot1.png", BytesIO(b"img"), "image/png")},
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_gallery"] is True
    assert data["is_public"] is False


@mock.patch(
    "endpoints.screenshots.fs_asset_handler.write_file", new_callable=mock.AsyncMock
)
@mock.patch("endpoints.screenshots.scan_screenshot", new_callable=mock.AsyncMock)
def test_upload_rejects_invalid_extension(
    _mock_scan,
    _mock_write,
    client,
    access_token: str,
    rom: Rom,
):
    response = client.post(
        f"/api/screenshots?rom_id={rom.id}",
        files={"screenshotFile": ("notes.txt", BytesIO(b"nope"), "text/plain")},
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unsupported image file type" in response.json()["detail"]


def _assert_hidden_upload_is_masked_before_effects(
    *,
    client,
    token: str,
    user: User,
    rom: Rom,
    platform: Platform,
) -> None:
    before_ids = _screenshot_ids_for_rom(rom.id)
    before_assets = _asset_manifest()
    file_name = "hidden-target-proof.png"
    scanned = Screenshot(
        file_name=file_name,
        file_name_no_tags="hidden-target-proof",
        file_name_no_ext="hidden-target-proof",
        file_extension="png",
        file_path="unused/screenshots",
        file_size_bytes=3,
    )
    real_get = db_screenshot_handler.get_screenshot
    real_add = db_screenshot_handler.add_screenshot
    real_update = db_screenshot_handler.update_screenshot

    with (
        mock.patch(
            "endpoints.screenshots.fs_asset_handler.build_screenshots_file_path",
            return_value=Path("/tmp/hidden-target-proof"),
        ) as mock_build_path,
        mock.patch(
            "endpoints.screenshots.fs_asset_handler.write_file",
            new_callable=mock.AsyncMock,
        ) as mock_write,
        mock.patch(
            "endpoints.screenshots.scan_screenshot",
            new_callable=mock.AsyncMock,
            return_value=scanned,
        ) as mock_scan,
        mock.patch(
            "endpoints.screenshots.db_screenshot_handler.get_screenshot",
            side_effect=real_get,
        ) as mock_get,
        mock.patch(
            "endpoints.screenshots.db_screenshot_handler.add_screenshot",
            side_effect=real_add,
        ) as mock_add,
        mock.patch(
            "endpoints.screenshots.db_screenshot_handler.update_screenshot",
            side_effect=real_update,
        ) as mock_update,
    ):
        response = client.post(
            f"/api/screenshots?rom_id={rom.id}",
            files={"screenshotFile": (file_name, BytesIO(b"img"), "image/png")},
            headers=_auth(token),
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "ROM not found"}
    for hidden_detail in (
        rom.id,
        rom.name,
        rom.fs_path,
        platform.id,
        platform.name,
        platform.fs_slug,
        file_name,
        user.username,
        "permission",
    ):
        assert str(hidden_detail).lower() not in response.text.lower()

    for effect in (
        mock_build_path,
        mock_write,
        mock_scan,
        mock_get,
        mock_add,
        mock_update,
    ):
        effect.assert_not_called()

    assert _screenshot_ids_for_rom(rom.id) == before_ids
    assert _asset_manifest() == before_assets


def test_hidden_rom_screenshot_upload_is_masked_before_effects(
    client,
    viewer_access_token: str,
    viewer_user: User,
    rom: Rom,
    platform: Platform,
):
    _hide(PermEntity.ROMS, rom.id, viewer_user.id)

    _assert_hidden_upload_is_masked_before_effects(
        client=client,
        token=viewer_access_token,
        user=viewer_user,
        rom=rom,
        platform=platform,
    )


def test_hidden_platform_screenshot_upload_is_masked_before_effects(
    client,
    viewer_access_token: str,
    viewer_user: User,
    rom: Rom,
    platform: Platform,
):
    _hide(PermEntity.PLATFORMS, platform.id, viewer_user.id)

    _assert_hidden_upload_is_masked_before_effects(
        client=client,
        token=viewer_access_token,
        user=viewer_user,
        rom=rom,
        platform=platform,
    )


# ---------- PUT /api/screenshots/{id} (visibility) ----------


def _assert_hidden_screenshot_mutation_is_masked_before_effects(
    *,
    client,
    token: str,
    user: User,
    rom: Rom,
    platform: Platform,
    method: str,
) -> None:
    file_name = f"hidden-{method.lower()}-{rom.id}-{user.id}.png"
    file_path = (
        Path("users")
        / user.fs_safe_folder_name
        / "screenshots"
        / platform.fs_slug
        / str(rom.id)
    )
    screenshot = db_screenshot_handler.add_screenshot(
        Screenshot(
            rom_id=rom.id,
            user_id=user.id,
            file_name=file_name,
            file_name_no_tags=Path(file_name).stem,
            file_name_no_ext=Path(file_name).stem,
            file_extension="png",
            file_path=file_path.as_posix(),
            file_size_bytes=18,
            is_gallery=True,
            is_public=False,
        )
    )
    asset_file = Path(ASSETS_BASE_PATH, file_path, file_name)
    asset_file.parent.mkdir(parents=True, exist_ok=True)
    asset_file.write_bytes(b"hidden screenshot")

    before_row = _screenshot_row_state(screenshot.id)
    before_assets = _asset_manifest()
    real_update = db_screenshot_handler.update_screenshot
    real_delete = db_screenshot_handler.delete_screenshot
    real_remove = fs_asset_handler.remove_file

    with (
        mock.patch(
            "endpoints.screenshots.db_screenshot_handler.update_screenshot",
            side_effect=real_update,
        ) as mock_update,
        mock.patch(
            "endpoints.screenshots.db_screenshot_handler.delete_screenshot",
            side_effect=real_delete,
        ) as mock_delete,
        mock.patch(
            "endpoints.screenshots.authorize_api_storage_operation",
            wraps=authorize_api_storage_operation,
        ) as mock_authorize,
        mock.patch(
            "endpoints.screenshots.fs_asset_handler.remove_file",
            new_callable=mock.AsyncMock,
            side_effect=real_remove,
        ) as mock_remove,
        mock.patch("endpoints.screenshots.log.info") as mock_info,
        mock.patch("endpoints.screenshots.log.warning") as mock_warning,
    ):
        if method == "PUT":
            response = client.put(
                f"/api/screenshots/{screenshot.id}",
                json={"is_public": True},
                headers=_auth(token),
            )
        else:
            response = client.delete(
                f"/api/screenshots/{screenshot.id}",
                headers=_auth(token),
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Screenshot not found"}
    for hidden_detail in (
        rom.id,
        rom.name,
        rom.fs_path,
        platform.id,
        platform.name,
        platform.fs_slug,
        screenshot.id,
        screenshot.file_name,
        screenshot.full_path,
        user.id,
        user.username,
        "permission",
    ):
        assert str(hidden_detail).lower() not in response.text.lower()

    mock_update.assert_not_called()
    mock_delete.assert_not_called()
    mock_authorize.assert_not_called()
    mock_remove.assert_not_awaited()
    mock_info.assert_not_called()
    mock_warning.assert_not_called()
    assert _screenshot_row_state(screenshot.id) == before_row
    assert _asset_manifest() == before_assets


def test_hidden_rom_screenshot_update_is_masked_before_effects(
    client,
    viewer_access_token: str,
    viewer_user: User,
    rom: Rom,
    platform: Platform,
):
    _hide(PermEntity.ROMS, rom.id, viewer_user.id)

    _assert_hidden_screenshot_mutation_is_masked_before_effects(
        client=client,
        token=viewer_access_token,
        user=viewer_user,
        rom=rom,
        platform=platform,
        method="PUT",
    )


def test_hidden_platform_screenshot_update_is_masked_before_effects(
    client,
    viewer_access_token: str,
    viewer_user: User,
    rom: Rom,
    platform: Platform,
):
    _hide(PermEntity.PLATFORMS, platform.id, viewer_user.id)

    _assert_hidden_screenshot_mutation_is_masked_before_effects(
        client=client,
        token=viewer_access_token,
        user=viewer_user,
        rom=rom,
        platform=platform,
        method="PUT",
    )


def test_update_visibility_owner(client, access_token: str, screenshot: Screenshot):
    response = client.put(
        f"/api/screenshots/{screenshot.id}",
        json={"is_public": True},
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_public"] is True

    refreshed = db_screenshot_handler.get_screenshot_by_id(screenshot.id)
    assert refreshed is not None and refreshed.is_public is True


def test_update_visibility_other_user_returns_404(
    client,
    access_token: str,
    rom: Rom,
    platform: Platform,
    editor_user: User,
):
    others = db_screenshot_handler.add_screenshot(
        Screenshot(
            rom_id=rom.id,
            user_id=editor_user.id,
            file_name="other.png",
            file_name_no_tags="other",
            file_name_no_ext="other",
            file_extension="png",
            file_path=f"{platform.slug}/screenshots",
            file_size_bytes=10,
        )
    )

    response = client.put(
        f"/api/screenshots/{others.id}",
        json={"is_public": True},
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------- DELETE /api/screenshots/{id} ----------


@mock.patch(
    "endpoints.screenshots.fs_asset_handler.remove_file", new_callable=mock.AsyncMock
)
def test_delete_screenshot_owner(
    _mock_remove,
    client,
    access_token: str,
    screenshot: Screenshot,
):
    response = client.delete(
        f"/api/screenshots/{screenshot.id}",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert db_screenshot_handler.get_screenshot_by_id(screenshot.id) is None


def test_hidden_rom_screenshot_delete_is_masked_before_effects(
    client,
    viewer_access_token: str,
    viewer_user: User,
    rom: Rom,
    platform: Platform,
):
    _hide(PermEntity.ROMS, rom.id, viewer_user.id)

    _assert_hidden_screenshot_mutation_is_masked_before_effects(
        client=client,
        token=viewer_access_token,
        user=viewer_user,
        rom=rom,
        platform=platform,
        method="DELETE",
    )


def test_hidden_platform_screenshot_delete_is_masked_before_effects(
    client,
    viewer_access_token: str,
    viewer_user: User,
    rom: Rom,
    platform: Platform,
):
    _hide(PermEntity.PLATFORMS, platform.id, viewer_user.id)

    _assert_hidden_screenshot_mutation_is_masked_before_effects(
        client=client,
        token=viewer_access_token,
        user=viewer_user,
        rom=rom,
        platform=platform,
        method="DELETE",
    )


@mock.patch(
    "endpoints.screenshots.fs_asset_handler.remove_file", new_callable=mock.AsyncMock
)
def test_delete_screenshot_other_user_returns_404(
    _mock_remove,
    client,
    access_token: str,
    rom: Rom,
    platform: Platform,
    editor_user: User,
):
    others = db_screenshot_handler.add_screenshot(
        Screenshot(
            rom_id=rom.id,
            user_id=editor_user.id,
            file_name="other.png",
            file_name_no_tags="other",
            file_name_no_ext="other",
            file_extension="png",
            file_path=f"{platform.slug}/screenshots",
            file_size_bytes=10,
        )
    )

    response = client.delete(
        f"/api/screenshots/{others.id}",
        headers=_auth(access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert db_screenshot_handler.get_screenshot_by_id(others.id) is not None


# ---------- Gallery visibility query ----------


def _add_screenshot(rom, platform, user_id, name, *, is_gallery, is_public):
    return db_screenshot_handler.add_screenshot(
        Screenshot(
            rom_id=rom.id,
            user_id=user_id,
            file_name=f"{name}.png",
            file_name_no_tags=name,
            file_name_no_ext=name,
            file_extension="png",
            file_path=f"{platform.slug}/screenshots",
            file_size_bytes=10,
            is_gallery=is_gallery,
            is_public=is_public,
        )
    )


def test_gallery_query_excludes_thumbnails_and_others_private(
    rom: Rom,
    platform: Platform,
    admin_user: User,
    editor_user: User,
):
    # Own save/state thumbnail — not a gallery upload.
    _add_screenshot(
        rom, platform, admin_user.id, "thumb", is_gallery=False, is_public=False
    )
    # Own private gallery screenshot — visible to self.
    mine = _add_screenshot(
        rom, platform, admin_user.id, "mine", is_gallery=True, is_public=False
    )
    # Another user's public gallery screenshot — visible (community).
    others_public = _add_screenshot(
        rom, platform, editor_user.id, "pub", is_gallery=True, is_public=True
    )
    # Another user's private gallery screenshot — hidden.
    _add_screenshot(
        rom, platform, editor_user.id, "priv", is_gallery=True, is_public=False
    )

    visible = {
        s.id
        for s in db_screenshot_handler.get_rom_gallery_screenshots(
            rom_id=rom.id, user_id=admin_user.id
        )
    }

    assert mine.id in visible
    assert others_public.id in visible
    assert len(visible) == 2


# ---------- GET /api/screenshots/{id}/content ----------


@mock.patch("endpoints.screenshots.fs_asset_handler.validate_path")
def test_owner_downloads_own_screenshot(
    mock_validate_path,
    client,
    access_token: str,
    admin_user: User,
    rom: Rom,
    platform: Platform,
    tmp_path,
):
    screenshot = _add_screenshot(
        rom, platform, admin_user.id, "shot", is_gallery=True, is_public=False
    )
    test_file = tmp_path / "shot.png"
    test_file.write_bytes(b"SHOT_DATA")
    mock_validate_path.return_value = test_file

    response = client.get(
        f"/api/screenshots/{screenshot.id}/content", headers=_auth(access_token)
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"SHOT_DATA"


def test_other_user_cannot_download_private_screenshot(
    client,
    viewer_access_token: str,
    admin_user: User,
    rom: Rom,
    platform: Platform,
):
    screenshot = _add_screenshot(
        rom, platform, admin_user.id, "shot", is_gallery=True, is_public=False
    )
    response = client.get(
        f"/api/screenshots/{screenshot.id}/content",
        headers=_auth(viewer_access_token),
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@mock.patch("endpoints.screenshots.fs_asset_handler.validate_path")
def test_other_user_downloads_public_screenshot(
    mock_validate_path,
    client,
    viewer_access_token: str,
    admin_user: User,
    rom: Rom,
    platform: Platform,
    tmp_path,
):
    screenshot = _add_screenshot(
        rom, platform, admin_user.id, "shot", is_gallery=True, is_public=True
    )
    test_file = tmp_path / "shot.png"
    test_file.write_bytes(b"SHARED_SHOT")
    mock_validate_path.return_value = test_file

    response = client.get(
        f"/api/screenshots/{screenshot.id}/content",
        headers=_auth(viewer_access_token),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"SHARED_SHOT"


def test_hidden_rom_masks_public_screenshot_download(
    client,
    viewer_access_token: str,
    viewer_user: User,
    admin_user: User,
    rom: Rom,
    platform: Platform,
):
    # A public screenshot on a ROM hidden from the caller must stay 404-masked;
    # sharing cannot override the hidden-resource boundary.
    screenshot = _add_screenshot(
        rom, platform, admin_user.id, "shot", is_gallery=True, is_public=True
    )
    _hide(PermEntity.ROMS, rom.id, viewer_user.id)

    response = client.get(
        f"/api/screenshots/{screenshot.id}/content",
        headers=_auth(viewer_access_token),
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_hidden_platform_masks_public_screenshot_download(
    client,
    viewer_access_token: str,
    viewer_user: User,
    admin_user: User,
    rom: Rom,
    platform: Platform,
):
    # Hiding the parent platform cascades to its screenshots as well.
    screenshot = _add_screenshot(
        rom, platform, admin_user.id, "shot", is_gallery=True, is_public=True
    )
    _hide(PermEntity.PLATFORMS, platform.id, viewer_user.id)

    response = client.get(
        f"/api/screenshots/{screenshot.id}/content",
        headers=_auth(viewer_access_token),
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_download_screenshot_not_found(client, access_token: str):
    response = client.get("/api/screenshots/99999/content", headers=_auth(access_token))
    assert response.status_code == status.HTTP_404_NOT_FOUND
