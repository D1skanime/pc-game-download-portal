from fastapi import HTTPException, Request, status

from decorators.auth import protected_route
from endpoints.responses.setup import (
    SetupFolderAssignmentRequest,
    SetupFolderAssignmentResponse,
    SetupFoldersResponse,
)
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_admin
from handler.database import db_user_handler
from handler.setup_folder_handler import setup_folder_handler
from utils.router import APIRouter

router = APIRouter(tags=["setup"])


@protected_route(router.get, "/setup/folders", [], response_model=SetupFoldersResponse)
def discover_setup_folders(request: Request) -> dict:
    if (
        db_user_handler.get_admin_users()
        and Scope.PLATFORMS_READ not in request.auth.scopes
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        return setup_folder_handler.discover_response()
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
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
        result = setup_folder_handler.assign(
            setup_folder_handler.root(),
            [item.model_dump() for item in body.assignments],
            {
                "actor_user_id": request.user.id,
                "actor_display_name": request.user.username,
            },
        )
        return setup_folder_handler.response(result)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
