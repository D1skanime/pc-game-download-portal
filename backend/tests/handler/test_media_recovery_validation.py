"""Malformed recovery evidence stays isolated from independent cleanup."""

import json

import pytest
from sqlalchemy import select
from tests.handler.test_scan_media_publication import (
    attempt,
    batch,
    cancel,
    command,
    prepare,
    read,
    recovery,
)
from tests.handler.test_scan_operations import repository
from tests.handler.test_scan_write_fence import context

from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.storage_access import (
    OwnedCreate,
    OwnedReplace,
    open_owned_access,
)
from handler.filesystem.storage_policy import StorageOperation
from models.owned_media_cleanup import OwnedMediaCleanupIntent, OwnedMediaCleanupState
from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task


def replace_receipt(unit, change=None, raw=None):
    root = fs_resource_handler.validate_path(unit.manifest_directory)
    receipt = sorted(root.glob("receipt-*.json"))[-1]
    document = json.loads(receipt.read_bytes())
    if change:
        change(document)
    data = raw if raw is not None else json.dumps(document).encode()
    relative = unit.manifest_directory + "/" + receipt.name
    with open_owned_access(
        unit.storage, StorageOperation.OVERWRITE, relative
    ) as access:
        assert isinstance(access, OwnedReplace)
        access.replace(data)
    return receipt, data


def stop(attempt, admin_user):
    stopping = cancel(attempt, admin_user)
    repository().confirm_stopped(stopping.id, stopping.version, attempt.attempt_id)


def orphan(attempt, rom):
    with bind_scan_write_context(context(attempt)):
        unit = batch(rom)
        output = prepare(unit, rom, b"stopped orphan")

        def fail(session):
            raise ValueError("intentional association rollback")

        with pytest.raises(ValueError, match="intentional association rollback"):
            unit.publish_and_associate(fail)
    return unit, output


@pytest.mark.parametrize("field", ["operation", "attempt", "batch"])
@pytest.mark.parametrize("value", [7, None, []])
def test_identity_primitives_are_validation_errors(attempt, rom, field, value):
    unit, output = orphan(attempt, rom)
    receipt, data = replace_receipt(unit, lambda doc: doc.update({field: value}))
    with pytest.raises(ValueError, match="scan_media_manifest"):
        recovery().reconcile_manifest(unit.storage, unit.manifest_directory)
    assert receipt.read_bytes() == data
    assert read(output.path) == b"stopped orphan"


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(outputs=[None]),
        lambda d: d.update(outputs=[7]),
        lambda d: d["outputs"][0].update(final=[]),
        lambda d: d["outputs"][0].update(private=7),
        lambda d: d["outputs"][0].update(digest=[]),
        lambda d: d.update(expected_prior={}),
        lambda d: d.update(schema=True),
    ],
)
def test_containers_are_validated_before_path_operations(attempt, rom, change):
    unit, output = orphan(attempt, rom)
    receipt, data = replace_receipt(unit, change)
    with pytest.raises(ValueError, match="scan_media_manifest"):
        recovery().reconcile_manifest(unit.storage, unit.manifest_directory)
    assert receipt.read_bytes() == data
    assert read(output.path) == b"stopped orphan"


def test_deep_json_is_bounded_validation_error(attempt, rom):
    unit, output = orphan(attempt, rom)
    receipt, data = replace_receipt(unit, raw=b"[" * 1500 + b"0" + b"]" * 1500)
    with pytest.raises(ValueError, match="scan_media_manifest"):
        recovery().reconcile_manifest(unit.storage, unit.manifest_directory)
    assert receipt.read_bytes() == data
    assert read(output.path) == b"stopped orphan"


def cleanup_file(rom):
    path = f"{rom.fs_resources_path}/cover/retired.png"
    from handler.filesystem.scan_media_publication import ensure_directory

    ensure_directory(fs_resource_handler.storage, path.rsplit("/", 1)[0])
    with open_owned_access(
        fs_resource_handler.storage, StorageOperation.CREATE, path
    ) as access:
        assert isinstance(access, OwnedCreate)
        access.create(b"retired")
    intent = db_rom_handler.create_owned_media_cleanup_intent(rom.id, 0, path)
    return path, intent.id


@pytest.mark.asyncio
async def test_malformed_receipt_does_not_block_outbox(attempt, rom, admin_user):
    unit, output = orphan(attempt, rom)
    receipt, data = replace_receipt(unit, lambda doc: doc.update(operation=7))
    stop(attempt, admin_user)
    path, intent = cleanup_file(rom)
    await owned_media_cleanup_task.run()
    assert not fs_resource_handler.validate_path(path).exists()
    with sync_session.begin() as session:
        assert (
            session.scalar(
                select(OwnedMediaCleanupIntent.state).where(
                    OwnedMediaCleanupIntent.id == intent
                )
            )
            == OwnedMediaCleanupState.COMPLETED
        )
    assert receipt.read_bytes() == data
    assert read(output.path) == b"stopped orphan"
