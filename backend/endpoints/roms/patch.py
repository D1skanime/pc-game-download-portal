from pathlib import Path
from typing import Annotated, cast
from urllib.parse import quote
from uuid import uuid4

from fastapi import File, Form, HTTPException
from fastapi import Path as PathVar
from fastapi import Request, UploadFile, status
from pydantic import BaseModel
from starlette.responses import Response

from config import ROM_PATCHER_MAX_FILE_SIZE_BYTES
from decorators.auth import protected_route
from endpoints.storage_policy import authorize_api_storage_operation
from handler.auth.constants import Scope
from handler.auth.dependencies import ResolvedPermissions, get_permissions
from handler.database import db_rom_handler
from handler.filesystem import (
    legacy_external_storage,
    storage_composition,
)
from handler.filesystem.storage_access import (
    OwnedCreate,
    OwnedDelete,
    OwnedDirectory,
    OwnedRead,
    ReadCapability,
    open_owned_access,
    open_storage_access,
)
from handler.filesystem.storage_policy import (
    OwnedStorageDescriptor,
    OwnedStorageKind,
    StorageOperation,
)
from logger.formatter import BLUE
from logger.formatter import highlight as hl
from logger.logger import log
from utils.rom_patcher import SUPPORTED_PATCH_EXTENSIONS, PatcherError, apply_patch
from utils.router import APIRouter

router = APIRouter()

# Read the uploaded patch in bounded chunks so a large upload can't be held
# fully in memory before the size check kicks in.
_UPLOAD_CHUNK_SIZE = 1024 * 1024


class PatchResponse(BaseModel):
    message: str
    output_file_name: str
    output_file_size: int


@protected_route(
    router.post,
    "/{id}/patch",
    [Scope.ROMS_READ],
    responses={
        status.HTTP_400_BAD_REQUEST: {},
        status.HTTP_404_NOT_FOUND: {},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {},
    },
)
async def patch_rom(
    request: Request,
    id: Annotated[int, PathVar(description="ROM file ID (the base game file).", ge=1)],
    patch_file_id: Annotated[
        int | None,
        Form(description="ID of a library patch file (RomFile) to apply."),
    ] = None,
    output_file_name: Annotated[
        str | None,
        Form(
            description="Custom output file name. If omitted, derived from ROM + patch names.",
        ),
    ] = None,
    patch_file: Annotated[
        UploadFile | None,
        File(
            description="A patch file uploaded from the client, applied without being stored in the library.",
        ),
    ] = None,
):
    authorize_api_storage_operation(StorageOperation.READ, legacy_external_storage)
    authorize_api_storage_operation(
        StorageOperation.PATCH, storage_composition.owned[OwnedStorageKind.TEMP]
    )

    """Apply a patch to a ROM file server-side and return the patched file.

    The base ROM file must exist in the library. The patch is supplied either
    as ``patch_file_id`` (a patch already in the library) or as an uploaded
    ``patch_file`` (never stored in the library). Exactly one must be provided.
    The patched ROM is streamed back as a download.
    """

    current_username = (
        request.user.username if request.user.is_authenticated else "unknown"
    )

    if (patch_file_id is None) == (patch_file is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of a library patch file or an uploaded patch file",
        )

    perms = get_permissions(request)

    rom_file = db_rom_handler.get_rom_file_by_id(id)
    if not rom_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROM file with id {id} not found",
        )
    # 404-mask file bytes of roms hidden from the caller.
    base_rom = db_rom_handler.get_rom(rom_file.rom_id)
    if not base_rom or not perms.can_see_rom(base_rom.id, base_rom.platform_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROM file with id {id} not found",
        )
    if rom_file.missing_from_fs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROM file '{rom_file.file_name}' is missing from filesystem",
        )

    # RomPatcher.js loads the whole ROM into memory, so reject oversized inputs.
    if rom_file.file_size_bytes > ROM_PATCHER_MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"ROM file is too large to patch "
                f"({rom_file.file_size_bytes} bytes, max {ROM_PATCHER_MAX_FILE_SIZE_BYTES})"
            ),
        )

    rom_ext = Path(rom_file.file_name).suffix
    rom_base = Path(rom_file.file_name).stem
    temp_storage = storage_composition.owned[OwnedStorageKind.TEMP]
    temp_dir = f"romm_patch_{uuid4().hex}"
    with cast(
        OwnedDirectory,
        open_owned_access(temp_storage, StorageOperation.MKDIR, temp_dir),
    ) as directory:
        directory.mkdir()
    cleanup_names: list[str] = []
    patch_capability: ReadCapability

    try:
        if patch_file is not None:
            patch_capability, patch_display_name, patch_name = (
                await _stage_uploaded_patch(patch_file, temp_storage, temp_dir)
            )
            cleanup_names.append(patch_name)
        elif patch_file_id is not None:
            patch_capability, patch_display_name = _resolve_library_patch(
                patch_file_id, perms
            )
        else:
            # Unreachable: the XOR check above guarantees exactly one source.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No patch source provided",
            )

        patch_base = Path(patch_display_name).stem
        if output_file_name:
            resolved_output_name = f"{Path(output_file_name).stem}{rom_ext}"
        else:
            resolved_output_name = f"{rom_base} (patched-{patch_base}){rom_ext}"

        output_relative = f"{temp_dir}/patched{rom_ext}"
        cleanup_names.append(output_relative)

        log.info(
            f"User {hl(current_username, color=BLUE)} is patching "
            f"ROM file {hl(rom_file.file_name)} with patch {hl(patch_display_name)}"
        )

        with (
            cast(
                ReadCapability,
                open_storage_access(
                    legacy_external_storage,
                    StorageOperation.READ,
                    rom_file.full_path,
                ),
            ) as rom_capability,
            patch_capability,
            cast(
                OwnedCreate,
                open_owned_access(
                    temp_storage, StorageOperation.CREATE, output_relative
                ),
            ) as output_capability,
        ):
            validated = await apply_patch(
                rom_capability, patch_capability, output_capability
            )
        with cast(
            OwnedRead,
            open_owned_access(temp_storage, StorageOperation.READ, output_relative),
        ) as output_read:
            output_content = output_read.read()
    except PatcherError as e:
        # Detail may contain server paths from node/RomPatcher.js; keep it server-side.
        log.error(f"Patching failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Patching failed",
        ) from e
    except Exception as e:
        log.error(f"Unexpected patching error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Patching failed",
        ) from e

    finally:
        for cleanup_name in reversed(cleanup_names):
            try:
                with cast(
                    OwnedDelete,
                    open_owned_access(
                        temp_storage, StorageOperation.DELETE, cleanup_name
                    ),
                ) as delete_capability:
                    delete_capability.delete()
            except Exception:
                log.warning("Failed to remove an owned temporary patch artifact")
        try:
            with cast(
                OwnedDirectory,
                open_owned_access(temp_storage, StorageOperation.MKDIR, temp_dir),
            ) as directory:
                directory.rmdir()
        except Exception:
            log.warning("Failed to remove the owned temporary patch directory")

    output_size = len(output_content)
    log.info(
        f"Successfully patched ROM for user {hl(current_username, color=BLUE)}: "
        f"{hl(resolved_output_name)} ({output_size} bytes)"
    )
    if not validated:
        log.warning(
            f"Patch {hl(patch_display_name)} source checksum did not match "
            f"ROM {hl(rom_file.file_name)}; output may be incorrect"
        )

    return Response(
        content=output_content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(resolved_output_name)}; filename=\"{quote(resolved_output_name)}\"",
            "Content-Length": str(output_size),
            # Lets callers warn when the patch's source checksum didn't match the ROM.
            "X-Patch-Validated": "true" if validated else "false",
        },
    )


def _resolve_library_patch(
    patch_file_id: int, perms: ResolvedPermissions
) -> tuple[ReadCapability, str]:
    """Bind a library patch to an external read capability."""
    patch_file = db_rom_handler.get_rom_file_by_id(patch_file_id)
    if not patch_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch file with id {patch_file_id} not found",
        )
    # The patch file's bytes are read too; mask it if its rom is hidden.
    patch_rom_parent = db_rom_handler.get_rom(patch_file.rom_id)
    if not patch_rom_parent or not perms.can_see_rom(
        patch_rom_parent.id, patch_rom_parent.platform_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch file with id {patch_file_id} not found",
        )
    if patch_file.missing_from_fs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch file '{patch_file.file_name}' is missing from filesystem",
        )

    patch_ext = Path(patch_file.file_name).suffix.lower()
    if patch_ext not in SUPPORTED_PATCH_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported patch format '{patch_ext}'. Supported: {', '.join(sorted(SUPPORTED_PATCH_EXTENSIONS))}",
        )
    if patch_file.file_size_bytes > ROM_PATCHER_MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Patch file is too large to patch "
                f"({patch_file.file_size_bytes} bytes, max {ROM_PATCHER_MAX_FILE_SIZE_BYTES})"
            ),
        )

    return (
        cast(
            ReadCapability,
            open_storage_access(
                legacy_external_storage, StorageOperation.READ, patch_file.full_path
            ),
        ),
        patch_file.file_name,
    )


async def _stage_uploaded_patch(
    patch_file: UploadFile,
    temp_storage: OwnedStorageDescriptor,
    temp_dir: str,
) -> tuple[OwnedRead, str, str]:
    """Stage an uploaded patch into owned temporary storage.

    The upload is never stored in the library; it lives only in the temp dir,
    which the response's background task removes once streaming completes.
    """
    display_name = patch_file.filename or "uploaded-patch"
    patch_ext = Path(display_name).suffix.lower()
    if patch_ext not in SUPPORTED_PATCH_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported patch format '{patch_ext}'. Supported: {', '.join(sorted(SUPPORTED_PATCH_EXTENSIONS))}",
        )

    # Fixed on-disk name (never the client filename) avoids any path traversal.
    patch_name = f"{temp_dir}/uploaded_patch{patch_ext}"
    size = 0
    content = bytearray()
    while chunk := await patch_file.read(_UPLOAD_CHUNK_SIZE):
        size += len(chunk)
        if size > ROM_PATCHER_MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Patch file is too large to patch "
                    f"(max {ROM_PATCHER_MAX_FILE_SIZE_BYTES} bytes)"
                ),
            )
        content.extend(chunk)

    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded patch file is empty",
        )

    with cast(
        OwnedCreate,
        open_owned_access(temp_storage, StorageOperation.CREATE, patch_name),
    ) as create_capability:
        create_capability.create(bytes(content))
    return (
        cast(
            OwnedRead,
            open_owned_access(temp_storage, StorageOperation.READ, patch_name),
        ),
        display_name,
        patch_name,
    )
