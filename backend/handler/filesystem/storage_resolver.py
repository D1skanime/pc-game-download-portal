import base64
import binascii
import heapq
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

from exceptions.storage_exceptions import (
    InactiveStorageRootError,
    InvalidRelativePathError,
    InvalidStorageCursorError,
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    SafeStorageFilesystemError,
    StorageEscapeError,
    StorageResolutionError,
    StorageScanLimitError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
    UnsafeWritableRootError,
)
from models.storage import EXTERNAL_READ_ONLY_MODE, StorageRoot

_ROOT_MISSING_ERROR = "Storage root was not found"
_ROOT_UNREADABLE_ERROR = "Storage root is not readable"
_ROOT_SYMLINK_ERROR = "Storage root contains an unsafe symbolic link"
_ROOT_INVALID_ERROR = "Storage root is not an accessible directory"
MAX_DIRECTORY_PAGE_SIZE = 100
MAX_DIRECTORY_SCAN_ENTRIES = 10_000
MAX_STORAGE_CURSOR_LENGTH = 2_048
_STORAGE_CURSOR_VERSION = 1


@dataclass(frozen=True, slots=True)
class StorageRootHealthSnapshot:
    reachable: bool
    readable: bool
    non_writable: bool | None
    checked_at: datetime
    error: str | None


@dataclass(frozen=True)
class StorageDirectoryEntry:
    name: str
    relative_path: str
    navigable: bool


@dataclass(frozen=True, slots=True)
class StorageDirectoryPage:
    entries: tuple[StorageDirectoryEntry, ...]
    next_cursor: str | None


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


def get_storage_root_health_snapshot(
    storage_root: StorageRoot,
) -> StorageRootHealthSnapshot:
    """Observe current root health without changing the supplied ORM object."""
    path = Path(storage_root.container_path)
    checked_at = datetime.now(timezone.utc)

    try:
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            return StorageRootHealthSnapshot(
                False, False, None, checked_at, _ROOT_SYMLINK_ERROR
            )
        if not stat.S_ISDIR(metadata.st_mode):
            return StorageRootHealthSnapshot(
                True, False, None, checked_at, _ROOT_INVALID_ERROR
            )
    except (FileNotFoundError, NotADirectoryError):
        return StorageRootHealthSnapshot(
            False, False, None, checked_at, _ROOT_MISSING_ERROR
        )
    except OSError:
        return StorageRootHealthSnapshot(
            False, False, None, checked_at, _ROOT_INVALID_ERROR
        )

    readable = os.access(path, os.R_OK | os.X_OK)
    if not readable:
        return StorageRootHealthSnapshot(
            True, False, None, checked_at, _ROOT_UNREADABLE_ERROR
        )

    non_writable = not os.access(path, os.W_OK)
    error = None
    if not non_writable:
        error = str(UnsafeWritableRootError(storage_root.id))
    return StorageRootHealthSnapshot(True, True, non_writable, checked_at, error)


def check_storage_root_health(storage_root: StorageRoot) -> StorageRoot:
    """Record a pure health snapshot on a root for registration compatibility."""
    snapshot = get_storage_root_health_snapshot(storage_root)
    storage_root.last_checked_at = snapshot.checked_at
    storage_root.reachable = snapshot.reachable
    storage_root.readable = snapshot.readable
    storage_root.non_writable = snapshot.non_writable
    storage_root.safe_error = snapshot.error

    return storage_root


def _directory_sort_key(name: str, relative_path: str) -> tuple[bytes, bytes]:
    return name.encode("utf-8"), relative_path.encode("utf-8")


def _encode_storage_cursor(
    storage_root_id: int, parent: str, entry: StorageDirectoryEntry
) -> str:
    payload = json.dumps(
        {
            "v": _STORAGE_CURSOR_VERSION,
            "root": storage_root_id,
            "parent": parent,
            "name": entry.name,
            "path": entry.relative_path,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_storage_cursor(
    cursor: str, storage_root_id: int, parent: str
) -> tuple[bytes, bytes]:
    if (
        not isinstance(cursor, str)
        or not cursor
        or len(cursor) > MAX_STORAGE_CURSOR_LENGTH
    ):
        raise InvalidStorageCursorError
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(
            base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
        )
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise InvalidStorageCursorError from None
    if (
        not isinstance(payload, dict)
        or set(payload) != {"v", "root", "parent", "name", "path"}
        or payload["v"] != _STORAGE_CURSOR_VERSION
        or type(payload["root"]) is not int
        or payload["root"] != storage_root_id
        or payload["parent"] != parent
        or not isinstance(payload["name"], str)
        or not isinstance(payload["path"], str)
    ):
        raise InvalidStorageCursorError
    expected_path = f"{parent}/{payload['name']}" if parent else payload["name"]
    if payload["path"] != expected_path:
        raise InvalidStorageCursorError
    try:
        normalized_path = normalize_relative_path(payload["path"])
    except InvalidRelativePathError:
        raise InvalidStorageCursorError from None
    if normalized_path != payload["path"]:
        raise InvalidStorageCursorError
    return _directory_sort_key(payload["name"], payload["path"])


def browse_storage_directories(
    storage_root: StorageRoot,
    raw_parent: str,
    *,
    limit: int = 50,
    cursor: str | None = None,
) -> StorageDirectoryPage:
    """Return one bounded, deterministic page of immediate contained directories."""
    if type(limit) is not int or not 1 <= limit <= MAX_DIRECTORY_PAGE_SIZE:
        raise InvalidStorageCursorError
    parent = normalize_relative_path(raw_parent, allow_root=True)
    directory = (
        resolve_storage_root(storage_root)
        if parent == ""
        else resolve_directory(storage_root, parent)
    )
    after = (
        _decode_storage_cursor(cursor, storage_root.id, parent)
        if cursor is not None
        else None
    )
    scanned = 0

    def entries():
        nonlocal scanned
        try:
            with os.scandir(directory) as iterator:
                for item in iterator:
                    scanned += 1
                    if scanned > MAX_DIRECTORY_SCAN_ENTRIES:
                        raise StorageScanLimitError(storage_root.id)
                    try:
                        if item.is_symlink():
                            raise UnsafeSymlinkError
                        if not item.is_dir(follow_symlinks=False):
                            continue
                    except OSError:
                        raise SafeStorageFilesystemError(storage_root.id) from None
                    relative_path = f"{parent}/{item.name}" if parent else item.name
                    try:
                        normalized_path = normalize_relative_path(relative_path)
                    except InvalidRelativePathError:
                        raise SafeStorageFilesystemError(storage_root.id) from None
                    entry = StorageDirectoryEntry(item.name, normalized_path, True)
                    if (
                        after is None
                        or _directory_sort_key(entry.name, entry.relative_path) > after
                    ):
                        yield entry
        except (StorageScanLimitError, UnsafeSymlinkError, SafeStorageFilesystemError):
            raise
        except OSError:
            raise SafeStorageFilesystemError(storage_root.id) from None

    selected = heapq.nsmallest(
        limit + 1,
        entries(),
        key=lambda entry: _directory_sort_key(entry.name, entry.relative_path),
    )
    visible = selected[:limit]
    next_cursor = (
        _encode_storage_cursor(storage_root.id, parent, visible[-1])
        if len(selected) > limit
        else None
    )
    return StorageDirectoryPage(tuple(visible), next_cursor)


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
