"""Recovery continuity with real cursors, capabilities and SQL authority."""

import importlib
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
from tests.handler.test_scan_operations import repository
from tests.handler.test_scan_write_fence import context

from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import RESERVED
from handler.filesystem.scan_media_recovery import reconcile_scan_media
from handler.filesystem.scan_media_traversal import RecoveryWalk
from handler.filesystem.storage_access import (
    OwnedDelete,
    OwnedDirectory,
    OwnedReplace,
    open_owned_access,
)
from handler.filesystem.storage_policy import StorageOperation
from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task


@pytest.mark.asyncio
async def test_disappearing_child_preserves_directory_continuity(
    attempt, rom, admin_user, monkeypatch
):
    unit, output = orphan(attempt, rom)
    paths = [seed_receipt(template_for(unit)) for _ in range(3)]
    parent = paths[0].parent
    ordered = [
        parent / entry.name
        for entry in os.scandir(parent)
        if entry.name in {path.name for path in paths}
    ]
    removed, later = ordered[0], ordered[1]
    module = importlib.import_module("handler.filesystem.scan_media_traversal")
    actual = module._entry
    raced = []

    def disappear(descriptor, cookie):
        entry = actual(descriptor, cookie)
        if entry and entry[1] == removed.name and not raced:
            relative = unit.manifest_directory.rsplit("/", 1)[0] + "/" + removed.name
            with open_owned_access(
                unit.storage, StorageOperation.DELETE, relative + "/receipt-0000.json"
            ) as access:
                assert isinstance(access, OwnedDelete)
                access.delete()
            with open_owned_access(
                unit.storage, StorageOperation.MKDIR, relative
            ) as access:
                assert isinstance(access, OwnedDirectory)
                access.rmdir()
            raced.append(removed.name)
        return entry

    stop(attempt, admin_user)
    monkeypatch.setattr(module, "_entry", disappear)
    await owned_media_cleanup_task.run()
    assert raced == [removed.name]
    assert not later.exists(), "one vanished entry abandoned later siblings"
    assert not fs_resource_handler.validate_path(output.path).exists()


@pytest.mark.asyncio
async def test_live_page_cannot_starve_stopped_orphan(attempt, rom, admin_user):
    old, output = orphan(attempt, rom)
    stop(attempt, admin_user)
    repo = repository()
    stopped = repo.get_by_id(attempt.id, admin_user.id)
    resumed = repo.request_resume(
        stopped.id, admin_user.id, stopped.version, "live-page"
    )
    queued = repo.transition(resumed.id, resumed.version, resumed.attempt_id, "queued")
    current = repo.claim_attempt(queued.id, queued.version, "worker", seconds=300)
    with bind_scan_write_context(context(current)):
        live, protected = orphan(current, rom)
    paths = [seed_receipt(template_for(live)) for _ in range(40)]
    # Start this invocation inside the live page; later calls must wrap fairly.
    with RecoveryWalk(live.storage) as walk:
        for _ in range(100):
            kind, path = walk.step()
            if kind == "batch" and path.startswith(
                live.manifest_directory.rsplit("/", 1)[0]
            ):
                break
        else:
            pytest.fail("live page was not reached")
    await drain_until(
        lambda: not fs_resource_handler.validate_path(output.path).exists(), calls=20
    )
    assert all(path.exists() for path in paths)
    assert (
        fs_resource_handler.validate_path(protected.path).read_bytes()
        == b"stopped orphan"
    )


def test_cursor_write_failure_keeps_prior_atomic_checkpoint(attempt, rom, monkeypatch):
    unit, _ = orphan(attempt, rom)
    with RecoveryWalk(unit.storage):
        pass
    cursor = fs_resource_handler.validate_path(RESERVED + "/.recovery-cursor.json")
    before = cursor.read_bytes()
    actual = os.replace

    def fail(source, target, **kwargs):
        if target == ".recovery-cursor.json":
            raise OSError("cursor replacement fault")
        return actual(source, target, **kwargs)

    with monkeypatch.context() as fault:
        fault.setattr(os, "replace", fail)
        with pytest.raises(OSError, match="cursor replacement fault"):
            with RecoveryWalk(unit.storage) as walk:
                for _ in range(4):
                    walk.step()
    assert cursor.read_bytes() == before
    with RecoveryWalk(unit.storage) as retry:
        assert not retry.busy


@pytest.mark.parametrize("raw", [b"7", b"{}", b"[" * 1500 + b"0" + b"]" * 1500])
def test_invalid_advisory_cursor_resets_without_deleting_evidence(attempt, rom, raw):
    unit, output = orphan(attempt, rom)
    with RecoveryWalk(unit.storage):
        pass
    with open_owned_access(
        unit.storage, StorageOperation.OVERWRITE, RESERVED + "/.recovery-cursor.json"
    ) as access:
        assert isinstance(access, OwnedReplace)
        access.replace(raw)
    reconcile_scan_media(unit.storage)
    assert (
        fs_resource_handler.validate_path(output.path).read_bytes() == b"stopped orphan"
    )
    assert fs_resource_handler.validate_path(unit.manifest_directory).exists()
    document = json.loads(
        fs_resource_handler.validate_path(
            RESERVED + "/.recovery-cursor.json"
        ).read_bytes()
    )
    assert type(document) is list and len(document) <= 3
