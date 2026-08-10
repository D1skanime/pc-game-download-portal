from __future__ import annotations

import errno
import hashlib
import os
import stat as stat_module
from collections.abc import Iterator
from contextlib import contextmanager
from typing import BinaryIO, Self

from exceptions.storage_exceptions import (
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    StorageResolutionError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
)
from handler.filesystem.storage_policy import (
    ExternalStorageDescriptor,
    OwnedStorageDescriptor,
    StorageOperation,
    StoragePolicy,
    create_external_descriptor,
)
from handler.filesystem.storage_resolver import normalize_relative_path
from models.storage import StorageRoot

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


def _root_path(
    storage_root: StorageRoot | ExternalStorageDescriptor | OwnedStorageDescriptor,
) -> str:
    if isinstance(storage_root, (ExternalStorageDescriptor, OwnedStorageDescriptor)):
        if storage_root._root_path is None:
            raise TypeError("a bound storage descriptor is required")
        return str(storage_root._root_path)
    return storage_root.container_path


def _open_root(
    storage_root: StorageRoot | ExternalStorageDescriptor | OwnedStorageDescriptor,
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
            else storage_root.id
        )
        raise MissingStorageRootError(root_id)
    return descriptor


def _open_target(
    storage_root: StorageRoot | ExternalStorageDescriptor | OwnedStorageDescriptor,
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


class ScanCapability(_DescriptorCapability):
    def scan(self) -> tuple[str, ...]:
        return tuple(sorted(os.listdir(self._require_descriptor())))


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
    storage_root: StorageRoot | ExternalStorageDescriptor | OwnedStorageDescriptor,
    operation: StorageOperation,
    raw_relative_path: str,
) -> _DescriptorCapability:
    """Authorize and bind one external read operation to an already-open descriptor."""
    descriptor = (
        storage_root
        if isinstance(storage_root, ExternalStorageDescriptor)
        else create_external_descriptor(storage_root)
    )
    grant = StoragePolicy.authorize(operation, descriptor)
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
    def create(self, content: bytes) -> None:
        parent = self._require_parent()
        try:
            descriptor = os.open(
                self._name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o644,
                dir_fd=parent,
            )
        except OSError as error:
            raise _bounded_open_error(error) from error
        try:
            os.write(descriptor, content)
        finally:
            os.close(descriptor)


class OwnedReplace(_OwnedMutationCapability):
    def replace(self, content: bytes) -> None:
        parent = self._require_parent()
        temporary = f".{self._name}.{os.getpid()}.tmp"
        descriptor: int | None = None
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o644,
                dir_fd=parent,
            )
            os.write(descriptor, content)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.replace(temporary, self._name, src_dir_fd=parent, dst_dir_fd=parent)
        except OSError as error:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=parent)
            except OSError:
                pass
            raise _bounded_open_error(error) from error


class OwnedDelete(_OwnedMutationCapability):
    def delete(self) -> None:
        try:
            os.unlink(self._name, dir_fd=self._require_parent())
        except OSError as error:
            raise _bounded_open_error(error) from error


class OwnedDirectory(_OwnedMutationCapability):
    def mkdir(self) -> None:
        try:
            os.mkdir(self._name, mode=0o755, dir_fd=self._require_parent())
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
        StoragePolicy.authorize(operation, object())
    StoragePolicy.authorize(operation, storage)
    relative_path = normalize_relative_path(raw_relative_path)
    capability_type = _OWNED_CAPABILITIES[operation]
    if capability_type is OwnedRead:
        return OwnedRead(_open_target(storage, relative_path, directory=False))
    parent, name = _open_owned_parent(storage, relative_path)
    return capability_type(parent, name)
