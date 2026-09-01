"""Review-first endpoints for selecting PC metadata candidates."""

from typing import Annotated

from fastapi import HTTPException, Path, Request, Response, status

from decorators.auth import protected_route
from endpoints.responses.rom import (
    PcComponentLocalMediaSchema,
    PcComponentMetadataSelectionResponse,
    PcLocalMediaCandidateSchema,
    PcLocalMediaCandidatesResponse,
    PcLocalMediaSelectionRequest,
    PcLocalMediaSelectionResponse,
    PcMetadataCandidateSchema,
    PcMetadataCandidatesResponse,
    PcMetadataProviderResultSchema,
    PcMetadataSelectionRequest,
    PcMetadataSelectionResponse,
)
from exceptions.endpoint_exceptions import RomNotFoundInDatabaseException
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_rom_visible
from handler.database import db_rom_handler
from handler.filesystem import fs_resource_handler, fs_rom_handler
from handler.metadata.pc_match_handler import (
    PcMetadataCandidate,
    pc_metadata_match_handler,
)
from models.rom import RomComponentKind
from utils.router import APIRouter

router = APIRouter()


def _dlc_component(rom_id: int, component_id: int):
    rom = db_rom_handler.get_rom(rom_id)
    if not rom:
        raise RomNotFoundInDatabaseException(rom_id)
    component = next((item for item in rom.components if item.id == component_id), None)
    if component is None or component.kind != RomComponentKind.DLC:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return rom, component


@protected_route(
    router.get,
    "/{id}/pc-components/{component_id}/metadata-candidates",
    [Scope.ROMS_READ],
)
async def get_pc_component_metadata_candidates(
    request: Request,
    id: Annotated[int, Path(description="Rom internal id.", ge=1)],
    component_id: Annotated[int, Path(ge=1)],
) -> PcMetadataCandidatesResponse:
    rom, component = _dlc_component(id, component_id)
    assert_rom_visible(request, rom)
    results = await pc_metadata_match_handler.collect_component_candidates(
        rom, component
    )
    return PcMetadataCandidatesResponse(
        expected_version=component.updated_at,
        providers={
            name: PcMetadataProviderResultSchema(
                provider=result.provider,
                available=result.available,
                candidates=[
                    _candidate_schema(candidate) for candidate in result.candidates
                ],
                reason=result.reason,
            )
            for name, result in results.items()
        },
    )


@protected_route(
    router.post,
    "/{id}/pc-components/{component_id}/metadata-selection",
    [Scope.ROMS_WRITE],
)
async def select_pc_component_metadata_candidate(
    request: Request,
    id: Annotated[int, Path(description="Rom internal id.", ge=1)],
    component_id: Annotated[int, Path(ge=1)],
    selection: PcMetadataSelectionRequest,
) -> PcComponentMetadataSelectionResponse:
    rom, component = _dlc_component(id, component_id)
    assert_rom_visible(request, rom)
    results = await pc_metadata_match_handler.collect_component_candidates(
        rom, component
    )
    candidate = next(
        (
            item
            for result in results.values()
            if result.available
            for item in result.candidates
            if item.id == selection.candidate_id
        ),
        None,
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown or unavailable PC component metadata candidate",
        )
    updated = db_rom_handler.apply_pc_component_metadata_candidate(
        id,
        component_id,
        selection.expected_version,
        candidate.provider,
        candidate.fields,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The PC component metadata changed before this selection was applied",
        )
    return PcComponentMetadataSelectionResponse(
        candidate_id=candidate.id,
        component_id=component_id,
        expected_version=updated.updated_at,
    )


@protected_route(router.get, "/{id}/pc-local-media-candidates", [Scope.ROMS_READ])
async def get_pc_local_media_candidates(
    request: Request,
    id: Annotated[int, Path(description="Rom internal id.", ge=1)],
) -> PcLocalMediaCandidatesResponse:
    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)
    assert_rom_visible(request, rom)

    candidates = [
        PcLocalMediaCandidateSchema(
            component_id=component.id,
            member_id=member.id,
            relative_path=member.relative_path,
            source_sha256=member.sha256,
            image_type=member.relative_path.rsplit(".", 1)[-1].lower(),
            preview_url=(
                f"/api/roms/{id}/pc-local-media-preview/{component.id}/{member.id}"
            ),
        )
        for component in rom.components
        if component.kind in {RomComponentKind.DLC, RomComponentKind.EXTRA}
        for member in component.manifest_members
        if fs_rom_handler.is_pc_component_image(member)
    ]
    return PcLocalMediaCandidatesResponse(
        expected_version=rom.updated_at, candidates=candidates
    )


@protected_route(
    router.get,
    "/{id}/pc-local-media-preview/{component_id}/{member_id}",
    [Scope.ROMS_READ],
)
async def preview_pc_local_media(
    request: Request,
    id: Annotated[int, Path(description="Rom internal id.", ge=1)],
    component_id: Annotated[int, Path(ge=1)],
    member_id: Annotated[int, Path(ge=1)],
) -> Response:
    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)
    assert_rom_visible(request, rom)
    component = next((item for item in rom.components if item.id == component_id), None)
    member = (
        next(
            (item for item in component.manifest_members if item.id == member_id), None
        )
        if component
        else None
    )
    if (
        component is None
        or component.kind
        not in {
            RomComponentKind.DLC,
            RomComponentKind.EXTRA,
        }
        or member is None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        content, image_type = fs_rom_handler.read_pc_component_image(rom, member)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return Response(content=content, media_type=f"image/{image_type}")


@protected_route(router.post, "/{id}/pc-local-media-selection", [Scope.ROMS_WRITE])
async def select_pc_local_media(
    request: Request,
    id: Annotated[int, Path(description="Rom internal id.", ge=1)],
    selection: PcLocalMediaSelectionRequest,
) -> PcLocalMediaSelectionResponse:
    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)
    assert_rom_visible(request, rom)

    component = next(
        (item for item in rom.components if item.id == selection.component_id), None
    )
    member = (
        next(
            (
                item
                for item in component.manifest_members
                if item.id == selection.member_id
            ),
            None,
        )
        if component
        else None
    )
    if (
        component is None
        or component.kind
        not in {
            RomComponentKind.DLC,
            RomComponentKind.EXTRA,
        }
        or member is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown PC local media selection",
        )

    try:
        content, image_type = fs_rom_handler.read_pc_component_image(rom, member)
        owned_path, cover_small_path, _ = (
            await fs_resource_handler.store_pc_component_image(
                rom,
                component.id,
                member.id,
                selection.role,
                content,
                image_type,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    applied = db_rom_handler.apply_pc_local_media(
        id,
        selection.expected_version,
        component.id,
        member.id,
        selection.role,
        owned_path,
        image_type,
        member.sha256,
        cover_small_path,
    )
    if applied is None:
        await fs_resource_handler.remove_file(owned_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The ROM metadata changed before this selection was applied",
        )
    for replaced_path in applied.replaced_owned_paths:
        await fs_resource_handler.remove_file(replaced_path)
    return PcLocalMediaSelectionResponse(
        expected_version=applied.rom.updated_at,
        media=PcComponentLocalMediaSchema.model_validate(applied.media),
    )


def _candidate_schema(candidate: PcMetadataCandidate) -> PcMetadataCandidateSchema:
    return PcMetadataCandidateSchema(
        id=candidate.id,
        provider=candidate.provider,
        title=candidate.title,
        provider_ids=candidate.provider_ids,
        description_available=candidate.description_available,
        media=candidate.media,
    )


@protected_route(router.get, "/{id}/pc-metadata-candidates", [Scope.ROMS_READ])
async def get_pc_metadata_candidates(
    request: Request,
    id: Annotated[int, Path(description="Rom internal id.", ge=1)],
) -> PcMetadataCandidatesResponse:
    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)
    assert_rom_visible(request, rom)

    results = await pc_metadata_match_handler.collect_candidates(rom)
    return PcMetadataCandidatesResponse(
        expected_version=rom.updated_at,
        providers={
            name: PcMetadataProviderResultSchema(
                provider=result.provider,
                available=result.available,
                candidates=[
                    _candidate_schema(candidate) for candidate in result.candidates
                ],
                reason=result.reason,
            )
            for name, result in results.items()
        },
    )


@protected_route(router.post, "/{id}/pc-metadata-selection", [Scope.ROMS_WRITE])
async def select_pc_metadata_candidate(
    request: Request,
    id: Annotated[int, Path(description="Rom internal id.", ge=1)],
    selection: PcMetadataSelectionRequest,
) -> PcMetadataSelectionResponse:
    rom = db_rom_handler.get_rom(id)
    if not rom:
        raise RomNotFoundInDatabaseException(id)
    assert_rom_visible(request, rom)

    results = await pc_metadata_match_handler.collect_candidates(rom)
    candidate = next(
        (
            item
            for result in results.values()
            if result.available
            for item in result.candidates
            if item.id == selection.candidate_id
        ),
        None,
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown or unavailable PC metadata candidate",
        )

    updated = db_rom_handler.apply_pc_metadata_candidate(
        id, selection.expected_version, candidate.fields
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The ROM metadata changed before this selection was applied",
        )
    return PcMetadataSelectionResponse(
        candidate_id=candidate.id, expected_version=updated.updated_at
    )
