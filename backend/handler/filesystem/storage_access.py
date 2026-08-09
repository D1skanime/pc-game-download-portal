from __future__ import annotations

import errno
import hashlib
import os
import stat as stat_module
from collections.abc import Iterator
from typing import Self

from exceptions.storage_exceptions import (
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    StorageResolutionError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
)
from handler.filesystem.storage_policy import (
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


def _open_root(storage_root: StorageRoot) -> int:
    try:
        descriptor = os.open(storage_root.container_path, _BASE_FLAGS | os.O_DIRECTORY)
    except OSError as error:
        if error.errno == errno.ENOTDIR:
            try:
                if stat_module.S_ISLNK(os.lstat(storage_root.container_path).st_mode):
                    raise UnsafeSymlinkError() from error
            except FileNotFoundError:
                pass
        raise _bounded_open_error(error, root=True) from error
    if not stat_module.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise MissingStorageRootError(storage_root.id)
    return descriptor


def _open_target(
    storage_root: StorageRoot, relative_path: str, *, directory: bool
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
            if not final or directory:
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
                        if final and directory:
                            raise NonDirectoryStorageTargetError() from error
                    except FileNotFoundError:
                        pass
                raise _bounded_open_error(error) from error
            os.close(current)
            current = following
        metadata = os.fstat(current)
        if directory and not stat_module.S_ISDIR(metadata.st_mode):
            raise NonDirectoryStorageTargetError()
        if not directory and not stat_module.S_ISREG(metadata.st_mode):
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
    storage_root: StorageRoot, operation: StorageOperation, raw_relative_path: str
) -> _DescriptorCapability:
    """Authorize and bind one external read operation to an already-open descriptor."""
    descriptor = create_external_descriptor(storage_root)
    grant = StoragePolicy.authorize(operation, descriptor)
    relative_path = normalize_relative_path(
        raw_relative_path, allow_root=grant.operation in _DIRECTORY_OPERATIONS
    )
    capability_type = _CAPABILITIES[grant.operation]
    target = _open_target(
        storage_root,
        relative_path,
        directory=grant.operation in _DIRECTORY_OPERATIONS,
    )
    return capability_type(target)
