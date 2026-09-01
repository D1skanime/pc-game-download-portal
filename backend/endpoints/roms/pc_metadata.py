"""Review-first endpoints for selecting PC metadata candidates."""

from typing import Annotated

from fastapi import HTTPException, Path, Request, status

from decorators.auth import protected_route
from endpoints.responses.rom import (
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
from handler.metadata.pc_match_handler import (
    PcMetadataCandidate,
    pc_metadata_match_handler,
)
from utils.router import APIRouter

router = APIRouter()


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
