import hashlib
import os
import stat
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from exceptions.storage_exceptions import StaleStorageMappingVersionError
from exceptions.storage_read import StaleMappedReadError
from handler.database import db_rom_handler, db_storage_handler
from handler.database.base_handler import sync_session
from handler.storage.read_context import MappingReadContext
from models.platform import Platform
from models.rom import Rom, RomFile
from models.storage import (
    LegacyCatalogEntityKind,
    LegacyDetectionResult,
    LegacyMigration,
    LegacyMigrationCatalogChange,
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


def _seed_atomic_migration(tmp_path: Path, *, suffix: str = "one"):
    from handler.database.legacy_migration_handler import DBLegacyMigrationHandler
    from handler.filesystem.storage_composition import (
        OWNED_STORAGE_PATHS,
        StorageCompositionConfig,
        build_storage_composition,
    )
    from handler.storage.legacy_migration import detect_legacy_storage

    source = tmp_path / suffix / "library"
    canonical = source / "roms" / f"pc-{suffix}"
    canonical.mkdir(parents=True)
    (canonical / "unique.bin").write_bytes(b"unique")
    (canonical / "duplicate.bin").write_bytes(b"duplicate")
    now = datetime(2026, 8, 12, 15, tzinfo=timezone.utc)
    with sync_session.begin() as session:
        platform = Platform(
            name=f"PC {suffix}", slug=f"pc-{suffix}", fs_slug=f"pc-{suffix}"
        )
        root = StorageRoot(name=f"Archive {suffix}", container_path=str(source))
        session.add_all([platform, root])
        session.flush()
        roms = []
        for index, (name, fs_path) in enumerate(
            (
                ("unique.bin", platform.fs_slug),
                ("duplicate.bin", platform.fs_slug),
                ("", f"{platform.fs_slug}/duplicate.bin"),
            )
        ):
            rom = Rom(
                platform_id=platform.id,
                fs_name=name,
                fs_name_no_tags=name.removesuffix(".bin"),
                fs_name_no_ext=name.removesuffix(".bin"),
                fs_extension="bin",
                fs_path=fs_path,
                fs_size_bytes=index + 1,
                name=f"Catalog {suffix} {index}",
                missing_from_fs=True,
            )
            session.add(rom)
            session.flush()
            session.add(
                RomFile(
                    rom_id=rom.id,
                    file_name=name,
                    file_path=fs_path,
                    file_size_bytes=index + 1,
                    missing_from_fs=True,
                )
            )
            roms.append(rom)
        composition = build_storage_composition(
            StorageCompositionConfig(
                source,
                OWNED_STORAGE_PATHS,
                legacy_external_root_id=root.id,
            )
        )
        detected = detect_legacy_storage(
            composition.legacy_external,
            platform_id=platform.id,
            storage_root_id=root.id,
            fs_slug=platform.fs_slug,
        )
        result = LegacyDetectionResult(
            platform_id=platform.id,
            storage_root_id=root.id,
            state="detected",
            proposed_relative_path=f"roms/{platform.fs_slug}",
            observed_files=2,
            observed_bytes=15,
            lower_bound=False,
            selectable=True,
            safe_problem_code=None,
            source_fingerprint=detected.source_fingerprint,
            observed_mapping_id=None,
            observed_mapping_version=None,
            version=1,
            actor_user_id=7,
            completed_at=now,
            expires_at=now + timedelta(hours=24),
        )
        session.add(result)
        session.flush()
        platform_id = platform.id
        result_id = result.id
        rom_ids = [rom.id for rom in roms]
    handler = DBLegacyMigrationHandler()
    impact = handler.preview_migration_impact(
        result_id,
        platform_id=platform_id,
        expected_result_version=1,
        now=now,
    )
    assert impact.confirmation is not None
    return handler, impact.confirmation, now, rom_ids, source


def test_atomic_migrate_commits_mapping_catalog_audit_and_rollback_metadata(
    tmp_path: Path,
):
    handler, confirmation, now, rom_ids, source = _seed_atomic_migration(tmp_path)
    before = _manifest(source)

    outcome = handler.migrate_platform(
        confirmation,
        actor_user_id=7,
        actor_display_name="Admin",
        now=now,
    )

    assert outcome.state == "completed"
    assert outcome.reconnected_catalog_count == 1
    assert outcome.unmatched_catalog_count == 2
    assert outcome.source_immutable is True
    assert outcome.legacy_fallback_enabled is False
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, outcome.mapping_id)
        migration = session.get(LegacyMigration, outcome.migration_id)
        roms = list(session.scalars(select(Rom).where(Rom.id.in_(rom_ids))))
        files = list(
            session.scalars(select(RomFile).where(RomFile.rom_id.in_(rom_ids)))
        )
        audits = session.scalar(
            select(func.count(StorageMappingAudit.id)).where(
                StorageMappingAudit.mapping_id == outcome.mapping_id
            )
        )
        detection = session.get(LegacyDetectionResult, confirmation.detection_result_id)
        assert mapping is not None and mapping.active and mapping.version == 1
        assert migration is not None and migration.state == "completed"
        assert migration.mapping_id == mapping.id
        assert migration.reconnected_catalog_count == 1
        assert migration.unmatched_catalog_count == 2
        changes = list(
            session.scalars(
                select(LegacyMigrationCatalogChange)
                .where(
                    LegacyMigrationCatalogChange.migration_id == outcome.migration_id
                )
                .order_by(
                    LegacyMigrationCatalogChange.entity_kind,
                    LegacyMigrationCatalogChange.entity_id,
                )
            )
        )
        assert [
            (change.entity_kind, change.entity_id, change.prior_missing_from_fs)
            for change in changes
        ] == [
            (LegacyCatalogEntityKind.ROM.value, rom_ids[0], True),
            (LegacyCatalogEntityKind.ROM_FILE.value, files[0].id, True),
        ]
        assert audits == 1
        assert detection is not None and detection.version == 2
        assert [rom.missing_from_fs for rom in roms] == [False, True, True]
        assert [item.missing_from_fs for item in files] == [False, True, True]
    assert _manifest(source) == before


@pytest.mark.parametrize("failure_stage", ["mapping", "catalog", "audit", "rollback"])
def test_atomic_migrate_rolls_back_every_flushed_stage_and_retries_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_stage: str
):
    handler, confirmation, now, rom_ids, source = _seed_atomic_migration(
        tmp_path, suffix=failure_stage
    )
    before = _manifest(source)

    def fail_after_flush(stage: str) -> None:
        if stage == failure_stage:
            raise RuntimeError(f"injected {stage} failure")

    monkeypatch.setattr(
        handler, "_after_migration_flush", fail_after_flush, raising=False
    )
    with pytest.raises(RuntimeError, match=f"injected {failure_stage} failure"):
        handler.migrate_platform(
            confirmation,
            actor_user_id=7,
            actor_display_name="Admin",
            now=now,
        )

    with sync_session() as session:
        assert (
            session.scalar(
                select(func.count(PlatformStorageMapping.id)).where(
                    PlatformStorageMapping.platform_id == confirmation.platform_id
                )
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count(StorageMappingAudit.id)).where(
                    StorageMappingAudit.platform_id == confirmation.platform_id
                )
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count(LegacyMigration.id)).where(
                    LegacyMigration.detection_result_id
                    == confirmation.detection_result_id
                )
            )
            == 0
        )
        detection = session.get(LegacyDetectionResult, confirmation.detection_result_id)
        assert detection is not None and detection.version == 1
        assert all(
            row.missing_from_fs
            for row in session.scalars(select(Rom).where(Rom.id.in_(rom_ids)))
        )
    assert _manifest(source) == before

    monkeypatch.setattr(handler, "_after_migration_flush", lambda _stage: None)
    retry = handler.migrate_platform(
        confirmation,
        actor_user_id=7,
        actor_display_name="Admin",
        now=now,
    )
    assert retry.state == "completed"
    assert _manifest(source) == before


def test_migrate_race_has_one_atomic_winner(tmp_path: Path):
    from handler.database.legacy_migration_handler import (
        DBLegacyMigrationHandler,
        LegacyDetectionResultError,
    )

    _, confirmation, now, _, _ = _seed_atomic_migration(tmp_path, suffix="race")
    barrier = threading.Barrier(2)

    def attempt():
        barrier.wait(timeout=5)
        try:
            return DBLegacyMigrationHandler().migrate_platform(
                confirmation,
                actor_user_id=7,
                actor_display_name="Admin",
                now=now,
            )
        except LegacyDetectionResultError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _index: attempt(), range(2)))

    assert sum(getattr(item, "state", None) == "completed" for item in outcomes) == 1
    loser = next(
        item for item in outcomes if isinstance(item, LegacyDetectionResultError)
    )
    assert loser.code in {"legacy_detection_stale", "legacy_migration_conflict"}
    with sync_session() as session:
        assert (
            session.scalar(
                select(func.count(PlatformStorageMapping.id)).where(
                    PlatformStorageMapping.platform_id == confirmation.platform_id
                )
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count(StorageMappingAudit.id)).where(
                    StorageMappingAudit.platform_id == confirmation.platform_id
                )
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count(LegacyMigration.id)).where(
                    LegacyMigration.detection_result_id
                    == confirmation.detection_result_id
                )
            )
            == 1
        )


def test_failed_platform_migration_preserves_prior_platform_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    first_handler, first_confirmation, now, _, _ = _seed_atomic_migration(
        tmp_path, suffix="independent-first"
    )
    second_handler, second_confirmation, _, _, _ = _seed_atomic_migration(
        tmp_path, suffix="independent-second"
    )

    first = first_handler.migrate_platform(
        first_confirmation,
        actor_user_id=7,
        actor_display_name="Admin",
        now=now,
    )

    def fail_second(stage: str) -> None:
        if stage == "audit":
            raise RuntimeError("injected second-platform failure")

    monkeypatch.setattr(
        second_handler, "_after_migration_flush", fail_second, raising=False
    )
    with pytest.raises(RuntimeError, match="injected second-platform failure"):
        second_handler.migrate_platform(
            second_confirmation,
            actor_user_id=7,
            actor_display_name="Admin",
            now=now,
        )

    with sync_session() as session:
        assert session.get(PlatformStorageMapping, first.mapping_id) is not None
        assert session.get(LegacyMigration, first.migration_id) is not None
        assert (
            session.scalar(
                select(func.count(PlatformStorageMapping.id)).where(
                    PlatformStorageMapping.platform_id
                    == second_confirmation.platform_id
                )
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count(LegacyMigration.id)).where(
                    LegacyMigration.detection_result_id
                    == second_confirmation.detection_result_id
                )
            )
            == 0
        )


def test_migrate_create_race_has_one_lifecycle_winner(tmp_path: Path):
    from exceptions.storage_exceptions import DuplicateStorageMappingError
    from handler.database.legacy_migration_handler import (
        DBLegacyMigrationHandler,
        LegacyDetectionResultError,
    )

    _, confirmation, now, _, _ = _seed_atomic_migration(tmp_path, suffix="create-race")
    barrier = threading.Barrier(2)

    def migrate():
        barrier.wait(timeout=5)
        try:
            DBLegacyMigrationHandler().migrate_platform(
                confirmation,
                actor_user_id=7,
                actor_display_name="Admin",
                now=now,
            )
            return "migration"
        except LegacyDetectionResultError:
            return "migration-conflict"

    def create():
        barrier.wait(timeout=5)
        try:
            with patch(
                "handler.filesystem.storage_resolver.os.access",
                side_effect=lambda _path, mode: mode != os.W_OK,
            ):
                db_storage_handler.create_mapping(
                    confirmation.platform_id,
                    confirmation.storage_root_id,
                    confirmation.relative_path,
                    actor_user_id=8,
                    actor_display_name="Other Admin",
                )
            return "lifecycle"
        except DuplicateStorageMappingError:
            return "lifecycle-conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        migration = executor.submit(migrate)
        lifecycle = executor.submit(create)
        outcomes = {migration.result(), lifecycle.result()}

    assert outcomes in (
        {"migration", "lifecycle-conflict"},
        {"migration-conflict", "lifecycle"},
    )
    with sync_session() as session:
        assert (
            session.scalar(
                select(func.count(PlatformStorageMapping.id)).where(
                    PlatformStorageMapping.platform_id == confirmation.platform_id
                )
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count(StorageMappingAudit.id)).where(
                    StorageMappingAudit.platform_id == confirmation.platform_id
                )
            )
            == 1
        )
        migration_count = session.scalar(
            select(func.count(LegacyMigration.id)).where(
                LegacyMigration.detection_result_id == confirmation.detection_result_id
            )
        )
        assert migration_count == (1 if "migration" in outcomes else 0)


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
    with patch(
        "handler.filesystem.storage_resolver.os.access",
        side_effect=lambda _path, mode: mode != os.W_OK,
    ):
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


def _seed_retained_reconnect(
    admin_user,
    *,
    suffix: str,
    duplicate_identity: bool = False,
):
    from models.assets import Save, State
    from models.catalog_lifecycle import RetainedCatalogIdentity
    from models.play_session import PlaySession

    now = datetime.now(timezone.utc)
    with sync_session.begin() as session:
        platform = Platform(
            name=f"Reconnect {suffix}",
            slug=f"reconnect-{suffix}",
            fs_slug=f"reconnect-{suffix}",
        )
        session.add(platform)
        session.flush()
        retained = RetainedCatalogIdentity(
            platform_id=platform.id,
            detached_rom_id=7000,
            logical_path=platform.fs_slug,
            file_name="game.bin",
            crc_hash="a1b2c3d4",
            md5_hash="1" * 32,
            sha1_hash="2" * 40,
            detached_by_user_id=admin_user.id,
        )
        session.add(retained)
        if duplicate_identity:
            session.add(
                RetainedCatalogIdentity(
                    platform_id=platform.id,
                    detached_rom_id=7001,
                    logical_path=platform.fs_slug,
                    file_name="game.bin",
                    crc_hash="a1b2c3d4",
                    md5_hash="1" * 32,
                    sha1_hash="2" * 40,
                    detached_by_user_id=admin_user.id,
                )
            )
        session.flush()
        target = Rom(
            platform_id=platform.id,
            fs_name="game.bin",
            fs_path=platform.fs_slug,
            fs_size_bytes=1,
            name="Reconnected Game",
            crc_hash="a1b2c3d4",
            md5_hash="1" * 32,
            sha1_hash="2" * 40,
        )
        alternate = Rom(
            platform_id=platform.id,
            fs_name="alternate.bin",
            fs_path=platform.fs_slug,
            fs_size_bytes=1,
            name="Alternate Claim",
            crc_hash="a1b2c3d4",
            md5_hash="1" * 32,
            sha1_hash="2" * 40,
        )
        session.add_all([target, alternate])
        session.flush()
        save = Save(
            rom_id=None,
            retained_catalog_id=retained.id,
            user_id=admin_user.id,
            file_name="slot.srm",
            file_path="users/admin/saves/reconnect",
            file_size_bytes=1,
        )
        state = State(
            rom_id=None,
            retained_catalog_id=retained.id,
            user_id=admin_user.id,
            file_name="slot.state",
            file_path="users/admin/states/reconnect",
            file_size_bytes=1,
        )
        play = PlaySession(
            rom_id=None,
            retained_catalog_id=retained.id,
            user_id=admin_user.id,
            device_id=None,
            start_time=now,
            end_time=now,
            duration_ms=1,
        )
        session.add_all([save, state, play])
        session.flush()
        return {
            "platform_id": platform.id,
            "retained_id": retained.id,
            "target_id": target.id,
            "alternate_id": alternate.id,
            "save_id": save.id,
            "state_id": state.id,
            "play_id": play.id,
            "logical_path": f"{platform.fs_slug}/game.bin",
        }


def test_retained_identity_reconnects_all_user_value_atomically(admin_user):
    from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
    from models.assets import Save, State
    from models.catalog_lifecycle import RetainedCatalogIdentity
    from models.play_session import PlaySession

    seeded = _seed_retained_reconnect(admin_user, suffix="exact")
    result = CatalogLifecycleHandler().reconnect_retained_identity(
        rom_id=seeded["target_id"],
        platform_id=seeded["platform_id"],
        logical_path=seeded["logical_path"].replace("/", "\\"),
        crc_hash=None,
        md5_hash=None,
        sha1_hash=None,
    )

    assert result is not None and result.id == seeded["retained_id"]
    with sync_session() as session:
        retained = session.get(RetainedCatalogIdentity, seeded["retained_id"])
        save = session.get(Save, seeded["save_id"])
        state = session.get(State, seeded["state_id"])
        play = session.get(PlaySession, seeded["play_id"])
        assert retained is not None
        assert retained.active_rom_id == seeded["target_id"]
        assert retained.version == 2
        assert retained.reconnected_at is not None
        assert (save.rom_id, save.retained_catalog_id) == (
            seeded["target_id"],
            None,
        )
        assert (state.rom_id, state.retained_catalog_id) == (
            seeded["target_id"],
            None,
        )
        assert (play.rom_id, play.retained_catalog_id) == (
            seeded["target_id"],
            None,
        )


def test_retained_identity_rejects_weak_and_ambiguous_matches(admin_user):
    from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
    from models.catalog_lifecycle import RetainedCatalogIdentity

    seeded = _seed_retained_reconnect(
        admin_user, suffix="ambiguous", duplicate_identity=True
    )
    handler = CatalogLifecycleHandler()

    assert (
        handler.reconnect_retained_identity(
            rom_id=seeded["target_id"],
            platform_id=seeded["platform_id"],
            logical_path="different/game.bin",
            crc_hash="a1b2c3d4",
            md5_hash=None,
            sha1_hash="2" * 40,
        )
        is None
    )
    assert (
        handler.reconnect_retained_identity(
            rom_id=seeded["target_id"],
            platform_id=seeded["platform_id"],
            logical_path="different/game.bin",
            crc_hash="a1b2c3d4",
            md5_hash="1" * 32,
            sha1_hash="2" * 40,
        )
        is None
    )
    assert (
        handler.reconnect_retained_identity(
            rom_id=seeded["target_id"],
            platform_id=seeded["platform_id"],
            logical_path=seeded["logical_path"],
            crc_hash=None,
            md5_hash=None,
            sha1_hash=None,
        )
        is None
    )
    with sync_session() as session:
        identities = session.scalars(
            select(RetainedCatalogIdentity).where(
                RetainedCatalogIdentity.platform_id == seeded["platform_id"]
            )
        ).all()
        assert all(identity.active_rom_id is None for identity in identities)


def test_concurrent_retained_claim_has_one_winner_and_no_mixed_ownership(admin_user):
    from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
    from models.assets import Save, State
    from models.catalog_lifecycle import RetainedCatalogIdentity
    from models.play_session import PlaySession

    seeded = _seed_retained_reconnect(admin_user, suffix="race")
    barrier = threading.Barrier(2)

    def claim(rom_id: int):
        barrier.wait(timeout=5)
        return CatalogLifecycleHandler().reconnect_retained_identity(
            rom_id=rom_id,
            platform_id=seeded["platform_id"],
            logical_path=seeded["logical_path"],
            crc_hash="a1b2c3d4",
            md5_hash="1" * 32,
            sha1_hash="2" * 40,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(claim, [seeded["target_id"], seeded["alternate_id"]])
        )

    assert sum(result is not None for result in outcomes) == 1
    with sync_session() as session:
        retained = session.get(RetainedCatalogIdentity, seeded["retained_id"])
        winner = retained.active_rom_id
        assert winner in {seeded["target_id"], seeded["alternate_id"]}
        for model, row_id in (
            (Save, seeded["save_id"]),
            (State, seeded["state_id"]),
            (PlaySession, seeded["play_id"]),
        ):
            row = session.get(model, row_id)
            assert (row.rom_id, row.retained_catalog_id) == (winner, None)
