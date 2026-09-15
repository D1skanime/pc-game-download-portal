from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from tests.conftest import session

from models.base import BaseModel
from models.download_manifest import (
    DownloadManifest,
    DownloadManifestComponent,
    DownloadManifestMember,
    DownloadManifestStatus,
)
from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember
from models.user import User


@pytest.fixture(scope="module", autouse=True)
def manifest_tables():
    tables = [
        DownloadManifest.__table__,
        DownloadManifestComponent.__table__,
        DownloadManifestMember.__table__,
    ]
    engine = session.kw["bind"]
    created = not inspect(engine).has_table(DownloadManifest.__tablename__)
    if created:
        BaseModel.metadata.create_all(bind=engine, tables=tables)
    yield
    if created:
        BaseModel.metadata.drop_all(bind=engine, tables=tables)


@pytest.fixture(autouse=True)
def clear_manifest_rows():
    yield
    with session.begin() as db:
        db.query(DownloadManifestMember).delete()
        db.query(DownloadManifestComponent).delete()
        db.query(DownloadManifest).delete()


def _component_with_member(rom):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="base",
        kind=RomComponentKind.BASE,
    )
    member = RomComponentManifestMember(
        component=component,
        relative_path="base/game.iso",
        size_bytes=5 * 1024**3,
        sha256="a" * 64,
    )
    return component, member


def test_manifest_persists_owner_scoped_path_free_immutable_selection(admin_user, rom):
    component, source_member = _component_with_member(rom)
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    manifest = DownloadManifest(user_id=admin_user.id, expires_at=expires_at)
    selected_component = DownloadManifestComponent(
        manifest=manifest,
        component=component,
    )
    selected_member = DownloadManifestMember(
        component=selected_component,
        manifest_member=source_member,
        destination="Cyberpunk 2077/game.iso",
        size_bytes=5 * 1024**3,
        sha256="a" * 64,
        snapshot='"manifest-v1"',
        mtime_ns=1_726_000_000_000_000_000,
        device=2049,
        inode=4096,
    )

    with session.begin() as db:
        db.add(selected_member)
        db.flush()
        manifest_id = manifest.id

    with session() as db:
        saved = db.get(DownloadManifest, manifest_id)
        assert saved is not None
        assert saved.user_id == admin_user.id
        assert saved.status is DownloadManifestStatus.VALID
        assert saved.expires_at.replace(tzinfo=UTC) == expires_at.replace(microsecond=0)
        assert len(saved.components) == 1
        member = saved.components[0].members[0]
        assert member.destination == "Cyberpunk 2077/game.iso"
        assert member.size_bytes == 5 * 1024**3
        assert member.sha256 == "a" * 64
        assert member.snapshot == '"manifest-v1"'
        assert member.snapshot != member.sha256
        assert (member.mtime_ns, member.device, member.inode) == (
            1_726_000_000_000_000_000,
            2049,
            4096,
        )

    persisted_columns = {
        column.name
        for table in (
            DownloadManifest.__table__,
            DownloadManifestComponent.__table__,
            DownloadManifestMember.__table__,
        )
        for column in table.columns
    }
    forbidden = {"fs_path", "fs_name", "container_path", "source_root", "source_path"}
    assert persisted_columns.isdisjoint(forbidden)


def test_manifest_member_allows_portable_nullable_device_and_inode(admin_user, rom):
    component, source_member = _component_with_member(rom)
    selected_member = DownloadManifestMember(
        component=DownloadManifestComponent(
            manifest=DownloadManifest(
                user_id=admin_user.id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
            component=component,
        ),
        manifest_member=source_member,
        destination="game.iso",
        size_bytes=1,
        sha256="b" * 64,
        snapshot='"snapshot"',
        mtime_ns=1,
        device=None,
        inode=None,
    )

    with session.begin() as db:
        db.add(selected_member)
        db.flush()
        member_id = selected_member.id

    with session() as db:
        saved = db.get(DownloadManifestMember, member_id)
        assert saved is not None
        assert saved.device is None
        assert saved.inode is None
        assert saved.mtime_ns == 1


def test_manifest_constraints_reject_duplicate_selection_and_members(admin_user, rom):
    component, source_member = _component_with_member(rom)
    manifest = DownloadManifest(
        user_id=admin_user.id,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    with session.begin() as db:
        db.add_all([manifest, component, source_member])
        db.flush()
        manifest_id = manifest.id
        component_id = component.id
        source_member_id = source_member.id

    with pytest.raises(IntegrityError), session.begin() as db:
        db.add_all(
            [
                DownloadManifestComponent(
                    manifest_id=manifest_id, component_id=component_id
                ),
                DownloadManifestComponent(
                    manifest_id=manifest_id, component_id=component_id
                ),
            ]
        )
        db.flush()

    with session.begin() as db:
        selected_component = DownloadManifestComponent(
            manifest_id=manifest_id,
            component_id=component_id,
        )
        db.add(selected_component)
        db.flush()
        selected_component_id = selected_component.id

    def member(destination):
        return DownloadManifestMember(
            download_manifest_component_id=selected_component_id,
            manifest_member_id=source_member_id,
            destination=destination,
            size_bytes=1,
            sha256="c" * 64,
            snapshot='"snapshot"',
            mtime_ns=1,
        )

    with pytest.raises(IntegrityError), session.begin() as db:
        db.add_all([member("one.iso"), member("two.iso")])
        db.flush()

    with session.begin() as db:
        db.add(member("one.iso"))

    with pytest.raises(IntegrityError), session.begin() as db:
        db.add(member("one.iso"))
        db.flush()


def test_manifest_owner_and_rows_cascade_without_touching_source_evidence(
    admin_user, rom
):
    component, source_member = _component_with_member(rom)
    selected_member = DownloadManifestMember(
        component=DownloadManifestComponent(
            manifest=DownloadManifest(
                user_id=admin_user.id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
            component=component,
        ),
        manifest_member=source_member,
        destination="game.iso",
        size_bytes=1,
        sha256="d" * 64,
        snapshot='"snapshot"',
        mtime_ns=1,
    )
    with session.begin() as db:
        db.add(selected_member)
        db.flush()
        manifest_id = selected_member.component.manifest_id
        source_member_id = source_member.id

    with session.begin() as db:
        db.delete(db.get(DownloadManifest, manifest_id))

    with session() as db:
        assert db.get(DownloadManifest, manifest_id) is None
        assert db.get(RomComponentManifestMember, source_member_id) is not None


def test_manifest_status_and_named_constraints_are_portable_metadata():
    assert {status.value for status in DownloadManifestStatus} == {
        "valid",
        "expired",
        "revoked",
        "source_changed",
    }
    constraints = {
        constraint.name
        for table in (
            DownloadManifest.__table__,
            DownloadManifestComponent.__table__,
            DownloadManifestMember.__table__,
        )
        for constraint in table.constraints
    }
    assert {
        "uq_download_manifest_components_manifest_component",
        "uq_download_manifest_members_manifest_member",
        "uq_download_manifest_members_manifest_destination",
    }.issubset(constraints)
    assert inspect(DownloadManifestMember).columns.mtime_ns.nullable is False


def test_download_manifest_migration_is_reversible_and_portable():
    migration = Path("alembic/versions/0119_download_manifests.py").read_text()

    assert 'revision = "0119_download_manifests"' in migration
    assert 'down_revision = "0118_pc_igdb_structured_metadata"' in migration
    assert 'op.create_table(\n        "download_manifests"' in migration
    assert 'op.create_table(\n        "download_manifest_components"' in migration
    assert 'op.create_table(\n        "download_manifest_members"' in migration
    assert 'op.drop_table("download_manifest_members")' in migration
    assert 'op.drop_table("download_manifest_components")' in migration
    assert 'op.drop_table("download_manifests")' in migration
    assert "sa.BigInteger()" in migration
    assert "sa.String(length=700)" in migration
    assert "native_enum=False" in migration
