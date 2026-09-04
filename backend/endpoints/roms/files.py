import os
import stat as stat_lib
from collections.abc import Iterator
from pathlib import PurePath
from typing import Annotated
from urllib.parse import quote

from fastapi import HTTPException
from fastapi import Path as PathVar
from fastapi import Request, status
from fastapi.responses import Response, StreamingResponse

from config import DISABLE_DOWNLOAD_ENDPOINT_AUTH
from decorators.auth import protected_route
from endpoints.responses.rom import RomFileSchema
from endpoints.storage_policy import authorize_api_storage_operation
from exceptions.endpoint_exceptions import RomNotFoundInDatabaseException
from exceptions.storage_read import MappedReadError, MissingMappedContentError
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_can, assert_rom_visible, get_permissions
from handler.database import db_rom_handler, db_storage_handler
from handler.filesystem import fs_rom_handler, legacy_external_storage
from handler.filesystem.storage_policy import StorageOperation
from handler.storage.read_context import MappingReadContext
from logger.formatter import BLUE
from logger.formatter import highlight as hl
from logger.logger import log
from models.permission import PermAction, PermEntity
from models.rom import RomFileCategory
from utils.audio_tags import guess_audio_media_type
from utils.media_types import (
    guess_media_file_type,
    is_allowed_document_file,
    is_allowed_media_file,
)
from utils.router import APIRouter

router = APIRouter()


class MappedContentResponse(StreamingResponse):
    """A response bound to one authorized descriptor for its whole transfer."""


def _mapped_relative_path(full_path: str, mapping_relative_path: str) -> str:
    parts = PurePath(full_path).parts
    mapping_parts = PurePath(mapping_relative_path).parts
    if mapping_parts:
        for start in (0, 1):
            end = start + len(mapping_parts)
            if parts[start:end] == mapping_parts:
                return PurePath(*parts[end:]).as_posix()
    if len(parts) < 2:
        return parts[0] if parts else ""
    return PurePath(*parts[1:]).as_posix()


def _content_disposition(disposition: str, filename: str) -> str:
    if any(
        ord(character) < 0x20 or 0x7F <= ord(character) <= 0x9F
        for character in filename
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid download filename",
        )
    fallback = filename.encode("ascii", errors="ignore").decode("ascii") or "download"
    fallback = fallback.replace("\\", "\\\\").replace('"', '\\"')
    encoded = quote(filename, safe="")
    return f"{disposition}; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


def preflight_mapped_download(rom, file, *, first_use_operation: str = "download"):
    """Authorize the current mapping revision and open one download handle."""
    mapping = db_storage_handler.get_active_mapping(rom.platform_id)
    context = MappingReadContext(mapping.id, mapping.version)
    access = context.open(
        StorageOperation.DOWNLOAD,
        _mapped_relative_path(file.full_path, mapping.relative_path),
        first_use_operation=first_use_operation,
    )
    try:
        context.boundary()
        size = os.fstat(access.fileno()).st_size
    except Exception:
        access.close()
        raise
    return context, access, size


def preflight_mapped_stat(rom, file) -> int:
    """Authorize the current mapping revision and read non-productive metadata."""
    mapping = db_storage_handler.get_active_mapping(rom.platform_id)
    context = MappingReadContext(mapping.id, mapping.version)
    with context.open(
        StorageOperation.STAT,
        _mapped_relative_path(file.full_path, mapping.relative_path),
    ) as access:
        metadata = access.stat()
        if not stat_lib.S_ISREG(metadata.st_mode):
            raise MissingMappedContentError(mapping.id, mapping.version)
        context.boundary()
        return metadata.st_size


def _mapped_http_error(error: MappedReadError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": error.code, "state": error.safe_state},
    )


def _range_bounds(value: str | None, size: int) -> tuple[int, int] | None:
    if not value:
        return None
    invalid = HTTPException(
        status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
        headers={"Content-Range": f"bytes */{size}"},
    )
    if not value.startswith("bytes=") or "," in value:
        raise invalid
    start_text, separator, end_text = value[6:].partition("-")
    if not separator:
        raise invalid
    try:
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else size - 1
        else:
            suffix = int(end_text)
            if suffix <= 0:
                raise ValueError
            start = max(size - suffix, 0)
            end = size - 1
    except ValueError:
        raise invalid from None
    if start < 0 or start >= size or end < start:
        raise invalid
    return start, min(end, size - 1)


def _mapped_chunks(context, access, start: int, length: int) -> Iterator[bytes]:
    remaining = length
    os.lseek(access.fileno(), start, os.SEEK_SET)
    try:
        while remaining:
            context.boundary()
            chunk = os.read(access.fileno(), min(1024 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
        context.boundary()
    finally:
        access.close()


@protected_route(
    router.get,
    "/{id}/files",
    [Scope.ROMS_READ],
    responses={status.HTTP_404_NOT_FOUND: {}},
)
async def get_romfile(
    request: Request,
    id: Annotated[int, PathVar(description="Rom file internal id.", ge=1)],
) -> RomFileSchema:
    """Retrieve a rom file by ID."""

    file = db_rom_handler.get_rom_file_by_id(id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Resolve back to the parent rom and enforce its visibility, so a file
    # belonging to a hidden rom can't be read by direct RomFile.id.
    rom = db_rom_handler.get_rom(file.rom_id)
    if not rom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    assert_rom_visible(request, rom, not_found_detail="File not found")

    return RomFileSchema.model_validate(file)


@protected_route(
    router.head,
    "/{id}/files/content/{file_name}",
    [] if DISABLE_DOWNLOAD_ENDPOINT_AUTH else [Scope.ROMS_READ],
    responses={status.HTTP_404_NOT_FOUND: {}},
)
@protected_route(
    router.get,
    "/{id}/files/content/{file_name}",
    [] if DISABLE_DOWNLOAD_ENDPOINT_AUTH else [Scope.ROMS_READ],
    responses={status.HTTP_404_NOT_FOUND: {}},
)
async def get_romfile_content(
    request: Request,
    id: Annotated[int, PathVar(description="Rom file internal id.", ge=1)],
    file_name: Annotated[str, PathVar(description="File name to download")],
):
    """Download a rom file."""

    current_username = (
        request.user.username if request.user.is_authenticated else "unknown"
    )

    file = db_rom_handler.get_rom_file_by_id(id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # 404-mask file bytes of roms hidden from the caller: resolve the parent
    # rom and apply its visibility before serving any content.
    rom = db_rom_handler.get_rom(file.rom_id)
    if not rom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    assert_rom_visible(request, rom, not_found_detail="File not found")

    log.info(
        f"User {hl(current_username, color=BLUE)} is downloading {hl(file.file_name)}"
    )

    # Derive content type / disposition / download name from the trusted DB
    # record, never from the client-supplied file_name path param â otherwise a
    # caller could request the same bytes with an arbitrary extension to force a
    # mismatched Content-Type while served inline (content-sniffing/XSS).
    # Audio, images and videos are served inline so <audio>/<video>/<img> in the
    # details view can render and seek them; everything else downloads.
    if file.category == RomFileCategory.SOUNDTRACK:
        media_type = guess_audio_media_type(file.file_name)
        disposition = "inline"
    elif file.category == RomFileCategory.MANUAL and is_allowed_document_file(
        file.file_name
    ):
        # Only manuals are served inline as documents so the in-page viewer can
        # render them; a game/extra file that happens to end in .pdf/.md still
        # downloads.
        media_type = guess_media_file_type(file.file_name)
        disposition = "inline"
    elif is_allowed_media_file(file.file_name):
        media_type = guess_media_file_type(file.file_name)
        disposition = "inline"
    else:
        media_type = "application/octet-stream"
        disposition = "attachment"

    # Inline files are served under an explicit, trusted Content-Type; nosniff
    # keeps the browser from sniffing them into anything script-capable (e.g. a
    # Markdown manual into HTML).
    headers = {"X-Content-Type-Options": "nosniff"} if disposition == "inline" else {}
    content_disposition = _content_disposition(disposition, file.file_name)

    context = None
    access = None
    try:
        if request.method == "HEAD":
            size = preflight_mapped_stat(rom, file)
        else:
            context, access, size = preflight_mapped_download(rom, file)
    except MappedReadError as error:
        raise _mapped_http_error(error) from None

    try:
        bounds = _range_bounds(request.headers.get("range"), size)
    except HTTPException:
        if access is not None:
            access.close()
        raise
    start, end = bounds if bounds is not None else (0, max(size - 1, 0))
    content_length = end - start + 1 if size else 0
    response_headers = {
        **headers,
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": content_disposition,
    }
    response_status = status.HTTP_200_OK
    if bounds is not None:
        response_status = status.HTTP_206_PARTIAL_CONTENT
        response_headers["Content-Range"] = f"bytes {start}-{end}/{size}"

    if request.method == "HEAD":
        return Response(
            status_code=response_status,
            media_type=media_type,
            headers=response_headers,
        )

    assert context is not None and access is not None
    return MappedContentResponse(
        _mapped_chunks(context, access, start, content_length),
        status_code=response_status,
        media_type=media_type,
        headers=response_headers,
    )


@protected_route(
    router.delete,
    "/{rom_id}/files/{file_id}",
    [Scope.ROMS_WRITE],
    responses={status.HTTP_404_NOT_FOUND: {}},
)
async def delete_rom_file(
    request: Request,
    rom_id: Annotated[int, PathVar(description="Rom internal id.", ge=1)],
    file_id: Annotated[int, PathVar(description="Rom file internal id.", ge=1)],
) -> Response:
    authorize_api_storage_operation(StorageOperation.DELETE, legacy_external_storage)

    """Delete a single file from a ROM."""

    # Removing a game file destroys library content, so it needs the same
    # DELETE grant the whole-ROM delete route requires. The sibling routes for
    # manuals/soundtracks/screenshots settle for ROMS_WRITE because a category
    # guard keeps them off the game files themselves.
    assert_can(get_permissions(request), PermEntity.ROMS, PermAction.DELETE)

    rom = db_rom_handler.get_rom(rom_id)
    if not rom:
        raise RomNotFoundInDatabaseException(rom_id)

    assert_rom_visible(request, rom, not_found_detail="File not found")

    rom_file = db_rom_handler.get_rom_file_by_id(file_id)
    if not rom_file or rom_file.rom_id != rom.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file_rel_path = rom_file.full_path

    try:
        await fs_rom_handler.remove_file(file_rel_path)
    except FileNotFoundError:
        log.warning(
            f"ROM file {hl(file_rel_path)} not found on disk; removing DB row anyway"
        )
    except Exception as exc:
        log.error(f"Error deleting ROM file {hl(file_rel_path)}", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error deleting the file",
        ) from exc

    db_rom_handler.delete_rom_file(file_id)

    log.info(
        f"Deleted file {hl(rom_file.file_name)} from "
        f"{hl(rom.name or 'ROM', color=BLUE)} [{hl(rom.fs_name)}]"
    )

    return Response()
