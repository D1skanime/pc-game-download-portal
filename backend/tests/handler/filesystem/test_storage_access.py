import hashlib
import os
import stat
from pathlib import Path

import pytest

from exceptions.storage_exceptions import (
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    StorageResolutionError,
    UnsafeSymlinkError,
)
from handler.filesystem.storage_access import open_storage_access
from handler.filesystem.storage_policy import StorageOperation
from models.storage import EXTERNAL_READ_ONLY_MODE, StorageRoot


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """The access suite is deliberately database free."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """Override shared database cleanup for descriptor-only tests."""


def _root(path: Path) -> StorageRoot:
    root = StorageRoot(
        name="Archive",
        container_path=str(path),
        mode=EXTERNAL_READ_ONLY_MODE,
        active=True,
    )
    root.id = 17
    return root


def _manifest(root: Path) -> tuple[tuple[object, ...], ...]:
    result = []
    for item in sorted(root.rglob("*"), key=lambda entry: str(entry.relative_to(root))):
        metadata = item.lstat()
        digest = (
            hashlib.sha256(item.read_bytes()).hexdigest() if item.is_file() else None
        )
        link = os.readlink(item) if item.is_symlink() else None
        result.append(
            (
                str(item.relative_to(root)),
                stat.S_IFMT(metadata.st_mode),
                metadata.st_size,
                stat.S_IMODE(metadata.st_mode),
                metadata.st_mtime_ns,
                link,
                digest,
            )
        )
    return tuple(result)


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    nested = tmp_path / "Nintendo" / "München"
    nested.mkdir(parents=True)
    (nested / "ゲーム.rom").write_bytes(b"immutable-rom-data")
    (tmp_path / "empty").mkdir()
    return tmp_path


METHODS = {
    StorageOperation.RESOLVE: "resolve",
    StorageOperation.LIST: "list",
    StorageOperation.STAT: "stat",
    StorageOperation.READ: "read",
    StorageOperation.SCAN: "scan",
    StorageOperation.HASH: "hash",
    StorageOperation.STREAM: "stream",
    StorageOperation.DOWNLOAD: "download",
}


@pytest.mark.parametrize(("operation", "method"), METHODS.items())
def test_each_capability_has_only_its_operation_surface(archive, operation, method):
    relative = (
        "Nintendo/München"
        if operation
        in {StorageOperation.LIST, StorageOperation.SCAN, StorageOperation.RESOLVE}
        else "Nintendo/München/ゲーム.rom"
    )
    with open_storage_access(_root(archive), operation, relative) as capability:
        public = {name for name in dir(capability) if not name.startswith("_")}
        assert method in public
        assert not ({"path", "open", "write", "unlink", "rename", "replace"} & public)
        assert not (set(METHODS.values()) - {method}) & public


def test_reads_preserve_complete_source_manifest(archive):
    before = _manifest(archive)
    with open_storage_access(
        _root(archive), StorageOperation.READ, "Nintendo/München/ゲーム.rom"
    ) as access:
        assert access.read() == b"immutable-rom-data"
    with open_storage_access(
        _root(archive), StorageOperation.HASH, "Nintendo/München/ゲーム.rom"
    ) as access:
        assert (
            access.hash("sha256") == hashlib.sha256(b"immutable-rom-data").hexdigest()
        )
    assert _manifest(archive) == before


@pytest.mark.parametrize("position", ["root", "intermediate", "leaf"])
def test_root_intermediate_and_leaf_symlinks_are_rejected(tmp_path, position):
    real = tmp_path / "real"
    (real / "nested").mkdir(parents=True)
    (real / "nested" / "game.rom").write_bytes(b"game")
    root_path, relative = real, "nested/game.rom"
    if position == "root":
        root_path = tmp_path / "linked"
        root_path.symlink_to(real, target_is_directory=True)
    elif position == "intermediate":
        (real / "nested").rename(real / "actual")
        (real / "nested").symlink_to(real / "actual", target_is_directory=True)
    else:
        (real / "nested" / "game.rom").unlink()
        (real / "nested" / "game.rom").symlink_to(tmp_path / "outside")
    with pytest.raises(UnsafeSymlinkError):
        open_storage_access(_root(root_path), StorageOperation.READ, relative)


def test_directory_and_file_kind_checks_are_bounded(archive):
    with pytest.raises(NonDirectoryStorageTargetError):
        open_storage_access(
            _root(archive), StorageOperation.LIST, "Nintendo/München/ゲーム.rom"
        )
    with pytest.raises(StorageResolutionError):
        open_storage_access(_root(archive), StorageOperation.READ, "Nintendo/München")
    with pytest.raises(MissingStorageTargetError):
        open_storage_access(_root(archive), StorageOperation.READ, "missing.rom")


def test_capability_rejects_use_after_close(archive):
    access = open_storage_access(
        _root(archive), StorageOperation.READ, "Nintendo/München/ゲーム.rom"
    )
    access.close()
    with pytest.raises(StorageResolutionError, match="closed"):
        access.read()


def test_repeated_access_and_partial_open_failure_do_not_leak_fds(archive):
    before = len(os.listdir("/proc/self/fd"))
    for _ in range(40):
        with open_storage_access(
            _root(archive), StorageOperation.STAT, "Nintendo/München/ゲーム.rom"
        ) as access:
            assert access.stat().st_size == len(b"immutable-rom-data")
        with pytest.raises(MissingStorageTargetError):
            open_storage_access(
                _root(archive), StorageOperation.READ, "Nintendo/missing/game.rom"
            )
    assert len(os.listdir("/proc/self/fd")) <= before + 1


def test_opened_descriptor_survives_name_swap_without_escape(archive, tmp_path):
    original = archive / "Nintendo" / "München" / "ゲーム.rom"
    outside = tmp_path / "outside.rom"
    outside.write_bytes(b"outside-secret")
    access = open_storage_access(
        _root(archive), StorageOperation.READ, "Nintendo/München/ゲーム.rom"
    )
    original.rename(original.with_suffix(".old"))
    original.symlink_to(outside)
    try:
        assert access.read() == b"immutable-rom-data"
    finally:
        access.close()
