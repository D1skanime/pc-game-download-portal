from typing import Annotated, NoReturn

from fastapi import HTTPException, Query, Request, status

from decorators.auth import protected_route
from endpoints.responses.download_transfer import (
    DownloadTransferCreateRequest,
    DownloadTransferEventResponse,
    DownloadTransferItemResponse,
    DownloadTransferObservationRequest,
    DownloadTransferResponse,
)
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_rom_visible, get_permissions
from handler.database import db_download_manifest_handler, db_download_transfer_handler
from models.download_transfer import DownloadTransferMode
from utils.router import APIRouter

router = APIRouter(prefix="/download-transfer-sessions", tags=["downloads"])
_NOT_FOUND = "Download transfer session not found"


def _not_found() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _conflict(error: ValueError) -> HTTPException:
    message = str(error)
    if "digest" in message:
        code = "integrity_mismatch"
    elif "observed bytes" in message:
        code = "invalid_observation"
    elif "closed or unavailable" in message:
        code = "session_closed"
    elif "event history" in message:
        code = "event_limit_reached"
    else:
        code = "invalid_transition"
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": code, "message": message},
    )


def _serialize(transfer) -> DownloadTransferResponse:
    manifest_members = {
        member.public_id: member
        for component in transfer.manifest.components
        for member in component.members
    }
    return DownloadTransferResponse(
        id=transfer.id,
        manifest_id=transfer.manifest_id,
        parent_session_id=transfer.parent_session_id,
        attempt_no=transfer.attempt_no,
        rom_id=transfer.rom_id,
        mode=transfer.mode.value,
        status=transfer.status.value,
        result=transfer.result.value if transfer.result is not None else None,
        selected_items=transfer.selected_items,
        selected_bytes=transfer.selected_bytes,
        observed_bytes=transfer.observed_bytes,
        started_at=transfer.started_at,
        last_activity_at=transfer.last_activity_at,
        ended_at=transfer.ended_at,
        items=[
            DownloadTransferItemResponse(
                id=item.id,
                manifest_member_id=item.manifest_member_public_id,
                destination=(
                    manifest_members[item.manifest_member_public_id].destination
                    if item.manifest_member_public_id in manifest_members
                    else ""
                ),
                expected_bytes=item.expected_bytes,
                observed_bytes=item.observed_bytes,
                status=item.status.value,
                started_at=item.started_at,
                last_activity_at=item.last_activity_at,
                ended_at=item.ended_at,
            )
            for item in transfer.items
            if item.dismissed_at is None
        ],
        events=[
            DownloadTransferEventResponse(
                ordinal=event.ordinal,
                event_type=event.event_type,
                observed_bytes=event.observed_bytes,
                error_code=event.error_code,
                occurred_at=event.occurred_at,
            )
            for event in sorted(transfer.events, key=lambda item: item.ordinal)
        ],
    )


def _load_visible(request: Request, transfer_id: str):
    transfer = db_download_transfer_handler.get_session(transfer_id, request.user.id)
    if transfer is None:
        _not_found()
    assert_rom_visible(request, transfer.rom, not_found_detail=_NOT_FOUND)
    return transfer


@protected_route(
    router.post, "", [Scope.ROMS_READ], status_code=status.HTTP_201_CREATED
)
async def create_download_transfer(
    request: Request, payload: DownloadTransferCreateRequest
) -> DownloadTransferResponse:
    manifest = db_download_manifest_handler.get_manifest(
        payload.manifest_id, request.user.id
    )
    if manifest is None:
        _not_found()
    assert_rom_visible(request, manifest.rom, not_found_detail=_NOT_FOUND)
    try:
        transfer = db_download_transfer_handler.create_session(
            request.user.id,
            payload.manifest_id,
            DownloadTransferMode(payload.mode),
            member_ids=set(payload.member_ids) if payload.member_ids else None,
            previous_session_id=payload.previous_session_id,
        )
    except ValueError:
        _not_found()
    # create_session returns after its managed DB session closes. Reload the
    # transfer so manifest members are available for the response serializer.
    transfer = db_download_transfer_handler.get_session(transfer.id, request.user.id)
    if transfer is None:
        _not_found()
    return _serialize(transfer)


@protected_route(router.get, "", [Scope.ROMS_READ])
async def list_download_transfers(
    request: Request,
    rom_id: Annotated[int | None, Query(gt=0)] = None,
    manifest_id: Annotated[str | None, Query(pattern=r"^[0-9a-f-]{36}$")] = None,
) -> list[DownloadTransferResponse]:
    permissions = get_permissions(request)
    return [
        _serialize(item)
        for item in db_download_transfer_handler.get_sessions(
            request.user.id,
            rom_id=rom_id,
            manifest_id=manifest_id,
            hidden_platform_ids=permissions.hidden_platform_ids,
            hidden_rom_ids=permissions.hidden_rom_ids,
        )
    ]


@protected_route(
    router.delete, "", [Scope.ROMS_READ], status_code=status.HTTP_204_NO_CONTENT
)
async def delete_download_transfer_history(
    request: Request,
    rom_id: Annotated[int | None, Query(gt=0)] = None,
) -> None:
    db_download_transfer_handler.delete_terminal_sessions(
        request.user.id, rom_id=rom_id
    )


@protected_route(
    router.delete,
    "/{transfer_id}",
    [Scope.ROMS_READ],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_download_transfer(request: Request, transfer_id: str) -> None:
    try:
        deleted = db_download_transfer_handler.delete_session(
            transfer_id, request.user.id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc
    if not deleted:
        _not_found()


@protected_route(
    router.delete,
    "/{transfer_id}/items/{item_id}",
    [Scope.ROMS_READ],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_download_transfer_item(
    request: Request, transfer_id: str, item_id: int
) -> None:
    try:
        deleted = db_download_transfer_handler.delete_item(
            transfer_id, request.user.id, item_id
        )
    except ValueError as exc:
        raise _conflict(exc) from exc
    if not deleted:
        _not_found()


@protected_route(router.post, "/{transfer_id}/cancel", [Scope.ROMS_READ])
async def cancel_download_transfer(
    request: Request, transfer_id: str
) -> DownloadTransferResponse:
    if not db_download_transfer_handler.cancel_session(transfer_id, request.user.id):
        _not_found()
    return _serialize(_load_visible(request, transfer_id))


@protected_route(router.get, "/{transfer_id}", [Scope.ROMS_READ])
async def get_download_transfer(
    request: Request, transfer_id: str
) -> DownloadTransferResponse:
    return _serialize(_load_visible(request, transfer_id))


@protected_route(
    router.post, "/{transfer_id}/items/{item_id}/events", [Scope.ROMS_READ]
)
async def append_download_transfer_event(
    request: Request,
    transfer_id: str,
    item_id: int,
    payload: DownloadTransferObservationRequest,
) -> DownloadTransferEventResponse:
    transfer = _load_visible(request, transfer_id)
    try:
        event = db_download_transfer_handler.append_observation(
            transfer.id,
            request.user.id,
            item_id,
            payload.event_type,
            payload.observed_bytes,
            payload.error_code,
            payload.sha256,
        )
    except ValueError as exc:
        raise _conflict(exc) from exc
    return DownloadTransferEventResponse(
        ordinal=event.ordinal,
        event_type=event.event_type,
        observed_bytes=event.observed_bytes,
        error_code=event.error_code,
        occurred_at=event.occurred_at,
    )
