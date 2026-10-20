"""Retired collection user state cannot reconnect to a byte-identical child."""

import pytest
from tests.handler.database.test_storage_lifecycle import _seed_retained_reconnect

from handler.database.base_handler import sync_session
from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
from models.assets import Save, State
from models.catalog_lifecycle import RetainedCatalogIdentity
from models.play_session import PlaySession
from models.rom import Rom


@pytest.mark.parametrize("audit_kind", ["collection", "empty", "malformed", None])
def test_same_hash_child_never_claims_collection_parent_state(admin_user, audit_kind):
    seeded = _seed_retained_reconnect(admin_user, suffix=str(audit_kind))
    with sync_session.begin() as session:
        retained = session.get(RetainedCatalogIdentity, seeded["retained_id"])
        retained.logical_path = "PC"
        retained.file_name = "Castlevania"
        retained.retained_audit = {
            "collection": {
                "parent_rom_id": retained.detached_rom_id,
                "parent_incarnation": "retired-parent-incarnation",
                "notes": [],
                "rom_users": [],
                "collections": [],
                "screenshots": [],
            },
            "empty": {},
            "malformed": {"parent_rom_id": None},
            None: None,
        }[audit_kind]
        target = session.get(Rom, seeded["target_id"])
        target.fs_path = "PC/Castlevania"
        target.fs_name = "Belmonts.Curse"

    result = CatalogLifecycleHandler().reconnect_retained_identity(
        rom_id=seeded["target_id"],
        platform_id=seeded["platform_id"],
        logical_path="PC/Castlevania/Belmonts.Curse",
        crc_hash="a1b2c3d4",
        md5_hash="1" * 32,
        sha1_hash="2" * 40,
    )
    with sync_session() as session:
        retained = session.get(RetainedCatalogIdentity, seeded["retained_id"])
        if audit_kind is None:
            assert result is not None
            assert retained.active_rom_id == seeded["target_id"]
            expected = (seeded["target_id"], None)
        else:
            assert result is None
            assert retained.active_rom_id is None
            assert retained.version == 1
            assert retained.reconnected_at is None
            expected = (None, seeded["retained_id"])
        for model, key in (
            (Save, "save_id"),
            (State, "state_id"),
            (PlaySession, "play_id"),
        ):
            value = session.get(model, seeded[key])
            assert (value.rom_id, value.retained_catalog_id) == expected
