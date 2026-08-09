from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import PurePath
from typing import Iterable

from exceptions.storage_exceptions import StoragePolicyDenied
from models.storage import EXTERNAL_READ_ONLY_MODE, StorageRoot


class StorageOperation(StrEnum):
    RESOLVE = "resolve"
    LIST = "list"
    STAT = "stat"
    READ = "read"
    SCAN = "scan"
    HASH = "hash"
    STREAM = "stream"
    DOWNLOAD = "download"
    CREATE = "create"
    UPLOAD = "upload"
    WRITE = "write"
    OVERWRITE = "overwrite"
    RENAME = "rename"
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    EXTRACT = "extract"
    PATCH = "patch"
    MKDIR = "mkdir"
    SIDECAR_WRITE = "sidecar_write"
    COVER_WRITE = "cover_write"


class OwnedStorageKind(StrEnum):
    DATABASE = "database"
    RESOURCES = "resources"
    ASSETS = "assets"
    CONFIG = "config"
    CACHE = "cache"
    HASHES = "hashes"
    SCAN_STATE = "scan_state"
    TEMP = "temp"
    SYNC = "sync"
    AUDIT = "audit"


EXTERNAL_READ_OPERATIONS = frozenset(
    {
        StorageOperation.RESOLVE,
        StorageOperation.LIST,
        StorageOperation.STAT,
        StorageOperation.READ,
        StorageOperation.SCAN,
        StorageOperation.HASH,
        StorageOperation.STREAM,
        StorageOperation.DOWNLOAD,
    }
)

_DESCRIPTOR_TOKEN = object()


@dataclass(frozen=True, slots=True, init=False)
class ExternalStorageDescriptor:
    root_id: int
    mapping_id: int | None
    storage_class: str
    _root_path: PurePath = field(repr=False)

    def __init__(
        self,
        token: object,
        root_id: int,
        mapping_id: int | None,
        root_path: PurePath,
    ) -> None:
        if token is not _DESCRIPTOR_TOKEN:
            raise TypeError("storage descriptors are created by composition")
        object.__setattr__(self, "root_id", root_id)
        object.__setattr__(self, "mapping_id", mapping_id)
        object.__setattr__(self, "storage_class", EXTERNAL_READ_ONLY_MODE)
        object.__setattr__(self, "_root_path", root_path)

    @property
    def storage_id(self) -> str:
        if self.mapping_id is not None:
            return f"mapping:{self.mapping_id}"
        return f"root:{self.root_id}"


@dataclass(frozen=True, slots=True, init=False)
class OwnedStorageDescriptor:
    kind: OwnedStorageKind
    logical_root: str
    storage_class: str
    _root_path: PurePath | None = field(repr=False)

    def __init__(
        self,
        token: object,
        kind: OwnedStorageKind,
        logical_root: str,
        root_path: PurePath | None = None,
    ) -> None:
        if token is not _DESCRIPTOR_TOKEN:
            raise TypeError("storage descriptors are created by composition")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "logical_root", logical_root)
        object.__setattr__(self, "storage_class", "romm_owned")
        object.__setattr__(self, "_root_path", root_path)

    @property
    def storage_id(self) -> str:
        return f"{self.kind.value}:{self.logical_root}"


StorageDescriptor = ExternalStorageDescriptor | OwnedStorageDescriptor


@dataclass(frozen=True, slots=True)
class StorageGrant:
    operation: StorageOperation
    storage: StorageDescriptor


def create_external_descriptor(
    storage_root: StorageRoot, *, mapping_id: int | None = None
) -> ExternalStorageDescriptor:
    """Create an immutable descriptor from composition-owned model identity."""
    if not isinstance(storage_root, StorageRoot):
        raise TypeError("a trusted StorageRoot is required")
    if storage_root.id is None or storage_root.mode != EXTERNAL_READ_ONLY_MODE:
        raise ValueError("storage root has no trusted external classification")
    return _create_external_descriptor(
        storage_root.id, PurePath(storage_root.container_path), mapping_id=mapping_id
    )


def _create_external_descriptor(
    root_id: int,
    root_path: PurePath,
    *,
    mapping_id: int | None = None,
) -> ExternalStorageDescriptor:
    return ExternalStorageDescriptor(_DESCRIPTOR_TOKEN, root_id, mapping_id, root_path)


def create_owned_descriptor(
    kind: OwnedStorageKind, logical_root: str
) -> OwnedStorageDescriptor:
    """Create an immutable descriptor from an explicit owned classification."""
    if not isinstance(kind, OwnedStorageKind):
        raise TypeError("an explicit owned storage kind is required")
    if not logical_root or "/" in logical_root or "\\" in logical_root:
        raise ValueError("logical root must be a bounded identifier")
    return OwnedStorageDescriptor(_DESCRIPTOR_TOKEN, kind, logical_root)


def _create_bound_owned_descriptor(
    kind: OwnedStorageKind,
    logical_root: str,
    root_path: PurePath,
) -> OwnedStorageDescriptor:
    if not isinstance(kind, OwnedStorageKind):
        raise TypeError("an explicit owned storage kind is required")
    if not logical_root or "/" in logical_root or "\\" in logical_root:
        raise ValueError("logical root must be a bounded identifier")
    return OwnedStorageDescriptor(_DESCRIPTOR_TOKEN, kind, logical_root, root_path)


def validate_disjoint_storage_roots(
    external_roots: Iterable[str], owned_roots: Iterable[str]
) -> None:
    """Reject equality and ancestry overlap without observing the filesystem."""
    external = tuple(PurePath(path) for path in external_roots)
    owned = tuple(PurePath(path) for path in owned_roots)
    for external_root in external:
        for owned_root in owned:
            if (
                external_root == owned_root
                or external_root in owned_root.parents
                or owned_root in external_root.parents
            ):
                raise ValueError("external and owned storage roots must be disjoint")


class StoragePolicy:
    @staticmethod
    def authorize(operation: object, storage: StorageDescriptor) -> StorageGrant:
        """Authorize one closed operation using trusted classification only."""
        valid_operation = operation if isinstance(operation, StorageOperation) else None
        allowed = isinstance(storage, OwnedStorageDescriptor) or (
            isinstance(storage, ExternalStorageDescriptor)
            and valid_operation in EXTERNAL_READ_OPERATIONS
        )
        if valid_operation is not None and allowed:
            return StorageGrant(valid_operation, storage)

        operation_name = (
            valid_operation.value if valid_operation is not None else "unknown"
        )
        if isinstance(storage, (ExternalStorageDescriptor, OwnedStorageDescriptor)):
            storage_class = storage.storage_class
            storage_id = storage.storage_id
        else:
            storage_class = "unknown"
            storage_id = "unknown"
        raise StoragePolicyDenied(operation_name, storage_class, storage_id)
