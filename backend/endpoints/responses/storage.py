import enum
from typing import Literal

from pydantic import Field

from endpoints.responses.base import BaseModel, UTCDatetime
from handler.filesystem.storage_resolver import (
    MAX_DIRECTORY_PAGE_SIZE,
    MAX_STORAGE_CURSOR_LENGTH,
)
from models.storage import (
    STORAGE_AUDIT_ACTOR_MAX_LENGTH,
    STORAGE_MAPPING_PATH_MAX_LENGTH,
    STORAGE_ROOT_MODE_MAX_LENGTH,
    STORAGE_ROOT_NAME_MAX_LENGTH,
    STORAGE_ROOT_PATH_MAX_LENGTH,
    StorageMappingAuditAction,
)


class StorageReadErrorCode(enum.StrEnum):
    INVALID_RELATIVE_PATH = "invalid_relative_path"
    INVALID_STORAGE_CURSOR = "invalid_storage_cursor"
    MISSING_STORAGE_ROOT = "missing_storage_root"
    MISSING_STORAGE_TARGET = "missing_storage_target"
    INACTIVE_STORAGE_ROOT = "inactive_storage_root"
    NON_DIRECTORY_STORAGE_TARGET = "non_directory_storage_target"
    UNREADABLE_STORAGE_TARGET = "unreadable_storage_target"
    UNSAFE_STORAGE_SYMLINK = "unsafe_storage_symlink"
    STORAGE_ESCAPE = "storage_escape"
    UNSAFE_WRITABLE_ROOT = "unsafe_writable_root"
    STORAGE_SCAN_LIMIT_EXCEEDED = "storage_scan_limit_exceeded"
    STORAGE_FILESYSTEM_ERROR = "storage_filesystem_error"
    STORAGE_RESOLUTION_ERROR = "storage_resolution_error"


class StorageErrorDetail(BaseModel):
    code: StorageReadErrorCode
    message: str = Field(min_length=1, max_length=160)


class StorageErrorResponse(BaseModel):
    detail: StorageErrorDetail


class StorageRootHealthSchema(BaseModel):
    reachable: bool
    readable: bool
    non_writable: bool | None
    checked_at: UTCDatetime
    error: str | None = Field(default=None, max_length=160)


class StorageRootSchema(BaseModel):
    id: int
    name: str = Field(max_length=STORAGE_ROOT_NAME_MAX_LENGTH)
    mode: Literal["external_read_only"]
    active: bool
    created_at: UTCDatetime
    updated_at: UTCDatetime
    health: StorageRootHealthSchema


class StorageDirectoryEntrySchema(BaseModel):
    name: str = Field(min_length=1, max_length=STORAGE_ROOT_PATH_MAX_LENGTH)
    relative_path: str = Field(min_length=1, max_length=STORAGE_ROOT_PATH_MAX_LENGTH)
    navigable: bool


class StorageDirectoryPageSchema(BaseModel):
    entries: list[StorageDirectoryEntrySchema] = Field(
        max_length=MAX_DIRECTORY_PAGE_SIZE
    )
    next_cursor: str | None = Field(default=None, max_length=MAX_STORAGE_CURSOR_LENGTH)


class StorageMappingCreateSchema(BaseModel):
    platform_id: int = Field(gt=0)
    storage_root_id: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)


class StorageMappingUpdateSchema(BaseModel):
    storage_root_id: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    expected_version: int = Field(gt=0)


class StorageMappingVersionSchema(BaseModel):
    expected_version: int = Field(gt=0)


class StorageMappingSchema(BaseModel):
    id: int
    platform_id: int
    storage_root_id: int
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    active: bool
    version: int = Field(gt=0)


class StorageMappingTestSchema(BaseModel):
    platform_id: int
    storage_root_id: int
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    valid: Literal[True] = True


class StorageMappingPreviewSchema(BaseModel):
    mapping_id: int
    platform_id: int
    storage_root_id: int
    mapping_version: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    examined_entry_count: int = Field(ge=0)
    candidate_file_count: int = Field(ge=0)
    candidate_directory_count: int = Field(ge=0)
    truncated: bool
    next_cursor: str | None = Field(default=None, max_length=MAX_STORAGE_CURSOR_LENGTH)


class StorageMappingPreviewStateSchema(BaseModel):
    mapping_id: int
    mapping_version: int = Field(gt=0)
    health: StorageRootHealthSchema
    state: Literal["pending", "partial", "complete"]
    observed_files: int = Field(ge=0)
    observed_directories: int = Field(ge=0)
    observed_bytes: int = Field(ge=0)
    lower_bound: bool
    budget_reason: Literal["time_budget", "entry_budget"] | None = None
    timestamp: UTCDatetime | None = None
    problems: dict[str, int] = Field(default_factory=dict)
    stale: bool
    error_code: str | None = Field(default=None, max_length=64)


class StorageConflictErrorCode(enum.StrEnum):
    PLATFORM_MAPPING_MISSING = "platform_mapping_missing"
    DUPLICATE_STORAGE_MAPPING = "duplicate_storage_mapping"
    STORAGE_MAPPING_OVERLAP = "storage_mapping_overlap"
    STORAGE_MAPPING_STALE_VERSION = "storage_mapping_stale_version"


class StorageConflictDetail(BaseModel):
    code: StorageConflictErrorCode
    message: str = Field(min_length=1, max_length=160)
    platform_id: int | None = None
    mapping_id: int | None = None
    current_version: int | None = Field(default=None, gt=0)


class StorageConflictResponse(BaseModel):
    detail: StorageConflictDetail


class StorageMappingSnapshotSchema(BaseModel):
    storage_root_id: int
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    version: int = Field(gt=0)
    active: bool


class StorageMappingAuditSchema(BaseModel):
    id: int
    actor_user_id: int
    actor_display_name: str = Field(
        min_length=1, max_length=STORAGE_AUDIT_ACTOR_MAX_LENGTH
    )
    platform_id: int
    mapping_id: int
    action: StorageMappingAuditAction
    old: StorageMappingSnapshotSchema | None
    new: StorageMappingSnapshotSchema | None
    created_at: UTCDatetime


class StorageMappingAuditPageSchema(BaseModel):
    entries: list[StorageMappingAuditSchema] = Field(max_length=100)
    next_cursor: str | None = Field(default=None, max_length=2048)
