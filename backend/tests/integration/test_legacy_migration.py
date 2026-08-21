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
from fastapi import status
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import delete, select

from config import OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS
from exceptions.storage_read import StaleMappedReadError
from handler.auth import oauth_handler
from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.legacy_migration_handler import (
    DBLegacyMigrationHandler,
    LegacyRollbackError,
)
from handler.filesystem.storage_policy import StorageOperation
from handler.redis_handler import sync_cache
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
    now = datetime.now(timezone.utc).replace(microsecond=0)
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


def _seed_downloadable_migration(
    source: Path, *, suffix: str, user_id: int
) -> tuple[int, int, int]:
    mapping_id, migration_id = _seed_migrated_mapping(source, suffix=suffix)
    with sync_session() as session:
        mapping = session.get(PlatformStorageMapping, mapping_id)
        assert mapping is not None
        platform_id = mapping.platform_id
    rom = db_rom_handler.add_rom(
        Rom(
            platform_id=platform_id,
            name=f"Download {suffix}",
            slug=f"download-{suffix}",
            fs_name="game.bin",
            fs_name_no_tags="game",
            fs_name_no_ext="game",
            fs_extension="bin",
            fs_path="mapped",
            fs_size_bytes=14,
        )
    )
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=user_id)
    rom_file = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name="game.bin",
            file_path="mapped",
            file_size_bytes=14,
        )
    )
    return rom_file.id, mapping_id, migration_id


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _healthy_root(*_args, **_kwargs):
    return SimpleNamespace(reachable=True, readable=True, non_writable=True)


def _seed_exact_rollback(
    source: Path, *, suffix: str, now: datetime | None = None
) -> tuple[int, int, int, dict[str, int]]:
    mapped = source / "mapped"
    mapped.mkdir(parents=True)
    (mapped / "changed.bin").write_bytes(b"immutable game")
    now = now or datetime(2026, 8, 12, 20, tzinfo=timezone.utc)
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
                    entity_incarnation_token=roms["changed"].incarnation_token,
                    lineage_valid=True,
                ),
                LegacyMigrationCatalogChange(
                    entity_kind=LegacyCatalogEntityKind.ROM_FILE.value,
                    entity_id=files["changed"].id,
                    prior_missing_from_fs=True,
                    entity_incarnation_token=files["changed"].incarnation_token,
                    parent_rom_id=roms["changed"].id,
                    parent_incarnation_token=roms["changed"].incarnation_token,
                    lineage_valid=True,
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


def _assert_rollback_authority_unchanged(mapping_id: int, migration_id: int) -> None:
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


@pytest.fixture
def migration_endpoint_client(admin_user):
    sync_cache.flushall()
    token = oauth_handler.create_access_token(
        data={
            "sub": admin_user.username,
            "iss": "romm:oauth",
            "scopes": " ".join(admin_user.oauth_scopes),
        },
        expires_delta=timedelta(seconds=OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS),
    )
    with TestClient(app) as client:
        yield client, token
    sync_cache.flushall()


@pytest.fixture(autouse=True)
def _approve_external_read_only(monkeypatch):
    from handler.filesystem import storage_resolver

    monkeypatch.setattr(
        storage_resolver.os,
        "access",
        lambda _path, mode: mode != os.W_OK,
    )


def test_migration_reconnects_only_source_observed_rom_and_sidecar(
    tmp_path: Path, admin_user
):
    from dataclasses import asdict

    from handler.filesystem.storage_policy import _create_external_descriptor
    from handler.storage.legacy_migration import detect_legacy_storage
    from models.storage import LegacyDetectionSourceIdentity

    fs_slug = "exact-observed"
    canonical = tmp_path / "roms" / fs_slug
    (canonical / "art").mkdir(parents=True)
    (canonical / "present.gb").write_bytes(b"present")
    (canonical / "art" / "manual.txt").write_bytes(b"manual")
    before = _manifest(tmp_path)

    with sync_session.begin() as session:
        platform = Platform(
            name="Exact observed",
            slug="exact-observed",
            fs_slug=fs_slug,
        )
        other_platform = Platform(
            name="Exact observed other",
            slug="exact-observed-other",
            fs_slug="exact-observed-other",
        )
        root = StorageRoot(name="Exact observed archive", container_path=str(tmp_path))
        session.add_all([platform, other_platform, root])
        session.flush()

        def add_rom(
            name: str,
            *,
            path: str = fs_slug,
            owner_id: int = platform.id,
        ) -> Rom:
            rom = Rom(
                platform_id=owner_id,
                fs_name=name,
                fs_name_no_tags=name.rsplit(".", 1)[0],
                fs_name_no_ext=name.rsplit(".", 1)[0],
                fs_extension=name.rsplit(".", 1)[-1],
                fs_path=path,
                fs_size_bytes=1,
                name=name,
                missing_from_fs=True,
            )
            session.add(rom)
            session.flush()
            return rom

        present = add_rom("present.gb")
        absent = add_rom("absent.gb")
        ambiguous_one = add_rom("folder/duplicate.gb")
        ambiguous_two = add_rom("duplicate.gb", path=f"{fs_slug}/folder")
        unsafe = add_rom("unsafe.gb", path=f"{fs_slug}/..")
        case_distinct = add_rom("case/Present.gb")
        unicode_distinct = add_rom("unicode/présent.gb")
        cross_platform = add_rom(
            "present.gb", path=other_platform.fs_slug, owner_id=other_platform.id
        )
        present_child = RomFile(
            rom_id=present.id,
            file_name="manual.txt",
            file_path=f"{fs_slug}/art",
            file_size_bytes=6,
            missing_from_fs=True,
        )
        absent_child = RomFile(
            rom_id=present.id,
            file_name="absent.txt",
            file_path=f"{fs_slug}/art",
            file_size_bytes=1,
            missing_from_fs=True,
        )
        session.add_all([present_child, absent_child])
        session.flush()
        platform_id = platform.id
        root_id = root.id
        ids = {
            "present": present.id,
            "absent": absent.id,
            "ambiguous_one": ambiguous_one.id,
            "ambiguous_two": ambiguous_two.id,
            "unsafe": unsafe.id,
            "case_distinct": case_distinct.id,
            "unicode_distinct": unicode_distinct.id,
            "cross_platform": cross_platform.id,
            "present_child": present_child.id,
            "absent_child": absent_child.id,
        }

    handler = DBLegacyMigrationHandler()
    context = handler.get_detection_context(platform_id, root_id)
    detected = detect_legacy_storage(
        _create_external_descriptor(root_id, tmp_path),
        platform_id=platform_id,
        storage_root_id=root_id,
        fs_slug=fs_slug,
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    result = handler.save_detection_result(
        context, detected, actor_user_id=admin_user.id, now=now
    )
    impact = handler.preview_migration_impact(
        result.id,
        platform_id=platform_id,
        expected_result_version=1,
        now=now,
    )

    assert impact.state == "ready"
    assert impact.reconnectable_catalog_count == 1
    assert impact.unmatched_catalog_count == 6
    assert impact.planned_owned_effects.catalog_reconnect_count == 1
    assert impact.planned_owned_effects.catalog_preserve_unmatched_count == 6
    public_preview = str(asdict(impact))
    for private_value in (
        "present.gb",
        "manual.txt",
        "absent.gb",
        "absent.txt",
        detected.source_identity_digests[0].hex(),
    ):
        assert private_value not in public_preview

    outcome = handler.migrate_platform(
        impact.confirmation,
        actor_user_id=admin_user.id,
        actor_display_name=admin_user.username,
        now=now,
    )
    assert outcome.reconnected_catalog_count == 1
    assert outcome.unmatched_catalog_count == 6

    restarted = DBLegacyMigrationHandler()
    with sync_session() as session:
        rom_states = {
            key: session.get(Rom, row_id).missing_from_fs
            for key, row_id in ids.items()
            if not key.endswith("child")
        }
        file_states = {
            key: session.get(RomFile, ids[key]).missing_from_fs
            for key in ("present_child", "absent_child")
        }
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
        persisted_digests = tuple(
            row.identity_digest
            for row in session.scalars(
                select(LegacyDetectionSourceIdentity)
                .where(LegacyDetectionSourceIdentity.detection_result_id == result.id)
                .order_by(LegacyDetectionSourceIdentity.identity_digest)
            )
        )
    assert rom_states["present"] is False
    assert all(state is True for key, state in rom_states.items() if key != "present")
    assert file_states == {"present_child": False, "absent_child": True}
    assert [(change.entity_kind, change.entity_id) for change in changes] == [
        (LegacyCatalogEntityKind.ROM.value, ids["present"]),
        (LegacyCatalogEntityKind.ROM_FILE.value, ids["present_child"]),
    ]
    assert persisted_digests == tuple(
        digest.hex() for digest in detected.source_identity_digests
    )

    rollback = restarted.rollback_migration(
        outcome.migration_id,
        platform_id=platform_id,
        expected_version=1,
        actor_user_id=admin_user.id,
        actor_display_name=admin_user.username,
        now=now,
    )
    assert rollback.state == "rolled_back"
    with sync_session() as session:
        assert session.get(Rom, ids["present"]).missing_from_fs is True
        assert session.get(RomFile, ids["present_child"]).missing_from_fs is True
        assert session.get(RomFile, ids["absent_child"]).missing_from_fs is True
    assert _manifest(tmp_path) == before


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


def test_head_metadata_preserves_direct_rollback_eligibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    migration_endpoint_client: tuple[TestClient, str],
    admin_user,
):
    client, access_token = migration_endpoint_client
    source = tmp_path / "external-head"
    rom_file_id, mapping_id, migration_id = _seed_downloadable_migration(
        source, suffix="head", user_id=admin_user.id
    )
    before = _manifest(source)
    opened_fds: list[int] = []
    real_open = MappingReadContext.open

    def tracked_open(context, operation, relative_path="", **kwargs):
        access = real_open(context, operation, relative_path, **kwargs)
        opened_fds.append(access.fileno())
        return access

    monkeypatch.setattr(MappingReadContext, "open", tracked_open)
    response = client.head(
        f"/api/roms/{rom_file_id}/files/content/client-name.bin",
        headers={**_auth(access_token), "Range": "bytes=2-5"},
    )

    assert response.status_code == status.HTTP_206_PARTIAL_CONTENT
    assert response.headers["content-type"].startswith("application/octet-stream")
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == "4"
    assert response.headers["content-range"] == "bytes 2-5/14"
    assert opened_fds
    for descriptor in opened_fds:
        with pytest.raises(OSError):
            os.fstat(descriptor)
    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        assert migration is not None
        assert migration.first_used_at is None
        assert migration.first_use_operation is None
        assert migration.version == 1
        mapping = session.get(PlatformStorageMapping, mapping_id)
        assert mapping is not None
        platform_id = mapping.platform_id
    rollback = DBLegacyMigrationHandler().get_rollback_status(
        migration_id,
        platform_id=platform_id,
    )
    assert rollback.rollback_eligible
    assert not rollback.first_used
    assert _manifest(source) == before


def test_get_consumes_direct_rollback_eligibility(
    tmp_path: Path,
    migration_endpoint_client: tuple[TestClient, str],
    admin_user,
):
    client, access_token = migration_endpoint_client
    source = tmp_path / "external-get"
    rom_file_id, _mapping_id, migration_id = _seed_downloadable_migration(
        source, suffix="get", user_id=admin_user.id
    )
    before = _manifest(source)

    first = client.get(
        f"/api/roms/{rom_file_id}/files/content/client-name.bin",
        headers=_auth(access_token),
    )
    assert first.status_code == status.HTTP_200_OK
    assert first.content == b"immutable game"
    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        assert migration is not None
        first_used_at = migration.first_used_at
        assert first_used_at is not None
        assert migration.first_use_operation == "download"
        assert migration.version == 2

    second = client.get(
        f"/api/roms/{rom_file_id}/files/content/ignored-again.bin",
        headers=_auth(access_token),
    )
    assert second.status_code == status.HTTP_200_OK
    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        assert migration is not None
        assert migration.first_used_at == first_used_at
        assert migration.first_use_operation == "download"
        assert migration.version == 2
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


def test_rollback_rejects_same_platform_reparenting_atomically(tmp_path: Path):
    source = tmp_path / "external"
    mapping_id, migration_id, platform_id, ids = _seed_exact_rollback(
        source, suffix="same-platform-reparent"
    )
    with sync_session.begin() as session:
        replacement_parent = Rom(
            platform_id=platform_id,
            fs_name="replacement-parent.bin",
            fs_name_no_tags="replacement-parent",
            fs_name_no_ext="replacement-parent",
            fs_extension="bin",
            fs_path="mapped",
            fs_size_bytes=1,
            name="Replacement Parent",
            missing_from_fs=False,
        )
        session.add(replacement_parent)
        session.flush()
        changed_file = session.get(RomFile, ids["changed_file"])
        assert changed_file is not None
        changed_file.rom_id = replacement_parent.id
        session.flush()
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
    _assert_rollback_authority_unchanged(mapping_id, migration_id)


@pytest.mark.parametrize("replacement_kind", ["rom", "rom_file"])
def test_rollback_rejects_timestamp_colliding_row_replacement(
    tmp_path: Path, replacement_kind: str
):
    source = tmp_path / "external"
    mapping_id, migration_id, platform_id, ids = _seed_exact_rollback(
        source, suffix=f"timestamp-collision-{replacement_kind}"
    )
    with sync_session.begin() as session:
        rom = session.get(Rom, ids["changed_rom"])
        rom_file = session.get(RomFile, ids["changed_file"])
        assert rom is not None and rom_file is not None
        old_rom_token = rom.incarnation_token
        old_file_token = rom_file.incarnation_token
        rom_times = (rom.created_at, rom.updated_at)
        file_times = (rom_file.created_at, rom_file.updated_at)
        if replacement_kind == "rom_file":
            session.delete(rom_file)
            session.flush()
            replacement_file = RomFile(
                id=ids["changed_file"],
                rom_id=ids["changed_rom"],
                file_name="changed.bin",
                file_path="mapped",
                file_size_bytes=1,
                missing_from_fs=False,
                created_at=file_times[0],
                updated_at=file_times[1],
                incarnation_token=old_file_token,
            )
            session.add(replacement_file)
            session.flush()
            assert replacement_file.incarnation_token != old_file_token
        else:
            session.expunge(rom_file)
            session.expunge(rom)
            session.execute(
                delete(RomFile)
                .where(RomFile.id == ids["changed_file"])
                .execution_options(synchronize_session=False)
            )
            session.execute(
                delete(Rom)
                .where(Rom.id == ids["changed_rom"])
                .execution_options(synchronize_session=False)
            )
            session.flush()
            replacement_rom = Rom(
                id=ids["changed_rom"],
                platform_id=platform_id,
                fs_name="changed.bin",
                fs_name_no_tags="changed",
                fs_name_no_ext="changed",
                fs_extension="bin",
                fs_path="mapped",
                fs_size_bytes=1,
                name="changed",
                missing_from_fs=False,
                created_at=rom_times[0],
                updated_at=rom_times[1],
                incarnation_token=old_rom_token,
            )
            session.add(replacement_rom)
            session.flush()
            replacement_file = RomFile(
                id=ids["changed_file"],
                rom_id=ids["changed_rom"],
                file_name="changed.bin",
                file_path="mapped",
                file_size_bytes=1,
                missing_from_fs=False,
                created_at=file_times[0],
                updated_at=file_times[1],
                incarnation_token=old_file_token,
            )
            session.add(replacement_file)
            session.flush()
            assert replacement_rom.incarnation_token != old_rom_token
            assert replacement_file.incarnation_token != old_file_token
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
    _assert_rollback_authority_unchanged(mapping_id, migration_id)


def test_adversarial_lineage_failures_and_exact_retry_preserve_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    attempt_at = datetime.now(timezone.utc).replace(microsecond=0)

    reparent_source = tmp_path / "reparent"
    reparent_mapping, reparent_migration, reparent_platform, reparent_ids = (
        _seed_exact_rollback(reparent_source, suffix="closure-reparent", now=attempt_at)
    )
    with sync_session.begin() as session:
        replacement_parent = Rom(
            platform_id=reparent_platform,
            fs_name="closure-parent.bin",
            fs_name_no_tags="closure-parent",
            fs_name_no_ext="closure-parent",
            fs_extension="bin",
            fs_path="mapped",
            fs_size_bytes=1,
            name="Closure Parent",
            missing_from_fs=False,
        )
        session.add(replacement_parent)
        session.flush()
        changed_file = session.get(RomFile, reparent_ids["changed_file"])
        assert changed_file is not None
        changed_file.rom_id = replacement_parent.id
    reparent_before = _manifest(reparent_source)

    with pytest.raises(LegacyRollbackError) as reparented:
        DBLegacyMigrationHandler().rollback_migration(
            reparent_migration,
            platform_id=reparent_platform,
            expected_version=1,
            actor_user_id=7,
            actor_display_name="Admin",
            now=attempt_at,
        )
    assert reparented.value.code == "legacy_rollback_stale"
    _assert_rollback_authority_unchanged(reparent_mapping, reparent_migration)
    assert _manifest(reparent_source) == reparent_before

    substitution_source = tmp_path / "substitution"
    (
        substitution_mapping,
        substitution_migration,
        substitution_platform,
        substitution_ids,
    ) = _seed_exact_rollback(
        substitution_source, suffix="closure-substitution", now=attempt_at
    )
    with sync_session.begin() as session:
        original = session.get(RomFile, substitution_ids["changed_file"])
        assert original is not None
        original_identity = (
            original.id,
            original.rom_id,
            original.file_name,
            original.file_path,
            original.file_size_bytes,
            original.missing_from_fs,
            original.created_at,
            original.updated_at,
        )
        original_token = original.incarnation_token
        session.delete(original)
        session.flush()
        replacement = RomFile(
            id=original_identity[0],
            rom_id=original_identity[1],
            file_name=original_identity[2],
            file_path=original_identity[3],
            file_size_bytes=original_identity[4],
            missing_from_fs=original_identity[5],
            created_at=original_identity[6],
            updated_at=original_identity[7],
            incarnation_token=original_token,
        )
        session.add(replacement)
        session.flush()
        assert (
            replacement.id,
            replacement.rom_id,
            replacement.file_name,
            replacement.file_path,
            replacement.file_size_bytes,
            replacement.missing_from_fs,
            replacement.created_at,
            replacement.updated_at,
        ) == original_identity
        assert replacement.incarnation_token != original_token
    substitution_before = _manifest(substitution_source)

    with pytest.raises(LegacyRollbackError) as substituted:
        DBLegacyMigrationHandler().rollback_migration(
            substitution_migration,
            platform_id=substitution_platform,
            expected_version=1,
            actor_user_id=7,
            actor_display_name="Admin",
            now=attempt_at,
        )
    assert substituted.value.code == "legacy_rollback_stale"
    _assert_rollback_authority_unchanged(substitution_mapping, substitution_migration)
    assert _manifest(substitution_source) == substitution_before

    retry_source = tmp_path / "retry"
    retry_mapping, retry_migration, retry_platform, retry_ids = _seed_exact_rollback(
        retry_source, suffix="closure-retry", now=attempt_at
    )
    retry_before = _manifest(retry_source)
    handler = DBLegacyMigrationHandler()
    failed_once = False

    def fail_once(stage: str) -> None:
        nonlocal failed_once
        if stage == "rollback_catalog" and not failed_once:
            failed_once = True
            raise RuntimeError("injected closure rollback failure")

    monkeypatch.setattr(handler, "_after_migration_flush", fail_once)
    with pytest.raises(RuntimeError, match="injected closure rollback failure"):
        handler.rollback_migration(
            retry_migration,
            platform_id=retry_platform,
            expected_version=1,
            actor_user_id=7,
            actor_display_name="Admin",
            now=attempt_at,
        )
    _assert_rollback_authority_unchanged(retry_mapping, retry_migration)
    assert _manifest(retry_source) == retry_before

    retry = handler.rollback_migration(
        retry_migration,
        platform_id=retry_platform,
        expected_version=1,
        actor_user_id=7,
        actor_display_name="Admin",
        now=attempt_at,
    )
    assert retry.state == "rolled_back"
    retry_states = _catalog_states(retry_ids)
    assert retry_states["changed_rom"] is True
    assert retry_states["changed_file"] is True
    assert _manifest(retry_source) == retry_before


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


def test_rollback_catalog_change_race_has_one_ordered_winner(tmp_path: Path):
    source = tmp_path / "external"
    _mapping_id, migration_id, platform_id, ids = _seed_exact_rollback(
        source,
        suffix="catalog-race",
    )
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

    def catalog_change():
        barrier.wait(timeout=5)
        with sync_session.begin() as session:
            migration = session.scalar(
                select(LegacyMigration)
                .where(LegacyMigration.id == migration_id)
                .with_for_update(of=LegacyMigration)
            )
            assert migration is not None
            if migration.state != "completed" or migration.version != 1:
                return "catalog-stale"
            rom = session.scalar(
                select(Rom).where(Rom.id == ids["changed_rom"]).with_for_update(of=Rom)
            )
            assert rom is not None
            rom.missing_from_fs = True
            session.flush()
            return "catalog-change"

    with ThreadPoolExecutor(max_workers=2) as executor:
        rollback_future = executor.submit(rollback)
        change_future = executor.submit(catalog_change)
        outcomes = {rollback_future.result(), change_future.result()}
    assert outcomes in (
        {"rollback", "catalog-stale"},
        {"catalog-change", "legacy_rollback_stale"},
    )

    with sync_session() as session:
        migration = session.get(LegacyMigration, migration_id)
        assert migration is not None
        if "rollback" in outcomes:
            assert migration.state == "rolled_back"
            assert migration.version == 2
        else:
            assert migration.state == "completed"
            assert migration.version == 1
        changed_rom = session.get(Rom, ids["changed_rom"])
        changed_file = session.get(RomFile, ids["changed_file"])
        assert changed_rom is not None and changed_file is not None
        assert changed_rom.missing_from_fs is True
        assert changed_file.missing_from_fs is ("rollback" in outcomes)


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
