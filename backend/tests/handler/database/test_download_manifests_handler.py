from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from tests.conftest import session

from handler.database.download_manifests_handler import DBDownloadManifestsHandler
from handler.filesystem.roms_handler import DownloadManifestMemberEvidence
from models.download_manifest import DownloadManifest, DownloadManifestStatus
from models.rom import Rom, RomComponent, RomComponentKind, RomComponentManifestMember


class FakeManifestFilesystem:
    def __init__(self):
        self.captured: list[int] = []
        self.light_checks: list[int] = []
        self.changed_member_ids: set[int] = set()

    def capture_download_manifest_member(self, rom, member):
        self.captured.append(member.id)
        return DownloadManifestMemberEvidence(
            destination=f"{rom.fs_name}/{member.relative_path}",
            size_bytes=member.size_bytes,
            sha256=member.sha256,
            snapshot=f'"snapshot-{member.id}"',
            mtime_ns=member.id,
            device=None,
            inode=None,
        )

    def light_revalidate_download_manifest_member(self, _rom, member, _evidence):
        self.light_checks.append(member.id)
        return (
            "SOURCE_CHANGED"
            if member.id in self.changed_member_ids
            else "UNCHANGED_BY_LIGHT_CHECK"
        )


@pytest.fixture(autouse=True)
def clear_download_manifests():
    yield
    with session.begin() as db:
        db.query(DownloadManifest).delete()


def _component(rom_id, kind, suffix):
    component = RomComponent(
        rom_id=rom_id,
        relative_path=f"{kind.value}-{suffix}",
        kind=kind,
    )
    component.manifest_members = [
        RomComponentManifestMember(
            relative_path=f"{kind.value}-{suffix}/content.bin",
            size_bytes=5 * 1024**3,
            sha256="a" * 64,
        )
    ]
    return component


def test_create_manifest_selects_only_eligible_components_atomically(admin_user, rom):
    selected = [
        _component(rom.id, RomComponentKind.BASE, "one"),
        _component(rom.id, RomComponentKind.UPDATE, "two"),
        _component(rom.id, RomComponentKind.DLC, "three"),
        _component(rom.id, RomComponentKind.EXTRA, "four"),
    ]
    excluded = _component(rom.id, RomComponentKind.HOTFIX, "five")
    with session.begin() as db:
        db.add_all([*selected, excluded])

    filesystem = FakeManifestFilesystem()
    handler = DBDownloadManifestsHandler(filesystem)
    manifest = handler.create_manifest(admin_user.id, rom.id, None)

    assert [item.component_id for item in manifest.components] == sorted(
        item.id for item in selected
    )
    assert [
        member.size_bytes for item in manifest.components for member in item.members
    ] == [5 * 1024**3] * 4
    assert filesystem.captured == sorted(filesystem.captured)
    with session() as db:
        assert db.scalar(
            select(DownloadManifest).where(DownloadManifest.id == manifest.id)
        )


def test_create_manifest_rejects_duplicate_foreign_and_empty_components(
    admin_user, viewer_user, rom
):
    good = _component(rom.id, RomComponentKind.BASE, "one")
    foreign_rom = Rom(
        platform_id=rom.platform_id,
        name="foreign",
        slug="foreign",
        fs_name="foreign",
        fs_name_no_tags="foreign",
        fs_name_no_ext="foreign",
        fs_extension="",
        fs_path=rom.fs_path,
    )
    empty = RomComponent(
        rom_id=rom.id,
        relative_path="extra-empty",
        kind=RomComponentKind.EXTRA,
    )
    with session.begin() as db:
        db.add_all([good, foreign_rom, empty])
        db.flush()
        foreign = _component(foreign_rom.id, RomComponentKind.DLC, "foreign")
        db.add(foreign)
    handler = DBDownloadManifestsHandler(FakeManifestFilesystem())

    for component_ids in ([good.id, good.id], [foreign.id], [empty.id]):
        with pytest.raises(ValueError):
            handler.create_manifest(admin_user.id, rom.id, component_ids)
    assert (
        handler.create_manifest(viewer_user.id, rom.id, [good.id]).user_id
        == viewer_user.id
    )


def test_get_manifest_is_owner_scoped_and_uses_only_light_checks(
    admin_user, viewer_user, rom
):
    component = _component(rom.id, RomComponentKind.BASE, "one")
    with session.begin() as db:
        db.add(component)
    filesystem = FakeManifestFilesystem()
    handler = DBDownloadManifestsHandler(filesystem)
    manifest = handler.create_manifest(admin_user.id, rom.id, [component.id])

    assert handler.get_manifest(manifest.id, viewer_user.id) is None
    loaded = handler.get_manifest(manifest.id, admin_user.id)
    assert loaded is not None
    assert filesystem.light_checks == [component.manifest_members[0].id]
    assert filesystem.captured == [component.manifest_members[0].id]

    filesystem.changed_member_ids.add(component.manifest_members[0].id)
    assert (
        handler.get_manifest(manifest.id, admin_user.id).status
        is DownloadManifestStatus.SOURCE_CHANGED
    )


def test_expiry_precedes_source_change_and_revocation_is_closed(admin_user, rom):
    component = _component(rom.id, RomComponentKind.BASE, "one")
    with session.begin() as db:
        db.add(component)
    filesystem = FakeManifestFilesystem()
    handler = DBDownloadManifestsHandler(filesystem)
    manifest = handler.create_manifest(admin_user.id, rom.id, [component.id])
    manifest_id = manifest.id
    manifest.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with session.begin() as db:
        db.merge(manifest)
    assert (
        handler.get_manifest(manifest_id, admin_user.id).status
        is DownloadManifestStatus.EXPIRED
    )
    assert filesystem.light_checks == []
    active = handler.create_manifest(admin_user.id, rom.id, [component.id])
    assert handler.revoke_manifest(active.id, admin_user.id)
    assert (
        handler.get_manifest(active.id, admin_user.id).status
        is DownloadManifestStatus.REVOKED
    )
