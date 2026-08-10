import enum
from typing import Literal

from pydantic import Field

from endpoints.responses.base import BaseModel, UTCDatetime
from handler.filesystem.storage_resolver import (
    MAX_DIRECTORY_PAGE_SIZE,
    MAX_STORAGE_CURSOR_LENGTH,
)
from models.storage import (
    STORAGE_ROOT_MODE_MAX_LENGTH,
    STORAGE_ROOT_NAME_MAX_LENGTH,
    STORAGE_ROOT_PATH_MAX_LENGTH,
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
