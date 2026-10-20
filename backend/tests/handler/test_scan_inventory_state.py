"""Portable SQL inventory records, never a content publication authority."""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from handler.database.base_handler import sync_session
from models.rom import Rom


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
