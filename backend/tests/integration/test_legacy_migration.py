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

from exceptions.storage_read import StaleMappedReadError
from handler.database.base_handler import sync_session
from handler.database.legacy_migration_handler import DBLegacyMigrationHandler
from handler.filesystem.storage_policy import StorageOperation
from handler.storage.read_context import MappingReadContext
from models.platform import Platform
from models.storage import (
    LegacyDetectionResult,
    LegacyMigration,
    PlatformStorageMapping,
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
    assert "context.open(StorageOperation.SCAN)" in scan
    assert "context.open(StorageOperation.HASH" in rom_filesystem
    assert "context.open(StorageOperation.STREAM" in streaming
    assert 'first_use_operation="play"' in roms
    assert 'first_use_operation="download"' in files
    assert "for rom, file, download_name in items" in roms
    assert "context.open(" in roms
