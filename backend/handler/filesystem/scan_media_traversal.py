"""Private Linux directory-cookie traversal for reserved recovery receipts."""

import ctypes
import errno
import fcntl
import json
import os
import re
import stat
import sys

from exceptions.storage_exceptions import (
    MissingStorageTargetError,
    StorageResolutionError,
)
from handler.filesystem.scan_media_publication import RESERVED, ensure_directory
from handler.filesystem.storage_access import (
    OwnedCreate,
    OwnedRead,
    OwnedReplace,
    _open_target,
    open_owned_access,
)
from handler.filesystem.storage_policy import (
    OwnedStorageDescriptor,
    OwnedStorageKind,
    StorageOperation,
    StoragePolicy,
)
from logger.logger import log

_UUID = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
_LOCK = RESERVED + "/.recovery.lock"
_CURSOR = RESERVED + "/.recovery-cursor.json"


def _scope(path):
    parts = path.split("/")
    return (
        parts[0] == RESERVED
        and len(parts) <= 4
        and all(
            re.fullmatch(_UUID if index < 3 else r"[a-f0-9]{32}", part)
            for index, part in enumerate(parts[1:], 1)
        )
    )


def open_directory(storage, path):
    if (
        not isinstance(storage, OwnedStorageDescriptor)
        or storage.kind != OwnedStorageKind.RESOURCES
        or not _scope(path)
    ):
        raise ValueError("scan_media_recovery_scope")
    StoragePolicy.authorize(StorageOperation.LIST, storage)
    return _open_target(storage, path, directory=True)


class _Dirent(ctypes.Structure):
    _fields_ = [
        ("inode", ctypes.c_uint64),
        ("offset", ctypes.c_int64),
        ("length", ctypes.c_ushort),
        ("kind", ctypes.c_ubyte),
        ("name", ctypes.c_char * 256),
    ]


def _entry(descriptor, cookie):
    # fdopendir/readdir/seekdir are provided by both supported Linux C libraries.
    if sys.platform != "linux" or ctypes.sizeof(ctypes.c_long) != 8:
        raise OSError("scan_media_recovery_platform")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.fdopendir.argtypes = (ctypes.c_int,)
    libc.fdopendir.restype = ctypes.c_void_p
    libc.seekdir.argtypes = (ctypes.c_void_p, ctypes.c_long)
    libc.readdir.argtypes = (ctypes.c_void_p,)
    libc.readdir.restype = ctypes.POINTER(_Dirent)
    libc.telldir.argtypes = (ctypes.c_void_p,)
    libc.telldir.restype = ctypes.c_long
    libc.closedir.argtypes = (ctypes.c_void_p,)
    duplicate = os.dup(descriptor)
    stream = libc.fdopendir(duplicate)
    if not stream:
        os.close(duplicate)
        raise OSError(ctypes.get_errno(), "scan_media_recovery_listing")
    try:
        libc.seekdir(stream, cookie)
        ctypes.set_errno(0)
        entry = libc.readdir(stream)
        if not entry:
            code = ctypes.get_errno()
            if code:
                raise OSError(code, "scan_media_recovery_listing")
            return None
        following = libc.telldir(stream)
        if following < 0 or following == cookie:
            raise OSError("scan_media_recovery_cookie")
        return following, os.fsdecode(bytes(entry.contents.name))
    finally:
        libc.closedir(stream)


class RecoveryWalk:
    """One bounded advisory cursor, serialized without adding attempt authority."""

    def __init__(self, storage):
        self.storage = storage
        self.lock = None
        self.stack = []
        self.busy = False

    def __enter__(self):
        try:
            return self._start()
        except BaseException:
            if self.lock:
                self.lock.close()
            raise

    def _start(self):
        if (
            not isinstance(self.storage, OwnedStorageDescriptor)
            or self.storage.kind != OwnedStorageKind.RESOURCES
        ):
            raise ValueError("scan_media_recovery_scope")
        ensure_directory(self.storage, RESERVED)
        try:
            with open_owned_access(
                self.storage, StorageOperation.CREATE, _LOCK
            ) as access:
                assert isinstance(access, OwnedCreate)
                access.create(b"")
        except StorageResolutionError as error:
            if (
                not isinstance(error.__cause__, OSError)
                or error.__cause__.errno != errno.EEXIST
            ):
                raise
        self.lock = open_owned_access(self.storage, StorageOperation.READ, _LOCK)
        assert isinstance(self.lock, OwnedRead)
        try:
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.busy = True
            return self
        try:
            with open_owned_access(
                self.storage, StorageOperation.READ, _CURSOR
            ) as access:
                assert isinstance(access, OwnedRead)
                with access.binary_file() as stream:
                    content = stream.read(4097)
                if len(content) > 4096:
                    raise ValueError("scan_media_recovery_cursor")
                stack = json.loads(content)
                if type(stack) is not list or len(stack) > 3:
                    raise ValueError("scan_media_recovery_cursor")
                for index, frame in enumerate(stack):
                    if (
                        type(frame) is not dict
                        or set(frame) != {"path", "device", "inode", "cookie"}
                        or type(frame["path"]) is not str
                        or not _scope(frame["path"])
                        or len(frame["path"].split("/")) != index + 1
                        or (
                            index
                            and frame["path"].rsplit("/", 1)[0]
                            != stack[index - 1]["path"]
                        )
                        or any(
                            type(frame[key]) is not int
                            or not 0
                            <= frame[key]
                            < 2 ** (63 if key == "cookie" else 64)
                            for key in ("device", "inode", "cookie")
                        )
                    ):
                        raise ValueError("scan_media_recovery_cursor")
                self.stack = stack
        except MissingStorageTargetError:
            pass
        except (ValueError, TypeError, RecursionError):
            log.warning("Scan media recovery reset invalid advisory cursor")
        if not self.stack:
            self.stack = [self._frame(RESERVED)]
        return self

    @staticmethod
    def _frame(path):
        return dict(path=path, device=0, inode=0, cookie=0)

    def __exit__(self, error_type, error, traceback):
        try:
            if not self.busy:
                with open_owned_access(
                    self.storage, StorageOperation.OVERWRITE, _CURSOR
                ) as access:
                    assert isinstance(access, OwnedReplace)
                    with access.binary_file(unique=True) as stream:
                        stream.write(
                            json.dumps(self.stack, separators=(",", ":")).encode()
                        )
                descriptor = open_directory(self.storage, RESERVED)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        except BaseException as cursor_error:
            if error is None:
                raise
            error.add_note(
                "scan_media_cursor_save_failed: " + type(cursor_error).__name__
            )
        finally:
            if self.lock:
                self.lock.close()

    def step(self):
        if self.busy or not self.stack:
            return "done", RESERVED
        frame = self.stack[-1]
        path = frame["path"]
        try:
            descriptor = open_directory(self.storage, path)
            try:
                info = os.fstat(descriptor)
                if (frame["device"], frame["inode"]) != (info.st_dev, info.st_ino):
                    frame.update(device=info.st_dev, inode=info.st_ino, cookie=0)
                entry = _entry(descriptor, frame["cookie"])
                if entry is None:
                    self.stack.pop()
                    return "exit", path
                cookie, name = entry
                frame["cookie"] = cookie
                grammar = _UUID if len(self.stack) < 3 else r"[a-f0-9]{32}"
                if not re.fullmatch(grammar, name):
                    return "skip", path
                try:
                    info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                except OSError as error:
                    log.warning(
                        "Scan media recovery retained inaccessible entry (%s)",
                        type(error).__name__,
                    )
                    return "skip", path
                if not stat.S_ISDIR(info.st_mode):
                    return "skip", path
            finally:
                os.close(descriptor)
        except (OSError, StorageResolutionError) as error:
            self.stack.pop()
            log.warning(
                "Scan media recovery retained inaccessible directory (%s)",
                type(error).__name__,
            )
            return "skip", path
        child = path + "/" + name
        if len(self.stack) == 3:
            return "batch", child
        self.stack.append(self._frame(child))
        return "skip", child
