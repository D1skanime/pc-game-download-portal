"""Descriptor traversal, restart, and ancestor races use real owned storage."""

import importlib
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from tests.handler.media_recovery_helpers import attempt as attempt
from tests.handler.media_recovery_helpers import command as command
from tests.handler.media_recovery_helpers import (
    drain_until,
    orphan,
    seed_receipt,
    stop,
    template_for,
)
from tests.handler.test_scan_media_publication import read, recovery

from exceptions.storage_exceptions import StorageResolutionError
from handler.database.base_handler import sync_engine
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import RESERVED, ensure_directory
from handler.filesystem.scan_media_traversal import RecoveryWalk, open_directory
from handler.filesystem.storage_access import OwnedRead
from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task


@pytest.mark.asyncio
async def test_symlinked_generated_hierarchy_is_never_followed(
    attempt, rom, admin_user, tmp_path
):
    unit, output = orphan(attempt, rom)
    root = fs_resource_handler.validate_path(RESERVED)
    operation = root / str(uuid4())
    operation.symlink_to(tmp_path, target_is_directory=True)
    protected = tmp_path / "protected"
    protected.write_bytes(b"outside the resource capability")
    with pytest.raises(StorageResolutionError):
        open_directory(unit.storage, RESERVED + "/" + operation.name)
    stop(attempt, admin_user)
    await drain_until(
        lambda: not fs_resource_handler.validate_path(output.path).exists()
    )
    assert protected.read_bytes() == b"outside the resource capability"
    assert operation.is_symlink()


@pytest.mark.asyncio
async def test_receipt_listing_failure_does_not_stop_other_receipts(
    attempt, rom, admin_user, monkeypatch
):
    unit, output = orphan(attempt, rom)
    other = seed_receipt(template_for(unit))
    stop(attempt, admin_user)
    actual = recovery()._children

    def listing(storage, path, *args):
        if path == unit.manifest_directory:
            raise OSError("one inaccessible receipt directory")
        return actual(storage, path, *args)

    monkeypatch.setattr(recovery(), "_children", listing)
    await drain_until(lambda: not other.exists())
    assert read(output.path) == b"stopped orphan"
    assert fs_resource_handler.validate_path(unit.manifest_directory).exists()


def test_cursor_read_failure_releases_advisory_lock(attempt, rom, monkeypatch):
    unit, _ = orphan(attempt, rom)
    with RecoveryWalk(unit.storage):
        pass
    cursor = fs_resource_handler.validate_path(RESERVED + "/.recovery-cursor.json")
    inode = cursor.stat().st_ino
    actual = OwnedRead.binary_file

    def unreadable(access):
        if os.fstat(access.fileno()).st_ino == inode:
            raise OSError("cursor read fault")
        return actual(access)

    with monkeypatch.context() as fault:
        fault.setattr(OwnedRead, "binary_file", unreadable)
        with pytest.raises(OSError, match="cursor read fault"):
            RecoveryWalk(unit.storage).__enter__()
    with RecoveryWalk(unit.storage) as walk:
        assert not walk.busy, "an initialization failure leaked the flock"


def test_two_scheduler_walks_do_not_overwrite_each_others_progress(attempt, rom):
    unit, _ = orphan(attempt, rom)
    entered, finish = Event(), Event()

    def first():
        with RecoveryWalk(unit.storage) as walk:
            assert not walk.busy
            for _ in range(3):
                walk.step()
            entered.set()
            assert finish.wait(5)

    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(first)
        assert entered.wait(5)
        with RecoveryWalk(unit.storage) as second:
            assert second.busy
        finish.set()
        work.result(timeout=10)
    with RecoveryWalk(unit.storage) as third:
        assert not third.busy


@pytest.mark.asyncio
async def test_process_exit_replays_bounded_page_then_recovers(
    attempt, rom, admin_user
):
    unit, output = orphan(attempt, rom)
    paths = [seed_receipt(template_for(unit)) for _ in range(40)]
    stop(attempt, admin_user)
    with RecoveryWalk(unit.storage) as walk:
        for _ in range(4):
            walk.step()
    cursor = fs_resource_handler.validate_path(RESERVED + "/.recovery-cursor.json")
    before = cursor.read_bytes()

    def interrupted():
        sync_engine.dispose(close=False)
        with RecoveryWalk(unit.storage) as walk:
            for _ in range(4):
                walk.step()
            os._exit(41)

    child = multiprocessing.get_context("fork").Process(target=interrupted)
    child.start()
    child.join(10)
    if child.is_alive():
        child.kill()
        child.join(5)
        pytest.fail("cursor crash worker exceeded deadline")
    assert child.exitcode == 41
    assert cursor.read_bytes() == before
    await drain_until(lambda: all(not path.exists() for path in paths))
    assert not fs_resource_handler.validate_path(output.path).exists()


@pytest.mark.asyncio
async def test_new_active_batch_wins_empty_ancestor_prune(
    attempt, rom, admin_user, monkeypatch
):
    from tests.handler.test_scan_operations import repository

    unit, output = orphan(attempt, rom)
    stop(attempt, admin_user)
    repo = repository()
    stopped = repo.get_by_id(attempt.id, admin_user.id)
    resumed = repo.request_resume(
        stopped.id, admin_user.id, stopped.version, "cursor-resume"
    )
    queued = repo.transition(resumed.id, resumed.version, resumed.attempt_id, "queued")
    next_attempt = repo.claim_attempt(queued.id, queued.version, "next-worker")
    actual = recovery()._prune_ancestor
    created: list[Path] = []

    def interleave(storage, path, **kwargs):
        if path == unit.manifest_directory.rsplit("/", 1)[0] and not created:
            document = template_for_saved
            created.append(
                seed_receipt(
                    document,
                    operation=next_attempt.id,
                    attempt_id=next_attempt.attempt_id,
                )
            )
        return actual(storage, path, **kwargs)

    template_for_saved = template_for(unit)
    monkeypatch.setattr(recovery(), "_prune_ancestor", interleave)
    await drain_until(lambda: bool(created))
    for _ in range(3):
        await owned_media_cleanup_task.run()
    assert created[0].exists()
    assert created[0].parent.exists() and created[0].parent.parent.exists()
    assert not fs_resource_handler.validate_path(output.path).exists()


@pytest.mark.parametrize("ordering", ["new-first", "prune-first"])
def test_new_attempt_and_ancestor_prune_serialize(
    attempt, rom, admin_user, monkeypatch, ordering
):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from contextvars import copy_context
    from threading import Event

    from tests.handler.test_scan_media_publication import recovery
    from tests.handler.test_scan_operations import repository
    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import bind_scan_write_context

    unit, output = orphan(attempt, rom)
    stop(attempt, admin_user)
    actual = recovery()._prune_ancestor
    ancestor = unit.manifest_directory.rsplit("/", 1)[0]
    visited, release = Event(), Event()

    def barrier(storage, path, **kwargs):
        if path == ancestor and not visited.is_set():
            visited.set()
            if ordering == "new-first":
                assert release.wait(10), "new attempt did not finish before prune"
        return actual(storage, path, **kwargs)

    async def sweep():
        for _ in range(40):
            await owned_media_cleanup_task.run()
            if visited.is_set():
                return
        pytest.fail("ancestor was not reached within bounded scheduler calls")

    monkeypatch.setattr(recovery(), "_prune_ancestor", barrier)
    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(copy_context().run, lambda: asyncio.run(sweep()))
        try:
            if ordering == "new-first":
                assert visited.wait(15), "scheduler did not reach prune barrier"
            else:
                work.result(timeout=30)
                assert not fs_resource_handler.validate_path(ancestor).exists()
            repo = repository()
            stopped = repo.get_by_id(attempt.id, admin_user.id)
            resumed = repo.request_resume(
                stopped.id, admin_user.id, stopped.version, "ancestor-" + ordering
            )
            queued = repo.transition(
                resumed.id, resumed.version, resumed.attempt_id, "queued"
            )
            current = repo.claim_attempt(
                queued.id, queued.version, "worker", seconds=300
            )
            with bind_scan_write_context(context(current)):
                newer, protected = orphan(current, rom)
        finally:
            release.set()
        work.result(timeout=30)
    assert fs_resource_handler.validate_path(newer.manifest_directory).exists()
    assert (
        fs_resource_handler.validate_path(protected.path).read_bytes()
        == b"stopped orphan"
    )
    assert not fs_resource_handler.validate_path(output.path).exists()
    for _ in range(3):
        asyncio.run(owned_media_cleanup_task.run())
    assert fs_resource_handler.validate_path(newer.manifest_directory).exists()


def test_scheduler_directory_work_is_bounded_even_without_batches(
    attempt, rom, monkeypatch
):
    unit, _ = orphan(attempt, rom)
    root = fs_resource_handler.validate_path(RESERVED)
    for index in range(600):
        ensure_directory(
            unit.storage, f"{RESERVED}/{index + 1:08x}-0000-4000-8000-000000000000"
        )
    module = importlib.import_module("handler.filesystem.scan_media_traversal")
    actual = module._entry
    observed = []

    def counted(*args):
        observed.append(1)
        return actual(*args)

    monkeypatch.setattr(module, "_entry", counted)
    recovery().reconcile_scan_media(unit.storage)
    assert len(observed) <= 512
    assert len(list(root.iterdir())) > 100, "one call swept the unbounded hierarchy"
