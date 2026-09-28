"""Protected parent-ROM media routes backed exclusively by owned resources."""

from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, cast

from fastapi import File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from decorators.auth import protected_route
from endpoints.responses.rom import (
    DetailedRomSchema,
    RomLocalBackgroundAudioRequest,
    RomOwnedMediaPlacementMutationRequest,
    RomOwnedMediaReorderRequest,
    RomOwnedMediaSchema,
)
from exceptions.endpoint_exceptions import RomNotFoundInDatabaseException
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_rom_visible
from handler.database import db_rom_handler
from handler.filesystem import fs_resource_handler, storage_composition
from handler.filesystem.storage_access import OwnedRead, open_owned_access
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from handler.metadata.rom_media import discover_provider_media
from models.rom import RomOwnedMediaRole
from utils.context import ctx_httpx_client
from utils.router import APIRouter

router = APIRouter()
_IMAGE_LIMIT = 10 * 1024 * 1024
_AUDIO_LIMIT = 512 * 1024 * 1024


def _visible_rom(request: Request, rom_id: int):
    rom = db_rom_handler.get_rom(rom_id)
    if rom is None:
        raise RomNotFoundInDatabaseException(rom_id)
    assert_rom_visible(request, rom)
    return rom


def _conflict(value):
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Media catalog changed"
        )
    return value


def _detailed_rom_response(rom_id: int, request: Request) -> DetailedRomSchema:
    """Serialize a fully hydrated ROM after a media mutation commits."""
    rom = db_rom_handler.get_rom(rom_id)
    if rom is None:
        raise RomNotFoundInDatabaseException(rom_id)
    return DetailedRomSchema.from_orm_with_request(rom, request)


async def _download_provider_image(rom, candidate):
    """Download bounded provider bytes before publishing them to owned storage."""
    client = ctx_httpx_client.get()
    async with client.stream("GET", candidate.url, timeout=30) as response:
        if response.status_code != status.HTTP_200_OK:
            raise ValueError("Provider media could not be downloaded")
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > _IMAGE_LIMIT:
                raise ValueError("Provider media exceeds the 10 MiB limit")
            chunks.append(chunk)
    return await fs_resource_handler.store_owned_media_image(
        rom, candidate.role, b"".join(chunks)
    )


@protected_route(router.get, "/{id}/media", [Scope.ROMS_READ])
async def get_media(request: Request, id: int) -> list[RomOwnedMediaSchema]:
    _visible_rom(request, id)
    return [
        RomOwnedMediaSchema.model_validate(item)
        for item in db_rom_handler.get_owned_media_catalog(id)
    ]


@protected_route(router.post, "/{id}/media/refresh", [Scope.ROMS_WRITE])
async def refresh_media(
    request: Request, id: int, expected_version: datetime
) -> DetailedRomSchema:
    """Explicitly reconcile provider images without changing user placements."""
    rom = _visible_rom(request, id)
    provider = rom.metadata_source or "provider"
    source = {
        "url_screenshots": rom.url_screenshots or [],
        "url_artworks": [rom.url_cover] if rom.url_cover else [],
    }
    for candidate in discover_provider_media(provider, source):
        path: str | None = None
        try:
            path, mime_type = await _download_provider_image(rom, candidate)
            applied = db_rom_handler.reconcile_provider_owned_media(
                id,
                expected_version,
                candidate.provider,
                candidate.provider_media_id,
                candidate.role,
                candidate.display_label,
                mime_type,
                path,
            )
            if applied is None:
                raise ValueError("Media catalog changed")
            expected_version = applied.rom.updated_at
            rom = applied.rom
        except ValueError:
            if path is not None:
                await fs_resource_handler.remove_file(path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provider media could not be refreshed",
            ) from None
    return _detailed_rom_response(id, request)


@protected_route(router.get, "/{id}/media/{media_id}/content", [Scope.ROMS_READ])
async def get_media_content(request: Request, id: int, media_id: int):
    _visible_rom(request, id)
    media = next(
        (
            item
            for item in db_rom_handler.get_owned_media_catalog(id)
            if item.id == media_id and item.owned_path
        ),
        None,
    )
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    with cast(
        OwnedRead,
        open_owned_access(
            storage_composition.owned[OwnedStorageKind.RESOURCES],
            StorageOperation.READ,
            media.owned_path,
        ),
    ) as access:
        content = access.read()
    return StreamingResponse(
        iter([content]),
        media_type=media.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{PurePosixPath(media.owned_path).name}"',
            "Content-Length": str(len(content)),
            "X-Content-Type-Options": "nosniff",
        },
    )


@protected_route(router.post, "/{id}/media/placements", [Scope.ROMS_WRITE])
async def set_placement(
    request: Request, id: int, payload: RomOwnedMediaPlacementMutationRequest
) -> DetailedRomSchema:
    _visible_rom(request, id)
    _conflict(
        db_rom_handler.set_owned_media_placement(
            id, payload.media_id, payload.expected_version, payload.surface, True
        )
    )
    return _detailed_rom_response(id, request)


@protected_route(router.delete, "/{id}/media/placements/{media_id}", [Scope.ROMS_WRITE])
async def remove_placement(
    request: Request, id: int, media_id: int, surface: str, expected_version: datetime
) -> DetailedRomSchema:
    _visible_rom(request, id)
    from models.rom import RomOwnedMediaSurface

    _conflict(
        db_rom_handler.set_owned_media_placement(
            id, media_id, expected_version, RomOwnedMediaSurface(surface), False
        )
    )
    return _detailed_rom_response(id, request)


@protected_route(router.put, "/{id}/media/placements", [Scope.ROMS_WRITE])
async def reorder_placements(
    request: Request, id: int, payload: RomOwnedMediaReorderRequest
) -> DetailedRomSchema:
    _visible_rom(request, id)
    _conflict(
        db_rom_handler.replace_owned_media_placements(
            id, payload.expected_version, payload.surface, payload.media_ids
        )
    )
    return _detailed_rom_response(id, request)


@protected_route(router.put, "/{id}/media/local-background-audio", [Scope.ROMS_WRITE])
async def replace_local_background_audio(
    request: Request, id: int, payload: RomLocalBackgroundAudioRequest
) -> DetailedRomSchema:
    _visible_rom(request, id)
    _conflict(
        db_rom_handler.replace_local_background_audio(
            id, payload.expected_version, payload.file_ids
        )
    )
    return _detailed_rom_response(id, request)


@protected_route(router.post, "/{id}/media/upload", [Scope.ROMS_WRITE])
async def upload_media(
    request: Request,
    id: int,
    expected_version: Annotated[datetime, Form()],
    role: Annotated[RomOwnedMediaRole, Form()],
    media: Annotated[UploadFile, File()],
) -> DetailedRomSchema:
    rom = _visible_rom(request, id)
    label = media.filename or "upload"
    content = await media.read(
        (_AUDIO_LIMIT if role is RomOwnedMediaRole.SOUNDTRACK else _IMAGE_LIMIT) + 1
    )
    path: str | None = None
    try:
        if role is RomOwnedMediaRole.SOUNDTRACK:
            extension = PurePosixPath(label).suffix
            path, mime_type = await fs_resource_handler.store_owned_media_audio(
                rom, content, extension
            )
        elif role is RomOwnedMediaRole.ARTWORK:
            if len(content) > _IMAGE_LIMIT:
                raise ValueError("Owned media image exceeds the 10 MiB limit")
            path, mime_type = await fs_resource_handler.store_owned_media_image(
                rom, role, content
            )
        else:
            raise ValueError("Only artwork and soundtrack uploads are accepted")
        applied = db_rom_handler.create_owned_upload_media(
            id, expected_version, role, label, mime_type, path
        )
        if applied is None:
            raise ValueError("Media catalog changed")
    except ValueError as exc:
        if path is not None:
            await fs_resource_handler.remove_file(path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return _detailed_rom_response(id, request)


@protected_route(router.delete, "/{id}/media/{media_id}", [Scope.ROMS_WRITE])
async def delete_media(
    request: Request, id: int, media_id: int, expected_version: datetime
) -> DetailedRomSchema:
    _visible_rom(request, id)
    applied = _conflict(
        db_rom_handler.delete_owned_media(id, media_id, expected_version)
    )
    for path in applied.replaced_owned_paths:
        try:
            await fs_resource_handler.remove_file(path)
        except OSError:
            db_rom_handler.create_owned_media_cleanup_intent(id, media_id, path)
    return _detailed_rom_response(id, request)
