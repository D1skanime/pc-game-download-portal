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


@pytest.fixture(autouse=True)
def clear_catalog_lifecycle_rows():
    yield
    with sync_session.begin() as session:
        session.query(OwnedCleanupIntent).delete(synchronize_session=False)
        session.query(RetainedCatalogIdentity).delete(synchronize_session=False)


def test_openapi_exposes_ids_only_catalog_removal(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/roms/remove-from-catalog" in paths
    assert "/api/roms/delete" not in paths

    operation = paths["/api/roms/remove-from-catalog"]["post"]
    serialized = str(operation)
    assert "rom_ids" in serialized
    assert "delete_from_fs" not in serialized
    assert "source_files_preserved" in serialized


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


def test_source_delete_inputs_and_duplicate_ids_are_rejected(
    client: TestClient, access_token: str, rom: Rom
) -> None:
    old_response = client.post(
        "/api/roms/delete",
        headers=_headers(access_token),
        json={"roms": [rom.id], "delete_from_fs": [rom.id]},
    )
    assert old_response.status_code == status.HTTP_404_NOT_FOUND

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
