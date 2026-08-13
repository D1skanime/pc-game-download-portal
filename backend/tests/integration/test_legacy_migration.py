import hashlib
import os
import stat
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import select

from exceptions.storage_read import StaleMappedReadError
from handler.database.base_handler import sync_session
from handler.database.legacy_migration_handler import (
    DBLegacyMigrationHandler,
    LegacyRollbackError,
)
from handler.filesystem.storage_policy import StorageOperation
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
    for item in sorted(root.rglob("*"), key=lambda value: value.as_posix().encode()):
        metadata = item.lstat()
        entries.append(
            (
                item.relative_to(root).as_posix(),
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


def _seed_migrated_mapping(source: Path, *, suffix: str = "one") -> tuple[int, int]:
    mapped = source / "mapped"
    mapped.mkdir(parents=True)
    (mapped / "game.bin").write_bytes(b"immutable game")
    now = datetime(2026, 8, 12, 20, tzinfo=timezone.utc)
    with sync_session.begin() as session:
        platform = Platform(
            name=f"First Use {suffix}",
            slug=f"first-use-{suffix}",
            fs_slug=f"first-use-{suffix}",
        )
        root = StorageRoot(name=f"Archive {suffix}", container_path=str(source))
        session.add_all([platform, root])
        session.flush()
        mapping = PlatformStorageMapping(
            platform_id=platform.id,
            storage_root_id=root.id,
            relative_path="mapped",
            active=True,
            version=1,
        )
        session.add(mapping)
        session.flush()
        detection = LegacyDetectionResult(
            platform_id=platform.id,
            storage_root_id=root.id,
            state="detected",
            proposed_relative_path="mapped",
            observed_files=1,
            observed_bytes=14,
            lower_bound=False,
            selectable=True,
            source_fingerprint="a" * 64,
            version=2,
            actor_user_id=7,
            completed_at=now,
            expires_at=now + timedelta(hours=24),
        )
        session.add(detection)
        session.flush()
        migration = LegacyMigration(
            detection_result_id=detection.id,
            platform_id=platform.id,
            storage_root_id=root.id,
            mapping_id=mapping.id,
            relative_path="mapped",
            state="completed",
            version=1,
            actor_user_id=7,
            reconnected_catalog_count=0,
            unmatched_catalog_count=0,
            completed_at=now,
            expires_at=now + timedelta(hours=24),
        )
        session.add(migration)
        session.flush()
        return mapping.id, migration.id


def _healthy_root(*_args, **_kwargs):
    return SimpleNamespace(reachable=True, readable=True, non_writable=True)


def _seed_exact_rollback(
    source: Path, *, suffix: str
) -> tuple[int, int, int, dict[str, int]]:
    mapped = source / "mapped"
    mapped.mkdir(parents=True)
    (mapped / "changed.bin").write_bytes(b"immutable game")
    now = datetime(2026, 8, 12, 20, tzinfo=timezone.utc)
    with sync_session.begin() as session:
        platform = Platform(
            name=f"Exact Rollback {suffix}",
            slug=f"exact-rollback-{suffix}",
            fs_slug=f"exact-rollback-{suffix}",
        )
        root = StorageRoot(name=f"Archive {suffix}", container_path=str(source))
        session.add_all([platform, root])
        session.flush()
        mapping = PlatformStorageMapping(
            platform_id=platform.id,
            storage_root_id=root.id,
            relative_path="mapped",
            active=True,
            version=1,
        )
        session.add(mapping)
        session.flush()
        roms: dict[str, Rom] = {}
        files: dict[str, RomFile] = {}
        for name, missing in (
            ("changed", False),
            ("already-visible", False),
            ("unmatched-missing", True),
        ):
            rom = Rom(
                platform_id=platform.id,
                fs_name=f"{name}.bin",
                fs_name_no_tags=name,
                fs_name_no_ext=name,
                fs_extension="bin",
                fs_path="mapped",
                fs_size_bytes=1,
                name=name,
                missing_from_fs=missing,
            )
            session.add(rom)
            session.flush()
            rom_file = RomFile(
                rom_id=rom.id,
                file_name=rom.fs_name,
                file_path=rom.fs_path,
                file_size_bytes=1,
                missing_from_fs=missing,
            )
            session.add(rom_file)
            roms[name] = rom
            files[name] = rom_file
        detection = LegacyDetectionResult(
            platform_id=platform.id,
            storage_root_id=root.id,
            state="detected",
            proposed_relative_path="mapped",
            observed_files=1,
            observed_bytes=14,
            lower_bound=False,
            selectable=True,
            source_fingerprint="a" * 64,
            version=2,
            actor_user_id=7,
            completed_at=now,
            expires_at=now + timedelta(hours=24),
        )
        session.add(detection)
        session.flush()
        migration = LegacyMigration(
            detection_result_id=detection.id,
            platform_id=platform.id,
            storage_root_id=root.id,
            mapping_id=mapping.id,
            relative_path="mapped",
            state="completed",
            version=1,
            actor_user_id=7,
            reconnected_catalog_count=1,
            unmatched_catalog_count=2,
            completed_at=now,
            expires_at=now + timedelta(hours=24),
            catalog_changes=[
                LegacyMigrationCatalogChange(
                    entity_kind=LegacyCatalogEntityKind.ROM.value,
                    entity_id=roms["changed"].id,
                    prior_missing_from_fs=True,
                ),
                LegacyMigrationCatalogChange(
                    entity_kind=LegacyCatalogEntityKind.ROM_FILE.value,
                    entity_id=files["changed"].id,
                    prior_missing_from_fs=True,
                ),
            ],
        )
        session.add(migration)
        session.flush()
        ids = {
            "changed_rom": roms["changed"].id,
            "changed_file": files["changed"].id,
            "visible_rom": roms["already-visible"].id,
            "visible_file": files["already-visible"].id,
            "missing_rom": roms["unmatched-missing"].id,
            "missing_file": files["unmatched-missing"].id,
        }
        return mapping.id, migration.id, platform.id, ids


def _catalog_states(ids: dict[str, int]) -> dict[str, bool | None]:
    with sync_session() as session:
        return {
            key: (
                row.missing_from_fs
                if (
                    row := session.get(RomFile if key.endswith("file") else Rom, row_id)
                )
                is not None
                else None
            )
            for key, row_id in ids.items()
        }


@pytest.fixture(autouse=True)
def _approve_external_read_only(monkeypatch):
    from handler.filesystem import storage_resolver

    monkeypatch.setattr(
        storage_resolver.os,
        "access",
        lambda _path, mode: mode != os.W_OK,
    )


@pytest.mark.parametrize(
    ("operation", "relative_path", "expected_marker"),
    [
        (StorageOperation.SCAN, "", "scan"),
        (StorageOperation.HASH, "game.bin", "hash"),
        (StorageOperation.STREAM, "game.bin", "stream"),
        (StorageOperation.READ, "game.bin", "play"),
        (StorageOperation.DOWNLOAD, "game.bin", "download"),
    ],
)
def test_productive_first_use_precedes_source_open(
    tmp_path: Path,
    operation: StorageOperation,
    relative_path: str,
    expected_marker: str,
):
    source = tmp_path / "external"
    mapping_id, migration_id = _seed_migrated_mapping(source)
    before = _manifest(source)

    from handler.storage import read_context

    real_open = read_context.open_storage_access

    def assert_marker_then_open(*args, **kwargs):
        with sync_session() as session:
            migration = session.get(LegacyMigration, migration_id)
            assert migration is not None
            assert migration.first_used_at is not None
            assert migration.first_use_operation == expected_marker
        return real_open(*args, **kwargs)

    with (
        patch(
            "handler.storage.read_context.get_storage_root_health_snapshot",
            side_effect=_healthy_root,
        ),
        patch(
            "handler.storage.read_context.open_storage_access",
            side_effect=assert_marker_then_open,
        ),
    ):
        access = MappingReadContext(mapping_id, 1).open(operation, relative_path)
        access.close()

    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        assert migration is not None
        assert migration.first_used_at is not None
        assert migration.first_use_operation == expected_marker
        assert migration.version == 2
    assert _manifest(source) == before


def test_first_use_revalidates_revision_after_marker_before_source_open(
    tmp_path: Path,
):
    source = tmp_path / "external"
    mapping_id, migration_id = _seed_migrated_mapping(source)
    root = SimpleNamespace(
        id=31,
        active=True,
        mode="external_read_only",
        container_path=str(source),
    )

    class RevisionRepository:
        calls = 0

        def get_mapping(self, requested_mapping_id: int):
            assert requested_mapping_id == mapping_id
            self.calls += 1
            return SimpleNamespace(
                id=mapping_id,
                version=1 if self.calls == 1 else 2,
                active=True,
                storage_root_id=root.id,
                storage_root=root,
                relative_path="mapped",
            )

    repository = RevisionRepository()
    with (
        patch(
            "handler.storage.read_context.get_storage_root_health_snapshot",
            side_effect=_healthy_root,
        ),
        patch("handler.storage.read_context.open_storage_access") as source_open,
        pytest.raises(StaleMappedReadError),
    ):
        MappingReadContext(mapping_id, 1, repository=repository).open(
            StorageOperation.DOWNLOAD, "game.bin"
        )

    assert repository.calls >= 2
    source_open.assert_not_called()
    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        assert migration is not None
        assert migration.first_use_operation == "download"
        assert migration.first_used_at is not None


def test_concurrent_consumer_cas_records_one_durable_marker(tmp_path: Path):
    source = tmp_path / "external"
    mapping_id, migration_id = _seed_migrated_mapping(source)
    before = _manifest(source)
    workers = 6
    barrier = threading.Barrier(workers + 1)

    def mark_first_use():
        barrier.wait()
        DBLegacyMigrationHandler().mark_first_use(
            mapping_id,
            expected_revision=1,
            operation="download",
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(mark_first_use) for _ in range(workers)]
        barrier.wait()
        for future in futures:
            future.result(timeout=10)

    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        assert migration is not None
        assert migration.first_use_operation == "download"
        assert migration.first_used_at is not None
        assert migration.version == 2
    assert _manifest(source) == before


@pytest.mark.parametrize("read_only", [False, True])
def test_first_use_preserves_writable_and_read_only_source_manifests(
    tmp_path: Path, read_only: bool
):
    source = tmp_path / "external"
    mapping_id, _ = _seed_migrated_mapping(source)
    if read_only:
        (source / "mapped" / "game.bin").chmod(0o444)
        (source / "mapped").chmod(0o555)
        source.chmod(0o555)
    before = _manifest(source)

    with patch(
        "handler.storage.read_context.get_storage_root_health_snapshot",
        side_effect=_healthy_root,
    ):
        access = MappingReadContext(mapping_id, 1).open(
            StorageOperation.DOWNLOAD, "game.bin"
        )
        access.close()

    assert _manifest(source) == before


def test_productive_consumer_cas_inventory_uses_the_shared_open_boundary():
    read_context = Path("handler/storage/read_context.py").read_text()
    scan = Path("handler/scan_handler.py").read_text()
    rom_filesystem = Path("handler/filesystem/roms_handler.py").read_text()
    streaming = Path("endpoints/streaming.py").read_text()
    roms = Path("endpoints/roms/__init__.py").read_text()
    files = Path("endpoints/roms/files.py").read_text()

    assert "mark_first_use" in read_context
    assert "StorageOperation.SCAN" in scan
    assert 'first_use_operation="scan"' in scan
    assert "context.open(StorageOperation.HASH" in rom_filesystem
    assert "context.open(StorageOperation.STREAM" in streaming
    assert 'first_use_operation="play"' in roms
    assert 'first_use_operation: str = "download"' in files
    assert "first_use_operation=first_use_operation" in files
    assert "for rom, file, download_name in items" in roms
    assert "context.open(" in roms


@pytest.mark.parametrize("read_only", [False, True])
def test_unused_migration_rollback_is_atomic_and_source_neutral(
    tmp_path: Path, read_only: bool
):
    source = tmp_path / "external"
    suffix = "rollback-read-only" if read_only else "rollback-writable"
    mapping_id, migration_id = _seed_migrated_mapping(source, suffix=suffix)
    if read_only:
        (source / "mapped" / "game.bin").chmod(0o444)
        (source / "mapped").chmod(0o555)
        source.chmod(0o555)
    before = _manifest(source)
    handler = DBLegacyMigrationHandler()
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        assert mapping is not None
        platform_id = mapping.platform_id

    status = handler.get_rollback_status(migration_id, platform_id=platform_id)
    assert status.rollback_eligible
    assert not status.first_used
    outcome = handler.rollback_migration(
        migration_id,
        platform_id=platform_id,
        expected_version=1,
        actor_user_id=7,
        actor_display_name="Admin",
        now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
    )
    assert outcome.state == "rolled_back"
    assert outcome.migration_version == 2
    assert not outcome.rollback_eligible
    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        mapping = session.get(PlatformStorageMapping, mapping_id)
        audit = session.scalar(
            select(StorageMappingAudit)
            .where(StorageMappingAudit.mapping_id == mapping_id)
            .order_by(StorageMappingAudit.id.desc())
        )
        assert migration is not None and migration.rolled_back_at is not None
        assert mapping is not None and not mapping.active and mapping.version == 2
        assert audit is not None
        assert audit.action == StorageMappingAuditAction.REMOVE
    assert _manifest(source) == before

    persisted = DBLegacyMigrationHandler().get_rollback_status(
        migration_id, platform_id=platform_id
    )
    assert persisted.state == "rolled_back"
    assert persisted.migration_version == 2
    assert not persisted.rollback_eligible


@pytest.mark.parametrize("read_only", [False, True])
def test_exact_rollback_restores_only_recorded_rows_and_preserves_later_rows(
    tmp_path: Path, read_only: bool
):
    source = tmp_path / "external"
    suffix = "exact-read-only" if read_only else "exact-writable"
    _, migration_id, platform_id, ids = _seed_exact_rollback(source, suffix=suffix)
    with sync_session.begin() as session:
        later = Rom(
            platform_id=platform_id,
            fs_name="later.bin",
            fs_name_no_tags="later",
            fs_name_no_ext="later",
            fs_extension="bin",
            fs_path="mapped",
            fs_size_bytes=1,
            name="later",
            missing_from_fs=False,
        )
        session.add(later)
        session.flush()
        later_file = RomFile(
            rom_id=later.id,
            file_name=later.fs_name,
            file_path=later.fs_path,
            file_size_bytes=1,
            missing_from_fs=False,
        )
        session.add(later_file)
        session.flush()
        ids.update(later_rom=later.id, later_file=later_file.id)
    if read_only:
        (source / "mapped" / "changed.bin").chmod(0o444)
        (source / "mapped").chmod(0o555)
        source.chmod(0o555)
    before_source = _manifest(source)

    outcome = DBLegacyMigrationHandler().rollback_migration(
        migration_id,
        platform_id=platform_id,
        expected_version=1,
        actor_user_id=7,
        actor_display_name="Admin",
        now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
    )

    assert outcome.state == "rolled_back"
    assert _catalog_states(ids) == {
        "changed_rom": True,
        "changed_file": True,
        "visible_rom": False,
        "visible_file": False,
        "missing_rom": True,
        "missing_file": True,
        "later_rom": False,
        "later_file": False,
    }
    assert _manifest(source) == before_source


@pytest.mark.parametrize("mutation", ["changed", "deleted", "cross-platform"])
def test_exact_rollback_rejects_stale_recorded_rows_atomically(
    tmp_path: Path, mutation: str
):
    source = tmp_path / "external"
    mapping_id, migration_id, platform_id, ids = _seed_exact_rollback(
        source, suffix=f"stale-{mutation}"
    )
    with sync_session.begin() as session:
        if mutation == "changed":
            row = session.get(Rom, ids["changed_rom"])
            assert row is not None
            row.missing_from_fs = True
        elif mutation == "deleted":
            row = session.get(RomFile, ids["changed_file"])
            assert row is not None
            session.delete(row)
        else:
            foreign_platform = Platform(
                name="Foreign Exact Rollback",
                slug=f"foreign-exact-rollback-{migration_id}",
                fs_slug=f"foreign-exact-rollback-{migration_id}",
            )
            session.add(foreign_platform)
            session.flush()
            foreign_rom = Rom(
                platform_id=foreign_platform.id,
                fs_name="foreign.bin",
                fs_name_no_tags="foreign",
                fs_name_no_ext="foreign",
                fs_extension="bin",
                fs_path="mapped",
                fs_size_bytes=1,
                name="foreign",
                missing_from_fs=False,
            )
            session.add(foreign_rom)
            session.flush()
            change = session.scalar(
                select(LegacyMigrationCatalogChange).where(
                    LegacyMigrationCatalogChange.migration_id == migration_id,
                    LegacyMigrationCatalogChange.entity_kind
                    == LegacyCatalogEntityKind.ROM.value,
                )
            )
            assert change is not None
            change.entity_id = foreign_rom.id
    before = _catalog_states(ids)

    with pytest.raises(LegacyRollbackError) as captured:
        DBLegacyMigrationHandler().rollback_migration(
            migration_id,
            platform_id=platform_id,
            expected_version=1,
            actor_user_id=7,
            actor_display_name="Admin",
            now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
        )

    assert captured.value.code == "legacy_rollback_stale"
    assert _catalog_states(ids) == before
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        migration = session.get(LegacyMigration, migration_id)
        audits = list(
            session.scalars(
                select(StorageMappingAudit).where(
                    StorageMappingAudit.mapping_id == mapping_id
                )
            )
        )
        assert mapping is not None and mapping.active and mapping.version == 1
        assert migration is not None and migration.state == "completed"
        assert migration.version == 1
        assert audits == []


def test_exact_rollback_catalog_flush_failure_restores_pre_attempt_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "external"
    mapping_id, migration_id, platform_id, ids = _seed_exact_rollback(
        source, suffix="catalog-flush"
    )
    before = _catalog_states(ids)
    handler = DBLegacyMigrationHandler()

    def fail(stage: str) -> None:
        if stage == "rollback_catalog":
            raise RuntimeError("injected exact catalog failure")

    monkeypatch.setattr(handler, "_after_migration_flush", fail)
    with pytest.raises(RuntimeError, match="injected exact catalog failure"):
        handler.rollback_migration(
            migration_id,
            platform_id=platform_id,
            expected_version=1,
            actor_user_id=7,
            actor_display_name="Admin",
            now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
        )

    assert _catalog_states(ids) == before
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        migration = session.get(LegacyMigration, migration_id)
        assert mapping is not None and mapping.active and mapping.version == 1
        assert migration is not None and migration.state == "completed"
        assert migration.version == 1

    monkeypatch.setattr(handler, "_after_migration_flush", lambda _stage: None)
    retry = handler.rollback_migration(
        migration_id,
        platform_id=platform_id,
        expected_version=1,
        actor_user_id=7,
        actor_display_name="Admin",
        now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
    )
    assert retry.state == "rolled_back"
    assert _catalog_states(ids) == {
        **before,
        "changed_rom": True,
        "changed_file": True,
    }


def test_first_use_makes_rollback_ineligible_with_stable_error(tmp_path: Path):
    source = tmp_path / "external"
    mapping_id, migration_id = _seed_migrated_mapping(source, suffix="used")
    handler = DBLegacyMigrationHandler()
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        assert mapping is not None
        platform_id = mapping.platform_id
    handler.mark_first_use(
        mapping_id,
        expected_revision=1,
        operation="download",
        now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
    )
    with pytest.raises(LegacyRollbackError) as captured:
        handler.rollback_migration(
            migration_id,
            platform_id=platform_id,
            expected_version=2,
            actor_user_id=7,
            actor_display_name="Admin",
            now=datetime(2026, 8, 12, 22, tzinfo=timezone.utc),
        )
    assert getattr(captured.value, "code", None) == "legacy_rollback_ineligible"
    status = handler.get_rollback_status(migration_id, platform_id=platform_id)
    assert status.first_used
    assert status.first_use_operation == "download"
    assert not status.rollback_eligible


def test_rollback_first_use_race_has_one_ordered_winner(tmp_path: Path):
    source = tmp_path / "external"
    mapping_id, migration_id = _seed_migrated_mapping(source, suffix="race")
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        assert mapping is not None
        platform_id = mapping.platform_id
    barrier = threading.Barrier(2)

    def rollback():
        barrier.wait(timeout=5)
        try:
            DBLegacyMigrationHandler().rollback_migration(
                migration_id,
                platform_id=platform_id,
                expected_version=1,
                actor_user_id=7,
                actor_display_name="Admin",
                now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
            )
            return "rollback"
        except LegacyRollbackError as error:
            return getattr(error, "code", "rollback-error")

    def first_use():
        barrier.wait(timeout=5)
        try:
            DBLegacyMigrationHandler().mark_first_use(
                mapping_id,
                expected_revision=1,
                operation="download",
                now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
            )
            return "use"
        except StaleMappedReadError:
            return "stale-read"

    with ThreadPoolExecutor(max_workers=2) as executor:
        rollback_future = executor.submit(rollback)
        use_future = executor.submit(first_use)
        outcomes = {rollback_future.result(), use_future.result()}
    assert outcomes in (
        {"rollback", "stale-read"},
        {"use", "legacy_rollback_stale"},
        {"use", "legacy_rollback_ineligible"},
    )


@pytest.mark.parametrize(
    "failure_stage",
    ["rollback_mapping", "rollback_catalog", "rollback_audit", "rollback_state"],
)
def test_rollback_failure_is_atomic_and_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_stage: str
):
    source = tmp_path / "external"
    mapping_id, migration_id = _seed_migrated_mapping(
        source, suffix=f"failure-{failure_stage}"
    )
    before = _manifest(source)
    handler = DBLegacyMigrationHandler()
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        assert mapping is not None
        platform_id = mapping.platform_id

    def fail(stage: str) -> None:
        if stage == failure_stage:
            raise RuntimeError(f"injected {failure_stage} failure")

    monkeypatch.setattr(handler, "_after_migration_flush", fail)
    with pytest.raises(RuntimeError, match=f"injected {failure_stage} failure"):
        handler.rollback_migration(
            migration_id,
            platform_id=platform_id,
            expected_version=1,
            actor_user_id=7,
            actor_display_name="Admin",
            now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
        )

    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        mapping = session.get(PlatformStorageMapping, mapping_id)
        audits = list(
            session.scalars(
                select(StorageMappingAudit).where(
                    StorageMappingAudit.mapping_id == mapping_id
                )
            )
        )
        assert migration is not None
        assert migration.state == "completed"
        assert migration.version == 1
        assert migration.rolled_back_at is None
        assert mapping is not None and mapping.active and mapping.version == 1
        assert audits == []
    assert _manifest(source) == before

    monkeypatch.setattr(handler, "_after_migration_flush", lambda _stage: None)
    retry = handler.rollback_migration(
        migration_id,
        platform_id=platform_id,
        expected_version=1,
        actor_user_id=7,
        actor_display_name="Admin",
        now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
    )
    assert retry.state == "rolled_back"
    assert _manifest(source) == before


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing", "legacy_rollback_missing"),
        ("cross_platform", "legacy_rollback_cross_platform"),
        ("stale", "legacy_rollback_stale"),
        ("expired", "legacy_rollback_expired"),
        ("replayed", "legacy_rollback_stale"),
    ],
)
def test_rollback_identity_and_lifecycle_fail_closed(
    tmp_path: Path, mutation: str, expected_code: str
):
    source = tmp_path / "external"
    mapping_id, migration_id = _seed_migrated_mapping(
        source, suffix=f"reject-{mutation}"
    )
    handler = DBLegacyMigrationHandler()
    with sync_session.begin() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        migration = session.get(LegacyMigration, migration_id)
        assert mapping is not None and migration is not None
        platform_id = mapping.platform_id
        if mutation == "expired":
            migration.expires_at = datetime(2026, 8, 12, 20, tzinfo=timezone.utc)
        elif mutation == "replayed":
            migration.state = "rolled_back"
            migration.version = 2
            migration.rolled_back_at = datetime(2026, 8, 12, 20, tzinfo=timezone.utc)

    requested_id = migration_id + 999999 if mutation == "missing" else migration_id
    requested_platform = (
        platform_id + 999999 if mutation == "cross_platform" else platform_id
    )
    expected_version = (
        99 if mutation == "stale" else (2 if mutation == "replayed" else 1)
    )
    with pytest.raises(LegacyRollbackError) as captured:
        handler.rollback_migration(
            requested_id,
            platform_id=requested_platform,
            expected_version=expected_version,
            actor_user_id=7,
            actor_display_name="Admin",
            now=datetime(2026, 8, 12, 21, tzinfo=timezone.utc),
        )
    assert captured.value.code == expected_code
