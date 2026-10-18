"""Authenticated durable scan commands and reconciliation."""

from uuid import UUID

from fastapi import HTTPException, Query, Request

from decorators.auth import protected_route
from endpoints.responses.scan_operations import (
    RequestKey,
    ScanOperationMutationRequest,
    ScanOperationRequest,
    ScanOperationSnapshot,
)
from exceptions.storage_exceptions import StorageResolutionError
from handler.auth.constants import Scope
from handler.database.scan_operations_handler import (
    DBScanOperationsHandler,
    OperationConflict,
    OperationNotFound,
    payload_digest,
)
from handler.scan_operation_commands import canonical_request, normalize_scan_request
from handler.scan_operation_projection import with_queue_projection
from models.user import Role
from utils.router import APIRouter

router = APIRouter(prefix="/scan-operations", tags=["scan-operations"])
operations = DBScanOperationsHandler()


def _admin(request):
    return request.user.role == Role.ADMIN


def _call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except OperationNotFound:
        raise HTTPException(404, "operation_not_found") from None
    except OperationConflict as error:
        raise HTTPException(409, str(error)) from None
    except StorageResolutionError as error:
        raise HTTPException(409, error.code) from None
    except ValueError:
        raise HTTPException(409, "invalid_scan_command") from None


def _project(snapshot):
    return with_queue_projection(snapshot) if snapshot is not None else None


@protected_route(
    router.post,
    "",
    [Scope.TASKS_RUN],
    response_model=ScanOperationSnapshot,
    status_code=202,
)
def submit(request: Request, body: ScanOperationRequest):
    digest = payload_digest(canonical_request(body))
    existing = _call(operations.replay, request.user.id, body.request_key, digest)
    if existing is not None:
        return _project(existing)
    command = _call(normalize_scan_request, body)
    return _project(
        _call(operations.accept, request.user.id, body.request_key, command, digest)
    )


@protected_route(
    router.get,
    "/active",
    [Scope.TASKS_RUN],
    response_model=ScanOperationSnapshot | None,
)
def active(request: Request):
    return _project(
        _call(operations.find_active, request.user.id, admin=_admin(request))
    )


@protected_route(
    router.get,
    "/by-request/{request_key}",
    [Scope.TASKS_RUN],
    response_model=ScanOperationSnapshot,
)
def by_request(request: Request, request_key: RequestKey):
    return _project(_call(operations.get_by_request_key, request.user.id, request_key))


@protected_route(
    router.get,
    "/{operation_id}",
    [Scope.TASKS_RUN],
    response_model=ScanOperationSnapshot,
)
def by_id(
    request: Request,
    operation_id: UUID,
    offset: int = Query(0, ge=0, le=1000000),
    limit: int = Query(100, ge=1, le=100),
):
    return _project(
        _call(
            operations.get_by_id,
            str(operation_id),
            request.user.id,
            admin=_admin(request),
            offset=offset,
            limit=limit,
        )
    )


@protected_route(
    router.post,
    "/{operation_id}/cancel",
    [Scope.TASKS_RUN],
    response_model=ScanOperationSnapshot,
)
def cancel(request: Request, operation_id: UUID, body: ScanOperationMutationRequest):
    return _project(
        _call(
            operations.request_cancel,
            str(operation_id),
            request.user.id,
            body.expected_version,
            body.request_key,
            admin=_admin(request),
        )
    )


@protected_route(
    router.post,
    "/{operation_id}/resume",
    [Scope.TASKS_RUN],
    response_model=ScanOperationSnapshot,
)
def resume(request: Request, operation_id: UUID, body: ScanOperationMutationRequest):
    _call(
        operations.get_by_id, str(operation_id), request.user.id, admin=_admin(request)
    )
    if body.item_ids:
        raise HTTPException(422, "use_metadata_retry")
    return _project(
        _call(
            operations.request_resume,
            str(operation_id),
            request.user.id,
            body.expected_version,
            body.request_key,
            admin=_admin(request),
        )
    )


@protected_route(
    router.post,
    "/{operation_id}/retry-metadata",
    [Scope.TASKS_RUN],
    response_model=ScanOperationSnapshot,
)
def retry_metadata(
    request: Request, operation_id: UUID, body: ScanOperationMutationRequest
):
    _call(
        operations.get_by_id, str(operation_id), request.user.id, admin=_admin(request)
    )
    if not body.item_ids:
        raise HTTPException(422, "metadata_items_required")
    return _project(
        _call(
            operations.request_resume,
            str(operation_id),
            request.user.id,
            body.expected_version,
            body.request_key,
            admin=_admin(request),
            item_ids=body.item_ids,
        )
    )
