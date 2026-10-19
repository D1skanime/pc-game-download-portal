"""Prepared no-clobber publication lifecycle for the owned storage authority."""

from __future__ import annotations

import errno
import hashlib
import os
import secrets
import stat
from contextlib import contextmanager
from functools import wraps

from exceptions.storage_exceptions import StorageResolutionError
from handler.filesystem.owned_content_proof import verify_owned_content
from handler.filesystem.owned_writer_domain import owned_writer_domain


def serialized_owned_write(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with owned_writer_domain():
            return function(*args, **kwargs)

    return wrapped


def _prove(parent, name, ownership, expected: tuple[str, int] | None):
    info = _private_metadata(parent, name, ownership)
    if ownership["sealed"] is not None or expected is not None:
        if expected is None:
            raise StorageResolutionError("Owned content proof is missing")
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent,
        )
        try:
            current = os.fstat(descriptor)
            if _inode(current) != _inode(info) or _version(current) != _version(info):
                raise StorageResolutionError("Owned content changed")
            verify_owned_content(
                descriptor,
                expected[0],
                expected[1],
                (*_inode(current), *_version(current)),
            )
            _private_metadata(parent, name, ownership)
        finally:
            os.close(descriptor)
    return info


def _open_error(error):
    from handler.filesystem.storage_access import _bounded_open_error

    return _bounded_open_error(error)


def _inode(info):
    return info.st_dev, info.st_ino


def _version(info):
    return info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _private_metadata(parent, name, ownership):
    info = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if (
        not stat.S_ISREG(info.st_mode)
        or list(_inode(os.fstat(parent))) != ownership["parent"]
        or list(_inode(info)) != ownership["file"]
        or (
            ownership["sealed"] is not None
            and list(_version(info)) != ownership["sealed"]
        )
    ):
        raise StorageResolutionError("Owned staging identity changed")
    return info


class IndeterminateOwnedPublicationError(StorageResolutionError):
    """Complete owned bytes may be visible, but publication was not acknowledged."""

    code = "indeterminate_owned_publication"

    def __init__(self) -> None:
        super().__init__("Owned publication state is indeterminate")


class _OwnedStagedPublication:
    _OPEN_ATTEMPTS = 8

    def __init__(self, parent_descriptor: int, final_name: str) -> None:
        self._parent_descriptor = parent_descriptor
        self._final_name = final_name
        self._staging_name = ""
        self._descriptor: int | None = None
        self._ownership: dict = {}
        self._expected: tuple[str, int] | None = None
        for _attempt in range(self._OPEN_ATTEMPTS):
            staging_name = f".{final_name}.{secrets.token_hex(16)}.tmp"
            try:
                descriptor = os.open(
                    staging_name,
                    os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                    0o644,
                    dir_fd=parent_descriptor,
                )
            except OSError as error:
                if error.errno == errno.EEXIST:
                    continue
                raise _open_error(error) from error
            self._staging_name = staging_name
            self._descriptor = descriptor
            self._ownership = dict(
                parent=list(_inode(os.fstat(parent_descriptor))),
                file=list(_inode(os.fstat(descriptor))),
                sealed=None,
            )
            return
        raise StorageResolutionError("Owned staging file could not be created")

    @classmethod
    def _reopen(cls, parent, final_name, private_name, ownership, expected=None):
        publication = cls.__new__(cls)
        publication._parent_descriptor = parent
        publication._final_name = final_name
        publication._staging_name = private_name
        publication._descriptor = None
        publication._ownership = ownership
        publication._expected = expected
        try:
            _private_metadata(parent, private_name, ownership)
            descriptor = os.open(
                private_name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=parent,
            )
            publication._descriptor = descriptor
            info = os.fstat(descriptor)
            if (
                not stat.S_ISREG(info.st_mode)
                or list(_inode(info)) != ownership["file"]
                or list(_version(info)) != ownership["sealed"]
            ):
                raise StorageResolutionError("Owned staging identity changed")
            return publication
        except BaseException:
            if publication._descriptor is not None:
                publication._close_descriptor()
            raise

    @property
    def descriptor(self) -> int:
        if self._descriptor is None:
            raise StorageResolutionError("Owned staging file is closed")
        return self._descriptor

    def _close_descriptor(self) -> None:
        descriptor = self.descriptor
        self._descriptor = None
        os.close(descriptor)

    def _unlink_owned(self, name):
        try:
            _prove(self._parent_descriptor, name, self._ownership, self._expected)
            os.unlink(name, dir_fd=self._parent_descriptor)
            return True
        except FileNotFoundError:
            return True
        except (OSError, StorageResolutionError):
            return False

    @serialized_owned_write
    def abort(self) -> None:
        if self._descriptor is not None:
            try:
                self._close_descriptor()
            except OSError:
                pass
        self._unlink_owned(self._staging_name)
        try:
            os.fsync(self._parent_descriptor)
        except OSError:
            pass

    def _rollback_published(self) -> bool:
        complete = self._unlink_owned(self._final_name)
        complete = self._unlink_owned(self._staging_name) and complete
        try:
            os.fsync(self._parent_descriptor)
        except OSError:
            complete = False
        return complete

    @serialized_owned_write
    def publish(self, *, final_authority_check=None) -> None:
        try:
            before = _prove(
                self._parent_descriptor,
                self._staging_name,
                self._ownership,
                self._expected,
            )
            if _inode(os.fstat(self.descriptor)) != _inode(before):
                raise StorageResolutionError("Owned staging identity changed")
            os.fsync(self.descriptor)
            self._close_descriptor()
            if final_authority_check is not None:
                final_authority_check()
            os.link(
                self._staging_name,
                self._final_name,
                src_dir_fd=self._parent_descriptor,
                dst_dir_fd=self._parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as error:
            self.abort()
            raise _open_error(error) from error
        # Linking changes ctime. The linked inode and completed content must still match.
        self._ownership = {**self._ownership, "sealed": None}
        after = os.stat(
            self._final_name, dir_fd=self._parent_descriptor, follow_symlinks=False
        )
        if (
            not stat.S_ISREG(after.st_mode)
            or _inode(after) != _inode(before)
            or (after.st_size, after.st_mtime_ns)
            != (before.st_size, before.st_mtime_ns)
        ):
            raise IndeterminateOwnedPublicationError()
        try:
            if not self._unlink_owned(self._staging_name):
                raise OSError(errno.EIO, "Owned staging identity changed")
            os.fsync(self._parent_descriptor)
        except OSError as error:
            if self._rollback_published():
                raise _open_error(error) from error
            raise IndeterminateOwnedPublicationError() from error


class PreparedOwnedFile:
    """Seal completed bytes and reopen only their exact owned private inode."""

    def __init__(
        self,
        parent_descriptor: int,
        final_name: str,
        *,
        storage=None,
        relative_path=None,
    ) -> None:
        self._parent: int | None = os.dup(parent_descriptor)
        self._closed = False
        self._sealed = False
        self._storage = storage
        self._relative_path = relative_path
        self._final_name = final_name
        self._expected: tuple[str, int] | None = None
        try:
            self._publication = _OwnedStagedPublication(self._parent, final_name)
            self.private_basename = self._publication._staging_name
            self.file = os.fdopen(self._publication.descriptor, "w+b", closefd=False)
            self.ownership = self._publication._ownership
        except BaseException:
            if hasattr(self, "_publication"):
                self._publication.abort()
            self._close_parent()
            raise

    def _close_parent(self):
        parent, self._parent = self._parent, None
        if parent is not None:
            os.close(parent)

    def seal(self):
        if (
            self._closed
            or self._sealed
            or self._storage is None
            or self._relative_path is None
        ):
            raise StorageResolutionError("Prepared owned file cannot be sealed")
        try:
            self.file.flush()
            os.fsync(self.file.fileno())
            before = os.fstat(self.file.fileno())
            self.file.seek(0)
            digest, total = hashlib.sha256(), 0
            while chunk := self.file.read(1024 * 1024):
                digest.update(chunk)
                total += len(chunk)
            after = os.fstat(self.file.fileno())
            if (
                _inode(before) != _inode(after)
                or _version(before) != _version(after)
                or total != after.st_size
            ):
                raise StorageResolutionError("Owned staging content changed")
            self.ownership = {**self.ownership, "sealed": list(_version(after))}
            self._expected = (digest.hexdigest(), total)
            _private_metadata(self._parent, self.private_basename, self.ownership)
            assert self._parent is not None
            os.fsync(self._parent)
            self.file.close()
            self._publication._ownership = self.ownership
            self._publication._expected = self._expected
            self._publication._close_descriptor()
            self._close_parent()
            self._sealed = True
            return digest.hexdigest(), total
        except BaseException:
            self.abort()
            raise

    @contextmanager
    def _reacquire(self):
        from handler.filesystem.storage_access import (
            OwnedCreate,
            OwnedReplace,
            open_owned_access,
        )
        from handler.filesystem.storage_policy import StorageOperation

        with open_owned_access(
            self._storage,
            getattr(self, "_operation", StorageOperation.CREATE),
            self._relative_path,
        ) as access:
            assert isinstance(access, (OwnedCreate, OwnedReplace))
            publication = _OwnedStagedPublication._reopen(
                access._require_parent(),
                self._final_name,
                self.private_basename,
                self.ownership,
                self._expected,
            )
            try:
                yield publication
            finally:
                publication.abort()

    @serialized_owned_write
    def publish(self, *, final_authority_check=None) -> None:
        if self._closed:
            raise StorageResolutionError("Prepared owned file is closed")
        try:
            if self._sealed:
                with self._reacquire() as publication:
                    publication.publish(final_authority_check=final_authority_check)
            else:
                self.file.flush()
                self.file.close()
                self._publication.publish(final_authority_check=final_authority_check)
        except OSError as error:
            raise _open_error(error) from error
        finally:
            if not self._sealed:
                self._publication.abort()
                self._close_parent()
            self._closed = True

    @serialized_owned_write
    def abort(self) -> None:
        if self._closed:
            return
        try:
            if self._sealed:
                try:
                    with self._reacquire():
                        pass
                except (OSError, StorageResolutionError):
                    pass
            else:
                try:
                    self.file.close()
                finally:
                    self._publication.abort()
                    self._close_parent()
        finally:
            self._closed = True


class PreparedOwnedReplace(PreparedOwnedFile):
    """Prepare stable output outside SQL; never compensate a completed replacement."""

    def __init__(self, *args, **kwargs):
        from handler.filesystem.storage_policy import StorageOperation

        super().__init__(*args, **kwargs)
        self._operation = StorageOperation.OVERWRITE

    @serialized_owned_write
    def publish(self, *, final_authority_check=None):
        if self._closed or not self._sealed:
            raise StorageResolutionError("Stable output must be sealed")
        replaced = False
        try:
            with self._reacquire() as publication:
                _prove(
                    publication._parent_descriptor,
                    publication._staging_name,
                    self.ownership,
                    self._expected,
                )
                if final_authority_check is not None:
                    final_authority_check()
                os.replace(
                    publication._staging_name,
                    publication._final_name,
                    src_dir_fd=publication._parent_descriptor,
                    dst_dir_fd=publication._parent_descriptor,
                )
                replaced = True
                os.fsync(publication._parent_descriptor)
        except BaseException as error:
            if replaced:
                raise IndeterminateOwnedPublicationError() from error
            raise
        finally:
            self._closed = True


def open_replacement_temporary(parent, name, flags, *, unique=True):
    if not unique:
        temporary = f".{name}.{os.getpid()}.tmp"
        descriptor = os.open(
            temporary,
            flags | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o644,
            dir_fd=parent,
        )
        return descriptor, temporary
    for _ in range(8):
        temporary = f".{name}.{secrets.token_hex(16)}.tmp"
        try:
            descriptor = os.open(
                temporary,
                flags | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o644,
                dir_fd=parent,
            )
            return descriptor, temporary
        except FileExistsError:
            continue
    raise StorageResolutionError("Owned replacement staging is unavailable")
