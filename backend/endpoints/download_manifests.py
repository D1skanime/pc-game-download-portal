from typing import NoReturn

from fastapi import HTTPException, Request, status

from decorators.auth import protected_route
from endpoints.responses.download_manifest import (
    DownloadManifestComponentSchema,
    DownloadManifestCreateRequest,
    DownloadManifestMemberSchema,
    DownloadManifestResponse,
)
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_rom_visible
from handler.database import db_download_manifest_handler, db_rom_handler
from models.download_manifest import DownloadManifest, DownloadManifestStatus
from utils.router import APIRouter

router = APIRouter()

_NOT_FOUND = "Download manifest not found"
_STATE_ERRORS = {
    DownloadManifestStatus.EXPIRED: (status.HTTP_410_GONE, "manifest_expired"),
    DownloadManifestStatus.REVOKED: (status.HTTP_410_GONE, "manifest_revoked"),
    DownloadManifestStatus.SOURCE_CHANGED: (
        status.HTTP_409_CONFLICT,
        "manifest_source_changed",
    ),
}


def _not_found() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _serialize(manifest: DownloadManifest) -> DownloadManifestResponse:
    components = sorted(manifest.components, key=lambda item: item.component_id)
    members = sorted(
        (member for component in components for member in component.members),
        key=lambda member: member.id,
    )
    return DownloadManifestResponse(
        id=manifest.id,
        created_at=manifest.created_at,
        expires_at=manifest.expires_at,
        components=[
            DownloadManifestComponentSchema(
                component_id=component.component_id,
                kind=component.component.kind.value,
            )
            for component in components
        ],
        members=[
            DownloadManifestMemberSchema(
                file_id=member.id,
                destination=member.destination,
                size=member.size_bytes,
                sha256=member.sha256,
                snapshot=member.snapshot,
                download=f"/api/download-manifests/{manifest.id}/files/{member.id}",
            )
            for member in members
        ],
    )


def _valid_or_error(manifest: DownloadManifest | None) -> DownloadManifest:
    if manifest is None:
        _not_found()
    if manifest.status is not DownloadManifestStatus.VALID:
        status_code, code = _STATE_ERRORS[manifest.status]
        raise HTTPException(status_code=status_code, detail={"code": code})
    return manifest


@protected_route(
    router.post,
    "/roms/{rom_id}/download-manifests",
    [Scope.ROMS_READ],
    status_code=status.HTTP_201_CREATED,
)
async def create_download_manifest(
    request: Request, rom_id: int, payload: DownloadManifestCreateRequest
) -> DownloadManifestResponse:
    rom = db_rom_handler.get_rom(rom_id)
    if rom is None:
        _not_found()
    assert_rom_visible(request, rom, not_found_detail=_NOT_FOUND)
    try:
        manifest = db_download_manifest_handler.create_manifest(
            request.user.id, rom.id, payload.component_ids
        )
    except ValueError:
        _not_found()
    manifest = db_download_manifest_handler.get_manifest(manifest.id, request.user.id)
    return _serialize(_valid_or_error(manifest))


@protected_route(router.get, "/download-manifests/{manifest_id}", [Scope.ROMS_READ])
async def get_download_manifest(
    request: Request, manifest_id: str
) -> DownloadManifestResponse:
    manifest = db_download_manifest_handler.get_manifest(manifest_id, request.user.id)
    if manifest is None:
        _not_found()
    assert_rom_visible(request, manifest.rom, not_found_detail=_NOT_FOUND)
    return _serialize(_valid_or_error(manifest))
