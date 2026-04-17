import os
from typing import Annotated

from fastapi import Header, HTTPException
from fastapi import Path as PathVar
from fastapi import Request, status
from fastapi.responses import Response
from starlette.requests import ClientDisconnect
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, NullTarget

from decorators.auth import protected_route
from exceptions.endpoint_exceptions import RomNotFoundInDatabaseException
from handler.auth.constants import Scope
from handler.database import db_rom_handler
from handler.filesystem import fs_rom_handler
from logger.formatter import BLUE
from logger.formatter import highlight as hl
from logger.logger import log
from models.rom import RomFile, RomFileCategory
from utils.router import APIRouter

router = APIRouter()

SOUNDTRACK_FOLDER = "soundtrack"
ALLOWED_AUDIO_EXTENSIONS = frozenset(
    {".mp3", ".ogg", ".oga", ".opus", ".m4a", ".aac", ".wav", ".flac"}
)


def _is_allowed_audio_file(file_name: str) -> bool:
    _, ext = os.path.splitext(file_name)
    return ext.lower() in ALLOWED_AUDIO_EXTENSIONS


@protected_route(
    router.post,
    "/{id}/soundtracks",
    [Scope.ROMS_WRITE],
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_404_NOT_FOUND: {}},
)
async def add_rom_soundtracks(
    request: Request,
    id: Annotated[int, PathVar(description="Rom internal id.", ge=1)],
    filename: Annotated[
        str,
        Header(
            description="The name of the file being uploaded.",
            alias="x-upload-filename",
        ),
    ],
) -> Response:
    """Upload a soundtrack audio file for a multi-file ROM."""

    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)

    if rom.has_simple_single_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Soundtracks can only be uploaded to folder-based ROMs",
        )

    if not _is_allowed_audio_file(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported audio file type. Allowed: "
                f"{', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
            ),
        )

    soundtrack_dir_rel = f"{rom.full_path}/{SOUNDTRACK_FOLDER}"
    file_rel_path = f"{soundtrack_dir_rel}/{filename}"
    file_location = fs_rom_handler.validate_path(file_rel_path)
    log.info(f"Uploading soundtrack to {hl(str(file_location))}")

    await fs_rom_handler.make_directory(soundtrack_dir_rel)

    parser = StreamingFormDataParser(headers=request.headers)
    parser.register("x-upload-platform", NullTarget())
    parser.register(filename, FileTarget(str(file_location)))

    def cleanup_partial_file():
        if file_location.exists():
            file_location.unlink()

    try:
        async for chunk in request.stream():
            parser.data_received(chunk)
    except ClientDisconnect:
        log.error("Client disconnected during upload")
        cleanup_partial_file()
        return Response()
    except Exception as exc:
        log.error("Error uploading soundtrack", exc_info=exc)
        cleanup_partial_file()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error uploading the soundtrack",
        ) from exc

    stat = os.stat(file_location)
    existing = db_rom_handler.get_rom_file_by_path(
        rom_id=rom.id, file_path=soundtrack_dir_rel, file_name=filename
    )
    if existing:
        db_rom_handler.update_rom_file(
            existing.id,
            {
                "file_size_bytes": stat.st_size,
                "last_modified": stat.st_mtime,
                "category": RomFileCategory.SOUNDTRACK,
                "missing_from_fs": False,
            },
        )
    else:
        db_rom_handler.add_rom_file(
            RomFile(
                rom_id=rom.id,
                file_name=filename,
                file_path=soundtrack_dir_rel,
                file_size_bytes=stat.st_size,
                last_modified=stat.st_mtime,
                category=RomFileCategory.SOUNDTRACK,
            )
        )

    return Response()


@protected_route(
    router.delete,
    "/{id}/soundtracks/{file_id}",
    [Scope.ROMS_WRITE],
    responses={status.HTTP_404_NOT_FOUND: {}},
)
async def delete_rom_soundtrack(
    request: Request,
    id: Annotated[int, PathVar(description="Rom internal id.", ge=1)],
    file_id: Annotated[int, PathVar(description="Rom file internal id.", ge=1)],
) -> Response:
    """Delete a single soundtrack file from a ROM."""

    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)

    rom_file = db_rom_handler.get_rom_file_by_id(file_id)
    if (
        not rom_file
        or rom_file.rom_id != rom.id
        or rom_file.category != RomFileCategory.SOUNDTRACK
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Soundtrack file not found",
        )

    file_rel_path = rom_file.full_path

    try:
        await fs_rom_handler.remove_file(file_rel_path)
    except FileNotFoundError:
        log.warning(
            f"Soundtrack file {hl(file_rel_path)} not found on disk; "
            f"removing DB row anyway"
        )
    except Exception as exc:
        log.error(
            f"Error deleting soundtrack {hl(file_rel_path)}",
            exc_info=exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error deleting the soundtrack",
        ) from exc

    db_rom_handler.delete_rom_file(file_id)

    log.info(
        f"Deleted soundtrack {hl(rom_file.file_name)} from "
        f"{hl(rom.name or 'ROM', color=BLUE)} [{hl(rom.fs_name)}]"
    )

    return Response()
