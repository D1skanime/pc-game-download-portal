class StorageResolutionError(Exception):
    """Base error for bounded storage resolution failures."""

    code = "storage_resolution_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def __repr__(self) -> str:
        return self.message


class InvalidRelativePathError(StorageResolutionError):
    code = "invalid_relative_path"

    def __init__(self):
        super().__init__("Storage path must be a safe relative path")


class MissingStorageRootError(StorageResolutionError):
    code = "missing_storage_root"

    def __init__(self, storage_root_id: int):
        super().__init__(f"Storage root {storage_root_id} was not found")


class MissingStoragePlatformError(StorageResolutionError):
    code = "missing_storage_platform"

    def __init__(self, platform_id: int):
        super().__init__(f"Storage platform {platform_id} was not found")


class InactiveStorageRootError(StorageResolutionError):
    code = "inactive_storage_root"

    def __init__(self, storage_root_id: int):
        super().__init__(f"Storage root {storage_root_id} is inactive")


class MissingStorageTargetError(StorageResolutionError):
    code = "missing_storage_target"

    def __init__(self):
        super().__init__("Storage target was not found")


class NonDirectoryStorageTargetError(StorageResolutionError):
    code = "non_directory_storage_target"

    def __init__(self):
        super().__init__("Storage target is not a directory")


class UnreadableStorageTargetError(StorageResolutionError):
    code = "unreadable_storage_target"

    def __init__(self):
        super().__init__("Storage target is not readable")


class UnsafeSymlinkError(StorageResolutionError):
    code = "unsafe_storage_symlink"

    def __init__(self):
        super().__init__("Storage path contains an unsafe symbolic link")


class StorageEscapeError(StorageResolutionError):
    code = "storage_escape"

    def __init__(self):
        super().__init__("Storage path escapes its approved root")


class UnsafeWritableRootError(StorageResolutionError):
    code = "unsafe_writable_root"

    def __init__(self, storage_root_id: int):
        super().__init__(f"Storage root {storage_root_id} is writable")


class StorageMappingOverlapError(StorageResolutionError):
    code = "storage_mapping_overlap"

    def __init__(
        self,
        storage_root_id: int,
        relative_path: str | None = None,
        *,
        platform_id: int | None = None,
        mapping_id: int | None = None,
    ):
        self.storage_root_id = storage_root_id
        self.platform_id = platform_id
        self.mapping_id = mapping_id
        super().__init__("Storage mapping overlaps an active mapping")


class DuplicateStorageMappingError(StorageResolutionError):
    code = "duplicate_storage_mapping"

    def __init__(self, platform_id: int, storage_root_id: int):
        super().__init__(
            f"Storage mapping for platform {platform_id} conflicts in root {storage_root_id}"
        )


class StoragePersistenceError(StorageResolutionError):
    code = "storage_persistence_error"

    def __init__(self):
        super().__init__("Storage mapping could not be persisted")


class StoragePolicyDenied(StorageResolutionError):
    """Bounded denial for a storage operation and trusted classification."""

    code = "external_storage_operation_denied"

    def __init__(self, operation: str, storage_class: str, storage_id: str) -> None:
        self.operation = operation
        self.storage_class = storage_class
        self.storage_id = storage_id
        super().__init__(f"{operation} denied for {storage_class} storage {storage_id}")


class MissingPlatformStorageMappingError(StorageResolutionError):
    code = "platform_mapping_missing"

    def __init__(self, platform_id: int):
        self.platform_id = platform_id
        super().__init__(f"Storage mapping for platform {platform_id} was not found")


class StaleStorageMappingVersionError(StorageResolutionError):
    code = "storage_mapping_stale_version"

    def __init__(self, mapping_id: int, current_version: int):
        self.mapping_id = mapping_id
        self.current_version = current_version
        super().__init__(f"Storage mapping {mapping_id} has version {current_version}")


class InvalidStorageCursorError(StorageResolutionError):
    code = "invalid_storage_cursor"

    def __init__(self):
        super().__init__("Storage cursor is invalid")


class StorageScanLimitError(StorageResolutionError):
    code = "storage_scan_limit_exceeded"

    def __init__(self, storage_root_id: int):
        self.storage_root_id = storage_root_id
        super().__init__(f"Storage scan limit exceeded for root {storage_root_id}")


class SafeStorageFilesystemError(StorageResolutionError):
    code = "storage_filesystem_error"

    def __init__(self, storage_root_id: int):
        self.storage_root_id = storage_root_id
        super().__init__(f"Storage operation failed for root {storage_root_id}")
