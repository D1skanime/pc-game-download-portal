import hashlib
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from exceptions.storage_exceptions import StaleStorageMappingVersionError
from exceptions.storage_read import StaleMappedReadError
from handler.database import db_rom_handler, db_storage_handler
from handler.database.base_handler import sync_session
from handler.storage.read_context import MappingReadContext
from models.platform import Platform
from models.rom import Rom, RomFile
from models.storage import (
    PlatformStorageMapping,
    StorageMappingAudit,
    StorageMappingAuditAction,
    StorageRoot,
)


def _manifest(root: Path) -> tuple[tuple[object, ...], ...]:
    entries = []
    for item in sorted(root.rglob("*"), key=lambda value: str(value.relative_to(root))):
        metadata = item.lstat()
        entries.append(
            (
                str(item.relative_to(root)),
                stat.S_IFMT(metadata.st_mode),
                stat.S_IMODE(metadata.st_mode),
                metadata.st_size,
                (
                    hashlib.sha256(item.read_bytes()).hexdigest()
                    if item.is_file() and not item.is_symlink()
                    else None
                ),
                os.readlink(item) if item.is_symlink() else None,
            )
        )
    return tuple(entries)


def _seed_mapping(tmp_path: Path, *, rom_count: int = 2):
    source = tmp_path / "library"
    mapped = source / "pc"
    mapped.mkdir(parents=True)
    for index in range(rom_count):
        (mapped / f"game-{index}.bin").write_bytes(f"game-{index}".encode())
    with sync_session.begin() as session:
        platform = Platform(name="PC", slug="pc", fs_slug="pc")
        root = StorageRoot(name="Archive", container_path=str(source))
        session.add_all([platform, root])
        session.flush()
        mapping = PlatformStorageMapping(
            platform_id=platform.id,
            storage_root_id=root.id,
            relative_path="pc",
            active=True,
            version=1,
        )
        session.add(mapping)
        session.flush()
        roms = []
        for index in range(rom_count):
            rom = Rom(
                platform_id=platform.id,
                fs_name=f"game-{index}.bin",
                fs_name_no_tags=f"game-{index}",
                fs_name_no_ext=f"game-{index}",
                fs_extension="bin",
                fs_path="pc",
                fs_size_bytes=6,
                name=f"Game {index}",
                crc_hash=f"crc-{index}",
                md5_hash=f"md5-{index}",
                sha1_hash=f"sha1-{index}",
            )
            session.add(rom)
            session.flush()
            session.add(
                RomFile(
                    rom_id=rom.id,
                    file_name=rom.fs_name,
                    file_path=rom.fs_path,
                    file_size_bytes=6,
                    crc_hash=rom.crc_hash,
                    md5_hash=rom.md5_hash,
                    sha1_hash=rom.sha1_hash,
                )
            )
            roms.append(rom)
        session.flush()
        return mapping.id, platform.id, [rom.id for rom in roms], source


def test_confirmed_mapping_removal_retains_catalog_and_marks_it_unreachable(
    tmp_path: Path,
):
    mapping_id, platform_id, rom_ids, source = _seed_mapping(tmp_path)
    before = _manifest(source)
    consequences = db_storage_handler.preview_mapping_removal(
        mapping_id, expected_version=1
    )
    assert consequences.mapping_id == mapping_id
    assert consequences.platform_id == platform_id
    assert consequences.mapping_version == 1
    assert consequences.retained_visible_unreachable_catalog_count == 2
    assert consequences.preserves_metadata
    assert consequences.preserves_saves
    assert consequences.preserves_states
    assert consequences.preserves_play_history
    assert consequences.source_immutable
    assert consequences.cancels_mapping_work_at_safe_boundaries

    result = db_storage_handler.remove_mapping(
        mapping_id,
        expected_version=1,
        expected_unreachable_catalog_count=2,
        actor_user_id=7,
        actor_display_name="Admin",
    )
    assert result.mapping.id == mapping_id
    assert not result.mapping.active
    assert result.mapping.version == 2
    assert result.consequences.mapping_revision_invalidated
    with sync_session() as session:
        roms = session.scalars(select(Rom).where(Rom.id.in_(rom_ids))).all()
        files = session.scalars(
            select(RomFile).where(RomFile.rom_id.in_(rom_ids))
        ).all()
        audit = session.scalar(
            select(StorageMappingAudit)
            .where(StorageMappingAudit.mapping_id == mapping_id)
            .order_by(StorageMappingAudit.id.desc())
        )
        assert len(roms) == 2
        assert all(rom.missing_from_fs for rom in roms)
        assert all(file.missing_from_fs for file in files)
        assert audit is not None
        assert audit.action == StorageMappingAuditAction.REMOVE
    assert _manifest(source) == before


def test_mapping_removal_rejects_stale_and_changed_consequences(tmp_path: Path):
    mapping_id, platform_id, _, _ = _seed_mapping(tmp_path, rom_count=1)
    with pytest.raises(StaleStorageMappingVersionError):
        db_storage_handler.preview_mapping_removal(mapping_id, expected_version=2)
    preview = db_storage_handler.preview_mapping_removal(mapping_id, expected_version=1)
    with sync_session.begin() as session:
        session.add(
            Rom(
                platform_id=platform_id,
                fs_name="late.bin",
                fs_name_no_tags="late",
                fs_name_no_ext="late",
                fs_extension="bin",
                fs_path="pc",
                fs_size_bytes=1,
                name="Late",
            )
        )
    with pytest.raises(Exception) as error:
        db_storage_handler.remove_mapping(
            mapping_id,
            expected_version=1,
            expected_unreachable_catalog_count=(
                preview.retained_visible_unreachable_catalog_count
            ),
            actor_user_id=7,
            actor_display_name="Admin",
        )
    assert getattr(error.value, "code", None) == "storage_mapping_consequences_changed"


def test_mapping_removal_rolls_back_mapping_catalog_and_audit_on_failure(
    tmp_path: Path,
):
    mapping_id, _, rom_ids, _ = _seed_mapping(tmp_path, rom_count=1)
    with (
        patch.object(
            db_storage_handler,
            "_append_audit",
            side_effect=RuntimeError("injected failure"),
        ),
        pytest.raises(RuntimeError, match="injected failure"),
    ):
        db_storage_handler.remove_mapping(
            mapping_id,
            expected_version=1,
            expected_unreachable_catalog_count=1,
            actor_user_id=7,
            actor_display_name="Admin",
        )
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        rom = session.get(Rom, rom_ids[0])
        assert mapping is not None and mapping.active and mapping.version == 1
        assert rom is not None and not rom.missing_from_fs
        assert (
            session.scalar(
                select(StorageMappingAudit).where(
                    StorageMappingAudit.mapping_id == mapping_id
                )
            )
            is None
        )


def test_removed_revision_cancels_old_work_at_next_boundary(tmp_path: Path):
    mapping_id, _, _, _ = _seed_mapping(tmp_path, rom_count=1)
    context = MappingReadContext(mapping_id, 1)
    context.boundary()
    db_storage_handler.remove_mapping(
        mapping_id,
        expected_version=1,
        expected_unreachable_catalog_count=1,
        actor_user_id=7,
        actor_display_name="Admin",
    )
    with pytest.raises(StaleMappedReadError):
        context.boundary()


def test_reconnect_requires_exact_logical_identity_or_unique_complete_hashes(
    tmp_path: Path,
):
    _, platform_id, rom_ids, _ = _seed_mapping(tmp_path, rom_count=2)
    with sync_session.begin() as session:
        for rom_id in rom_ids:
            session.get(Rom, rom_id).missing_from_fs = True
    exact = db_rom_handler.get_matching_missing_rom(
        platform_id,
        logical_path="pc/game-0.bin",
        crc_hash=None,
        md5_hash=None,
        sha1_hash=None,
    )
    assert exact is not None and exact.id == rom_ids[0]
    assert (
        db_rom_handler.get_matching_missing_rom(
            platform_id,
            logical_path="other/game-0.bin",
            crc_hash=None,
            md5_hash=None,
            sha1_hash=None,
        )
        is None
    )
    assert (
        db_rom_handler.get_matching_missing_rom(
            platform_id,
            logical_path=None,
            crc_hash="crc-1",
            md5_hash=None,
            sha1_hash="sha1-1",
        )
        is None
    )
    hashed = db_rom_handler.get_matching_missing_rom(
        platform_id,
        logical_path=None,
        crc_hash="crc-1",
        md5_hash="md5-1",
        sha1_hash="sha1-1",
    )
    assert hashed is not None and hashed.id == rom_ids[1]
    with sync_session.begin() as session:
        session.add(
            Rom(
                platform_id=platform_id,
                fs_name="duplicate.bin",
                fs_name_no_tags="duplicate",
                fs_name_no_ext="duplicate",
                fs_extension="bin",
                fs_path="pc",
                fs_size_bytes=1,
                name="Duplicate",
                crc_hash="crc-1",
                md5_hash="md5-1",
                sha1_hash="sha1-1",
                missing_from_fs=True,
            )
        )
    assert (
        db_rom_handler.get_matching_missing_rom(
            platform_id,
            logical_path=None,
            crc_hash="crc-1",
            md5_hash="md5-1",
            sha1_hash="sha1-1",
        )
        is None
    )
