from datetime import datetime, timedelta, timezone

from tests.conftest import session

from handler.database import db_rom_handler
from models.rom import (
    RomComponent,
    RomComponentKind,
    RomComponentOwnedMediaOrigin,
    RomComponentOwnedMediaRole,
)


def _dlc(rom_id: int, relative_path: str) -> RomComponent:
    return RomComponent(
        rom_id=rom_id,
        relative_path=relative_path,
        kind=RomComponentKind.DLC,
    )


def _create_components(rom_id: int) -> tuple[RomComponent, RomComponent]:
    component = _dlc(rom_id, "dlc/owned")
    sibling = _dlc(rom_id, "dlc/sibling")
    with session.begin() as db:
        db.add_all((component, sibling))
        db.flush()
    saved_component = db_rom_handler.get_pc_component_by_id(rom_id, component.id)
    saved_sibling = db_rom_handler.get_pc_component_by_id(rom_id, sibling.id)
    assert saved_component is not None
    assert saved_sibling is not None
    return saved_component, saved_sibling


def test_owned_media_mutations_are_component_scoped_and_version_guarded(
    rom, admin_user
):
    component, sibling = _create_components(rom.id)
    original_component_version = component.updated_at
    persisted_parent = db_rom_handler.get_rom(rom.id)
    assert persisted_parent is not None
    original_parent_version = persisted_parent.updated_at

    created = db_rom_handler.create_pc_component_owned_media(
        rom_id=rom.id,
        component_id=component.id,
        user_id=admin_user.id,
        expected_updated_at=original_component_version,
        role=RomComponentOwnedMediaRole.GALLERY,
        mime_type="image/webp",
        owned_path="roms/1/components/owned/gallery.webp",
        origin=RomComponentOwnedMediaOrigin.UPLOAD,
    )

    assert created is not None
    assert created.media.component_id == component.id
    assert created.replaced_owned_paths == []
    assert (
        db_rom_handler.get_pc_component_owned_media(rom.id, sibling.id, admin_user.id)
        == []
    )

    stale = db_rom_handler.create_pc_component_owned_media(
        rom_id=rom.id,
        component_id=component.id,
        user_id=admin_user.id,
        expected_updated_at=original_component_version - timedelta(seconds=1),
        role=RomComponentOwnedMediaRole.GALLERY,
        mime_type="image/webp",
        owned_path="roms/1/components/owned/stale.webp",
        origin=RomComponentOwnedMediaOrigin.UPLOAD,
    )
    assert stale is None
    assert [
        item.owned_path
        for item in db_rom_handler.get_pc_component_owned_media(
            rom.id, component.id, admin_user.id
        )
    ] == ["roms/1/components/owned/gallery.webp"]

    latest = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert latest is not None
    updated = db_rom_handler.update_pc_component_owned_media(
        rom_id=rom.id,
        component_id=component.id,
        user_id=admin_user.id,
        media_id=created.media.id,
        expected_updated_at=latest.updated_at,
        role=RomComponentOwnedMediaRole.COVER,
        mime_type="image/png",
        owned_path="roms/1/components/owned/cover.png",
        origin=RomComponentOwnedMediaOrigin.PROVIDER,
        provider="igdb",
        provider_media_id="cover-123",
    )
    assert updated is not None
    assert updated.replaced_owned_paths == ["roms/1/components/owned/gallery.webp"]
    assert updated.media.owned_path == "roms/1/components/owned/cover.png"
    assert db_rom_handler.get_rom(rom.id).updated_at == original_parent_version


def test_component_notes_are_private_to_their_component_and_owner(rom, admin_user):
    component, sibling = _create_components(rom.id)
    created = db_rom_handler.create_pc_component_note(
        rom_id=rom.id,
        component_id=component.id,
        user_id=admin_user.id,
        expected_updated_at=component.updated_at,
        title="Owner note",
        content="DLC-only note",
        tags=["dlc"],
    )

    assert created is not None
    assert [
        note.title
        for note in db_rom_handler.get_pc_component_notes(
            rom.id, component.id, admin_user.id
        )
    ] == ["Owner note"]
    assert (
        db_rom_handler.get_pc_component_notes(rom.id, sibling.id, admin_user.id) == []
    )

    stale = db_rom_handler.update_pc_component_note(
        rom_id=rom.id,
        component_id=component.id,
        user_id=admin_user.id,
        note_id=created.id,
        expected_updated_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        content="Must not persist",
    )
    assert stale is None
    assert (
        db_rom_handler.get_pc_component_notes(rom.id, component.id, admin_user.id)[
            0
        ].content
        == "DLC-only note"
    )

    latest = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert latest is not None
    assert (
        db_rom_handler.delete_pc_component_note(
            rom.id,
            component.id,
            admin_user.id,
            created.id,
            latest.updated_at,
        )
        is True
    )
    assert (
        db_rom_handler.get_pc_component_notes(rom.id, component.id, admin_user.id) == []
    )


def test_component_resource_helpers_reject_foreign_parent_or_non_dlc_target(
    rom, admin_user
):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="base",
        kind=RomComponentKind.BASE,
    )
    with session.begin() as db:
        db.add(component)
        db.flush()

    assert (
        db_rom_handler.create_pc_component_note(
            rom_id=rom.id + 1,
            component_id=component.id,
            user_id=admin_user.id,
            expected_updated_at=component.updated_at,
            title="Foreign parent",
            content="Must not persist",
        )
        is None
    )
    assert (
        db_rom_handler.create_pc_component_note(
            rom_id=rom.id,
            component_id=component.id,
            user_id=admin_user.id,
            expected_updated_at=component.updated_at,
            title="Base component",
            content="Must not persist",
        )
        is None
    )
