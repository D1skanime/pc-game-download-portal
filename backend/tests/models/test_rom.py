import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from tests.conftest import session

from handler.database import db_rom_handler
from models.rom import (
    Rom,
    RomComponent,
    RomComponentKind,
    RomComponentLocalMedia,
    RomComponentLocalMediaRole,
    RomComponentManifestMember,
    RomComponentMetadata,
)


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


def test_pc_component_metadata_and_local_media_remain_separate_from_base_rom(
    rom: Rom,
):
    """A DLC selection must retain manifest evidence without changing base metadata."""
    component = RomComponent(
        rom_id=rom.id,
        relative_path="dlc/phantom-liberty",
        kind=RomComponentKind.DLC,
        component_metadata=RomComponentMetadata(
            igdb_id=119133,
            name="Cyberpunk 2077: Phantom Liberty",
            summary="A separate DLC selection",
        ),
        local_media=[
            RomComponentLocalMedia(
                source_relative_path="dlc/phantom-liberty/wallpaper.png",
                source_sha256="d" * 64,
                owned_path="roms/1/1/pc-media/1.png",
                image_type="png",
                role=RomComponentLocalMediaRole.GALLERY,
            )
        ],
    )

    with session.begin() as db:
        base_rom = db.get(Rom, rom.id)
        assert base_rom is not None
        base_rom.igdb_id = 1877
        base_rom.name = "Cyberpunk 2077"
        db.add(component)
        db.flush()
        component_id = component.id

    with session() as db:
        saved = db.scalar(
            select(RomComponent)
            .options(
                selectinload(RomComponent.component_metadata),
                selectinload(RomComponent.local_media),
            )
            .where(RomComponent.id == component_id)
        )

        assert saved is not None
        assert saved.component_metadata is not None
        assert saved.component_metadata.igdb_id == 119133
        assert saved.component_metadata.name == "Cyberpunk 2077: Phantom Liberty"
        assert [
            (
                media.source_relative_path,
                media.source_sha256,
                media.owned_path,
                media.role,
            )
            for media in saved.local_media
        ] == [
            (
                "dlc/phantom-liberty/wallpaper.png",
                "d" * 64,
                "roms/1/1/pc-media/1.png",
                RomComponentLocalMediaRole.GALLERY,
            )
        ]

    persisted_base = db_rom_handler.get_rom(rom.id)
    assert persisted_base is not None
    assert persisted_base.igdb_id == 1877
    assert persisted_base.name == "Cyberpunk 2077"


def test_pc_component_local_media_evidence_is_unique(rom: Rom):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="extra/artwork",
        kind=RomComponentKind.EXTRA,
    )
    with session.begin() as db:
        db.add(component)
        db.flush()
        component_id = component.id

    with pytest.raises(IntegrityError), session.begin() as db:
        db.add_all(
            [
                RomComponentLocalMedia(
                    component_id=component_id,
                    source_relative_path="extra/artwork/cover.webp",
                    source_sha256="e" * 64,
                    owned_path="roms/1/1/pc-media/cover.webp",
                    image_type="webp",
                    role=RomComponentLocalMediaRole.COVER,
                ),
                RomComponentLocalMedia(
                    component_id=component_id,
                    source_relative_path="extra/artwork/cover.webp",
                    source_sha256="e" * 64,
                    owned_path="roms/1/1/pc-media/cover-duplicate.webp",
                    image_type="webp",
                    role=RomComponentLocalMediaRole.COVER,
                ),
            ]
        )
        db.flush()
