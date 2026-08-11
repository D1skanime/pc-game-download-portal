from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import Protocol

from exceptions.storage_exceptions import (
    MissingPlatformStorageMappingError,
    MissingStorageRootError,
    MissingStorageTargetError,
    StoragePolicyDenied,
    UnreadableStorageTargetError,
)
from exceptions.storage_read import (
    MappedReadDeniedError,
    MissingMappedContentError,
    StaleMappedReadError,
    UnreachableMappedStorageError,
)
from handler.filesystem.storage_access import open_storage_access
from handler.filesystem.storage_policy import (
    StorageOperation,
    _create_external_descriptor,
)
from handler.filesystem.storage_resolver import (
    get_storage_root_health_snapshot,
    normalize_relative_path,
    resolve_directory,
)


class MappingRepository(Protocol):
    def get_mapping(self, mapping_id: int): ...


@dataclass(frozen=True, slots=True)
class MappingReadContext:
    mapping_id: int
    expected_revision: int
    repository: MappingRepository | None = None

    def __post_init__(self) -> None:
        if type(self.mapping_id) is not int or self.mapping_id <= 0:
            raise ValueError("mapping_id must be a positive integer")
        if type(self.expected_revision) is not int or self.expected_revision <= 0:
            raise ValueError("expected_revision must be a positive integer")

    def _repository(self) -> MappingRepository:
        if self.repository is not None:
            return self.repository
        from handler.database import db_storage_handler

        return db_storage_handler

    def validate(self):
        try:
            mapping = self._repository().get_mapping(self.mapping_id)
        except MissingPlatformStorageMappingError:
            raise StaleMappedReadError(
                self.mapping_id, self.expected_revision
            ) from None
        if (
            mapping.id != self.mapping_id
            or mapping.version != self.expected_revision
            or not mapping.active
        ):
            raise StaleMappedReadError(self.mapping_id, self.expected_revision)

        health = get_storage_root_health_snapshot(mapping.storage_root)
        if (
            not mapping.storage_root.active
            or not health.reachable
            or not health.readable
            or health.non_writable is not True
        ):
            raise UnreachableMappedStorageError(self.mapping_id, self.expected_revision)
        return mapping

    def boundary(self) -> None:
        self.validate()

    def open(self, operation: StorageOperation, relative_path: str = ""):
        mapping = self.validate()
        try:
            mapped_root = resolve_directory(mapping.storage_root, mapping.relative_path)
            logical_path = normalize_relative_path(
                relative_path,
                allow_root=operation
                in {
                    StorageOperation.LIST,
                    StorageOperation.SCAN,
                    StorageOperation.RESOLVE,
                },
            )
            descriptor = _create_external_descriptor(
                mapping.storage_root_id,
                PurePath(mapped_root),
                mapping_id=mapping.id,
            )
            self.boundary()
            return open_storage_access(descriptor, operation, logical_path)
        except (MissingStorageRootError, UnreadableStorageTargetError):
            raise UnreachableMappedStorageError(
                self.mapping_id, self.expected_revision
            ) from None
        except MissingStorageTargetError:
            raise MissingMappedContentError(
                self.mapping_id, self.expected_revision
            ) from None
        except StoragePolicyDenied:
            raise MappedReadDeniedError(
                self.mapping_id, self.expected_revision
            ) from None
