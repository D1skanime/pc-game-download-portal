from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from endpoints import roms as roms_endpoint
from handler.database.base_handler import sync_session
from models.assets import Save, Screenshot, State
from models.catalog_lifecycle import (
    OwnedCleanupIntent,
    OwnedCleanupState,
    RetainedCatalogIdentity,
)
from models.play_session import PlaySession
from models.rom import Rom, RomFile, RomNote
from models.user import User


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _source_manifest(root: Path) -> tuple[tuple[object, ...], ...]:
    entries: list[tuple[object, ...]] = []
    for path in sorted(root.rglob("*")):
        metadata = path.lstat()
        digest = None
        target = None
        if path.is_symlink():
            target = os.readlink(path)
        elif path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(
            (
                path.relative_to(root).as_posix(),
                metadata.st_mode,
                metadata.st_size,
                digest,
                target,
            )
        )
    return tuple(entries)


def _seed_dependencies(rom: Rom, user: User) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    save = Save(
        rom_id=rom.id,
        user_id=user.id,
        file_name="slot.srm",
        file_path="users/admin/saves/test",
        file_size_bytes=8,
    )
    state = State(
        rom_id=rom.id,
        user_id=user.id,
        file_name="slot.state",
        file_path="users/admin/states/test",
        file_size_bytes=9,
    )
    screenshot = Screenshot(
        rom_id=rom.id,
        user_id=user.id,
        file_name="shot.png",
        file_path="users/admin/screenshots/test",
        file_size_bytes=10,
    )
    play_session = PlaySession(
        rom_id=rom.id,
        user_id=user.id,
        device_id=None,
        start_time=now,
        end_time=now,
        duration_ms=1000,
    )
    note = RomNote(
        rom_id=rom.id,
        user_id=user.id,
        title="Disposable note",
        content="catalog only",
        is_public=False,
    )
    with sync_session.begin() as session:
        session.add_all([save, state, screenshot, play_session, note])
        session.flush()
        return {
            "save": save.id,
            "state": state.id,
            "screenshot": screenshot.id,
            "play_session": play_session.id,
            "note": note.id,
        }


def test_openapi_exposes_ids_only_catalog_removal(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/roms/remove-from-catalog" in paths
    assert "/api/roms/delete" not in paths

    operation = paths["/api/roms/remove-from-catalog"]["post"]
    request_ref = operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    request_name = request_ref.rsplit("/", 1)[-1]
    response_ref = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    response_name = response_ref.rsplit("/", 1)[-1]
    request_schema = schema["components"]["schemas"][request_name]
    response_schema = schema["components"]["schemas"][response_name]
    assert set(request_schema["properties"]) == {"rom_ids"}
    assert "source_files_preserved" in response_schema["properties"]


def test_remove_from_catalog_retains_user_value_and_source_manifest(
    client: TestClient,
    access_token: str,
    admin_user: User,
    rom: Rom,
    rom_file: RomFile,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "game.bin").write_bytes(b"immutable source bytes")
    (source / "nested").mkdir()
    (source / "nested" / "manual.txt").write_text("source manual")
    (source / "link").symlink_to("game.bin")
    before = _source_manifest(source)
    dependency_ids = _seed_dependencies(rom, admin_user)

    response = client.post(
        "/api/roms/remove-from-catalog",
        headers=_headers(access_token),
        json={"rom_ids": [rom.id]},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["successful_items"] == 1
    assert body["failed_ids"] == []
    assert body["source_files_preserved"] is True
    assert body["retained_user_data"] is True
    assert _source_manifest(source) == before

    with sync_session.begin() as session:
        retained = session.scalar(
            select(RetainedCatalogIdentity).where(
                RetainedCatalogIdentity.detached_rom_id == rom.id
            )
        )
        assert retained is not None
        assert retained.active_rom_id is None
        assert retained.platform_id == rom.platform_id
        assert retained.logical_path == rom.fs_path
        assert retained.file_name == rom.fs_name
        assert session.get(Rom, rom.id) is None
        assert session.get(RomFile, rom_file.id) is None
        assert session.get(RomNote, dependency_ids["note"]) is None
        assert session.get(Screenshot, dependency_ids["screenshot"]) is None

        save = session.get(Save, dependency_ids["save"])
        state = session.get(State, dependency_ids["state"])
        play_session = session.get(PlaySession, dependency_ids["play_session"])
        assert save is not None and save.rom_id is None
        assert state is not None and state.rom_id is None
        assert play_session is not None and play_session.rom_id is None
        assert save.retained_catalog_id == retained.id
        assert state.retained_catalog_id == retained.id
        assert play_session.retained_catalog_id == retained.id

        intents = session.scalars(
            select(OwnedCleanupIntent).where(
                OwnedCleanupIntent.retained_catalog_id == retained.id
            )
        ).all()
        assert {intent.kind for intent in intents} == {"resource", "screenshot"}
        assert all(intent.state == OwnedCleanupState.PENDING for intent in intents)


def test_remove_from_catalog_exposes_detached_asset_contract(
    client: TestClient,
    access_token: str,
    admin_user: User,
    rom: Rom,
) -> None:
    dependency_ids = _seed_dependencies(rom, admin_user)

    response = client.post(
        "/api/roms/remove-from-catalog",
        headers=_headers(access_token),
        json={"rom_ids": [rom.id]},
    )
    assert response.status_code == status.HTTP_200_OK

    saves_response = client.get("/api/saves", headers=_headers(access_token))
    states_response = client.get("/api/states", headers=_headers(access_token))

    assert saves_response.status_code == status.HTTP_200_OK
    assert states_response.status_code == status.HTTP_200_OK
    save = next(
        item for item in saves_response.json() if item["id"] == dependency_ids["save"]
    )
    state = next(
        item for item in states_response.json() if item["id"] == dependency_ids["state"]
    )
    assert save["rom_id"] is None
    assert state["rom_id"] is None
    assert isinstance(save["retained_catalog_id"], int)
    assert save["retained_catalog_id"] == state["retained_catalog_id"]

    platform_saves = client.get(
        f"/api/saves?platform_id={rom.platform_id}", headers=_headers(access_token)
    )
    platform_states = client.get(
        f"/api/states?platform_id={rom.platform_id}", headers=_headers(access_token)
    )
    assert [item["id"] for item in platform_saves.json()] == [dependency_ids["save"]]
    assert [item["id"] for item in platform_states.json()] == [dependency_ids["state"]]


def test_source_delete_inputs_and_duplicate_ids_are_rejected(
    client: TestClient, access_token: str, rom: Rom
) -> None:
    old_response = client.post(
        "/api/roms/delete",
        headers=_headers(access_token),
        json={"roms": [rom.id], "delete_from_fs": [rom.id]},
    )
    assert old_response.status_code in {
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
    }

    for payload in (
        {"rom_ids": [rom.id], "delete_from_fs": [rom.id]},
        {"rom_ids": [rom.id, rom.id]},
    ):
        response = client.post(
            "/api/roms/remove-from-catalog",
            headers=_headers(access_token),
            json=payload,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    with sync_session.begin() as session:
        assert session.get(Rom, rom.id) is not None


@pytest.mark.parametrize(
    ("failed_operation", "expected_log_context"),
    (
        ("invalidate_filter_values_cache", "filter cache invalidation"),
        ("refresh_affected_smart_collections", "smart collection refresh"),
    ),
)
def test_remove_from_catalog_preserves_committed_response_on_cache_failure(
    client: TestClient,
    access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
    failed_operation: str,
    expected_log_context: str,
) -> None:
    raw_failure = "/secret/source/game.bin dependent service failure"
    invalidate = Mock()
    refresh = Mock()
    if failed_operation == "invalidate_filter_values_cache":
        invalidate.side_effect = RuntimeError(raw_failure)
    else:
        refresh.side_effect = RuntimeError(raw_failure)
    monkeypatch.setattr(
        roms_endpoint.db_rom_handler,
        "invalidate_filter_values_cache",
        invalidate,
    )
    monkeypatch.setattr(
        roms_endpoint,
        "refresh_affected_smart_collections",
        refresh,
    )
    log_error = Mock()
    monkeypatch.setattr(roms_endpoint.log, "error", log_error)

    response = client.post(
        "/api/roms/remove-from-catalog",
        headers=_headers(access_token),
        json={"rom_ids": [rom.id]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["successful_items"] == 1
    assert response.json()["failed_ids"] == []
    assert [item["rom_id"] for item in response.json()["items"]] == [rom.id]
    invalidate.assert_called_once_with()
    refresh.assert_called_once_with([rom.id])
    messages = [str(call.args[0]) for call in log_error.call_args_list]
    assert any(expected_log_context in message for message in messages)
    assert all(raw_failure not in message for message in messages)


def test_remove_from_catalog_authorizes_before_observation(
    client: TestClient,
    viewer_access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler

    observation = Mock(side_effect=AssertionError("catalog observed"))
    monkeypatch.setattr(CatalogLifecycleHandler, "remove_from_catalog", observation)

    response = client.post(
        "/api/roms/remove-from-catalog",
        headers=_headers(viewer_access_token),
        json={"rom_ids": [rom.id]},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    observation.assert_not_called()


def test_injected_failure_rolls_back_without_disclosure(
    client: TestClient,
    access_token: str,
    admin_user: User,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler

    dependencies = _seed_dependencies(rom, admin_user)

    def fail_after_retention(*_args, **_kwargs):
        raise RuntimeError("/secret/source/path raw database failure")

    monkeypatch.setattr(
        CatalogLifecycleHandler,
        "_before_catalog_delete",
        fail_after_retention,
    )
    response = client.post(
        "/api/roms/remove-from-catalog",
        headers=_headers(access_token),
        json={"rom_ids": [rom.id]},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["successful_items"] == 0
    assert body["failed_ids"] == [rom.id]
    assert body["errors"] == [
        {
            "rom_id": rom.id,
            "code": "catalog_removal_failed",
            "message": "Catalog removal failed",
        }
    ]
    assert "/secret" not in response.text
    assert "database failure" not in response.text

    with sync_session.begin() as session:
        assert session.get(Rom, rom.id) is not None
        assert session.get(Save, dependencies["save"]).rom_id == rom.id
        assert session.get(State, dependencies["state"]).rom_id == rom.id
        assert session.get(PlaySession, dependencies["play_session"]).rom_id == rom.id
        assert session.scalar(select(RetainedCatalogIdentity)) is None
        assert session.scalar(select(OwnedCleanupIntent)) is None


@pytest.mark.asyncio
async def test_owned_cleanup_failure_is_persisted_and_retryable(
    client: TestClient,
    access_token: str,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tasks.manual.cleanup_catalog_assets import CleanupCatalogAssetsTask

    response = client.post(
        "/api/roms/remove-from-catalog",
        headers=_headers(access_token),
        json={"rom_ids": [rom.id]},
    )
    assert response.status_code == status.HTTP_200_OK

    remove_directory = AsyncMock(
        side_effect=[OSError("/secret/owned/path unavailable"), None]
    )
    monkeypatch.setattr(
        "tasks.manual.cleanup_catalog_assets.fs_resource_handler.remove_directory",
        remove_directory,
    )

    first = await CleanupCatalogAssetsTask().run(limit=1)
    assert first == {"completed": 0, "failed": 1, "pending": 1}
    with sync_session.begin() as session:
        intent = session.scalar(select(OwnedCleanupIntent))
        assert intent is not None
        assert intent.state == OwnedCleanupState.FAILED
        assert intent.attempt_count == 1
        assert "/secret" not in (intent.safe_error or "")

    second = await CleanupCatalogAssetsTask().run(limit=1)
    assert second == {"completed": 1, "failed": 0, "pending": 0}
    with sync_session.begin() as session:
        intent = session.scalar(select(OwnedCleanupIntent))
        assert intent is not None
        assert intent.state == OwnedCleanupState.COMPLETED
        assert intent.attempt_count == 2


def test_concurrent_removal_creates_one_retained_identity(
    admin_user: User, rom: Rom
) -> None:
    from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler

    barrier = Barrier(2)

    def remove() -> object:
        barrier.wait()
        return CatalogLifecycleHandler().remove_from_catalog(
            rom.id, actor_user_id=admin_user.id
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _index: remove(), range(2)))

    assert sum(outcome is not None for outcome in outcomes) == 1
    with sync_session.begin() as session:
        retained = session.scalars(
            select(RetainedCatalogIdentity).where(
                RetainedCatalogIdentity.detached_rom_id == rom.id
            )
        ).all()
        assert len(retained) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("read_only", [False, True])
async def test_remove_then_production_scan_reconnects_retained_user_value(
    client: TestClient,
    access_token: str,
    admin_user: User,
    rom: Rom,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    read_only: bool,
) -> None:
    from endpoints.sockets import scan as scan_module
    from handler.filesystem.roms_handler import FSRom, ParsedRomFiles, ParsedTags
    from handler.scan_handler import ScanType

    dependencies = _seed_dependencies(rom, admin_user)
    old_rom_id = rom.id
    platform = rom.platform
    logical_path = rom.fs_path
    file_name = rom.fs_name
    hashes = (rom.crc_hash, rom.md5_hash, rom.sha1_hash)

    source = tmp_path / "source"
    source.mkdir()
    (source / "game.bin").write_bytes(b"immutable source bytes")
    (source / "nested").mkdir()
    (source / "nested" / "manual.txt").write_text("source manual")
    (source / "link").symlink_to("game.bin")
    if read_only:
        (source / "game.bin").chmod(0o444)
        (source / "nested" / "manual.txt").chmod(0o444)
        (source / "nested").chmod(0o555)
        source.chmod(0o555)
    source_before = _source_manifest(source)

    response = client.post(
        "/api/roms/remove-from-catalog",
        headers=_headers(access_token),
        json={"rom_ids": [old_rom_id]},
    )
    assert response.status_code == status.HTTP_200_OK

    detached_saves = client.get("/api/saves", headers=_headers(access_token))
    detached_states = client.get("/api/states", headers=_headers(access_token))
    assert detached_saves.status_code == status.HTTP_200_OK
    assert detached_states.status_code == status.HTTP_200_OK
    detached_save = next(
        item for item in detached_saves.json() if item["id"] == dependencies["save"]
    )
    detached_state = next(
        item for item in detached_states.json() if item["id"] == dependencies["state"]
    )
    assert detached_save["rom_id"] is None
    assert detached_state["rom_id"] is None
    assert detached_save["retained_catalog_id"] == detached_state["retained_catalog_id"]

    monkeypatch.setattr(scan_module, "redis_client", Mock(get=Mock(return_value=None)))
    monkeypatch.setattr(
        scan_module.fs_rom_handler,
        "parse_tags",
        Mock(
            return_value=ParsedTags(
                version="", revision="", regions=[], languages=[], other_tags=[]
            )
        ),
    )
    monkeypatch.setattr(
        scan_module.fs_rom_handler,
        "get_roms_fs_structure",
        Mock(return_value=logical_path),
    )
    monkeypatch.setattr(
        scan_module.fs_rom_handler,
        "get_file_name_with_no_tags",
        Mock(return_value=rom.name),
    )
    monkeypatch.setattr(
        scan_module.fs_rom_handler,
        "get_rom_files",
        AsyncMock(
            return_value=ParsedRomFiles(
                rom_files=[],
                crc_hash=hashes[0],
                md5_hash=hashes[1],
                sha1_hash=hashes[2],
                ra_hash="",
            )
        ),
    )
    config = Mock(SKIP_HASH_CALCULATION=False)
    monkeypatch.setattr(scan_module.cm, "get_config", Mock(return_value=config))

    async def scan_without_external_metadata(**kwargs):
        scanned = kwargs["rom"]
        scanned.crc_hash, scanned.md5_hash, scanned.sha1_hash = hashes
        return scanned

    monkeypatch.setattr(
        scan_module, "scan_rom", AsyncMock(side_effect=scan_without_external_metadata)
    )

    fs_rom: FSRom = {
        "fs_name": file_name,
        "flat": True,
        "nested": False,
        "files": [],
        "crc_hash": "",
        "md5_hash": "",
        "sha1_hash": "",
        "ra_hash": "",
    }
    real_reconnect = scan_module.catalog_lifecycle_handler.reconnect_retained_identity
    reconnect_attempt = 0

    def fail_once_then_reconnect(**kwargs):
        nonlocal reconnect_attempt
        reconnect_attempt += 1
        if reconnect_attempt == 1:
            raise RuntimeError("injected post-insert reconnect failure")
        return real_reconnect(**kwargs)

    monkeypatch.setattr(
        scan_module.catalog_lifecycle_handler,
        "reconnect_retained_identity",
        fail_once_then_reconnect,
    )

    with pytest.raises(RuntimeError, match="injected post-insert reconnect failure"):
        await scan_module._identify_rom(
            platform=platform,
            fs_rom=fs_rom,
            rom=None,
            scan_type=ScanType.HASHES,
            roms_ids=[],
            metadata_sources=[],
            launchbox_remote_enabled=False,
            playmatch_enabled=False,
            socket_manager=AsyncMock(),
            scan_stats=AsyncMock(),
        )

    with sync_session() as session:
        persisted = session.scalar(
            select(Rom).where(
                Rom.platform_id == platform.id,
                Rom.fs_name == file_name,
            )
        )
        retained = session.scalar(
            select(RetainedCatalogIdentity).where(
                RetainedCatalogIdentity.detached_rom_id == old_rom_id
            )
        )
        assert persisted is not None and persisted.id != old_rom_id
        assert retained is not None and retained.active_rom_id is None
        persisted_id = persisted.id
        for model, key in (
            (Save, "save"),
            (State, "state"),
            (PlaySession, "play_session"),
        ):
            row = session.get(model, dependencies[key])
            assert (row.rom_id, row.retained_catalog_id) == (
                None,
                retained.id,
            )

    await scan_module._identify_rom(
        platform=platform,
        fs_rom=fs_rom,
        rom=persisted,
        scan_type=ScanType.HASHES,
        roms_ids=[],
        metadata_sources=[],
        launchbox_remote_enabled=False,
        playmatch_enabled=False,
        socket_manager=AsyncMock(),
        scan_stats=AsyncMock(),
    )

    with sync_session() as session:
        reconnected = session.scalar(
            select(Rom).where(
                Rom.platform_id == platform.id,
                Rom.fs_name == file_name,
            )
        )
        retained = session.scalar(
            select(RetainedCatalogIdentity).where(
                RetainedCatalogIdentity.detached_rom_id == old_rom_id
            )
        )
        assert reconnected is not None and reconnected.id == persisted_id
        assert retained is not None and retained.active_rom_id == reconnected.id
        for model, key in (
            (Save, "save"),
            (State, "state"),
            (PlaySession, "play_session"),
        ):
            row = session.get(model, dependencies[key])
            assert (row.rom_id, row.retained_catalog_id) == (
                reconnected.id,
                None,
            )
    assert _source_manifest(source) == source_before
