"""Real receipt hierarchies for bounded scheduler recovery tests."""

import json
import time
from uuid import uuid4

import pytest
from tests.handler.test_media_recovery_validation import (
    orphan,
    replace_receipt,
    stop,
)
from tests.handler.test_scan_media_publication import attempt, command, read

from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import RESERVED, ensure_directory
from handler.filesystem.storage_access import OwnedCreate, open_owned_access
from handler.filesystem.storage_policy import StorageOperation
from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task


def seed_receipt(template, *, operation=None, attempt_id=None):
    document = dict(template)
    document.update(
        operation=operation or template["operation"],
        attempt=attempt_id or template["attempt"],
        batch=uuid4().hex,
        outputs=[],
    )
    directory = (
        f'{RESERVED}/{document["operation"]}/{document["attempt"]}/{document["batch"]}'
    )
    ensure_directory(fs_resource_handler.storage, directory)
    with open_owned_access(
        fs_resource_handler.storage,
        StorageOperation.CREATE,
        directory + "/receipt-0000.json",
    ) as access:
        assert isinstance(access, OwnedCreate)
        access.create(json.dumps(document).encode())
    return fs_resource_handler.validate_path(directory)


def template_for(unit):
    root = fs_resource_handler.validate_path(unit.manifest_directory)
    return json.loads(sorted(root.glob("receipt-*.json"))[-1].read_bytes())


async def drain_until(predicate, calls=100):
    deadline = time.monotonic() + 40
    for _ in range(calls):
        assert time.monotonic() < deadline, "scheduler recovery exceeded deadline"
        await owned_media_cleanup_task.run()
        if predicate():
            return
    assert predicate(), "repeated scheduler calls made no eventual progress"
