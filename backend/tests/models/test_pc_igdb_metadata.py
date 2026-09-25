"""PC-specific IGDB metadata persistence contracts."""

from pathlib import Path

from sqlalchemy import select
from tests.conftest import session

from endpoints.responses.rom import PcComponentMetadataSchema, RomMetadataSchema
from models.rom import (
    METADATA_SOURCE_COLUMNS,
    METADATA_SOURCE_FACET_COLUMNS,
    Rom,
    RomComponent,
    RomComponentKind,
    RomComponentMetadata,
    RomFacets,
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


def test_component_metadata_allows_shared_steam_app_ids():
    first = RomComponentMetadata(component_id=1, steam_id=123)
    second = RomComponentMetadata(component_id=2, steam_id=123)

    assert first.steam_id == second.steam_id == 123


def test_steam_persistence_fields_are_nullable_and_source_mapped():
    for model, field in (
        (Rom, "steam_id"),
        (Rom, "steam_metadata"),
        (RomFacets, "steam_id"),
        (RomComponentMetadata, "steam_id"),
        (RomComponentMetadata, "steam_metadata"),
    ):
        assert getattr(model, field).property.columns[0].nullable

    assert METADATA_SOURCE_COLUMNS["steam"] is Rom.steam_id
    assert METADATA_SOURCE_FACET_COLUMNS["steam"] is RomFacets.steam_id


def test_steam_metadata_migration_has_the_current_download_head():
    migration = Path("alembic/versions/0126_add_steam_metadata.py").read_text()

    assert 'revision = "0126_add_steam_metadata"' in migration
    assert (
        'down_revision = "0125_pc_component_manifest_members_missing_from_fs"'
        in migration
    )
    for table, column in (
        ("roms", "steam_id"),
        ("roms", "steam_metadata"),
        ("roms_facets", "steam_id"),
        ("rom_component_metadata", "steam_id"),
        ("rom_component_metadata", "steam_metadata"),
    ):
        assert f'"{table}"' in migration
        assert f'sa.Column("{column}"' in migration
        assert f'op.drop_column("{table}", "{column}")' in migration
    assert migration.count("sa.JSON()") == 2
    assert "unique=True" not in migration
