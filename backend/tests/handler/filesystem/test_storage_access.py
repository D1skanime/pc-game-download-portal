import errno
import hashlib
import os
import select
import signal
import stat
import threading
from pathlib import Path

import pytest

from exceptions.storage_exceptions import (
    DescriptorHashBudgetError,
    DescriptorHashConcurrentChangeError,
    DescriptorHashDeadlineError,
    DescriptorHashShortReadError,
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
    hash_descriptor_file,
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


def _assert_descriptors_closed(descriptors: set[int]) -> None:
    assert descriptors
    for descriptor in descriptors:
        with pytest.raises(OSError) as error:
            os.fstat(descriptor)
        assert error.value.errno == errno.EBADF


def test_owned_create_retries_short_write_to_completion(tmp_path, monkeypatch):
    content = b"complete-create"
    counts = iter((2, 3, len(content) - 5))
    descriptors: set[int] = set()
    real_write = os.write

    def short_write(descriptor: int, data: bytes | memoryview) -> int:
        descriptors.add(descriptor)
        count = next(counts)
        return real_write(descriptor, data[:count])

    monkeypatch.setattr("handler.filesystem.storage_access.os.write", short_write)
    with open_owned_access(
        _owned(tmp_path), StorageOperation.CREATE, "created.bin"
    ) as create:
        create.create(content)  # type: ignore[union-attr]

    assert (tmp_path / "created.bin").read_bytes() == content
    _assert_descriptors_closed(descriptors)


def test_owned_replace_retries_short_write_to_completion(tmp_path, monkeypatch):
    target = tmp_path / "replaced.bin"
    target.write_bytes(b"old-content")
    content = b"complete-replace"
    counts = iter((1, 4, len(content) - 5))
    descriptors: set[int] = set()
    real_write = os.write

    def short_write(descriptor: int, data: bytes | memoryview) -> int:
        descriptors.add(descriptor)
        count = next(counts)
        return real_write(descriptor, data[:count])

    monkeypatch.setattr("handler.filesystem.storage_access.os.write", short_write)
    with open_owned_access(
        _owned(tmp_path), StorageOperation.OVERWRITE, target.name
    ) as replace:
        replace.replace(content)  # type: ignore[union-attr]

    assert target.read_bytes() == content
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()
    _assert_descriptors_closed(descriptors)


@pytest.mark.parametrize(
    ("operation", "method_name"),
    [
        (StorageOperation.CREATE, "create"),
        (StorageOperation.OVERWRITE, "replace"),
    ],
)
def test_owned_writes_retry_interrupted_calls(
    tmp_path, monkeypatch, operation, method_name
):
    target = tmp_path / "interrupted.bin"
    if operation is StorageOperation.OVERWRITE:
        target.write_bytes(b"old-content")
    content = b"complete-after-interrupt"
    calls = 0
    descriptors: set[int] = set()
    real_write = os.write

    def interrupted_write(descriptor: int, data: bytes | memoryview) -> int:
        nonlocal calls
        descriptors.add(descriptor)
        calls += 1
        if calls == 1:
            raise InterruptedError(errno.EINTR, "interrupted")
        count = min(3, len(data))
        return real_write(descriptor, data[:count])

    monkeypatch.setattr("handler.filesystem.storage_access.os.write", interrupted_write)
    with open_owned_access(_owned(tmp_path), operation, target.name) as capability:
        getattr(capability, method_name)(content)

    assert calls > 2
    assert target.read_bytes() == content
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()
    _assert_descriptors_closed(descriptors)


@pytest.mark.parametrize("reported_count", [0, -1, len(b"payload") + 1])
@pytest.mark.parametrize(
    ("operation", "method_name"),
    [
        (StorageOperation.CREATE, "create"),
        (StorageOperation.OVERWRITE, "replace"),
    ],
)
def test_owned_writes_reject_invalid_progress_and_rollback(
    tmp_path, monkeypatch, operation, method_name, reported_count
):
    target = tmp_path / "invalid-progress.bin"
    if operation is StorageOperation.OVERWRITE:
        target.write_bytes(b"old-content")
    descriptors: set[int] = set()

    def invalid_write(descriptor: int, _data: bytes | memoryview) -> int:
        descriptors.add(descriptor)
        return reported_count

    monkeypatch.setattr("handler.filesystem.storage_access.os.write", invalid_write)
    with pytest.raises(StorageResolutionError):
        with open_owned_access(_owned(tmp_path), operation, target.name) as capability:
            getattr(capability, method_name)(b"payload")

    if operation is StorageOperation.OVERWRITE:
        assert target.read_bytes() == b"old-content"
    else:
        assert not target.exists()
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()
    _assert_descriptors_closed(descriptors)


@pytest.mark.parametrize(
    ("operation", "method_name"),
    [
        (StorageOperation.CREATE, "create"),
        (StorageOperation.OVERWRITE, "replace"),
    ],
)
def test_owned_writes_rollback_after_partial_failure(
    tmp_path, monkeypatch, operation, method_name
):
    target = tmp_path / "partial-failure.bin"
    if operation is StorageOperation.OVERWRITE:
        target.write_bytes(b"old-content")
    calls = 0
    descriptors: set[int] = set()
    real_write = os.write

    def failing_write(descriptor: int, data: bytes | memoryview) -> int:
        nonlocal calls
        descriptors.add(descriptor)
        calls += 1
        if calls == 1:
            return real_write(descriptor, data[:2])
        raise OSError(errno.ENOSPC, "simulated write failure")

    monkeypatch.setattr("handler.filesystem.storage_access.os.write", failing_write)
    with pytest.raises(StorageResolutionError, match="not accessible"):
        with open_owned_access(_owned(tmp_path), operation, target.name) as capability:
            getattr(capability, method_name)(b"payload")

    if operation is StorageOperation.OVERWRITE:
        assert target.read_bytes() == b"old-content"
    else:
        assert not target.exists()
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()
    _assert_descriptors_closed(descriptors)


@pytest.mark.parametrize(
    ("operation", "method_name"),
    [
        (StorageOperation.CREATE, "create"),
        (StorageOperation.OVERWRITE, "replace"),
    ],
)
def test_owned_empty_writes_skip_os_write_and_close_descriptors(
    tmp_path, monkeypatch, operation, method_name
):
    target = tmp_path / "empty.bin"
    if operation is StorageOperation.OVERWRITE:
        target.write_bytes(b"old-content")
    opened: set[int] = set()
    real_open = os.open

    def tracking_open(*args, **kwargs):
        descriptor = real_open(*args, **kwargs)
        opened.add(descriptor)
        return descriptor

    def forbidden_write(*_args, **_kwargs):
        raise AssertionError("empty writes must not call os.write")

    monkeypatch.setattr("handler.filesystem.storage_access.os.open", tracking_open)
    monkeypatch.setattr("handler.filesystem.storage_access.os.write", forbidden_write)
    with open_owned_access(_owned(tmp_path), operation, target.name) as capability:
        getattr(capability, method_name)(b"")

    assert target.read_bytes() == b""
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()
    _assert_descriptors_closed(opened)


def test_subprocess_adapter_lists_only_the_capability_fd(tmp_path):
    (tmp_path / "game.rom").write_bytes(b"game")
    with open_storage_access(
        _external(tmp_path), StorageOperation.READ, "game.rom"
    ) as access:
        argv, pass_fds = access.subprocess_fd("tool", "--input")
        assert argv[:2] == ("tool", "--input")
        assert argv[2] == f"/proc/self/fd/{pass_fds[0]}"
        assert pass_fds == (access.fileno(),)


@pytest.mark.parametrize("size", [0, 1024 * 1024, 1024 * 1024 + 17])
def test_descriptor_hash_reads_exact_bytes_in_fixed_chunks(tmp_path, size):
    content = bytes((index % 251 for index in range(size)))
    (tmp_path / "game.rom").write_bytes(content)
    result = hash_descriptor_file(
        _external(tmp_path),
        "game.rom",
        max_bytes=max(1, size),
        deadline_monotonic=10.0,
        monotonic=lambda: 0.0,
    )
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    assert result.bytes_read == size
    assert result.before == result.after
    assert result.before.size == size


def test_descriptor_hash_distinguishes_same_metadata_different_bytes(tmp_path):
    path = tmp_path / "game.rom"
    path.write_bytes(b"first")
    timestamp = path.stat().st_mtime_ns
    first = hash_descriptor_file(
        _external(tmp_path),
        "game.rom",
        max_bytes=5,
        deadline_monotonic=10.0,
        monotonic=lambda: 0.0,
    )
    path.write_bytes(b"other")
    os.utime(path, ns=(timestamp, timestamp))
    second = hash_descriptor_file(
        _external(tmp_path),
        "game.rom",
        max_bytes=5,
        deadline_monotonic=10.0,
        monotonic=lambda: 0.0,
    )
    assert first.before.size == second.before.size
    assert first.before.mode == second.before.mode
    assert first.before.mtime_ns == second.before.mtime_ns
    assert first.sha256 != second.sha256


def test_descriptor_hash_rejects_byte_budget_and_deadline_without_path(tmp_path):
    (tmp_path / "secret-name.rom").write_bytes(b"1234")
    with pytest.raises(DescriptorHashBudgetError) as budget:
        hash_descriptor_file(
            _external(tmp_path),
            "secret-name.rom",
            max_bytes=3,
            deadline_monotonic=10.0,
            monotonic=lambda: 0.0,
        )
    clock = iter((0.0, 10.0))
    with pytest.raises(DescriptorHashDeadlineError) as deadline:
        hash_descriptor_file(
            _external(tmp_path),
            "secret-name.rom",
            max_bytes=4,
            deadline_monotonic=10.0,
            monotonic=lambda: next(clock),
        )
    assert "secret-name" not in str(budget.value)
    assert "secret-name" not in str(deadline.value)


def test_descriptor_hash_rejects_short_long_and_changed_reads(tmp_path, monkeypatch):
    path = tmp_path / "game.rom"
    path.write_bytes(b"1234")
    real_read = os.read
    monkeypatch.setattr("handler.filesystem.storage_access.os.read", lambda *_: b"")
    with pytest.raises(DescriptorHashShortReadError):
        hash_descriptor_file(
            _external(tmp_path),
            "game.rom",
            max_bytes=4,
            deadline_monotonic=10.0,
            monotonic=lambda: 0.0,
        )

    monkeypatch.setattr(
        "handler.filesystem.storage_access.os.read",
        lambda _fd, count: b"x" * (count + 1),
    )
    with pytest.raises(DescriptorHashConcurrentChangeError):
        hash_descriptor_file(
            _external(tmp_path),
            "game.rom",
            max_bytes=4,
            deadline_monotonic=10.0,
            monotonic=lambda: 0.0,
        )

    changed = False

    def mutate_after_read(descriptor, count):
        nonlocal changed
        chunk = real_read(descriptor, count)
        if not changed:
            changed = True
            path.write_bytes(b"12345")
        return chunk

    monkeypatch.setattr("handler.filesystem.storage_access.os.read", mutate_after_read)
    with pytest.raises(DescriptorHashConcurrentChangeError):
        hash_descriptor_file(
            _external(tmp_path),
            "game.rom",
            max_bytes=8,
            deadline_monotonic=10.0,
            monotonic=lambda: 0.0,
        )


def test_descriptor_hash_denies_symlinks_and_closes_on_every_failure(tmp_path):
    (tmp_path / "real.rom").write_bytes(b"1234")
    (tmp_path / "link.rom").symlink_to(tmp_path / "real.rom")
    before = len(os.listdir("/proc/self/fd"))
    for _ in range(20):
        with pytest.raises(UnsafeSymlinkError):
            hash_descriptor_file(
                _external(tmp_path),
                "link.rom",
                max_bytes=4,
                deadline_monotonic=10.0,
                monotonic=lambda: 0.0,
            )
        with pytest.raises(DescriptorHashBudgetError):
            hash_descriptor_file(
                _external(tmp_path),
                "real.rom",
                max_bytes=3,
                deadline_monotonic=10.0,
                monotonic=lambda: 0.0,
            )
    assert len(os.listdir("/proc/self/fd")) <= before + 1


def _kill_owned_writer(tmp_path: Path, method: str) -> Path:
    target = tmp_path / f"killed-{method}.bin"
    ready_read, ready_write = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(ready_read)
        real_write = os.write
        try:
            with open_owned_access(
                _owned(tmp_path), StorageOperation.CREATE, target.name
            ) as create:
                if method == "create":

                    def blocking_write(
                        descriptor: int, data: bytes | memoryview
                    ) -> int:
                        written = real_write(descriptor, data[:3])
                        real_write(ready_write, b"1")
                        signal.pause()
                        return written

                    os.write = blocking_write
                    create.create(b"complete-content")  # type: ignore[union-attr]
                else:
                    with create.subprocess_file() as descriptor:  # type: ignore[union-attr]
                        real_write(descriptor, b"partial")
                        real_write(ready_write, b"1")
                        signal.pause()
        finally:
            os._exit(3)

    os.close(ready_write)
    waited = False
    try:
        readable, _, _ = select.select((ready_read,), (), (), 5)
        assert readable, "writer did not reach its partial-write barrier"
        assert os.read(ready_read, 1) == b"1"
        os.kill(child, signal.SIGKILL)
        _, status = os.waitpid(child, 0)
        waited = True
        assert os.WIFSIGNALED(status)
        assert os.WTERMSIG(status) == signal.SIGKILL
    finally:
        os.close(ready_read)
        if not waited:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(child, 0)
    return target


def test_owned_create_process_crash_never_publishes_final(tmp_path):
    target = _kill_owned_writer(tmp_path, "create")

    assert not target.exists()
    staging = tuple(tmp_path.glob(f".{target.name}.*.tmp"))
    assert len(staging) == 1
    assert staging[0].read_bytes() == b"com"


def test_owned_create_subprocess_killed_writer_never_publishes_final(tmp_path):
    target = _kill_owned_writer(tmp_path, "subprocess")

    assert not target.exists()
    staging = tuple(tmp_path.glob(f".{target.name}.*.tmp"))
    assert len(staging) == 1
    assert staging[0].read_bytes() == b"partial"


def _capture_staging_descriptors(monkeypatch, target_name: str) -> set[int]:
    descriptors: set[int] = set()
    real_open = os.open

    def tracking_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        if (
            isinstance(path, str)
            and path.startswith(f".{target_name}.")
            and path.endswith(".tmp")
        ):
            descriptors.add(descriptor)
        return descriptor

    monkeypatch.setattr("handler.filesystem.storage_access.os.open", tracking_open)
    return descriptors


@pytest.mark.parametrize("method", ["create", "subprocess"])
def test_owned_create_close_failure_still_cleans_exact_staging(
    tmp_path, monkeypatch, method
):
    target = tmp_path / f"close-{method}.bin"
    staged = _capture_staging_descriptors(monkeypatch, target.name)
    real_close = os.close
    failed = False

    def failing_close(descriptor: int) -> None:
        nonlocal failed
        if descriptor in staged and not failed:
            failed = True
            real_close(descriptor)
            raise OSError(errno.EIO, "simulated close failure")
        real_close(descriptor)

    monkeypatch.setattr("handler.filesystem.storage_access.os.close", failing_close)
    with pytest.raises(StorageResolutionError):
        with open_owned_access(
            _owned(tmp_path), StorageOperation.CREATE, target.name
        ) as create:
            if method == "create":
                create.create(b"complete")  # type: ignore[union-attr]
            else:
                with create.subprocess_file() as descriptor:  # type: ignore[union-attr]
                    os.write(descriptor, b"complete")

    assert failed
    assert not target.exists()
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()


@pytest.mark.parametrize("method", ["create", "subprocess"])
def test_owned_create_file_fsync_failure_cleans_staging(tmp_path, monkeypatch, method):
    target = tmp_path / f"fsync-{method}.bin"
    staged = _capture_staging_descriptors(monkeypatch, target.name)
    real_fsync = os.fsync

    def failing_fsync(descriptor: int) -> None:
        if descriptor in staged:
            raise OSError(errno.EIO, "simulated file fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr("handler.filesystem.storage_access.os.fsync", failing_fsync)
    with pytest.raises(StorageResolutionError):
        with open_owned_access(
            _owned(tmp_path), StorageOperation.CREATE, target.name
        ) as create:
            if method == "create":
                create.create(b"complete")  # type: ignore[union-attr]
            else:
                with create.subprocess_file() as descriptor:  # type: ignore[union-attr]
                    os.write(descriptor, b"complete")

    assert not target.exists()
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()


@pytest.mark.parametrize("method", ["create", "subprocess"])
def test_owned_create_collision_preserves_existing_target(tmp_path, method):
    target = tmp_path / f"collision-{method}.bin"
    target.write_bytes(b"existing")

    with pytest.raises(StorageResolutionError):
        with open_owned_access(
            _owned(tmp_path), StorageOperation.CREATE, target.name
        ) as create:
            if method == "create":
                create.create(b"replacement")  # type: ignore[union-attr]
            else:
                with create.subprocess_file() as descriptor:  # type: ignore[union-attr]
                    os.write(descriptor, b"replacement")

    assert target.read_bytes() == b"existing"
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()


@pytest.mark.parametrize("method", ["create", "subprocess"])
def test_owned_create_success_orders_durable_no_replace_publication(
    tmp_path, monkeypatch, method
):
    target = tmp_path / f"ordered-{method}.bin"
    events: list[str] = []
    staged = _capture_staging_descriptors(monkeypatch, target.name)
    real_write = os.write
    real_fsync = os.fsync
    real_close = os.close
    real_link = os.link
    real_unlink = os.unlink

    def tracking_write(descriptor: int, data: bytes | memoryview) -> int:
        if descriptor in staged:
            events.append("write")
        return real_write(descriptor, data)

    def tracking_fsync(descriptor: int) -> None:
        events.append("file_fsync" if descriptor in staged else "parent_fsync")
        real_fsync(descriptor)

    def tracking_close(descriptor: int) -> None:
        if descriptor in staged:
            events.append("close")
        real_close(descriptor)

    def tracking_link(*args, **kwargs) -> None:
        events.append("publish")
        real_link(*args, **kwargs)

    def tracking_unlink(path, *args, **kwargs) -> None:
        if isinstance(path, str) and path.startswith(f".{target.name}."):
            events.append("staging_unlink")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr("handler.filesystem.storage_access.os.write", tracking_write)
    monkeypatch.setattr("handler.filesystem.storage_access.os.fsync", tracking_fsync)
    monkeypatch.setattr("handler.filesystem.storage_access.os.close", tracking_close)
    monkeypatch.setattr("handler.filesystem.storage_access.os.link", tracking_link)
    monkeypatch.setattr("handler.filesystem.storage_access.os.unlink", tracking_unlink)

    with open_owned_access(
        _owned(tmp_path), StorageOperation.CREATE, target.name
    ) as create:
        if method == "create":
            create.create(b"complete")  # type: ignore[union-attr]
        else:
            with create.subprocess_file() as descriptor:  # type: ignore[union-attr]
                os.write(descriptor, b"complete")

    assert target.read_bytes() == b"complete"
    assert events[:6] == [
        "write",
        "file_fsync",
        "close",
        "publish",
        "staging_unlink",
        "parent_fsync",
    ]


def test_owned_create_binary_file_publishes_only_after_success(tmp_path):
    target = tmp_path / "streamed.bin"
    with open_owned_access(
        _owned(tmp_path), StorageOperation.CREATE, target.name
    ) as create:
        with create.binary_file() as file:  # type: ignore[union-attr]
            file.write(b"streamed")
            file.flush()
            assert not target.exists()

    assert target.read_bytes() == b"streamed"


def test_owned_create_parent_fsync_failure_durably_rolls_back(tmp_path, monkeypatch):
    target = tmp_path / "parent-fsync.bin"
    staged = _capture_staging_descriptors(monkeypatch, target.name)
    real_fsync = os.fsync
    parent_calls = 0

    def failing_first_parent_fsync(descriptor: int) -> None:
        nonlocal parent_calls
        if descriptor not in staged:
            parent_calls += 1
            if parent_calls == 1:
                raise OSError(errno.EIO, "simulated parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(
        "handler.filesystem.storage_access.os.fsync", failing_first_parent_fsync
    )
    with pytest.raises(StorageResolutionError) as error:
        with open_owned_access(
            _owned(tmp_path), StorageOperation.CREATE, target.name
        ) as create:
            create.create(b"complete")  # type: ignore[union-attr]

    assert error.value.__class__.__name__ != "IndeterminateOwnedPublicationError"
    assert parent_calls == 2
    assert not target.exists()
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()


def test_owned_create_parent_fsync_rollback_failure_is_indeterminate_complete(
    tmp_path, monkeypatch
):
    target = tmp_path / "indeterminate.bin"
    staged = _capture_staging_descriptors(monkeypatch, target.name)
    real_fsync = os.fsync
    real_unlink = os.unlink

    def failing_parent_fsync(descriptor: int) -> None:
        if descriptor not in staged:
            raise OSError(errno.EIO, "simulated parent fsync failure")
        real_fsync(descriptor)

    def failing_final_unlink(path, *args, **kwargs) -> None:
        if path == target.name:
            raise OSError(errno.EIO, "simulated rollback unlink failure")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(
        "handler.filesystem.storage_access.os.fsync", failing_parent_fsync
    )
    monkeypatch.setattr(
        "handler.filesystem.storage_access.os.unlink", failing_final_unlink
    )
    with pytest.raises(StorageResolutionError, match="state") as error:
        with open_owned_access(
            _owned(tmp_path), StorageOperation.CREATE, target.name
        ) as create:
            create.create(b"complete")  # type: ignore[union-attr]

    assert error.value.__class__.__name__ == "IndeterminateOwnedPublicationError"
    assert target.read_bytes() == b"complete"
    assert tuple(tmp_path.glob(f".{target.name}.*.tmp")) == ()


def test_owned_create_concurrent_calls_use_unique_staging_names(tmp_path):
    target = "concurrent.bin"
    barrier = threading.Barrier(2, timeout=5)
    staging_names: list[str] = []
    errors: list[BaseException] = []

    class AbortPublication(Exception):
        pass

    def hold_staging() -> None:
        try:
            with open_owned_access(
                _owned(tmp_path), StorageOperation.CREATE, target
            ) as create:
                try:
                    with create.subprocess_file() as descriptor:  # type: ignore[union-attr]
                        staging_names.append(
                            Path(os.readlink(f"/proc/self/fd/{descriptor}")).name
                        )
                        barrier.wait()
                        raise AbortPublication()
                except AbortPublication:
                    pass
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=hold_staging) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=7)

    assert all(not thread.is_alive() for thread in threads)
    assert errors == []
    assert len(staging_names) == 2
    assert len(set(staging_names)) == 2
    assert not (tmp_path / target).exists()
    assert tuple(tmp_path.glob(f".{target}.*.tmp")) == ()
