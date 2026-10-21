from __future__ import annotations

import errno
import hashlib
import os
import stat as stat_module
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import BinaryIO, Self

from exceptions.storage_exceptions import (
    DescriptorHashBudgetError,
    DescriptorHashConcurrentChangeError,
    DescriptorHashDeadlineError,
    DescriptorHashShortReadError,
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    StorageResolutionError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
)
from handler.filesystem.owned_publication import (
    IndeterminateOwnedPublicationError as IndeterminateOwnedPublicationError,
)
from handler.filesystem.owned_publication import PreparedOwnedFile as PreparedOwnedFile
from handler.filesystem.owned_publication import (
    PreparedOwnedReplace,
    _OwnedStagedPublication,
    open_replacement_temporary,
    serialized_owned_write,
)
from handler.filesystem.owned_writer_domain import owned_writer_domain
from handler.filesystem.storage_policy import (
    ExternalStorageDescriptor,
    OwnedStorageDescriptor,
    StorageOperation,
    StoragePolicy,
)
from handler.filesystem.storage_resolver import normalize_relative_path

_BASE_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
_DIRECTORY_OPERATIONS = {
    StorageOperation.RESOLVE,
    StorageOperation.LIST,
    StorageOperation.SCAN,
}


def _bounded_open_error(
    error: OSError, *, root: bool = False
) -> StorageResolutionError:
    if error.errno == errno.ELOOP:
        return UnsafeSymlinkError()
    if error.errno in {errno.EACCES, errno.EPERM}:
        return UnreadableStorageTargetError()
    if error.errno in {errno.ENOENT, errno.ENOTDIR}:
        return MissingStorageRootError(0) if root else MissingStorageTargetError()
    return StorageResolutionError("Storage target is not accessible")


def _write_all(descriptor: int, content: bytes) -> None:
    remaining = memoryview(content)
    while remaining:
        try:
            written = os.write(descriptor, remaining)
        except InterruptedError:
            continue
        if written <= 0 or written > len(remaining):
            raise OSError(errno.EIO, "Storage write did not make valid progress")
        remaining = remaining[written:]


def _root_path(
    storage_root: ExternalStorageDescriptor | OwnedStorageDescriptor,
) -> str:
    if storage_root._root_path is None:
        raise TypeError("a bound storage descriptor is required")
    return str(storage_root._root_path)


def _open_root(
    storage_root: ExternalStorageDescriptor | OwnedStorageDescriptor,
) -> int:
    try:
        descriptor = os.open(_root_path(storage_root), _BASE_FLAGS | os.O_DIRECTORY)
    except OSError as error:
        if error.errno == errno.ENOTDIR:
            try:
                if stat_module.S_ISLNK(os.lstat(_root_path(storage_root)).st_mode):
                    raise UnsafeSymlinkError() from error
            except FileNotFoundError:
                pass
        raise _bounded_open_error(error, root=True) from error
    if not stat_module.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        root_id = (
            storage_root.root_id
            if isinstance(storage_root, ExternalStorageDescriptor)
            else 0
        )
        raise MissingStorageRootError(root_id)
    return descriptor


def _open_target(
    storage_root: ExternalStorageDescriptor | OwnedStorageDescriptor,
    relative_path: str,
    *,
    directory: bool | None,
) -> int:
    current = _open_root(storage_root)
    if not relative_path:
        if directory:
            return current
        os.close(current)
        raise MissingStorageTargetError()
    components = relative_path.split("/")
    try:
        for index, component in enumerate(components):
            final = index == len(components) - 1
            flags = _BASE_FLAGS
            if not final or directory is True:
                flags |= os.O_DIRECTORY
            try:
                following = os.open(component, flags, dir_fd=current)
            except OSError as error:
                if error.errno == errno.ENOTDIR:
                    try:
                        metadata = os.stat(
                            component, dir_fd=current, follow_symlinks=False
                        )
                        if stat_module.S_ISLNK(metadata.st_mode):
                            raise UnsafeSymlinkError() from error
                        if final and directory is True:
                            raise NonDirectoryStorageTargetError() from error
                    except FileNotFoundError:
                        pass
                raise _bounded_open_error(error) from error
            os.close(current)
            current = following
        metadata = os.fstat(current)
        if directory is True and not stat_module.S_ISDIR(metadata.st_mode):
            raise NonDirectoryStorageTargetError()
        if directory is False and not stat_module.S_ISREG(metadata.st_mode):
            raise StorageResolutionError("Storage target is not a regular file")
        return current
    except Exception:
        os.close(current)
        raise


class _DescriptorCapability:
    __slots__ = ("_descriptor",)

    def __init__(self, descriptor: int) -> None:
        self._descriptor: int | None = descriptor

    def __enter__(self) -> Self:
        self._require_descriptor()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _require_descriptor(self) -> int:
        if self._descriptor is None:
            raise StorageResolutionError("Storage capability is closed")
        return self._descriptor

    def fileno(self) -> int:
        return self._require_descriptor()

    def subprocess_fd(self, *argv: str) -> tuple[tuple[str, ...], tuple[int, ...]]:
        descriptor = self._require_descriptor()
        return (*argv, f"/proc/self/fd/{descriptor}"), (descriptor,)

    def close(self) -> None:
        if self._descriptor is not None:
            os.close(self._descriptor)
            self._descriptor = None


class ResolveCapability(_DescriptorCapability):
    def resolve(self) -> os.stat_result:
        return os.fstat(self._require_descriptor())


class ListCapability(_DescriptorCapability):
    def list(self) -> tuple[str, ...]:
        return tuple(sorted(os.listdir(self._require_descriptor())))


class StatCapability(_DescriptorCapability):
    def stat(self) -> os.stat_result:
        return os.fstat(self._require_descriptor())


class ReadCapability(_DescriptorCapability):
    @contextmanager
    def binary_file(self) -> Iterator[BinaryIO]:
        descriptor = os.dup(self._require_descriptor())
        with os.fdopen(descriptor, "rb", closefd=True) as file:
            yield file

    def read(self) -> bytes:
        descriptor = self._require_descriptor()
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        return b"".join(chunks)


@dataclass(frozen=True, slots=True)
class ScannedEntry:
    name: str
    metadata: os.stat_result


@dataclass(frozen=True, slots=True)
class BoundedScan:
    entries: tuple[ScannedEntry, ...]
    complete: bool
    reason: str = ""


def directory_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


class ScanCapability(_DescriptorCapability):
    def scan(self) -> tuple[str, ...]:
        return tuple(sorted(os.listdir(self._require_descriptor())))

    def scan_bounded(self, max_entries: int, *, check=lambda: None) -> BoundedScan:
        """Bound retained entries before allocation; never open entry bodies."""
        if type(max_entries) is not int or max_entries < 0:
            raise ValueError("max_entries must be a nonnegative integer")
        descriptor = self._require_descriptor()
        entries: list[ScannedEntry] = []
        try:
            before = directory_signature(os.fstat(descriptor))
            check()
            with os.scandir(descriptor) as iterator:
                for entry in iterator:
                    check()
                    if len(entries) == max_entries:
                        return BoundedScan(tuple(entries), False, "entry_limit")
                    metadata = os.stat(
                        entry.name, dir_fd=descriptor, follow_symlinks=False
                    )
                    if not (
                        stat_module.S_ISDIR(metadata.st_mode)
                        or stat_module.S_ISREG(metadata.st_mode)
                    ):
                        return BoundedScan(tuple(entries), False, "unsupported_entry")
                    entries.append(ScannedEntry(entry.name, metadata))
            check()
            if before != directory_signature(os.fstat(descriptor)):
                return BoundedScan(tuple(entries), False, "unstable_directory")
        except OSError:
            return BoundedScan(tuple(entries), False, "unreadable")
        return BoundedScan(tuple(sorted(entries, key=lambda entry: entry.name)), True)


class HashCapability(_DescriptorCapability):
    def hash(self, algorithm: str = "sha256") -> str:
        try:
            digest = hashlib.new(algorithm)
        except ValueError as error:
            raise StorageResolutionError("Unsupported hash algorithm") from error
        descriptor = self._require_descriptor()
        os.lseek(descriptor, 0, os.SEEK_SET)
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        return digest.hexdigest()


class StreamCapability(_DescriptorCapability):
    def stream(self, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        descriptor = self._require_descriptor()
        os.lseek(descriptor, 0, os.SEEK_SET)
        while chunk := os.read(descriptor, chunk_size):
            yield chunk


class DownloadCapability(_DescriptorCapability):
    @contextmanager
    def binary_file(self) -> Iterator[BinaryIO]:
        descriptor = os.dup(self._require_descriptor())
        with os.fdopen(descriptor, "rb", closefd=True) as file:
            yield file

    def download(self, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        descriptor = self._require_descriptor()
        os.lseek(descriptor, 0, os.SEEK_SET)
        while chunk := os.read(descriptor, chunk_size):
            yield chunk


_CAPABILITIES = {
    StorageOperation.RESOLVE: ResolveCapability,
    StorageOperation.LIST: ListCapability,
    StorageOperation.STAT: StatCapability,
    StorageOperation.READ: ReadCapability,
    StorageOperation.SCAN: ScanCapability,
    StorageOperation.HASH: HashCapability,
    StorageOperation.STREAM: StreamCapability,
    StorageOperation.DOWNLOAD: DownloadCapability,
}


def open_storage_access(
    storage_root: ExternalStorageDescriptor | OwnedStorageDescriptor,
    operation: StorageOperation,
    raw_relative_path: str,
) -> _DescriptorCapability:
    """Authorize and bind one external read operation to an already-open descriptor."""
    if not isinstance(storage_root, ExternalStorageDescriptor):
        raise TypeError("a bound external storage descriptor is required")
    grant = StoragePolicy.authorize(operation, storage_root)
    relative_path = normalize_relative_path(
        raw_relative_path, allow_root=grant.operation in _DIRECTORY_OPERATIONS
    )
    capability_type = _CAPABILITIES[grant.operation]
    target = _open_target(
        storage_root,
        relative_path,
        directory=(
            True
            if grant.operation in _DIRECTORY_OPERATIONS
            else None if grant.operation is StorageOperation.STAT else False
        ),
    )
    return capability_type(target)


@dataclass(frozen=True, slots=True)
class DescriptorFileMetadata:
    device: int
    inode: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int


@dataclass(frozen=True, slots=True)
class DescriptorHashResult:
    sha256: str
    bytes_read: int
    before: DescriptorFileMetadata
    after: DescriptorFileMetadata


def _descriptor_metadata(metadata: os.stat_result) -> DescriptorFileMetadata:
    return DescriptorFileMetadata(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        size=metadata.st_size,
        mtime_ns=metadata.st_mtime_ns,
        ctime_ns=metadata.st_ctime_ns,
    )


def hash_descriptor_file(
    descriptor: ExternalStorageDescriptor,
    relative_path: str,
    *,
    max_bytes: int,
    deadline_monotonic: float,
    monotonic=time.monotonic,
) -> DescriptorHashResult:
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    if not isinstance(deadline_monotonic, (int, float)):
        raise TypeError("deadline_monotonic must be numeric")

    with open_storage_access(
        descriptor, StorageOperation.HASH, relative_path
    ) as capability:
        file_descriptor = capability.fileno()
        before = _descriptor_metadata(os.fstat(file_descriptor))
        if not stat_module.S_ISREG(before.mode):
            raise DescriptorHashConcurrentChangeError()
        if before.size > max_bytes:
            raise DescriptorHashBudgetError()

        digest = hashlib.sha256()
        bytes_read = 0
        os.lseek(file_descriptor, 0, os.SEEK_SET)
        while bytes_read < before.size:
            if monotonic() >= deadline_monotonic:
                raise DescriptorHashDeadlineError()
            requested = min(1024 * 1024, before.size - bytes_read)
            try:
                chunk = os.read(file_descriptor, requested)
            except OSError as error:
                raise StorageResolutionError(
                    "Storage hash read could not be completed"
                ) from error
            if monotonic() >= deadline_monotonic:
                raise DescriptorHashDeadlineError()
            if not chunk:
                raise DescriptorHashShortReadError()
            if len(chunk) > requested:
                raise DescriptorHashConcurrentChangeError()
            digest.update(chunk)
            bytes_read += len(chunk)

        if monotonic() >= deadline_monotonic:
            raise DescriptorHashDeadlineError()
        try:
            extra = os.read(file_descriptor, 1)
        except OSError as error:
            raise StorageResolutionError(
                "Storage hash read could not be completed"
            ) from error
        if monotonic() >= deadline_monotonic:
            raise DescriptorHashDeadlineError()
        if extra:
            raise DescriptorHashConcurrentChangeError()
        after = _descriptor_metadata(os.fstat(file_descriptor))
        if before != after or not stat_module.S_ISREG(after.mode):
            raise DescriptorHashConcurrentChangeError()
        return DescriptorHashResult(digest.hexdigest(), bytes_read, before, after)


class OwnedRead(ReadCapability):
    pass


class _OwnedMutationCapability:
    __slots__ = ("_parent_descriptor", "_name")

    def __init__(self, parent_descriptor: int, name: str) -> None:
        self._parent_descriptor: int | None = parent_descriptor
        self._name = name

    def __enter__(self) -> Self:
        self._require_parent()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _require_parent(self) -> int:
        if self._parent_descriptor is None:
            raise StorageResolutionError("Storage capability is closed")
        return self._parent_descriptor

    def close(self) -> None:
        if self._parent_descriptor is not None:
            os.close(self._parent_descriptor)
            self._parent_descriptor = None


class OwnedCreate(_OwnedMutationCapability):
    def __init__(self, parent_descriptor, name, *, storage=None, relative_path=None):
        super().__init__(parent_descriptor, name)
        self._storage = storage
        self._relative_path = relative_path

    def prepare_binary_file(self) -> PreparedOwnedFile:
        return PreparedOwnedFile(
            self._require_parent(),
            self._name,
            storage=self._storage,
            relative_path=self._relative_path,
        )

    @contextmanager
    def subprocess_file(self) -> Iterator[int]:
        publication = _OwnedStagedPublication(self._require_parent(), self._name)
        try:
            yield publication.descriptor
        except BaseException:
            publication.abort()
            raise
        publication.publish()

    @contextmanager
    def binary_file(self) -> Iterator[BinaryIO]:
        publication = _OwnedStagedPublication(self._require_parent(), self._name)
        try:
            file = os.fdopen(publication.descriptor, "w+b", closefd=False)
        except OSError as error:
            publication.abort()
            raise _bounded_open_error(error) from error
        try:
            yield file
        except BaseException:
            try:
                file.close()
            except OSError:
                pass
            publication.abort()
            raise
        try:
            file.flush()
            file.close()
        except OSError as error:
            try:
                file.close()
            except OSError:
                pass
            publication.abort()
            raise _bounded_open_error(error) from error
        publication.publish()

    def create(self, content: bytes) -> None:
        publication = _OwnedStagedPublication(self._require_parent(), self._name)
        try:
            _write_all(publication.descriptor, content)
        except OSError as error:
            publication.abort()
            raise _bounded_open_error(error) from error
        publication.publish()


class OwnedReplace(_OwnedMutationCapability):
    def __init__(self, parent_descriptor, name, *, storage=None, relative_path=None):
        super().__init__(parent_descriptor, name)
        self._storage = storage
        self._relative_path = relative_path

    def prepare_binary_file(self):
        return PreparedOwnedReplace(
            self._require_parent(),
            self._name,
            storage=self._storage,
            relative_path=self._relative_path,
        )

    @contextmanager
    def binary_file(self, *, unique=False) -> Iterator[BinaryIO]:
        parent = self._require_parent()
        temporary = ""
        descriptor: int | None = None
        created = False
        try:
            descriptor, temporary = open_replacement_temporary(
                parent, self._name, os.O_RDWR, unique=unique
            )
            created = True
            with os.fdopen(descriptor, "w+b", closefd=False) as file:
                yield file
                file.flush()
                os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            with owned_writer_domain():
                os.replace(temporary, self._name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            if created:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except OSError:
                    pass
            raise

    def replace(self, content: bytes, *, unique=False) -> None:
        parent = self._require_parent()
        temporary = ""
        descriptor: int | None = None
        created = False
        try:
            descriptor, temporary = open_replacement_temporary(
                parent, self._name, os.O_WRONLY, unique=unique
            )
            created = True
            _write_all(descriptor, content)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            with owned_writer_domain():
                os.replace(temporary, self._name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
        except OSError as error:
            if descriptor is not None:
                os.close(descriptor)
            if created:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except OSError:
                    pass
            raise _bounded_open_error(error) from error


class OwnedDelete(_OwnedMutationCapability):
    @serialized_owned_write
    def delete(self) -> None:
        try:
            os.unlink(self._name, dir_fd=self._require_parent())
            os.fsync(self._require_parent())
        except OSError as error:
            raise _bounded_open_error(error) from error


class OwnedDirectory(_OwnedMutationCapability):
    def mkdir(self) -> None:
        try:
            os.mkdir(self._name, mode=0o755, dir_fd=self._require_parent())
            os.fsync(self._require_parent())
        except OSError as error:
            raise _bounded_open_error(error) from error

    def rmdir(self) -> None:
        try:
            os.rmdir(self._name, dir_fd=self._require_parent())
        except OSError as error:
            raise _bounded_open_error(error) from error


_OWNED_CAPABILITIES = {
    StorageOperation.READ: OwnedRead,
    StorageOperation.CREATE: OwnedCreate,
    StorageOperation.OVERWRITE: OwnedReplace,
    StorageOperation.DELETE: OwnedDelete,
    StorageOperation.MKDIR: OwnedDirectory,
}


def _open_owned_parent(
    storage: OwnedStorageDescriptor, relative_path: str
) -> tuple[int, str]:
    components = relative_path.split("/")
    name = components.pop()
    parent_path = "/".join(components)
    parent = (
        _open_target(storage, parent_path, directory=True)
        if parent_path
        else _open_root(storage)
    )
    return parent, name


def open_owned_access(
    storage: OwnedStorageDescriptor, operation: StorageOperation, raw_relative_path: str
) -> OwnedRead | OwnedCreate | OwnedReplace | OwnedDelete | OwnedDirectory:
    """Authorize one closed owned operation without exposing ambient paths."""
    if not isinstance(storage, OwnedStorageDescriptor):
        raise TypeError("a trusted owned storage descriptor is required")
    if storage._root_path is None:
        raise TypeError("a composition-bound owned storage descriptor is required")
    if operation not in _OWNED_CAPABILITIES:
        StoragePolicy.authorize(operation, storage)
    StoragePolicy.authorize(operation, storage)
    relative_path = normalize_relative_path(raw_relative_path)
    capability_type = _OWNED_CAPABILITIES[operation]
    if capability_type is OwnedRead:
        return OwnedRead(_open_target(storage, relative_path, directory=False))
    parent, name = _open_owned_parent(storage, relative_path)
    if capability_type in (OwnedCreate, OwnedReplace):
        return capability_type(
            parent, name, storage=storage, relative_path=relative_path
        )
    return capability_type(parent, name)
