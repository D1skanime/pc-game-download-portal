import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from tests.conftest import session

from models.rom import (
    RomComponent,
    RomComponentKind,
    RomComponentLocalMedia,
    RomComponentNote,
    RomComponentOwnedMedia,
    RomComponentOwnedMediaOrigin,
    RomComponentOwnedMediaRole,
)


def _component(rom_id: int, relative_path: str) -> RomComponent:
    return RomComponent(
        rom_id=rom_id,
        relative_path=relative_path,
        kind=RomComponentKind.DLC,
    )


def test_component_owned_resources_are_isolated_from_parent_and_siblings(
    rom, admin_user
):
    first = _component(rom.id, "dlc/first")
    sibling = _component(rom.id, "dlc/sibling")
    with session.begin() as db:
        db.add_all((first, sibling))
        db.flush()
        db.add_all(
            (
                RomComponentOwnedMedia(
                    component_id=first.id,
                    role=RomComponentOwnedMediaRole.GALLERY,
                    mime_type="image/webp",
                    owned_path="roms/1/components/first/gallery.webp",
                    origin=RomComponentOwnedMediaOrigin.UPLOAD,
                ),
                RomComponentNote(
                    component_id=first.id,
                    user_id=admin_user.id,
                    title="First DLC note",
                    content="Only this DLC can show this note.",
                ),
            )
        )
        first_id = first.id
        sibling_id = sibling.id

    with session() as db:
        components = db.scalars(
            select(RomComponent)
            .options(
                selectinload(RomComponent.owned_media),
                selectinload(RomComponent.notes),
            )
            .where(RomComponent.id.in_((first_id, sibling_id)))
        ).all()

    saved_first = next(
        component for component in components if component.id == first_id
    )
    saved_sibling = next(
        component for component in components if component.id == sibling_id
    )
    assert [media.owned_path for media in saved_first.owned_media] == [
        "roms/1/components/first/gallery.webp"
    ]
    assert [note.title for note in saved_first.notes] == ["First DLC note"]
    assert saved_sibling.owned_media == []
    assert saved_sibling.notes == []


def test_component_owned_resource_constraints_and_local_evidence_remain_distinct(
    rom, admin_user
):
    component = _component(rom.id, "dlc/resources")
    with session.begin() as db:
        db.add(component)
        db.flush()
        component_id = component.id

    with pytest.raises(IntegrityError), session.begin() as db:
        db.add_all(
            (
                RomComponentNote(
                    component_id=component_id,
                    user_id=admin_user.id,
                    title="Same title",
                    content="One",
                ),
                RomComponentNote(
                    component_id=component_id,
                    user_id=admin_user.id,
                    title="Same title",
                    content="Two",
                ),
            )
        )
        db.flush()

    local_media_columns = inspect(RomComponentLocalMedia).columns
    assert local_media_columns.source_relative_path.nullable is False
    assert local_media_columns.source_sha256.nullable is False
    assert "source_relative_path" not in inspect(RomComponentOwnedMedia).columns
    assert "source_sha256" not in inspect(RomComponentOwnedMedia).columns
