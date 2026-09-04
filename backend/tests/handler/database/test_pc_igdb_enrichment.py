from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from tests.conftest import session

from handler.database import db_rom_handler
from models.rom import RomComponent, RomComponentKind, RomComponentOwnedMediaRole


def _metadata() -> dict[str, object]:
    return {
        "igdb_id": 77,
        "name": "Trusted DLC",
        "summary": "Imported from IGDB",
        "igdb_metadata": {
            "main_developer": "Example Studio",
            "publishers": ["Example Publishing"],
            "themes": ["Science fiction"],
            "pc_release_date": 1_700_000_000,
        },
    }


def test_pc_igdb_enrichment_is_parent_and_dlc_contained(rom):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="dlc/trusted",
        kind=RomComponentKind.DLC,
    )
    sibling = RomComponent(
        rom_id=rom.id,
        relative_path="dlc/untouched",
        kind=RomComponentKind.DLC,
    )
    with session.begin() as db:
        db.add_all((component, sibling))
        db.flush()

    parent = db_rom_handler.get_rom(rom.id)
    assert parent is not None
    enriched_parent = db_rom_handler.apply_pc_igdb_enrichment(
        rom.id, parent.updated_at, _metadata()
    )
    assert enriched_parent is not None
    assert enriched_parent.igdb_metadata["main_developer"] == "Example Studio"

    target = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert target is not None
    enriched_component = db_rom_handler.apply_pc_component_metadata_candidate(
        rom.id, target.id, target.updated_at, "igdb", _metadata()
    )
    assert enriched_component is not None
    assert enriched_component.component_metadata is not None
    assert enriched_component.component_metadata.main_developer == "Example Studio"
    assert enriched_component.component_metadata.publishers == ["Example Publishing"]

    with session.begin() as db:
        untouched = db.scalar(
            select(RomComponent)
            .options(selectinload(RomComponent.component_metadata))
            .where(RomComponent.id == sibling.id)
        )
    assert untouched is not None
    assert untouched.component_metadata is None


def test_pc_igdb_enrichment_rejects_stale_parent_or_component(rom):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="dlc/stale",
        kind=RomComponentKind.DLC,
    )
    with session.begin() as db:
        db.add(component)
        db.flush()

    parent = db_rom_handler.get_rom(rom.id)
    assert parent is not None
    assert (
        db_rom_handler.apply_pc_igdb_enrichment(
            rom.id, parent.updated_at - timedelta(seconds=1), _metadata()
        )
        is None
    )

    target = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert target is not None
    assert (
        db_rom_handler.apply_pc_component_metadata_candidate(
            rom.id,
            target.id,
            target.updated_at - timedelta(seconds=1),
            "igdb",
            _metadata(),
        )
        is None
    )


def test_scan_provider_media_import_is_dlc_contained_and_version_guarded(rom):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="dlc/media",
        kind=RomComponentKind.DLC,
    )
    with session.begin() as db:
        db.add(component)
        db.flush()

    target = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert target is not None
    imported = db_rom_handler.import_pc_component_provider_media(
        rom.id,
        target.id,
        target.updated_at,
        RomComponentOwnedMediaRole.ARTWORK,
        "image/webp",
        "roms/1/pc-owned-media/artwork.webp",
        "igdb",
        "stable-media-id",
    )
    assert imported is not None
    assert imported.media.component_id == target.id
    assert imported.media.provider_media_id == "stable-media-id"

    assert (
        db_rom_handler.import_pc_component_provider_media(
            rom.id,
            target.id,
            target.updated_at - timedelta(seconds=1),
            RomComponentOwnedMediaRole.ARTWORK,
            "image/webp",
            "roms/1/pc-owned-media/stale.webp",
            "igdb",
            "stale-media-id",
        )
        is None
    )
