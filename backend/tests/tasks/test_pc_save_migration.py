from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import zipfile

import pytest
from tests._zipfile_shim import reload_zipfile

from handler.filesystem import fs_asset_handler, fs_resource_handler
from models.assets import Save
from tasks import pc_save_migration as subject


def _save(tmp_path: Path, filename: str = "slot.sav") -> Save:
    save = Save(
        id=7,
        file_name=filename,
        file_name_no_tags=Path(filename).stem,
        file_name_no_ext=Path(filename).stem,
        file_extension=Path(filename).suffix.lstrip("."),
        file_path="users/test/saves/windows/7",
        file_size_bytes=0,
        rom_id=7,
        user_id=1,
        emulator="retroarch",
    )
    save.__dict__["rom"] = SimpleNamespace(fs_resources_path="roms/7/stable")
    return save


@pytest.fixture
def storage_roots(tmp_path, monkeypatch):
    asset_root = tmp_path / "assets"
    resource_root = tmp_path / "resources"
    asset_root.mkdir()
    resource_root.mkdir()
    monkeypatch.setattr(fs_asset_handler, "base_path", asset_root)
    monkeypatch.setattr(fs_resource_handler, "base_path", resource_root)
    return asset_root, resource_root


def _write_legacy(asset, root: Path, content: bytes) -> Path:
    source = root / asset.full_path
    source.parent.mkdir(parents=True)
    source.write_bytes(content)
    return source


@pytest.mark.parametrize("content", [b"opaque raw bytes", b"PK\x03\x04opaque zip bytes"])
def test_migrates_bytes_without_transforming_them(storage_roots, content):
    asset_root, resource_root = storage_roots
    save = _save(resource_root)
    source = _write_legacy(save, asset_root, content)

    with mock.patch.object(subject.db_save_handler, "update_save") as update:
        assert subject._migrate_one(save) is True

    canonical = resource_root / subject._canonical_path(save)
    assert canonical.read_bytes() == content
    assert source.read_bytes() == content
    update.assert_called_once_with(
        save.id, {"file_path": subject._canonical_directory(save)}
    )


def test_zip_archive_round_trip_is_lossless(storage_roots):
    asset_root, resource_root = storage_roots
    reload_zipfile()
    save = _save(resource_root, "save.zip")
    payload = BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("save.bin", b"opaque\x00bytes")
    source = _write_legacy(save, asset_root, payload.getvalue())

    with mock.patch.object(subject.db_save_handler, "update_save"):
        subject._migrate_one(save)

    assert (resource_root / subject._canonical_path(save)).read_bytes() == source.read_bytes()


def test_existing_identical_canonical_file_is_retryable_and_idempotent(storage_roots):
    asset_root, resource_root = storage_roots
    save = _save(resource_root)
    source = _write_legacy(save, asset_root, b"same bytes")
    canonical = resource_root / subject._canonical_path(save)
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(source.read_bytes())

    with mock.patch.object(subject.db_save_handler, "update_save") as update:
        assert subject._migrate_one(save) is True
        assert subject._migrate_one(save) is True
    assert update.call_count == 2
    assert source.exists()


def test_mismatch_preserves_legacy_and_does_not_overwrite_canonical(storage_roots):
    asset_root, resource_root = storage_roots
    save = _save(resource_root)
    source = _write_legacy(save, asset_root, b"legacy")
    canonical = resource_root / subject._canonical_path(save)
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"different")

    with pytest.raises(ValueError):
        subject._migrate_one(save)

    assert source.read_bytes() == b"legacy"
    assert canonical.read_bytes() == b"different"


def test_database_failure_leaves_both_files_for_retry(storage_roots):
    asset_root, resource_root = storage_roots
    save = _save(resource_root)
    source = _write_legacy(save, asset_root, b"retry me")

    with mock.patch.object(
        subject.db_save_handler, "update_save", side_effect=RuntimeError("db down")
    ):
        with pytest.raises(RuntimeError):
            subject._migrate_one(save)

    canonical = resource_root / subject._canonical_path(save)
    assert source.read_bytes() == b"retry me"
    assert canonical.read_bytes() == b"retry me"

    with mock.patch.object(subject.db_save_handler, "update_save") as update:
        assert subject._migrate_one(save) is True
    update.assert_called_once()


def test_copy_failure_preserves_source_and_cleans_temp(storage_roots, monkeypatch):
    asset_root, resource_root = storage_roots
    save = _save(resource_root)
    source = _write_legacy(save, asset_root, b"do not lose")

    def fail_copy(*args, **kwargs):
        raise OSError("copy interrupted")

    monkeypatch.setattr(subject.shutil, "copyfileobj", fail_copy)
    with pytest.raises(OSError):
        subject._migrate_one(save)

    assert source.read_bytes() == b"do not lose"
    target_dir = resource_root / subject._canonical_directory(save)
    assert list(target_dir.glob(".*-migration-*")) == []
