import hashlib
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

import httpx
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

import endpoints.roms.manual as manual_endpoint
from config import LAUNCHBOX_BASE_PATH, LIBRARY_BASE_PATH, RESOURCES_BASE_PATH
from endpoints.storage_policy import authorize_api_storage_operation
from handler.database import db_primary_manual_handler, db_rom_handler
from handler.filesystem import legacy_external_storage, storage_composition
from handler.filesystem.resources_handler import FSResourcesHandler
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
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
    monkeypatch: pytest.MonkeyPatch,
):
    manual_dir = Path(RESOURCES_BASE_PATH, rom.fs_resources_path, "manual")
    manual_dir.mkdir(parents=True, exist_ok=True)
    prior = manual_dir / "prior.pdf"
    prior.write_bytes(b"prior-complete")
    db_rom_handler.update_rom(
        rom.id, {"path_manual": f"{rom.fs_resources_path}/manual/prior.pdf"}
    )

    barrier = Barrier(2)
    original_cas = db_primary_manual_handler.compare_and_swap_path

    def synchronized_cas(*args, **kwargs):
        assert prior.read_bytes() == b"prior-complete"
        barrier.wait(timeout=5)
        return original_cas(*args, **kwargs)

    monkeypatch.setattr(
        db_primary_manual_handler, "compare_and_swap_path", synchronized_cas
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda item: _upload_primary_manual(
                    TestClient(client.app), access_token, rom.id, item[0], item[1]
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


class _ManualResponse:
    def __init__(self, content: bytes, *, fail_after_first_chunk: bool = False):
        self.status_code = status.HTTP_200_OK
        self.headers = {"content-type": "application/pdf"}
        self._content = content
        self._fail_after_first_chunk = fail_after_first_chunk

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def aiter_raw(self):
        if self._fail_after_first_chunk:
            yield self._content[:4]
            raise httpx.ReadError(
                "connection lost",
                request=httpx.Request("GET", "https://cdn.example/manual.pdf"),
            )
        yield self._content


class _ManualClient:
    def __init__(self, response: _ManualResponse):
        self._response = response

    def stream(self, *_args, **_kwargs):
        return self._response


def _manual_directory(rom: Rom) -> Path:
    path = Path(RESOURCES_BASE_PATH, rom.fs_resources_path, "manual")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _set_prior_manual(rom: Rom, content: bytes = b"prior-complete") -> tuple[str, Path]:
    manual_dir = _manual_directory(rom)
    path = manual_dir / "prior.pdf"
    path.write_bytes(content)
    relative = f"{rom.fs_resources_path}/manual/prior.pdf"
    db_rom_handler.update_rom(
        rom.id,
        {
            "path_manual": relative,
            "url_manual": "https://cdn.example/manual.pdf",
        },
    )
    return relative, path


def _manual_inventory(manual_dir: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(manual_dir.iterdir(), key=lambda item: item.name)
        if path.is_file()
    }


def _source_record(path: Path) -> tuple[int, int, int, str]:
    metadata = path.stat()
    return (
        stat.S_IMODE(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _redownload(client: TestClient, token: str, rom_id: int):
    return client.post(f"/api/roms/{rom_id}/manuals/redownload", headers=_auth(token))


def test_uploaded_token_manual_survives_restart_and_deletes_exactly(
    client: TestClient,
    access_token: str,
    rom: Rom,
):
    for extension in (".pdf", ".md"):
        uploaded = _upload_primary_manual(
            client,
            access_token,
            rom.id,
            f"primary{extension}",
            f"complete-{extension}".encode(),
        )
        assert uploaded.status_code == status.HTTP_201_CREATED

        current = db_rom_handler.get_rom(rom.id)
        assert current is not None
        token_path = current.path_manual
        assert token_path
        assert token_path.endswith(extension)
        token_file = Path(RESOURCES_BASE_PATH, token_path)
        sibling = token_file.parent / f"sibling{extension}"
        sibling.write_bytes(b"sibling")
        db_rom_handler.update_rom(
            rom.id, {"url_manual": "https://cdn.example/manual.pdf"}
        )

        restarted = FSResourcesHandler(
            storage_composition.owned[OwnedStorageKind.RESOURCES]
        )
        assert restarted.manual_exists(db_rom_handler.get_rom(rom.id))
        assert restarted._get_manual_path(db_rom_handler.get_rom(rom.id)) == token_path

        with TestClient(client.app) as restarted_client:
            deleted = restarted_client.delete(
                f"/api/roms/{rom.id}/manuals", headers=_auth(access_token)
            )
        assert deleted.status_code == status.HTTP_200_OK
        refreshed = db_rom_handler.get_rom(rom.id)
        assert refreshed is not None
        assert refreshed.path_manual == ""
        assert refreshed.url_manual == ""
        assert not token_file.exists()
        assert sibling.read_bytes() == b"sibling"
        sibling.unlink()


def test_missing_owned_token_manual_clears_exact_authoritative_reference(
    client: TestClient,
    access_token: str,
    rom: Rom,
):
    manual_dir = _manual_directory(rom)
    missing_path = f"{rom.fs_resources_path}/manual/missing-token.pdf"
    sibling = manual_dir / "sibling.pdf"
    sibling.write_bytes(b"keep")
    db_rom_handler.update_rom(
        rom.id,
        {
            "path_manual": missing_path,
            "url_manual": "https://cdn.example/manual.pdf",
        },
    )

    response = client.delete(f"/api/roms/{rom.id}/manuals", headers=_auth(access_token))

    assert response.status_code == status.HTTP_200_OK
    refreshed = db_rom_handler.get_rom(rom.id)
    assert refreshed is not None
    assert refreshed.path_manual == ""
    assert refreshed.url_manual == ""
    assert sibling.read_bytes() == b"keep"


def test_invalid_primary_manual_reference_is_never_deleted(
    client: TestClient,
    access_token: str,
    rom: Rom,
):
    manual_dir = _manual_directory(rom)
    sibling = manual_dir / "sibling.pdf"
    sibling.write_bytes(b"keep")
    db_rom_handler.update_rom(
        rom.id,
        {
            "path_manual": f"{rom.fs_resources_path}/../escape.pdf",
            "url_manual": "https://cdn.example/manual.pdf",
        },
    )

    response = client.delete(f"/api/roms/{rom.id}/manuals", headers=_auth(access_token))

    assert response.status_code in {
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    }
    refreshed = db_rom_handler.get_rom(rom.id)
    assert refreshed is not None
    assert refreshed.path_manual.endswith("../escape.pdf")
    assert refreshed.url_manual == "https://cdn.example/manual.pdf"
    assert sibling.read_bytes() == b"keep"


def test_primary_manual_cas_failure_preserves_prior_path_and_cleans_candidate(
    client: TestClient,
    access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
):
    prior_path, prior = _set_prior_manual(rom)
    manual_dir = prior.parent
    client.app.state.httpx_client = _ManualClient(
        _ManualResponse(b"redownload-complete")
    )
    monkeypatch.setattr(
        db_primary_manual_handler,
        "compare_and_swap_path",
        lambda *_args, **_kwargs: False,
    )

    response = _redownload(client, access_token, rom.id)

    assert response.status_code == status.HTTP_409_CONFLICT
    current = db_rom_handler.get_rom(rom.id)
    assert current is not None
    assert current.path_manual == prior_path
    assert prior.read_bytes() == b"prior-complete"
    assert _manual_inventory(manual_dir) == {"prior.pdf": b"prior-complete"}


@pytest.mark.parametrize("failure", ["transport", "write"])
def test_http_redownload_failure_preserves_prior_and_leaves_no_orphan(
    client: TestClient,
    access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
):
    prior_path, prior = _set_prior_manual(rom)
    manual_dir = prior.parent
    client.app.state.httpx_client = _ManualClient(
        _ManualResponse(
            b"redownload-complete", fail_after_first_chunk=failure == "transport"
        )
    )

    if failure == "write":

        def fail_binary_file(_self):
            raise OSError("write failed")

        monkeypatch.setattr(
            manual_endpoint.OwnedCreate, "binary_file", fail_binary_file
        )

    response = _redownload(client, access_token, rom.id)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    current = db_rom_handler.get_rom(rom.id)
    assert current is not None
    assert current.path_manual == prior_path
    assert prior.read_bytes() == b"prior-complete"
    assert _manual_inventory(manual_dir) == {"prior.pdf": b"prior-complete"}


def _run_upload_redownload_race(
    client: TestClient,
    access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
    *,
    first_content: bytes,
):
    _prior_path, prior = _set_prior_manual(rom)
    manual_dir = prior.parent
    upload_content = b"upload-complete"
    redownload_content = b"redownload-complete"
    client.app.state.httpx_client = _ManualClient(_ManualResponse(redownload_content))
    original_cas = db_primary_manual_handler.compare_and_swap_path
    barrier = Barrier(2)
    first_finished = Event()

    def ordered_cas(*args, **kwargs):
        candidate = Path(RESOURCES_BASE_PATH, kwargs["new_path"])
        content = candidate.read_bytes()
        barrier.wait(timeout=10)
        if content == first_content:
            try:
                return original_cas(*args, **kwargs)
            finally:
                first_finished.set()
        assert first_finished.wait(timeout=10)
        return original_cas(*args, **kwargs)

    monkeypatch.setattr(db_primary_manual_handler, "compare_and_swap_path", ordered_cas)

    with ThreadPoolExecutor(max_workers=2) as executor:
        upload_future = executor.submit(
            _upload_primary_manual,
            TestClient(client.app),
            access_token,
            rom.id,
            "upload.pdf",
            upload_content,
        )
        redownload_future = executor.submit(
            _redownload, TestClient(client.app), access_token, rom.id
        )
        responses = [upload_future.result(), redownload_future.result()]

    assert sorted(response.status_code for response in responses) == [
        (
            status.HTTP_200_OK
            if first_content == redownload_content
            else status.HTTP_201_CREATED
        ),
        status.HTTP_409_CONFLICT,
    ]
    current = db_rom_handler.get_rom(rom.id)
    assert current is not None
    winner = Path(RESOURCES_BASE_PATH, current.path_manual)
    assert winner.read_bytes() == first_content
    assert not prior.exists()
    assert _manual_inventory(manual_dir) == {winner.name: first_content}


def test_upload_first_redownload_race_has_one_winner_and_no_orphan(
    client: TestClient,
    access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
):
    _run_upload_redownload_race(
        client,
        access_token,
        rom,
        monkeypatch,
        first_content=b"upload-complete",
    )


def test_redownload_first_upload_race_has_one_winner_and_no_orphan(
    client: TestClient,
    access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
):
    _run_upload_redownload_race(
        client,
        access_token,
        rom,
        monkeypatch,
        first_content=b"redownload-complete",
    )


@pytest.mark.parametrize(
    ("scheme", "base_path"),
    [
        pytest.param("file", Path(LIBRARY_BASE_PATH), id="file"),
        pytest.param("launchbox-file", Path(LAUNCHBOX_BASE_PATH), id="launchbox-file"),
    ],
)
def test_local_uri_redownload_uses_staged_cas_and_preserves_source(
    client: TestClient,
    access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
    scheme: str,
    base_path: Path,
):
    source = base_path / f"manual-source-{rom.id}.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"read-only-source")
    source.chmod(0o444)
    before = _source_record(source)
    prior_path, prior = _set_prior_manual(rom)
    db_rom_handler.update_rom(
        rom.id,
        {"url_manual": f"{scheme}://{source.name}"},
    )

    try:
        response = _redownload(client, access_token, rom.id)
        assert response.status_code == status.HTTP_200_OK
        current = db_rom_handler.get_rom(rom.id)
        assert current is not None
        assert current.path_manual != prior_path
        assert Path(current.path_manual).name != f"{rom.id}.pdf"
        winner = Path(RESOURCES_BASE_PATH, current.path_manual)
        assert winner.read_bytes() == b"read-only-source"
        assert not prior.exists()
        assert _source_record(source) == before

        monkeypatch.setattr(
            db_primary_manual_handler,
            "compare_and_swap_path",
            lambda *_args, **_kwargs: False,
        )
        losing = _redownload(client, access_token, rom.id)
        assert losing.status_code == status.HTTP_409_CONFLICT
        after_failure = db_rom_handler.get_rom(rom.id)
        assert after_failure is not None
        assert after_failure.path_manual == current.path_manual
        assert winner.read_bytes() == b"read-only-source"
        assert _manual_inventory(winner.parent) == {winner.name: b"read-only-source"}
        assert _source_record(source) == before
    finally:
        source.chmod(0o644)
        source.unlink(missing_ok=True)
