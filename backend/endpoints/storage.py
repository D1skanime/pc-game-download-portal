from typing import Annotated

from fastapi import HTTPException, Query, Request, status

from decorators.auth import protected_route
from endpoints.responses.storage import (
    StorageDirectoryEntrySchema,
    StorageDirectoryPageSchema,
    StorageErrorDetail,
    StorageErrorResponse,
    StorageReadErrorCode,
    StorageRootHealthSchema,
    StorageRootSchema,
)
from exceptions.storage_exceptions import (
    InvalidRelativePathError,
    InvalidStorageCursorError,
    MissingStorageRootError,
    MissingStorageTargetError,
    StorageResolutionError,
)
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_admin
from handler.database import db_storage_handler
from handler.filesystem.storage_resolver import (
    MAX_DIRECTORY_PAGE_SIZE,
    MAX_STORAGE_CURSOR_LENGTH,
    browse_storage_directories,
    get_storage_root_health_snapshot,
)
from models.storage import STORAGE_MAPPING_PATH_MAX_LENGTH, StorageRoot
from utils.router import APIRouter

router = APIRouter(prefix="/storage", tags=["storage"])

_ERROR_STATUS = {
    InvalidRelativePathError: status.HTTP_400_BAD_REQUEST,
    InvalidStorageCursorError: status.HTTP_400_BAD_REQUEST,
    MissingStorageRootError: status.HTTP_404_NOT_FOUND,
    MissingStorageTargetError: status.HTTP_404_NOT_FOUND,
}
_ERROR_MESSAGES = {
    "invalid_relative_path": "Storage path must be a safe relative path",
    "invalid_storage_cursor": "Storage cursor is invalid",
    "missing_storage_root": "Storage root was not found",
    "missing_storage_target": "Storage target was not found",
    "inactive_storage_root": "Storage root is inactive",
    "non_directory_storage_target": "Storage target is not a directory",
    "unreadable_storage_target": "Storage target is not readable",
    "unsafe_storage_symlink": "Storage path contains an unsafe symbolic link",
    "storage_escape": "Storage path escapes its approved root",
    "unsafe_writable_root": "Storage root is writable",
    "storage_scan_limit_exceeded": "Storage directory scan limit was exceeded",
    "storage_filesystem_error": "Storage directory could not be read",
    "storage_resolution_error": "Storage operation could not be completed",
}
_ERROR_RESPONSES = {
    400: {"model": StorageErrorResponse},
    404: {"model": StorageErrorResponse},
    422: {"model": StorageErrorResponse},
}


def _raise_safe_storage_error(error: StorageResolutionError) -> None:
    code = error.code if error.code in _ERROR_MESSAGES else "storage_resolution_error"
    detail = StorageErrorDetail(
        code=StorageReadErrorCode(code), message=_ERROR_MESSAGES[code]
    )
    raise HTTPException(
        status_code=_ERROR_STATUS.get(
            type(error), status.HTTP_422_UNPROCESSABLE_ENTITY
        ),
        detail=detail.model_dump(mode="json"),
    ) from None


def _root_schema(root: StorageRoot) -> StorageRootSchema:
    health = get_storage_root_health_snapshot(root)
    return StorageRootSchema(
        id=root.id,
        name=root.name,
        mode=root.mode,
        active=root.active,
        created_at=root.created_at,
        updated_at=root.updated_at,
        health=StorageRootHealthSchema(
            reachable=health.reachable,
            readable=health.readable,
            non_writable=health.non_writable,
            checked_at=health.checked_at,
            error=health.error,
        ),
    )


@protected_route(
    router.get,
    "/roots",
    [Scope.USERS_READ],
    response_model=list[StorageRootSchema],
    responses=_ERROR_RESPONSES,
)
def get_storage_roots(request: Request) -> list[StorageRootSchema]:
    assert_admin(request)
    return [_root_schema(root) for root in db_storage_handler.get_roots()]


@protected_route(
    router.get,
    "/roots/{storage_root_id}",
    [Scope.USERS_READ],
    response_model=StorageRootSchema,
    responses=_ERROR_RESPONSES,
)
def get_storage_root(request: Request, storage_root_id: int) -> StorageRootSchema:
    assert_admin(request)
    try:
        return _root_schema(db_storage_handler.get_root(storage_root_id))
    except StorageResolutionError as error:
        _raise_safe_storage_error(error)


@protected_route(
    router.get,
    "/roots/{storage_root_id}/browse",
    [Scope.USERS_READ],
    response_model=StorageDirectoryPageSchema,
    responses=_ERROR_RESPONSES,
)
def browse_storage_root(
    request: Request,
    storage_root_id: int,
    parent: Annotated[str, Query(max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)] = "",
    limit: Annotated[int, Query(ge=1, le=MAX_DIRECTORY_PAGE_SIZE)] = 50,
    cursor: Annotated[str | None, Query(max_length=MAX_STORAGE_CURSOR_LENGTH)] = None,
) -> StorageDirectoryPageSchema:
    assert_admin(request)
    try:
        root = db_storage_handler.get_root(storage_root_id)
        page = browse_storage_directories(root, parent, limit=limit, cursor=cursor)
    except StorageResolutionError as error:
        _raise_safe_storage_error(error)

    return StorageDirectoryPageSchema(
        entries=[
            StorageDirectoryEntrySchema(
                name=entry.name,
                relative_path=entry.relative_path,
                navigable=entry.navigable,
            )
            for entry in page.entries
        ],
        next_cursor=page.next_cursor,
    )
