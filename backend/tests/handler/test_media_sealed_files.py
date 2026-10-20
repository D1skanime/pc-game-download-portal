"""Sealed scan files use bounded descriptors and retain foreign staging evidence."""

import errno
import os
import resource
from pathlib import Path

import pytest
from tests.handler.media_download_helpers import (
    owned_resource_files as owned_resource_files,
)
from tests.handler.test_media_recovery_validation import stop
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_operations import command as command
from tests.handler.test_scan_write_fence import context

from exceptions.storage_exceptions import StorageResolutionError
from handler.database import db_rom_handler
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_inventory import ScanMediaInventory
from handler.filesystem.scan_media_publication import ScanMediaBatch
from handler.filesystem.scan_media_recovery import reconcile_manifest


def stage(rom, *, finish=True):
    unit = ScanMediaBatch(rom.id, rom.platform_id, fs_resource_handler.storage)
    output = unit.prepare(f"{rom.fs_resources_path}/seal-tests/media.png")
    output.file.write(b"complete owned bytes")
    output.file.flush()
    if finish:
        unit.finish(output)
    return unit, output


def substitute(output, kind):
    private = fs_resource_handler.validate_path(output.private_path)
    if kind == "parent":
        private.parent.rename(private.parent.with_name("held-parent"))
        private.parent.mkdir()
        private.write_bytes(b"foreign private bytes")
    elif kind == "modified":
        info = private.stat()
        private.write_bytes(b"modified owned bytes")
        os.utime(private, ns=(info.st_atime_ns, info.st_mtime_ns))
    else:
        held = private.with_name(private.name + ".held")
        private.rename(held)
        if kind == "symlink":
            private.symlink_to(held.name)
        else:
            private.write_bytes(b"complete owned bytes")
    return private, private.lstat(), private.read_bytes()


def unchanged(private, info, data):
    assert private.lstat().st_ino == info.st_ino
    assert private.read_bytes() == data


def test_finished_inventory_runs_under_96_descriptor_soft_limit(attempt, rom):
    original = resource.getrlimit(resource.RLIMIT_NOFILE)
    baseline = len(list(Path("/proc/self/fd").iterdir()))
    assert baseline < 80, "isolated test needs room for ordinary runtime descriptors"
    with bind_scan_write_context(context(attempt)):
        with ScanMediaInventory(
            rom.id, rom.platform_id, fs_resource_handler.storage, output_limit=256
        ) as unit:
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE, (96, original[1]))
                paths = []
                for index in range(256):
                    output = unit.prepare(
                        f"{rom.fs_resources_path}/seal-budget/{index}.png"
                    )
                    output.file.write(b"complete owned bytes")
                    unit.finish(output)
                    paths.append(output.path)
                    assert len(list(Path("/proc/self/fd").iterdir())) <= baseline + 8
                unit.publish_and_associate(
                    lambda session: db_rom_handler.update_rom(
                        rom.id, {"path_screenshots": paths}, session=session
                    )
                )
            finally:
                resource.setrlimit(resource.RLIMIT_NOFILE, original)
    assert db_rom_handler.get_rom(rom.id).path_screenshots == paths
    assert all(
        fs_resource_handler.validate_path(path).read_bytes() == b"complete owned bytes"
        for path in paths
    )
    assert len(list(Path("/proc/self/fd").iterdir())) <= baseline + 2


@pytest.mark.parametrize("kind", ["parent", "file", "symlink", "modified"])
def test_sealed_publication_rejects_substitution_before_sql(attempt, rom, kind):
    with bind_scan_write_context(context(attempt)):
        unit, output = stage(rom)
        private, info, data = substitute(output, kind)
        try:
            with pytest.raises(StorageResolutionError):
                unit.publish_and_associate(
                    lambda session: db_rom_handler.update_rom(
                        rom.id, {"path_cover_l": output.path}, session=session
                    )
                )
        finally:
            unit.abort()
    assert not fs_resource_handler.validate_path(output.path).exists()
    assert db_rom_handler.get_rom(rom.id).path_cover_l in (None, "")
    unchanged(private, info, data)


@pytest.mark.parametrize(
    "finish,kind",
    [
        (False, "parent"),
        (False, "file"),
        (False, "symlink"),
        (True, "parent"),
        (True, "file"),
        (True, "symlink"),
        (True, "modified"),
    ],
)
def test_abort_preserves_substituted_private(attempt, rom, finish, kind):
    with bind_scan_write_context(context(attempt)):
        unit, output = stage(rom, finish=finish)
        private, info, data = substitute(output, kind)
        unit.abort()
    unchanged(private, info, data)
    assert not fs_resource_handler.validate_path(output.path).exists()


@pytest.mark.parametrize("kind", ["parent", "file", "symlink", "modified"])
def test_recovery_retains_sealed_substitution(attempt, rom, admin_user, kind):
    with bind_scan_write_context(context(attempt)):
        unit, output = stage(rom)
    private, info, data = substitute(output, kind)
    stop(attempt, admin_user)
    try:
        with pytest.raises((ValueError, StorageResolutionError)):
            reconcile_manifest(unit.storage, unit.manifest_directory)
        unchanged(private, info, data)
        assert fs_resource_handler.validate_path(unit.manifest_directory).exists()
    finally:
        unit.abort()


@pytest.mark.parametrize("boundary", ["file", "parent"])
def test_sealing_fsync_failure_cleans_exact_private(
    attempt, rom, monkeypatch, boundary
):
    with bind_scan_write_context(context(attempt)):
        unit, output = stage(rom, finish=False)
        private = fs_resource_handler.validate_path(output.private_path)
        expected = private.stat() if boundary == "file" else private.parent.stat()
        real_fsync = os.fsync
        failed = False

        def fail_exact(descriptor):
            nonlocal failed
            info = os.fstat(descriptor)
            if (info.st_dev, info.st_ino) == (
                expected.st_dev,
                expected.st_ino,
            ) and not failed:
                failed = True
                raise OSError(errno.EIO, "deterministic seal durability failure")
            return real_fsync(descriptor)

        monkeypatch.setattr(os, "fsync", fail_exact)
        try:
            with pytest.raises((OSError, StorageResolutionError)):
                unit.finish(output)
        finally:
            unit.abort()
    assert failed
    assert not private.exists()
    assert not fs_resource_handler.validate_path(output.path).exists()


def test_sealed_no_clobber_retains_foreign_final(attempt, rom):
    with bind_scan_write_context(context(attempt)):
        unit, output = stage(rom)
        final = fs_resource_handler.validate_path(output.path)
        final.write_bytes(b"foreign final bytes")
        try:
            with pytest.raises(StorageResolutionError):
                unit.publish_and_associate(lambda session: None)
        finally:
            unit.abort()
    assert final.read_bytes() == b"foreign final bytes"
    assert not fs_resource_handler.validate_path(output.private_path).exists()
