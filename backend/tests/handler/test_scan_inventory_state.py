"""Portable SQL inventory records, never a content publication authority."""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from tests.handler.test_scan_operations import command as command  # noqa: F401

from handler.database.base_handler import sync_session
from models.assets import Screenshot
from models.rom import Rom
from models.storage import PlatformStorageMapping


def models():
    from models.scan_inventory import ScanInventoryBaseline, ScanMetadataRetry

    return ScanInventoryBaseline, ScanMetadataRetry


def identity(rom):
    return dict(
        mapping_id=1,
        storage_root_id=1,
        mapping_relative_path="PC",
        mapping_revision=1,
        binding_digest="a" * 64,
        game_relative_path="Collection/Game",
        path_digest="b" * 64,
        rom_id=rom.id,
        rom_incarnation=rom.incarnation_token,
        inventory_version=1,
        classifier_version=1,
        policy_fingerprint="c" * 64,
        identity_digest="d" * 64,
    )


def test_portable_bounded_identity_constraints(rom):
    baseline, retry = models()
    with sync_session.begin() as session:
        inspector = inspect(session.bind)
        for model, name in (
            (baseline, "uq_scan_inventory_identity"),
            (retry, "uq_scan_metadata_retry_identity"),
        ):
            unique = inspector.get_unique_constraints(model.__tablename__)
            assert any(
                c["name"] == name and c["column_names"] == ["identity_digest"]
                for c in unique
            )
            assert model.__table__.c.identity_digest.type.length == 64
            assert model.__table__.c.game_relative_path.type.length == 700
            assert model.__table__.c.mapping_relative_path.type.length == 700
        session.add(
            baseline(
                **identity(rom),
                inventory_digest="e" * 64,
                entry_count=2,
                validated_at=rom.created_at,
                completed_at=rom.created_at
            )
        )
    with pytest.raises(IntegrityError):
        with sync_session.begin() as session:
            session.add(
                baseline(
                    **identity(rom),
                    inventory_digest="e" * 64,
                    entry_count=2,
                    validated_at=rom.created_at,
                    completed_at=rom.created_at
                )
            )
    with sync_session.begin() as session:
        assert session.get(Rom, rom.id).incarnation_token == rom.incarnation_token
        assert session.scalar(select(baseline)).entry_count == 2


@pytest.fixture(autouse=True)
def clear_inventory():
    baseline, retry = models()
    with sync_session.begin() as session:
        session.query(retry).delete()
        session.query(baseline).delete()
    yield
    with sync_session.begin() as session:
        session.query(retry).delete()
        session.query(baseline).delete()


def test_additive_migration_round_trip_preserves_catalog(rom, command, screenshot):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    baseline, retry = models()
    source = Path(__file__).parents[2] / "alembic/versions/0142_scan_inventory_state.py"
    spec = importlib.util.spec_from_file_location("inventory_migration", source)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with sync_session.begin() as session:
        engine = session.get_bind()
    with engine.begin() as connection:
        migration.__dict__["op"] = Operations(MigrationContext.configure(connection))
        migration.downgrade()
        assert "scan_inventory_baselines" not in inspect(connection).get_table_names()
        assert (
            connection.scalar(select(Rom.incarnation_token).where(Rom.id == rom.id))
            == rom.incarnation_token
        )
        mapping_id = command["commands"][0]["mapping_id"]
        assert (
            connection.scalar(
                select(PlatformStorageMapping.relative_path).where(
                    PlatformStorageMapping.id == mapping_id
                )
            )
            == "PC"
        )
        assert (
            connection.scalar(
                select(Screenshot.file_name).where(Screenshot.id == screenshot.id)
            )
            == screenshot.file_name
        )
        migration.upgrade()
    with sync_session.begin() as session:
        assert session.get(Rom, rom.id).incarnation_token == rom.incarnation_token
        assert session.scalar(select(baseline)) is None
        session.add(
            retry(
                **identity(rom),
                provider="igdb",
                normalized_query="game",
                locale="en-US",
                config_fingerprint="f" * 64,
                outcome="no_match"
            )
        )
    with sync_session.begin() as session:
        row = session.scalar(select(retry))
        assert row.provider == "igdb" and row.no_match_streak == 0
