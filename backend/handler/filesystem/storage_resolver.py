import os
import stat
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

from exceptions.storage_exceptions import (
    InactiveStorageRootError,
    InvalidRelativePathError,
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    StorageEscapeError,
    StorageResolutionError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
    UnsafeWritableRootError,
)
from models.storage import EXTERNAL_READ_ONLY_MODE, StorageRoot


_ROOT_MISSING_ERROR = "Storage root was not found"
_ROOT_UNREADABLE_ERROR = "Storage root is not readable"
_ROOT_SYMLINK_ERROR = "Storage root contains an unsafe symbolic link"
_ROOT_INVALID_ERROR = "Storage root is not an accessible directory"


def normalize_relative_path(raw: str, *, allow_root: bool = False) -> str:
    """Validate and preserve a logical POSIX-style relative storage path."""
    if not isinstance(raw, str):
        raise InvalidRelativePathError

    if raw == "":
        if allow_root:
            return ""
        raise InvalidRelativePathError

    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        raise InvalidRelativePathError

    if "\\" in raw or raw.startswith("/"):
        raise InvalidRelativePathError

    if PureWindowsPath(raw).drive:
        raise InvalidRelativePathError

    segments = raw.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise InvalidRelativePathError

    return raw


def check_storage_root_health(storage_root: StorageRoot) -> StorageRoot:
    """Record bounded root health using metadata and permission observation only."""
    path = Path(storage_root.container_path)
    storage_root.last_checked_at = datetime.now(timezone.utc)
    storage_root.reachable = False
    storage_root.readable = False
    storage_root.non_writable = None
    storage_root.safe_error = None

    try:
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            storage_root.safe_error = _ROOT_SYMLINK_ERROR
            return storage_root
        if not stat.S_ISDIR(metadata.st_mode):
            storage_root.reachable = True
            storage_root.safe_error = _ROOT_INVALID_ERROR
            return storage_root
    except (FileNotFoundError, NotADirectoryError):
        storage_root.safe_error = _ROOT_MISSING_ERROR
        return storage_root
    except OSError:
        storage_root.safe_error = _ROOT_INVALID_ERROR
        return storage_root

    storage_root.reachable = True
    storage_root.readable = os.access(path, os.R_OK | os.X_OK)
    if not storage_root.readable:
        storage_root.safe_error = _ROOT_UNREADABLE_ERROR
        return storage_root

    storage_root.non_writable = not os.access(path, os.W_OK)
    if not storage_root.non_writable:
        storage_root.safe_error = str(UnsafeWritableRootError(storage_root.id))

    return storage_root


def resolve_storage_root(storage_root: StorageRoot) -> Path:
    """Resolve an approved root for internal health-aware operations."""
    if not storage_root.active:
        raise InactiveStorageRootError(storage_root.id)
    if storage_root.mode != EXTERNAL_READ_ONLY_MODE:
        raise UnsafeWritableRootError(storage_root.id)

    path = Path(storage_root.container_path)
    try:
        metadata = path.lstat()
    except (FileNotFoundError, NotADirectoryError) as error:
        raise MissingStorageRootError(storage_root.id) from error
    except OSError as error:
        raise StorageResolutionError("Storage root is not accessible") from error

    if stat.S_ISLNK(metadata.st_mode):
        raise UnsafeSymlinkError
    if not stat.S_ISDIR(metadata.st_mode):
        raise MissingStorageRootError(storage_root.id)
    if not os.access(path, os.R_OK | os.X_OK):
        raise UnreadableStorageTargetError
    if os.access(path, os.W_OK):
        raise UnsafeWritableRootError(storage_root.id)

    try:
        return path.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError) as error:
        raise MissingStorageRootError(storage_root.id) from error
    except OSError as error:
        raise StorageResolutionError("Storage root is not accessible") from error


def _reject_component_symlinks(root: Path, relative_path: str) -> Path:
    candidate = root
    for segment in relative_path.split("/"):
        candidate = candidate / segment
        try:
            metadata = candidate.lstat()
        except (FileNotFoundError, NotADirectoryError) as error:
            raise MissingStorageTargetError from error
        except OSError as error:
            raise StorageResolutionError("Storage target is not accessible") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise UnsafeSymlinkError
    return candidate


def _strict_resolve_target(target: Path) -> Path:
    try:
        return target.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError) as error:
        raise MissingStorageTargetError from error
    except OSError as error:
        raise StorageResolutionError("Storage target is not accessible") from error


def resolve_directory(storage_root: StorageRoot, raw_relative_path: str) -> Path:
    """Resolve a non-empty logical mapping directory inside an approved root."""
    relative_path = normalize_relative_path(raw_relative_path)
    root = resolve_storage_root(storage_root)
    target = _reject_component_symlinks(root, relative_path)
    resolved_target = _strict_resolve_target(target)

    try:
        resolved_target.relative_to(root)
    except ValueError as error:
        raise StorageEscapeError from error

    try:
        metadata = resolved_target.stat()
    except (FileNotFoundError, NotADirectoryError) as error:
        raise MissingStorageTargetError from error
    except OSError as error:
        raise StorageResolutionError("Storage target is not accessible") from error

    if not stat.S_ISDIR(metadata.st_mode):
        raise NonDirectoryStorageTargetError
    if not os.access(resolved_target, os.R_OK | os.X_OK):
        raise UnreadableStorageTargetError

    return resolved_target
