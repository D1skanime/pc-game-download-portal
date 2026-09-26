from datetime import timedelta

from sqlalchemy import func, select
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


def test_pc_component_steam_provenance_preserves_existing_provider_metadata(rom):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="dlc/steam-provenance",
        kind=RomComponentKind.DLC,
    )
    sibling = RomComponent(
        rom_id=rom.id,
        relative_path="dlc/shared-steam-id",
        kind=RomComponentKind.DLC,
    )
    with session.begin() as db:
        db.add_all((component, sibling))
        db.flush()

    target = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert target is not None
    enriched = db_rom_handler.apply_pc_component_metadata_candidate(
        rom.id, target.id, target.updated_at, "igdb", _metadata()
    )
    assert enriched is not None
    assert enriched.component_metadata is not None
    current = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert current is not None
    assert enriched.updated_at == current.updated_at

    steam_data = {
        "steam_id": 1091500,
        "steam_metadata": {"app_id": 1091500, "name": "Cyberpunk 2077"},
    }
    persisted = db_rom_handler.apply_pc_component_metadata_candidate(
        rom.id,
        enriched.id,
        enriched.updated_at,
        "steam",
        steam_data,
    )
    assert persisted is not None
    assert persisted.component_metadata is not None
    metadata = persisted.component_metadata
    assert metadata.steam_id == 1091500
    assert metadata.name == "Trusted DLC"
    assert metadata.summary == "Imported from IGDB"
    assert metadata.provider_metadata == {
        "igdb_metadata": _metadata()["igdb_metadata"],
        "steam_metadata": steam_data["steam_metadata"],
    }
    assert metadata.main_developer == "Example Studio"
    assert metadata.publishers == ["Example Publishing"]
    assert metadata.themes == ["Science fiction"]
    assert metadata.pc_release_date == 1_700_000_000

    sibling_target = db_rom_handler.get_pc_component_by_id(rom.id, sibling.id)
    assert sibling_target is not None
    shared = db_rom_handler.apply_pc_component_metadata_candidate(
        rom.id,
        sibling_target.id,
        sibling_target.updated_at,
        "steam",
        steam_data,
    )
    assert shared is not None
    assert shared.component_metadata is not None
    assert shared.component_metadata.steam_id == 1091500

    with session() as db:
        component_count = db.scalar(
            select(func.count())
            .select_from(RomComponent)
            .where(RomComponent.rom_id == rom.id)
        )
    assert component_count == 2


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
