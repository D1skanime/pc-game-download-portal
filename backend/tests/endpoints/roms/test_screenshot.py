from pathlib import Path

import pytest
from fastapi import HTTPException

from endpoints.storage_policy import authorize_api_storage_operation
from handler.filesystem import legacy_external_storage
from handler.filesystem.storage_policy import StorageOperation


@pytest.mark.parametrize(
    "operation", [StorageOperation.COVER_WRITE, StorageOperation.DELETE]
)
def test_external_mutation_is_bounded_and_precedes_io(operation, monkeypatch):
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("filesystem reached")

    monkeypatch.setattr(Path, "open", forbidden)
    with pytest.raises(HTTPException) as error:
        authorize_api_storage_operation(operation, legacy_external_storage)
    assert error.value.status_code == 403
    assert error.value.detail["code"] == "external_storage_operation_denied"
    assert set(error.value.detail) == {
        "code",
        "operation",
        "storage_class",
        "storage_id",
    }
    assert not touched
