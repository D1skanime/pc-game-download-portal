"""Real SQL authority and atomic collection retirement regression."""

from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from tests.endpoints.test_scan_operations import mapped  # noqa: F401
from tests.handler.test_scan_collection_policy import (
    promotion_body as promotion_body_fixture,
)
from tests.handler.test_scan_operations import running

from endpoints.responses.scan_operations import ScanOperationRequest
from handler.database.base_handler import sync_session
from handler.database.scan_operations_handler import DBScanOperationsHandler
from handler.database.scan_write_fence import ScanWriteContext, bind_scan_write_context
from handler.scan_operation_checkpoint import (
    bind_checkpoint_command,
    record_completed_game,
)
from handler.scan_operation_commands import normalize_scan_request
from models.rom import Rom, RomFile, RomNote
from models.scan_collection import ScanCollectionFolder

promotion_body = promotion_body_fixture


def prepare_attempt(promotion_body, admin_user):
    normalized = normalize_scan_request(
        ScanOperationRequest.model_validate(promotion_body)
    )
    repository = DBScanOperationsHandler()
    attempt = running(repository, admin_user, normalized)
    with sync_session.begin() as session:
        parent = session.get(
            Rom, promotion_body["collection_promotion"]["parent_rom_id"]
        )
        child = Rom(
            platform_id=parent.platform_id,
            name="Belmonts Curse",
            fs_path="PC/Castlevania",
            fs_name="Belmonts.Curse",
        )
        session.add(child)
        session.add(
            RomNote(
                rom_id=parent.id,
                user_id=admin_user.id,
                title="Retain me",
                content="Parent operator context",
                is_public=False,
            )
        )
        session.flush()
        session.add(
            RomFile(
                rom_id=child.id,
                file_name="game.rar",
                file_path="PC/Castlevania/Belmonts.Curse",
                file_size_bytes=4,
            )
        )
        child_id = child.id
    return repository, attempt, child_id


def complete(attempt, child_id):
    repository = DBScanOperationsHandler()
    execution = repository.execution(attempt.id)
    raw = execution["command"]["commands"][0]
    command = SimpleNamespace(
        mapping_id=raw["mapping_id"],
        expected_revision=raw["expected_revision"],
        options=raw["options"],
    )
    with sync_session() as session:
        child = session.get(Rom, child_id)
    with bind_scan_write_context(
        ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    ), bind_checkpoint_command(command):
        record_completed_game(child)


def test_successful_child_completion_retires_parent_atomically(
    promotion_body, admin_user
):
    repository, attempt, child_id = prepare_attempt(promotion_body, admin_user)
    complete(attempt, child_id)
    with sync_session() as session:
        assert (
            session.get(Rom, promotion_body["collection_promotion"]["parent_rom_id"])
            is None
        )
        classification = session.scalar(select(ScanCollectionFolder))
        assert classification.parent_relative_path == "Castlevania"
        assert (
            classification.selected_child_relative_path == "Castlevania/Belmonts.Curse"
        )
        assert classification.audit["notes"][0]["content"] == "Parent operator context"
    assert (
        repository.execution(attempt.id)["checkpoint"]["committed_rom_id"] == child_id
    )


def test_failure_before_parent_retirement_rolls_back_classification_and_checkpoint(
    promotion_body, admin_user, monkeypatch
):
    from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler

    repository, attempt, child_id = prepare_attempt(promotion_body, admin_user)

    def fail(*args, **kwargs):
        raise RuntimeError("before-retirement")

    monkeypatch.setattr(CatalogLifecycleHandler, "_before_catalog_delete", fail)
    with pytest.raises(RuntimeError, match="before-retirement"):
        complete(attempt, child_id)
    with sync_session() as session:
        assert (
            session.get(Rom, promotion_body["collection_promotion"]["parent_rom_id"])
            is not None
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ScanCollectionFolder)
                .where(
                    ScanCollectionFolder.mapping_id
                    == promotion_body["collection_promotion"]["mapping_id"]
                )
            )
            == 0
        )
    assert repository.execution(attempt.id)["checkpoint"] == {}


def test_success_replay_is_idempotent_and_parent_cannot_be_republished(
    promotion_body, admin_user
):
    from handler.database import db_rom_handler
    from handler.database.scan_write_fence import ScanWriteRejected
    from models.catalog_lifecycle import OwnedCleanupIntent, RetainedCatalogIdentity

    repository, attempt, child_id = prepare_attempt(promotion_body, admin_user)
    complete(attempt, child_id)
    complete(attempt, child_id)
    parent_id = promotion_body["collection_promotion"]["parent_rom_id"]
    raw = repository.execution(attempt.id)["command"]["commands"][0]
    command = SimpleNamespace(
        mapping_id=raw["mapping_id"],
        expected_revision=raw["expected_revision"],
        options=raw["options"],
    )
    with bind_scan_write_context(
        ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    ), bind_checkpoint_command(command):
        with pytest.raises(ScanWriteRejected, match="classified_collection_not_game"):
            db_rom_handler.add_rom(
                Rom(
                    id=parent_id,
                    platform_id=promotion_body["platforms"][0],
                    fs_name="Castlevania",
                    fs_path="PC",
                    name="Stale parent",
                )
            )
    with sync_session() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(ScanCollectionFolder)
                .where(
                    ScanCollectionFolder.mapping_id
                    == promotion_body["collection_promotion"]["mapping_id"]
                )
            )
            == 1
        )
        assert (
            session.scalar(select(func.count()).select_from(RetainedCatalogIdentity))
            == 1
        )
        assert session.scalar(select(func.count()).select_from(OwnedCleanupIntent)) == 1
        assert session.get(Rom, parent_id) is None


@pytest.mark.parametrize("revocation", ["cancel", "remap", "lease"])
def test_revoked_attempt_preserves_parent_and_has_no_classification(
    promotion_body, admin_user, revocation
):
    from datetime import timedelta

    from handler.database.scan_operations_handler import utc_now
    from models.scan_operation import ScanOperation
    from models.storage import PlatformStorageMapping

    repository, attempt, child_id = prepare_attempt(promotion_body, admin_user)
    if revocation == "cancel":
        repository.request_cancel(
            attempt.id, admin_user.id, attempt.version, "cancel-promotion"
        )
    else:
        with sync_session.begin() as session:
            if revocation == "remap":
                session.get(
                    PlatformStorageMapping,
                    promotion_body["collection_promotion"]["mapping_id"],
                ).version += 1
            else:
                session.get(ScanOperation, attempt.id).lease_expires_at = (
                    utc_now() - timedelta(seconds=1)
                )
    from exceptions.storage_read import StaleMappedReadError
    from handler.database.scan_write_fence import ScanWriteRejected

    with pytest.raises((ScanWriteRejected, StaleMappedReadError)):
        complete(attempt, child_id)
    with sync_session() as session:
        assert (
            session.get(Rom, promotion_body["collection_promotion"]["parent_rom_id"])
            is not None
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ScanCollectionFolder)
                .where(
                    ScanCollectionFolder.mapping_id
                    == promotion_body["collection_promotion"]["mapping_id"]
                )
            )
            == 0
        )
    assert repository.execution(attempt.id)["checkpoint"] == {}


def test_empty_child_cannot_retire_parent(promotion_body, admin_user):
    from sqlalchemy import update

    repository, attempt, child_id = prepare_attempt(promotion_body, admin_user)
    with sync_session.begin() as session:
        session.execute(
            update(RomFile)
            .where(RomFile.rom_id == child_id)
            .values(missing_from_fs=True)
        )
    with pytest.raises(ValueError, match="collection_child_empty"):
        complete(attempt, child_id)
    with sync_session() as session:
        assert (
            session.get(Rom, promotion_body["collection_promotion"]["parent_rom_id"])
            is not None
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ScanCollectionFolder)
                .where(
                    ScanCollectionFolder.mapping_id
                    == promotion_body["collection_promotion"]["mapping_id"]
                )
            )
            == 0
        )
