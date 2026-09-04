"""PC-specific IGDB metadata persistence contracts."""

from pathlib import Path

from sqlalchemy import select
from tests.conftest import session

from endpoints.responses.rom import PcComponentMetadataSchema, RomMetadataSchema
from models.rom import (
    Rom,
    RomComponent,
    RomComponentKind,
    RomComponentMetadata,
    RomMetadata,
)


def test_parent_and_component_persist_equivalent_pc_igdb_metadata(rom: Rom):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="dlc/phantom-liberty",
        kind=RomComponentKind.DLC,
        component_metadata=RomComponentMetadata(
            main_developer="CD Projekt Red",
            publishers=["CD Projekt"],
            themes=["Science fiction", "Cyberpunk"],
            pc_release_date=1_696_032_000,
        ),
    )

    with session.begin() as db:
        saved_rom = db.get(Rom, rom.id)
        assert saved_rom is not None
        saved_rom.igdb_metadata = {
            "main_developer": "CD Projekt Red",
            "publishers": ["CD Projekt"],
            "themes": ["Science fiction", "Cyberpunk"],
            "pc_release_date": 1_507_939_200,
        }
        db.add(component)
        db.flush()
        component_metadata = component.component_metadata
        assert component_metadata is not None

    with session() as db:
        parent_metadata = db.scalar(
            select(RomMetadata).where(RomMetadata.rom_id == rom.id)
        )
    assert parent_metadata is not None

    parent_schema = RomMetadataSchema.model_validate(parent_metadata)
    component_schema = PcComponentMetadataSchema.model_validate(component_metadata)

    for field, expected in {
        "main_developer": "CD Projekt Red",
        "publishers": ["CD Projekt"],
        "themes": ["Science fiction", "Cyberpunk"],
    }.items():
        assert getattr(parent_schema, field) == expected
        assert getattr(component_schema, field) == expected
    assert parent_schema.pc_release_date == 1_507_939_200
    assert component_schema.pc_release_date == 1_696_032_000


def test_pc_igdb_metadata_migration_is_reversible_and_portable():
    migration = Path("alembic/versions/0118_pc_igdb_structured_metadata.py").read_text()

    assert 'down_revision = "0117_component_owned_media_notes"' in migration
    assert 'op.add_column(\n        "rom_component_metadata"' in migration
    assert 'op.drop_column("rom_component_metadata"' in migration
    assert "CREATE OR REPLACE VIEW roms_metadata" in migration
    assert "is_postgresql" in migration
    assert migration.count("sa.JSON()") == 2
    assert "pc_release_date" in migration
