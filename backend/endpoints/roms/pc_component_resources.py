"""Bounded resources belonging to one contained DLC component."""

from datetime import datetime
from io import BytesIO
from pathlib import PurePosixPath
from typing import Annotated, cast

from fastapi import File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from PIL import Image, UnidentifiedImageError

from decorators.auth import protected_route
from endpoints.responses.rom import (
    PcComponentNoteCreateRequest,
    PcComponentNoteSchema,
    PcComponentNoteUpdateRequest,
    PcComponentOwnedMediaSchema,
)
from endpoints.roms.files import (
    _content_disposition,
    _mapped_chunks,
    preflight_mapped_download,
)
from exceptions.endpoint_exceptions import RomNotFoundInDatabaseException
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_rom_visible
from handler.database import db_rom_handler
from handler.filesystem import fs_resource_handler, fs_rom_handler, storage_composition
from handler.filesystem.storage_access import OwnedRead, open_owned_access
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from models.rom import RomComponentOwnedMediaOrigin, RomComponentOwnedMediaRole
from utils.router import APIRouter

router = APIRouter()

_UPLOAD_LIMIT = 10 * 1024 * 1024
_UPLOAD_MIME_TYPES = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


def _dlc_component(request: Request, rom_id: int, component_id: int):
    rom = db_rom_handler.get_rom(rom_id)
    if not rom:
        raise RomNotFoundInDatabaseException(rom_id)
    assert_rom_visible(request, rom)
    component = db_rom_handler.get_pc_component_by_id(rom_id, component_id)
    if component is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return rom, component


def _note_or_404(value):
    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return PcComponentNoteSchema.model_validate(value)


@protected_route(
    router.get, "/{id}/pc-components/{component_id}/notes", [Scope.ROMS_READ]
)
async def get_component_notes(
    request: Request, id: int, component_id: int
) -> list[PcComponentNoteSchema]:
    _dlc_component(request, id, component_id)
    return [
        PcComponentNoteSchema.model_validate(note)
        for note in db_rom_handler.get_pc_component_notes(
            id, component_id, request.user.id
        )
    ]


@protected_route(
    router.post, "/{id}/pc-components/{component_id}/notes", [Scope.ROMS_USER_WRITE]
)
async def create_component_note(
    request: Request, id: int, component_id: int, note: PcComponentNoteCreateRequest
) -> PcComponentNoteSchema:
    _dlc_component(request, id, component_id)
    return _note_or_404(
        db_rom_handler.create_pc_component_note(
            id,
            component_id,
            request.user.id,
            note.expected_version,
            note.title,
            note.content,
            note.is_public,
            note.tags,
        )
    )


@protected_route(
    router.put,
    "/{id}/pc-components/{component_id}/notes/{note_id}",
    [Scope.ROMS_USER_WRITE],
)
async def update_component_note(
    request: Request,
    id: int,
    component_id: int,
    note_id: int,
    note: PcComponentNoteUpdateRequest,
) -> PcComponentNoteSchema:
    _dlc_component(request, id, component_id)
    fields = note.model_dump(exclude={"expected_version"}, exclude_none=True)
    return _note_or_404(
        db_rom_handler.update_pc_component_note(
            id, component_id, request.user.id, note_id, note.expected_version, **fields
        )
    )


@protected_route(
    router.delete,
    "/{id}/pc-components/{component_id}/notes/{note_id}",
    [Scope.ROMS_USER_WRITE],
)
async def delete_component_note(
    request: Request,
    id: int,
    component_id: int,
    note_id: int,
    expected_version: datetime,
) -> dict[str, str]:
    _dlc_component(request, id, component_id)
    if not db_rom_handler.delete_pc_component_note(
        id, component_id, request.user.id, note_id, expected_version
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"message": "Note deleted successfully"}


@protected_route(
    router.get, "/{id}/pc-components/{component_id}/media", [Scope.ROMS_READ]
)
async def get_component_media(
    request: Request, id: int, component_id: int
) -> list[PcComponentOwnedMediaSchema]:
    _dlc_component(request, id, component_id)
    return [
        PcComponentOwnedMediaSchema.model_validate(media)
        for media in db_rom_handler.get_pc_component_owned_media(
            id, component_id, request.user.id
        )
    ]


async def _validated_upload(upload: UploadFile) -> tuple[bytes, str, str]:
    content = await upload.read(_UPLOAD_LIMIT + 1)
    if not content or len(content) > _UPLOAD_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Component media must be at most 10 MiB",
        )
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
            media = _UPLOAD_MIME_TYPES.get(image.format or "")
    except (UnidentifiedImageError, OSError, ValueError):
        media = None
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Component media must be a PNG, JPEG, or WebP image",
        )
    return content, *media


@protected_route(
    router.post, "/{id}/pc-components/{component_id}/media", [Scope.ROMS_WRITE]
)
async def upload_component_media(
    request: Request,
    id: int,
    component_id: int,
    role: Annotated[RomComponentOwnedMediaRole, Form()],
    expected_version: Annotated[datetime, Form()],
    media: Annotated[UploadFile, File()],
) -> PcComponentOwnedMediaSchema:
    rom, _ = _dlc_component(request, id, component_id)
    content, mime_type, extension = await _validated_upload(media)
    owned_path: str | None = None
    try:
        owned_path = await fs_resource_handler.store_pc_component_upload(
            rom, component_id, role, content, extension
        )
        applied = db_rom_handler.create_pc_component_owned_media(
            id,
            component_id,
            request.user.id,
            expected_version,
            role,
            mime_type,
            owned_path,
            RomComponentOwnedMediaOrigin.UPLOAD,
        )
        if applied is None:
            raise ValueError("The PC component changed before media was stored")
    except ValueError as exc:
        if owned_path is not None:
            await fs_resource_handler.remove_file(owned_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    for replaced_path in applied.replaced_owned_paths:
        await fs_resource_handler.remove_file(replaced_path)
    return PcComponentOwnedMediaSchema.model_validate(applied.media)


@protected_route(
    router.delete,
    "/{id}/pc-components/{component_id}/media/{media_id}",
    [Scope.ROMS_WRITE],
)
async def delete_component_media(
    request: Request,
    id: int,
    component_id: int,
    media_id: int,
    expected_version: datetime,
) -> dict[str, str]:
    _dlc_component(request, id, component_id)
    owned_path = db_rom_handler.delete_pc_component_owned_media(
        id, component_id, request.user.id, media_id, expected_version
    )
    if owned_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await fs_resource_handler.remove_file(owned_path)
    return {"message": "Media deleted successfully"}


@protected_route(
    router.get,
    "/{id}/pc-components/{component_id}/manifest-members/{member_id}/content",
    [Scope.ROMS_READ],
)
async def download_component_manifest_member(
    request: Request, id: int, component_id: int, member_id: int
):
    rom, component = _dlc_component(request, id, component_id)
    member = next(
        (item for item in component.manifest_members if item.id == member_id), None
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        full_path = fs_rom_handler.pc_component_member_path(rom, member)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from None
    file = type(
        "ManifestFile",
        (),
        {"full_path": full_path},
    )()
    context, access, size = preflight_mapped_download(rom, file)
    return StreamingResponse(
        _mapped_chunks(context, access, 0, size),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition(
                "attachment", PurePosixPath(member.relative_path).name
            ),
            "Content-Length": str(size),
        },
    )


@protected_route(
    router.get,
    "/{id}/pc-components/{component_id}/media/{media_id}/content",
    [Scope.ROMS_READ],
)
async def download_component_media(
    request: Request, id: int, component_id: int, media_id: int
):
    _, component = _dlc_component(request, id, component_id)
    media = next(
        (
            item
            for item in db_rom_handler.get_pc_component_owned_media(
                id, component.id, request.user.id
            )
            if item.id == media_id
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
            "Content-Disposition": _content_disposition(
                "inline", PurePosixPath(media.owned_path).name
            ),
            "Content-Length": str(len(content)),
            "X-Content-Type-Options": "nosniff",
        },
    )
