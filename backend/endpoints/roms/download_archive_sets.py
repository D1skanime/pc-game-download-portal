from __future__ import annotations

from typing import Annotated

from fastapi import Body, HTTPException
from fastapi import Path as PathVar
from fastapi import Request, status

from decorators.auth import protected_route
from endpoints.responses.download_archive_set import (
    DownloadArchiveSetImportRequest,
    DownloadArchiveSetRequest,
    DownloadArchiveSetResponse,
)
from exceptions.endpoint_exceptions import RomNotFoundInDatabaseException
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_rom_visible
from handler.database import db_download_archive_sets_handler, db_rom_handler
from models.download_archive_set import DownloadArchiveSet
from utils.router import APIRouter

router = APIRouter()
_NOT_FOUND = "Download archive set not found"


def _serialize(archive_set: DownloadArchiveSet) -> DownloadArchiveSetResponse:
    return DownloadArchiveSetResponse(
        id=archive_set.id,
        rom_id=archive_set.rom_id,
        name=archive_set.name,
        members=[
            {
                "component_id": member.component_id,
                "manifest_member_id": member.manifest_member_id,
                "position": member.position,
                "required": member.required,
            }
            for member in archive_set.members
        ],
    )


def _rom_or_404(request: Request, rom_id: int):
    rom = db_rom_handler.get_rom(rom_id)
    if rom is None:
        raise RomNotFoundInDatabaseException(rom_id)
    assert_rom_visible(request, rom, not_found_detail=_NOT_FOUND)
    return rom


def _members(payload: DownloadArchiveSetRequest):
    return [member.model_dump() for member in payload.members]


@protected_route(
    router.get,
    "/{rom_id}/download-archive-sets",
    [Scope.ROMS_READ],
    response_model=list[DownloadArchiveSetResponse],
)
def list_download_archive_sets(
    request: Request,
    rom_id: Annotated[int, PathVar(ge=1)],
) -> list[DownloadArchiveSetResponse]:
    _rom_or_404(request, rom_id)
    return [
        _serialize(archive_set)
        for archive_set in db_download_archive_sets_handler.list_for_rom(rom_id)
    ]


@protected_route(
    router.post,
    "/{rom_id}/download-archive-sets",
    [Scope.ROMS_WRITE],
    status_code=status.HTTP_201_CREATED,
    response_model=DownloadArchiveSetResponse,
)
def create_download_archive_set(
    request: Request,
    rom_id: Annotated[int, PathVar(ge=1)],
    payload: Annotated[DownloadArchiveSetRequest, Body()],
) -> DownloadArchiveSetResponse:
    _rom_or_404(request, rom_id)
    try:
        archive_set = db_download_archive_sets_handler.create(
            rom_id, payload.name, _members(payload)
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return _serialize(archive_set)


@protected_route(
    router.put,
    "/{rom_id}/download-archive-sets/{archive_set_id}",
    [Scope.ROMS_WRITE],
    response_model=DownloadArchiveSetResponse,
)
def replace_download_archive_set(
    request: Request,
    rom_id: Annotated[int, PathVar(ge=1)],
    archive_set_id: Annotated[int, PathVar(ge=1)],
    payload: Annotated[DownloadArchiveSetRequest, Body()],
) -> DownloadArchiveSetResponse:
    _rom_or_404(request, rom_id)
    try:
        archive_set = db_download_archive_sets_handler.replace(
            rom_id, archive_set_id, payload.name, _members(payload)
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    if archive_set is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return _serialize(archive_set)


@protected_route(
    router.post,
    "/{rom_id}/download-archive-sets/import",
    [Scope.ROMS_WRITE],
    response_model=list[DownloadArchiveSetResponse],
)
def import_download_archive_sets(
    request: Request,
    rom_id: Annotated[int, PathVar(ge=1)],
    payload: Annotated[DownloadArchiveSetImportRequest, Body()],
) -> list[DownloadArchiveSetResponse]:
    _rom_or_404(request, rom_id)
    try:
        archive_sets = db_download_archive_sets_handler.import_sets(
            rom_id,
            [(archive_set.name, _members(archive_set)) for archive_set in payload.sets],
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return [_serialize(archive_set) for archive_set in archive_sets]
