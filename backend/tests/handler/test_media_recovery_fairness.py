"""Fair recovery must retain ambiguous evidence and reach later receipts."""

import hashlib
import json
import os

import pytest
from tests.handler.media_recovery_helpers import (
    attempt,
    command,
    drain_until,
    orphan,
    seed_receipt,
    stop,
    template_for,
)
from tests.handler.test_scan_media_publication import read

from handler.filesystem import fs_resource_handler
from handler.filesystem.storage_access import (
    OwnedCreate,
    OwnedReplace,
    open_owned_access,
)
from handler.filesystem.storage_policy import StorageOperation
from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task


@pytest.mark.asyncio
async def test_32_retained_receipts_do_not_starve_later_orphan(
    attempt, rom, admin_user
):
    unit, original = orphan(attempt, rom)
    template = template_for(unit)
    paths = [seed_receipt(template) for _ in range(33)]
    parent = paths[0].parent
    ordered = [
        parent / entry.name
        for entry in os.scandir(parent)
        if entry.is_dir(follow_symlinks=False) and entry.name != unit.token
    ]
    relative_parent = unit.manifest_directory.rsplit("/", 1)[0]
    retained = {}
    for path in ordered[:32]:
        receipt = path / "receipt-0000.json"
        data = json.loads(receipt.read_bytes())
        data["operation"] = 7
        with open_owned_access(
            unit.storage,
            StorageOperation.OVERWRITE,
            f"{relative_parent}/{path.name}/receipt-0000.json",
        ) as access:
            assert isinstance(access, OwnedReplace)
            access.replace(json.dumps(data).encode())
        retained[receipt] = receipt.read_bytes()
    target = ordered[32]
    receipt = target / "receipt-0000.json"
    document = json.loads(receipt.read_bytes())
    final = f"{rom.fs_resources_path}/cover/later.scan-{attempt.attempt_id.replace('-', '')}-{target.name}-0.png"
    data = b"later stopped orphan"
    with open_owned_access(unit.storage, StorageOperation.CREATE, final) as access:
        assert isinstance(access, OwnedCreate)
        access.create(data)
    document["outputs"] = [
        dict(
            final=final,
            private=final.rsplit("/", 1)[0]
            + "/."
            + final.rsplit("/", 1)[1]
            + "."
            + "a" * 32
            + ".tmp",
            digest=hashlib.sha256(data).hexdigest(),
            size=len(data),
        )
    ]
    with open_owned_access(
        unit.storage,
        StorageOperation.OVERWRITE,
        f"{relative_parent}/{target.name}/receipt-0000.json",
    ) as access:
        assert isinstance(access, OwnedReplace)
        access.replace(json.dumps(document).encode())
    stop(attempt, admin_user)
    await drain_until(
        lambda: not fs_resource_handler.validate_path(final).exists(), calls=20
    )
    assert not target.exists()
    for receipt, expected in retained.items():
        assert receipt.read_bytes() == expected


@pytest.mark.asyncio
async def test_live_attempt_and_interleaved_new_batch_are_preserved(attempt, rom):
    unit, output = orphan(attempt, rom)
    template = template_for(unit)
    directories = [seed_receipt(template) for _ in range(40)]
    for _ in range(3):
        await owned_media_cleanup_task.run()
    newer = seed_receipt(template)
    for _ in range(3):
        await owned_media_cleanup_task.run()
    assert newer.exists()
    assert all(path.exists() for path in directories)
    assert read(output.path) == b"stopped orphan"
    assert newer.parent.exists() and newer.parent.parent.exists()
