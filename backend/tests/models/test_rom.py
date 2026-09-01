import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from tests.conftest import session

from models.rom import Rom, RomComponent, RomComponentKind, RomComponentManifestMember


def test_rom(rom: Rom):
    assert rom.fs_path == "test_platform_slug/roms"
    assert rom.full_path == "test_platform_slug/roms/test_rom.zip"


def test_rom_with_libretro_match_is_identified(rom: Rom):
    rom.libretro_id = "abc123"

    assert rom.is_unidentified is False
    assert rom.is_identified is True


def test_pc_component_kinds_and_manifest_member_are_persisted(rom: Rom):
    """Changing a component kind or manifest byte evidence must break this contract."""
    component = RomComponent(
        rom_id=rom.id,
        relative_path="updates/v1",
        kind=RomComponentKind.UPDATE,
        manifest_members=[
            RomComponentManifestMember(
                relative_path="updates/v1/game.exe",
                size_bytes=42,
                sha256="a" * 64,
            )
        ],
    )

    with session.begin() as db:
        db.add(component)
        db.flush()
        component_id = component.id

    with session() as db:
        saved = db.scalar(
            select(RomComponent)
            .options(selectinload(RomComponent.manifest_members))
            .where(RomComponent.id == component_id)
        )
        assert saved is not None
        assert saved.kind == RomComponentKind.UPDATE
        assert saved.relative_path == "updates/v1"
        assert [
            (member.relative_path, member.size_bytes, member.sha256)
            for member in saved.manifest_members
        ] == [("updates/v1/game.exe", 42, "a" * 64)]
        assert {kind.value for kind in RomComponentKind} == {
            "base",
            "update",
            "dlc",
            "hotfix",
            "language_pack",
            "extra",
            "unresolved",
        }


def test_pc_component_and_manifest_paths_are_unique(rom: Rom):
    """Removing either uniqueness constraint would allow ambiguous scan reconciliation."""
    with pytest.raises(IntegrityError), session.begin() as db:
        db.add_all(
            [
                RomComponent(
                    rom_id=rom.id,
                    relative_path="base",
                    kind=RomComponentKind.BASE,
                ),
                RomComponent(
                    rom_id=rom.id,
                    relative_path="base",
                    kind=RomComponentKind.BASE,
                ),
            ]
        )
        db.flush()

    with session.begin() as db:
        component = RomComponent(
            rom_id=rom.id,
            relative_path="base",
            kind=RomComponentKind.BASE,
        )
        db.add(component)
        db.flush()
        component_id = component.id

    with pytest.raises(IntegrityError), session.begin() as db:
        db.add_all(
            [
                RomComponentManifestMember(
                    component_id=component_id,
                    relative_path="base/game.exe",
                    size_bytes=1,
                    sha256="b" * 64,
                ),
                RomComponentManifestMember(
                    component_id=component_id,
                    relative_path="base/game.exe",
                    size_bytes=2,
                    sha256="c" * 64,
                ),
            ]
        )
        db.flush()
