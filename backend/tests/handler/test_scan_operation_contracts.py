"""Operation schema and pure transition contract regressions."""

import pytest

from models.base import BaseModel


def test_operation_tables_registered():
    import models  # noqa: F401

    assert {"scan_operations", "scan_operation_items", "scan_execution_slot"} <= set(
        BaseModel.metadata.tables
    ), "durable operation schema is absent"


def test_transition_contracts():
    from handler.scan_operation_state import validate_transition

    validate_transition("accepted", "queued", lease=False, confirmed_stop=False)
    validate_transition("queued", "running", lease=True, confirmed_stop=False)
    for source, target, lease, stopped in (
        ("accepted", "running", False, False),
        ("running", "cancelled", True, False),
        ("cancelled", "recovering", False, False),
        ("completed", "running", True, False),
    ):
        with pytest.raises(ValueError):
            validate_transition(source, target, lease=lease, confirmed_stop=stopped)


def test_request_and_snapshot_reject_client_authority():
    from pydantic import ValidationError

    from endpoints.responses.scan_operations import ScanOperationRequest

    for field in ("actor_id", "state", "lease_owner", "source_evidence"):
        with pytest.raises(ValidationError):
            ScanOperationRequest(
                request_key="contract-test", platforms=[1], **{field: "untrusted"}
            )
    with pytest.raises(ValidationError):
        ScanOperationRequest(request_key="../unsafe", platforms=[1])
