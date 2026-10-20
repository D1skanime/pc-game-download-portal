"""Same-inode changes at the final SQL boundary never become cleanup authority."""

import os
from contextlib import contextmanager

import pytest
from tests.handler.test_media_recovery_validation import orphan, stop
from tests.handler.test_media_sealed_files import stage
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_operations import command as command
from tests.handler.test_scan_write_fence import context

from exceptions.storage_exceptions import StorageResolutionError
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem import scan_media_publication as publication
from handler.filesystem import scan_media_recovery as recovery


def modify_in_place(path):
    before = path.stat()
    changed = bytes(value ^ 1 for value in path.read_bytes())
    path.write_bytes(changed)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    return changed


def test_publication_rechecks_bytes_after_sql_fence_acquisition(
    attempt, rom, monkeypatch
):
    with bind_scan_write_context(context(attempt)):
        unit, output = stage(rom)
        private = fs_resource_handler.validate_path(output.private_path)
        original = publication.checked_scan_write
        observed = []

        @contextmanager
        def boundary(session, **kwargs):
            with original(session, **kwargs) as row:
                observed.append(modify_in_place(private))
                yield row

        monkeypatch.setattr(publication, "checked_scan_write", boundary)
        with pytest.raises(StorageResolutionError):
            unit.publish_and_associate(
                lambda session: pytest.fail("unproven association")
            )
        unit.abort()
    assert observed
    assert private.read_bytes() == observed[0]
    assert not fs_resource_handler.validate_path(output.path).exists()


@pytest.mark.parametrize("target", ["private", "final"])
def test_recovery_rechecks_original_digest_after_reference_lock(
    attempt, rom, admin_user, monkeypatch, target
):
    if target == "private":
        with bind_scan_write_context(context(attempt)):
            unit, output = stage(rom)
        path = fs_resource_handler.validate_path(output.private_path)
    else:
        unit, output = orphan(attempt, rom)
        path = fs_resource_handler.validate_path(output.path)
    stop(attempt, admin_user)
    original = recovery._lock_attempt
    changed = []

    def boundary(session, operation):
        row = original(session, operation)
        changed.append(modify_in_place(path))
        return row

    monkeypatch.setattr(recovery, "_lock_attempt", boundary)
    with pytest.raises((StorageResolutionError, ValueError)):
        recovery.reconcile_manifest(unit.storage, unit.manifest_directory)
    assert path.read_bytes() == changed[0]
    assert fs_resource_handler.validate_path(unit.manifest_directory).exists()


def test_expired_lease_after_fresh_proof_cannot_link_owned_bytes(
    attempt, rom, monkeypatch
):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import update

    from handler.database.scan_write_fence import ScanWriteRejected
    from handler.filesystem import owned_publication
    from models.scan_operation import ScanOperation

    active = []
    original_fence = publication.checked_scan_write
    original_proof = owned_publication._prove
    changed: list[bool] = []

    @contextmanager
    def capture_fence(session, **kwargs):
        with original_fence(session, **kwargs) as row:
            active.append(session)
            yield row

    def expire_after_proof(*args, **kwargs):
        result = original_proof(*args, **kwargs)
        if not changed:
            active[0].execute(
                update(ScanOperation)
                .where(ScanOperation.id == attempt.id)
                .values(
                    lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
                )
            )
            changed.append(True)
        return result

    with bind_scan_write_context(context(attempt)):
        unit, output = stage(rom)
        monkeypatch.setattr(publication, "checked_scan_write", capture_fence)
        monkeypatch.setattr(owned_publication, "_prove", expire_after_proof)
        with pytest.raises(ScanWriteRejected, match="revoked"):
            unit.publish_and_associate(
                lambda session: pytest.fail("expired association")
            )
        unit.abort()
    assert changed
    assert not fs_resource_handler.validate_path(output.path).exists()


@pytest.mark.asyncio
async def test_crash_left_pid_cursor_temporary_does_not_block_recovery(
    attempt, rom, admin_user
):
    from tests.handler.media_recovery_helpers import drain_until

    from handler.filesystem.scan_media_publication import RESERVED
    from handler.filesystem.scan_media_traversal import RecoveryWalk

    unit, output = orphan(attempt, rom)
    with RecoveryWalk(unit.storage):
        pass
    cursor = fs_resource_handler.validate_path(RESERVED + "/.recovery-cursor.json")
    stale = cursor.with_name(f".{cursor.name}.{os.getpid()}.tmp")
    stale.write_bytes(b"interrupted writer owns this cursor temporary")
    stop(attempt, admin_user)
    await drain_until(
        lambda: not fs_resource_handler.validate_path(unit.manifest_directory).exists()
    )
    assert not fs_resource_handler.validate_path(output.path).exists()
    assert stale.read_bytes() == b"interrupted writer owns this cursor temporary"
    assert cursor.is_file()
