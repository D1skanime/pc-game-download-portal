from fastapi import HTTPException, Request, status

from decorators.auth import protected_route
from endpoints.responses.setup import (
    SetupFolderAssignmentRequest,
    SetupFolderAssignmentResponse,
    SetupFoldersResponse,
    SetupRecoverySnapshot,
)
from exceptions.storage_exceptions import StorageResolutionError
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_admin
from handler.database import db_user_handler
from handler.setup_folder_handler import setup_folder_handler
from handler.setup_recovery import setup_recovery_handler
from utils.router import APIRouter

router = APIRouter(tags=["setup"])


@protected_route(router.get, "/setup/folders", [], response_model=SetupFoldersResponse)
def discover_setup_folders(request: Request) -> dict:
    if db_user_handler.get_admin_users():
        if not request.user.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")
        assert_admin(request)
    try:
        return setup_folder_handler.discover_response()
    except (ValueError, StorageResolutionError, OSError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="setup_folders_unavailable"
        ) from error


@protected_route(
    router.post,
    "/setup/folders/assign",
    [Scope.USERS_WRITE],
    response_model=SetupFolderAssignmentResponse,
)
def assign_setup_folders(request: Request, body: SetupFolderAssignmentRequest) -> dict:
    assert_admin(request)
    try:
        return setup_recovery_handler.assign(
            [item.model_dump() for item in body.assignments],
            {
                "actor_user_id": request.user.id,
                "actor_display_name": request.user.username,
            },
        )
    except (ValueError, StorageResolutionError, OSError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="setup_assignment_conflict"
        ) from error


@protected_route(
    router.get,
    "/setup/status",
    [Scope.USERS_WRITE],
    response_model=SetupRecoverySnapshot,
)
def get_setup_status(request: Request) -> SetupRecoverySnapshot:
    assert_admin(request)
    return setup_recovery_handler.snapshot()
