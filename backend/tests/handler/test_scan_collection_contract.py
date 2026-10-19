"""Explicit collection intent remains distinct from ordinary scoped scans."""

import pytest
from pydantic import ValidationError

from endpoints.responses.scan_operations import ScanOperationRequest


def intent(**changes):
    return {
        "parent_rom_id": 12,
        "mapping_id": 4,
        "expected_revision": 2,
        "parent_relative_path": "Castlevania",
        "selected_child_relative_path": "Castlevania/Belmonts.Curse",
        **changes,
    }


def test_explicit_collection_promotion_round_trips():
    body = ScanOperationRequest.model_validate(
        {
            "request_key": "collection-select",
            "filesystem_scope_paths": {"win": "Castlevania/Belmonts.Curse"},
            "collection_promotion": intent(),
        }
    )
    assert body.model_dump()["collection_promotion"] == intent()


@pytest.mark.parametrize("field", ["parent_rom_id", "mapping_id", "expected_revision"])
@pytest.mark.parametrize("value", [0, -1, True, "2"])
def test_collection_intent_requires_strict_positive_identities(field, value):
    with pytest.raises(ValidationError):
        ScanOperationRequest.model_validate(
            {
                "request_key": "invalid-select",
                "collection_promotion": intent(**{field: value}),
            }
        )


@pytest.mark.parametrize(
    "path",
    ["../escape", "/Castlevania", "Castlevania/../other", "Castlevania//child", ""],
)
def test_collection_intent_rejects_unsafe_paths(path):
    with pytest.raises(ValidationError):
        ScanOperationRequest.model_validate(
            {
                "request_key": "invalid-path",
                "collection_promotion": intent(selected_child_relative_path=path),
            }
        )


def test_generic_scope_remains_nondestructive():
    body = ScanOperationRequest.model_validate(
        {
            "request_key": "generic-scope",
            "filesystem_scope_paths": {"win": "Castlevania/Belmonts.Curse"},
        }
    )
    assert body.model_dump().get("collection_promotion") is None
