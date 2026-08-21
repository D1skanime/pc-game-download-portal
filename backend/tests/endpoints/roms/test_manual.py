from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from config import RESOURCES_BASE_PATH
from endpoints.storage_policy import authorize_api_storage_operation
from handler.database import db_rom_handler
from handler.filesystem import legacy_external_storage
from handler.filesystem.storage_policy import StorageOperation
from models.rom import Rom


@pytest.mark.parametrize(
    "operation", [StorageOperation.SIDECAR_WRITE, StorageOperation.DELETE]
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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload_primary_manual(
    client: TestClient, token: str, rom_id: int, filename: str, content: bytes
):
    return client.post(
        f"/api/roms/{rom_id}/manuals",
        headers={**_auth(token), "x-upload-filename": filename},
        files={filename: (filename, content, "application/pdf")},
    )


def test_primary_manual_concurrent_replacement_has_one_winner(
    client: TestClient,
    access_token: str,
    rom: Rom,
):
    manual_dir = Path(RESOURCES_BASE_PATH, rom.fs_resources_path, "manual")
    manual_dir.mkdir(parents=True, exist_ok=True)
    prior = manual_dir / "prior.pdf"
    prior.write_bytes(b"prior-complete")
    db_rom_handler.update_rom(
        rom.id, {"path_manual": f"{rom.fs_resources_path}/manual/prior.pdf"}
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda item: _upload_primary_manual(
                    client, access_token, rom.id, item[0], item[1]
                ),
                (("first.pdf", b"first-complete"), ("second.pdf", b"second-complete")),
            )
        )

    assert sorted(response.status_code for response in responses) == [
        status.HTTP_201_CREATED,
        status.HTTP_409_CONFLICT,
    ]
    current = db_rom_handler.get_rom(rom.id)
    assert current is not None
    winner = Path(RESOURCES_BASE_PATH, current.path_manual)
    assert winner.read_bytes() in {b"first-complete", b"second-complete"}
    assert not prior.exists()
    assert sorted(path.name for path in manual_dir.iterdir()) == [winner.name]
