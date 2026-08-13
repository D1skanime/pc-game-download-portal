from datetime import datetime, timezone
from typing import Annotated

from fastapi import Body, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from decorators.auth import protected_route
from endpoints.responses.assets import StateSchema
from endpoints.roms import refresh_affected_smart_collections
from endpoints.storage_policy import authorize_api_storage_operation
from exceptions.endpoint_exceptions import RomNotFoundInDatabaseException
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_platform_visible, assert_rom_visible
from handler.database import (
    db_platform_handler,
    db_rom_handler,
    db_screenshot_handler,
    db_state_handler,
)
from handler.filesystem import fs_asset_handler, storage_composition
from handler.filesystem.assets_handler import build_asset_file_response
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from handler.scan_handler import scan_screenshot, scan_state
from logger.formatter import BLUE
from logger.formatter import highlight as hl
from logger.logger import log
from models.assets import State
from models.platform import Platform
from utils.filesystem import sanitize_filename
from utils.router import APIRouter
from utils.uploads import check_asset_upload_size


def _resolve_state_platform(
    request: Request, state: State, *, not_found_detail: str
) -> Platform:
    """Resolve and authorize the platform that owns a live or retained state."""
    if state.rom is not None:
        assert_rom_visible(request, state.rom, not_found_detail=not_found_detail)
        return state.rom.platform

    retained_catalog = state.retained_catalog
    if retained_catalog is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="State has no live or retained catalog identity",
        )

    platform = db_platform_handler.get_platform(retained_catalog.platform_id)
    if platform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    assert_platform_visible(request, platform, not_found_detail=not_found_detail)
    return platform


router = APIRouter(
    prefix="/states",
    tags=["states"],
)

STATE_FILE_UPLOAD = File(..., description="State file to upload.")
STATE_SCREENSHOT_UPLOAD = File(
    default=None,
    description="Screenshot file associated with this state.",
)
STATE_FILE_UPDATE = File(default=None, description="Updated state file content.")
STATE_SCREENSHOT_UPDATE = File(default=None, description="Updated screenshot file.")


@protected_route(router.post, "", [Scope.ASSETS_WRITE])
async def add_state(
    request: Request,
    rom_id: int,
    emulator: str | None = None,
    stateFile: UploadFile = STATE_FILE_UPLOAD,
    screenshotFile: UploadFile | None = STATE_SCREENSHOT_UPLOAD,
) -> StateSchema:
    authorize_api_storage_operation(
        StorageOperation.WRITE, storage_composition.owned[OwnedStorageKind.ASSETS]
    )

    check_asset_upload_size(stateFile, "State file")
    check_asset_upload_size(screenshotFile, "Screenshot file")

    rom = db_rom_handler.get_rom(rom_id)
    if not rom:
        raise RomNotFoundInDatabaseException(rom_id)

    log.info(f"Uploading state of {rom.name}")

    states_path = fs_asset_handler.build_states_file_path(
        user=request.user,
        platform_fs_slug=rom.platform.fs_slug,
        rom_id=rom_id,
        emulator=emulator,
    )

    if not stateFile.filename:
        log.error("State file has no filename")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="State file has no filename"
        )

    try:
        sanitized_state_filename = sanitize_filename(stateFile.filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state filename: {str(exc)}",
        ) from exc

    rom = db_rom_handler.get_rom(rom_id)
    if not rom:
        raise RomNotFoundInDatabaseException(rom_id)

    log.info(
        f"Uploading state {hl(sanitized_state_filename)} for {hl(str(rom.name), color=BLUE)}"
    )

    states_path = fs_asset_handler.build_states_file_path(
        user=request.user,
        platform_fs_slug=rom.platform.fs_slug,
        rom_id=rom.id,
        emulator=emulator,
    )

    await fs_asset_handler.write_file(
        file=stateFile, path=states_path, filename=sanitized_state_filename
    )

    # Scan or update state
    scanned_state = await scan_state(
        file_name=sanitized_state_filename,
        user=request.user,
        platform_fs_slug=rom.platform.fs_slug,
        rom_id=rom_id,
        emulator=emulator,
    )
    db_state = db_state_handler.get_state_by_filename(
        user_id=request.user.id, rom_id=rom.id, file_name=sanitized_state_filename
    )
    if db_state:
        db_state = db_state_handler.update_state(
            db_state.id, {"file_size_bytes": scanned_state.file_size_bytes}
        )
    else:
        scanned_state.rom_id = rom.id
        scanned_state.user_id = request.user.id
        scanned_state.emulator = emulator
        db_state = db_state_handler.add_state(state=scanned_state)

    if screenshotFile and screenshotFile.filename:
        try:
            sanitized_screenshot_filename = sanitize_filename(screenshotFile.filename)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid screenshot filename: {str(exc)}",
            ) from exc

        screenshots_path = fs_asset_handler.build_screenshots_file_path(
            user=request.user, platform_fs_slug=rom.platform_slug, rom_id=rom.id
        )

        await fs_asset_handler.write_file(
            file=screenshotFile,
            path=screenshots_path,
            filename=sanitized_screenshot_filename,
        )

        # Scan or update screenshot
        scanned_screenshot = await scan_screenshot(
            file_name=sanitized_screenshot_filename,
            user=request.user,
            platform_fs_slug=rom.platform_slug,
            rom_id=rom.id,
        )
        db_screenshot = db_screenshot_handler.get_screenshot(
            file_name=sanitized_screenshot_filename,
            rom_id=rom.id,
            user_id=request.user.id,
        )
        if db_screenshot:
            db_screenshot = db_screenshot_handler.update_screenshot(
                db_screenshot.id,
                {"file_size_bytes": scanned_screenshot.file_size_bytes},
            )
        else:
            scanned_screenshot.rom_id = rom.id
            scanned_screenshot.user_id = request.user.id
            db_screenshot = db_screenshot_handler.add_screenshot(
                screenshot=scanned_screenshot
            )

    # Set the last played time for the current user
    rom_user = db_rom_handler.get_rom_user(rom_id=rom.id, user_id=request.user.id)
    if not rom_user:
        rom_user = db_rom_handler.add_rom_user(rom_id=rom.id, user_id=request.user.id)
    db_rom_handler.update_rom_user(
        rom_user.id, {"last_played": datetime.now(timezone.utc)}
    )

    # Refetch the rom to get updated states
    rom = db_rom_handler.get_rom(rom_id)
    if not rom:
        raise RomNotFoundInDatabaseException(rom_id)

    refresh_affected_smart_collections([rom.id], membership_only=True)

    return StateSchema.model_validate(db_state)


@protected_route(router.get, "", [Scope.ASSETS_READ])
def get_states(
    request: Request, rom_id: int | None = None, platform_id: int | None = None
) -> list[StateSchema]:
    states = db_state_handler.get_states(
        user_id=request.user.id, rom_id=rom_id, platform_id=platform_id
    )

    return [StateSchema.model_validate(state) for state in states]


@protected_route(router.get, "/identifiers", [Scope.ASSETS_READ])
def get_state_identifiers(
    request: Request,
) -> list[int]:
    """Get state identifiers endpoint

    Args:
        request (Request): Fastapi Request object

    Returns:
        list[int]: List of state IDs
    """
    states = db_state_handler.get_states(
        user_id=request.user.id,
        only_fields=[State.id],
    )

    return [state.id for state in states]


@protected_route(router.get, "/{id}", [Scope.ASSETS_READ])
def get_state(request: Request, id: int) -> StateSchema:
    state = db_state_handler.get_state(user_id=request.user.id, id=id)

    if not state:
        error = f"State with ID {id} not found"
        log.error(error)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    _resolve_state_platform(
        request, state, not_found_detail=f"State with ID {id} not found"
    )
    return StateSchema.model_validate(state)


@protected_route(router.get, "/{id}/content", [Scope.ASSETS_READ])
def download_state(request: Request, id: int) -> FileResponse:
    """Download a state file. Owner can download any of their states; everyone
    else only public ones."""
    state = db_state_handler.get_state_by_id(id)
    if not state or (state.user_id != request.user.id and not state.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State with ID {id} not found",
        )

    # Sharing must not override hidden live-ROM or retained-platform policy.
    _resolve_state_platform(
        request, state, not_found_detail=f"State with ID {id} not found"
    )

    try:
        file_path = fs_asset_handler.validate_path(state.full_path)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="State file not found",
        ) from None

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="State file not found on disk",
        )

    return build_asset_file_response(file_path, filename=state.file_name)


@protected_route(router.put, "/{id}", [Scope.ASSETS_WRITE])
async def update_state(
    request: Request,
    id: int,
    stateFile: UploadFile | None = STATE_FILE_UPDATE,
    screenshotFile: UploadFile | None = STATE_SCREENSHOT_UPDATE,
) -> StateSchema:
    authorize_api_storage_operation(
        StorageOperation.OVERWRITE, storage_composition.owned[OwnedStorageKind.ASSETS]
    )

    check_asset_upload_size(stateFile, "State file")
    check_asset_upload_size(screenshotFile, "Screenshot file")

    db_state = db_state_handler.get_state(user_id=request.user.id, id=id)
    if not db_state:
        error = f"State with ID {id} not found"
        log.error(error)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    _resolve_state_platform(
        request, db_state, not_found_detail=f"State with ID {id} not found"
    )
    if db_state.rom is None and screenshotFile is not None and screenshotFile.filename:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A detached state cannot update a ROM-owned screenshot",
        )

    if stateFile:
        await fs_asset_handler.write_file(
            file=stateFile, path=db_state.file_path, filename=db_state.file_name
        )
        db_state = db_state_handler.update_state(
            db_state.id, {"file_size_bytes": stateFile.size}
        )
    if screenshotFile and screenshotFile.filename:
        try:
            sanitized_screenshot_filename = sanitize_filename(screenshotFile.filename)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid screenshot filename: {str(exc)}",
            ) from exc

        screenshots_path = fs_asset_handler.build_screenshots_file_path(
            user=request.user,
            platform_fs_slug=db_state.rom.platform_slug,
            rom_id=db_state.rom.id,
        )

        await fs_asset_handler.write_file(
            file=screenshotFile,
            path=screenshots_path,
            filename=sanitized_screenshot_filename,
        )

        # Scan or update screenshot
        scanned_screenshot = await scan_screenshot(
            file_name=sanitized_screenshot_filename,
            user=request.user,
            platform_fs_slug=db_state.rom.platform_slug,
            rom_id=db_state.rom.id,
        )
        db_screenshot = db_screenshot_handler.get_screenshot(
            file_name=sanitized_screenshot_filename,
            rom_id=db_state.rom.id,
            user_id=request.user.id,
        )
        if db_screenshot:
            db_screenshot = db_screenshot_handler.update_screenshot(
                db_screenshot.id,
                {"file_size_bytes": scanned_screenshot.file_size_bytes},
            )
        else:
            scanned_screenshot.rom_id = db_state.rom.id
            scanned_screenshot.user_id = request.user.id
            db_screenshot = db_screenshot_handler.add_screenshot(
                screenshot=scanned_screenshot
            )

    # Detached states have no live RomUser row to update.
    if db_state.rom_id is not None:
        rom_user = db_rom_handler.get_rom_user(db_state.rom_id, request.user.id)
        if not rom_user:
            rom_user = db_rom_handler.add_rom_user(db_state.rom_id, request.user.id)
        db_rom_handler.update_rom_user(
            rom_user.id, {"last_played": datetime.now(timezone.utc)}
        )

    # Refetch the state to get updated fields
    return StateSchema.model_validate(db_state)


@protected_route(
    router.put,
    "/{id}/visibility",
    [Scope.ASSETS_WRITE],
    responses={status.HTTP_404_NOT_FOUND: {}},
)
def update_state_visibility(
    request: Request,
    id: int,
    is_public: Annotated[bool, Body(embed=True)],
) -> StateSchema:
    """Toggle a state's public/private visibility (owner only)."""
    state = db_state_handler.get_state_by_id(id)
    if not state or state.user_id != request.user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State with ID {id} not found",
        )

    _resolve_state_platform(
        request, state, not_found_detail=f"State with ID {id} not found"
    )
    updated = db_state_handler.update_state(id, {"is_public": is_public})

    # Keep the auto-captured thumbnail's visibility in sync so a shared state
    # still renders its preview for other users.
    if state.screenshot:
        db_screenshot_handler.update_screenshot(
            state.screenshot.id, {"is_public": is_public}
        )

    # Sharing a state exposes it to every other user's `has_states` filter.
    if state.rom_id is not None:
        refresh_affected_smart_collections([state.rom_id], membership_only=True)

    return StateSchema.model_validate(updated)


@protected_route(
    router.post,
    "/delete",
    [Scope.ASSETS_WRITE],
    responses={
        status.HTTP_400_BAD_REQUEST: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
async def delete_states(
    request: Request,
    states: Annotated[
        list[int],
        Body(
            description="List of states ids to delete from database.",
            embed=True,
        ),
    ],
) -> list[int]:
    authorize_api_storage_operation(
        StorageOperation.DELETE, storage_composition.owned[OwnedStorageKind.ASSETS]
    )

    """Delete states."""
    if not states:
        error = "No states were provided"
        log.error(error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    affected_rom_ids: set[int] = set()

    for state_id in states:
        state = db_state_handler.get_state(user_id=request.user.id, id=state_id)
        if not state:
            error = f"State with ID {state_id} not found"
            log.error(error)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

        platform = _resolve_state_platform(
            request,
            state,
            not_found_detail=f"State with ID {state_id} not found",
        )
        if state.rom_id is not None:
            affected_rom_ids.add(state.rom_id)
        db_state_handler.delete_state(state_id)
        log.info(
            f"Deleting state {hl(state.file_name)} [{platform.fs_slug}] from filesystem"
        )

        try:
            file_path = f"{state.file_path}/{state.file_name}"
            await fs_asset_handler.remove_file(file_path=file_path)
        except FileNotFoundError:
            error = f"State file {hl(state.file_name)} not found for platform {hl(platform.name, color=BLUE)}[{hl(platform.fs_slug)}]"
            log.error(error)

        if state.screenshot:
            db_screenshot_handler.delete_screenshot(state.screenshot.id)

            try:
                file_path = f"{state.screenshot.file_path}/{state.screenshot.file_name}"
                await fs_asset_handler.remove_file(file_path=file_path)
            except FileNotFoundError:
                error = f"Screenshot file {hl(state.screenshot.file_name)} not found for state {hl(state.file_name)}[{hl(platform.fs_slug)}]"
                log.error(error)

    if affected_rom_ids:
        refresh_affected_smart_collections(list(affected_rom_ids), membership_only=True)

    return states
