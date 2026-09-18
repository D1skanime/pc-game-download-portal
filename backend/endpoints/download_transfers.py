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
from handler.auth.dependencies import assert_rom_visible
from handler.database import db_download_manifest_handler, db_download_transfer_handler
from models.download_transfer import DownloadTransferMode
from utils.router import APIRouter

router = APIRouter(prefix="/download-transfer-sessions", tags=["downloads"])
_NOT_FOUND = "Download transfer session not found"


def _not_found() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _serialize(transfer) -> DownloadTransferResponse:
    return DownloadTransferResponse(
        id=transfer.id,
        manifest_id=transfer.manifest_id,
        rom_id=transfer.rom_id,
        mode=transfer.mode.value,
        status=transfer.status.value,
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
                expected_bytes=item.expected_bytes,
                observed_bytes=item.observed_bytes,
                status=item.status.value,
                started_at=item.started_at,
                last_activity_at=item.last_activity_at,
                ended_at=item.ended_at,
            )
            for item in transfer.items
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
            request.user.id, payload.manifest_id, DownloadTransferMode(payload.mode)
        )
    except ValueError:
        _not_found()
    return _serialize(transfer)


@protected_route(router.get, "", [Scope.ROMS_READ])
async def list_download_transfers(
    request: Request,
    rom_id: Annotated[int | None, Query(gt=0)] = None,
    manifest_id: Annotated[str | None, Query(pattern=r"^[0-9a-f-]{36}$")] = None,
) -> list[DownloadTransferResponse]:
    return [
        _serialize(item)
        for item in db_download_transfer_handler.get_sessions(
            request.user.id, rom_id=rom_id, manifest_id=manifest_id
        )
    ]


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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return DownloadTransferEventResponse(
        ordinal=event.ordinal,
        event_type=event.event_type,
        observed_bytes=event.observed_bytes,
        error_code=event.error_code,
        occurred_at=event.occurred_at,
    )
