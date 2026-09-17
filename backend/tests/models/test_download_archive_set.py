import pytest
from sqlalchemy.exc import IntegrityError
from tests.conftest import session

from models.download_archive_set import DownloadArchiveSet, DownloadArchiveSetMember
from models.rom import RomComponent, RomComponentManifestMember


def test_archive_set_preserves_explicit_order_and_flags(rom):
    component = RomComponent(rom_id=rom.id, relative_path="base", kind="base")
    component.manifest_members = [
        RomComponentManifestMember(
            relative_path="base/a.bin", size_bytes=1, sha256="a" * 64
        ),
        RomComponentManifestMember(
            relative_path="base/b.bin", size_bytes=2, sha256="b" * 64
        ),
    ]
    archive_set = DownloadArchiveSet(rom_id=rom.id, name="portable")
    with session.begin() as db:
        db.add(component)
        db.flush()
        archive_set.members = [
            DownloadArchiveSetMember(
                component_id=component.id,
                manifest_member_id=component.manifest_members[1].id,
                position=0,
                required=False,
            ),
            DownloadArchiveSetMember(
                component_id=component.id,
                manifest_member_id=component.manifest_members[0].id,
                position=1,
                required=True,
            ),
        ]
        db.add(archive_set)
    with session() as db:
        loaded = db.get(DownloadArchiveSet, archive_set.id)
        assert loaded is not None
        assert [
            (item.manifest_member_id, item.required) for item in loaded.members
        ] == [
            (component.manifest_members[1].id, False),
            (component.manifest_members[0].id, True),
        ]


def test_archive_set_names_are_unique_per_rom(rom):
    with session.begin() as db:
        db.add_all(
            [
                DownloadArchiveSet(rom_id=rom.id, name="whole-game"),
                DownloadArchiveSet(rom_id=rom.id, name="whole-game"),
            ]
        )
        with pytest.raises(IntegrityError):
            db.flush()
