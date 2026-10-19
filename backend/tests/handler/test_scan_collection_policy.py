"""Server-derived collection promotion identity and policy constraints."""

import os

import pytest
from tests.endpoints.test_scan_operations import mapped  # noqa: F401

from endpoints.responses.scan_operations import ScanOperationRequest
from handler.database.base_handler import sync_session
from handler.scan_operation_commands import normalize_scan_request
from models.rom import Rom
from models.storage import PlatformStorageMapping, StorageRoot


@pytest.fixture
def promotion_body(mapped, rom, tmp_path, monkeypatch):
    (tmp_path / "PC/Castlevania/Belmonts.Curse").mkdir(parents=True)
    with sync_session.begin() as session:
        session.get(StorageRoot, mapped.storage_root_id).container_path = str(tmp_path)
        parent = session.get(Rom, rom.id)
        parent.fs_path = "PC"
        parent.fs_name = "Castlevania"
        parent_id = parent.id
    access = os.access
    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: False if mode == os.W_OK else access(path, mode),
    )
    return {
        "request_key": "collection-choice",
        "platforms": [mapped.platform_id],
        "filesystem_scope_paths": {"test_platform_slug": "Castlevania/Belmonts.Curse"},
        "collection_promotion": {
            "parent_rom_id": parent_id,
            "mapping_id": mapped.id,
            "expected_revision": mapped.version,
            "parent_relative_path": "Castlevania",
            "selected_child_relative_path": "Castlevania/Belmonts.Curse",
        },
    }


def test_acceptance_freezes_server_derived_parent_incarnation(promotion_body, rom):
    normalized = normalize_scan_request(
        ScanOperationRequest.model_validate(promotion_body)
    )
    assert (
        normalized.get("collection_promotion", {}).get("parent_incarnation")
        == rom.incarnation_token
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("parent_rom_id", 987654),
        ("expected_revision", 999),
        ("parent_relative_path", "Another.Parent"),
        ("selected_child_relative_path", "Castlevania/Another.Child"),
    ],
)
def test_forged_collection_intent_is_rejected(promotion_body, field, value):
    promotion_body["collection_promotion"][field] = value
    with pytest.raises(ValueError):
        normalize_scan_request(ScanOperationRequest.model_validate(promotion_body))


@pytest.mark.parametrize(
    "policy", [{"metadata_only": True}, {"media_only": True}, {"type": "hashes"}]
)
def test_nonfilesystem_policy_cannot_promote(promotion_body, policy):
    with pytest.raises(ValueError):
        normalize_scan_request(
            ScanOperationRequest.model_validate({**promotion_body, **policy})
        )
