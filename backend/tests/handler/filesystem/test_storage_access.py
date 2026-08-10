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
from handler.filesystem.storage_access import (
    OwnedCreate,
    OwnedDelete,
    OwnedDirectory,
    OwnedRead,
    OwnedReplace,
    open_owned_access,
    open_storage_access,
)
from handler.filesystem.storage_composition import (
    StorageCompositionConfig,
    build_storage_composition,
)
from handler.filesystem.storage_policy import (
    ExternalStorageDescriptor,
    OwnedStorageKind,
    StorageOperation,
    _create_bound_owned_descriptor,
)
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


def _external(path: Path) -> ExternalStorageDescriptor:
    owned = {kind: path.parent / "owned" / kind.value for kind in OwnedStorageKind}
    return build_storage_composition(
        StorageCompositionConfig(path, owned)
    ).legacy_external


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
    with open_storage_access(_external(archive), operation, relative) as capability:
        public = {name for name in dir(capability) if not name.startswith("_")}
        assert method in public
        assert not ({"path", "open", "write", "unlink", "rename", "replace"} & public)
        assert not (set(METHODS.values()) - {method}) & public


def test_reads_preserve_complete_source_manifest(archive):
    before = _manifest(archive)
    with open_storage_access(
        _external(archive), StorageOperation.READ, "Nintendo/München/ゲーム.rom"
    ) as access:
        assert access.read() == b"immutable-rom-data"  # type: ignore[attr-defined]
    with open_storage_access(
        _external(archive), StorageOperation.HASH, "Nintendo/München/ゲーム.rom"
    ) as access:
        assert (
            access.hash("sha256") == hashlib.sha256(b"immutable-rom-data").hexdigest()  # type: ignore
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
        open_storage_access(_external(root_path), StorageOperation.READ, relative)


def test_directory_and_file_kind_checks_are_bounded(archive):
    with pytest.raises(NonDirectoryStorageTargetError):
        open_storage_access(
            _external(archive), StorageOperation.LIST, "Nintendo/München/ゲーム.rom"
        )
    with pytest.raises(StorageResolutionError):
        open_storage_access(
            _external(archive), StorageOperation.READ, "Nintendo/München"
        )
    with pytest.raises(MissingStorageTargetError):
        open_storage_access(_external(archive), StorageOperation.READ, "missing.rom")


def test_capability_rejects_use_after_close(archive):
    access = open_storage_access(
        _external(archive), StorageOperation.READ, "Nintendo/München/ゲーム.rom"
    )
    access.close()
    with pytest.raises(StorageResolutionError, match="closed"):
        access.read()  # type: ignore


def test_repeated_access_and_partial_open_failure_do_not_leak_fds(archive):
    before = len(os.listdir("/proc/self/fd"))
    for _ in range(40):
        with open_storage_access(
            _external(archive), StorageOperation.STAT, "Nintendo/München/ゲーム.rom"
        ) as access:
            assert access.stat().st_size == len(b"immutable-rom-data")  # type: ignore[attr-defined]
        with pytest.raises(MissingStorageTargetError):
            open_storage_access(
                _external(archive), StorageOperation.READ, "Nintendo/missing/game.rom"
            )
    assert len(os.listdir("/proc/self/fd")) <= before + 1


def test_opened_descriptor_survives_name_swap_without_escape(archive, tmp_path):
    original = archive / "Nintendo" / "München" / "ゲーム.rom"
    outside = tmp_path / "outside.rom"
    outside.write_bytes(b"outside-secret")
    access = open_storage_access(
        _external(archive), StorageOperation.READ, "Nintendo/München/ゲーム.rom"
    )
    original.rename(original.with_suffix(".old"))
    original.symlink_to(outside)
    try:
        assert access.read() == b"immutable-rom-data"  # type: ignore[attr-defined]
    finally:
        access.close()


def test_raw_storage_root_is_rejected_before_authorization_or_io(tmp_path, monkeypatch):
    forged = _root(tmp_path / "caller-selected")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("authority, normalization, or I/O was reached")

    monkeypatch.setattr(
        "handler.filesystem.storage_access.StoragePolicy.authorize", forbidden
    )
    monkeypatch.setattr(
        "handler.filesystem.storage_access.normalize_relative_path", forbidden
    )
    monkeypatch.setattr("handler.filesystem.storage_access.os.open", forbidden)
    with pytest.raises(TypeError, match="bound external storage descriptor"):
        open_storage_access(forged, StorageOperation.READ, "game.rom")


def _owned(path: Path):
    return _create_bound_owned_descriptor(OwnedStorageKind.CACHE, "cache", path)


@pytest.mark.parametrize(
    ("operation", "capability_type", "method"),
    [
        (StorageOperation.READ, OwnedRead, "read"),
        (StorageOperation.CREATE, OwnedCreate, "create"),
        (StorageOperation.OVERWRITE, OwnedReplace, "replace"),
        (StorageOperation.DELETE, OwnedDelete, "delete"),
        (StorageOperation.MKDIR, OwnedDirectory, "mkdir"),
    ],
)
def test_owned_capabilities_expose_only_named_authority(
    tmp_path, operation, capability_type, method
):
    (tmp_path / "existing.bin").write_bytes(b"old")
    relative = "new" if operation is StorageOperation.MKDIR else "existing.bin"
    capability = open_owned_access(_owned(tmp_path), operation, relative)
    try:
        assert isinstance(capability, capability_type)
        public = {name for name in dir(capability) if not name.startswith("_")}
        assert method in public
        assert not ({"path", "open", "write", "unlink", "rename"} & public)
    finally:
        capability.close()


@pytest.mark.parametrize("raw", [Path("x"), "/tmp/x"])
def test_owned_access_rejects_raw_path_objects_and_strings_before_io(tmp_path, raw):
    before = _manifest(tmp_path)
    with pytest.raises((TypeError, StorageResolutionError)):
        open_owned_access(raw, StorageOperation.CREATE, "new.bin")
    assert _manifest(tmp_path) == before


def test_owned_create_replace_delete_and_directory_are_descriptor_relative(tmp_path):
    owned = _owned(tmp_path)
    with open_owned_access(owned, StorageOperation.MKDIR, "nested") as directory:
        directory.mkdir()  # type: ignore
    with open_owned_access(owned, StorageOperation.CREATE, "nested/game.bin") as create:
        create.create(b"one")  # type: ignore
    with open_owned_access(owned, StorageOperation.READ, "nested/game.bin") as read:
        assert read.read() == b"one"  # type: ignore
    with open_owned_access(
        owned, StorageOperation.OVERWRITE, "nested/game.bin"
    ) as replace:
        replace.replace(b"two")  # type: ignore
    with open_owned_access(owned, StorageOperation.DELETE, "nested/game.bin") as delete:
        delete.delete()  # type: ignore
    assert not (tmp_path / "nested" / "game.bin").exists()


def test_subprocess_adapter_lists_only_the_capability_fd(tmp_path):
    (tmp_path / "game.rom").write_bytes(b"game")
    with open_storage_access(
        _external(tmp_path), StorageOperation.READ, "game.rom"
    ) as access:
        argv, pass_fds = access.subprocess_fd("tool", "--input")
        assert argv[:2] == ("tool", "--input")
        assert argv[2] == f"/proc/self/fd/{pass_fds[0]}"
        assert pass_fds == (access.fileno(),)
