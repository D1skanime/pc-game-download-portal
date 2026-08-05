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

    def __init__(self, storage_root_id: int, relative_path: str):
        super().__init__(
            f"Storage mapping {storage_root_id}:{relative_path} overlaps an active mapping"
        )


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
