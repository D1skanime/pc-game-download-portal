"""PC-specific IGDB metadata persistence contracts."""

from pathlib import Path

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
    parent_metadata = RomMetadata(
        rom_id=rom.id,
        main_developer="CD Projekt Red",
        publishers=["CD Projekt"],
        themes=["Science fiction", "Cyberpunk"],
        pc_release_date=1_507_939_200,
    )
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
        db.add_all([parent_metadata, component])
        db.flush()
        component_metadata = component.component_metadata
        assert component_metadata is not None

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
    for table in ("roms_metadata", "rom_component_metadata"):
        assert f'op.add_column("{table}"' in migration
        assert f'op.drop_column("{table}"' in migration
    assert migration.count("sa.JSON()") == 4
    assert "pc_release_date" in migration
