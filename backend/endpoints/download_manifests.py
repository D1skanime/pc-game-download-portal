from collections.abc import Iterator
from typing import NoReturn
from urllib.parse import quote

from fastapi import HTTPException, Request, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

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
from handler.filesystem import fs_rom_handler
from handler.filesystem.roms_handler import DownloadManifestTransferState
from models.download_manifest import DownloadManifest, DownloadManifestStatus
from utils.router import APIRouter

router = APIRouter()

_NOT_FOUND = "Download manifest not found"
_MAX_U64 = 2**64 - 1
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
                file_id=member.public_id,
                destination=member.destination,
                size=member.size_bytes,
                sha256=member.sha256,
                snapshot=member.snapshot,
                download=(
                    f"/api/download-manifests/{manifest.id}/files/{member.public_id}"
                ),
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


def _precondition_failed() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_412_PRECONDITION_FAILED,
        detail={"code": "snapshot_mismatch"},
    )


def _range_not_satisfiable(size: int) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
        headers={"Content-Range": f"bytes */{size}"},
    )


def _parse_u64(value: str) -> int:
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError
    parsed = int(value)
    if parsed > _MAX_U64:
        raise ValueError
    return parsed


def _transfer_range_bounds(value: str | None, size: int) -> tuple[int, int] | None:
    if value is None:
        return None
    if size < 0 or size > _MAX_U64 or not value.startswith("bytes="):
        _range_not_satisfiable(size)
    range_spec = value[6:]
    if "," in range_spec:
        _range_not_satisfiable(size)
    start_text, separator, end_text = range_spec.partition("-")
    if not separator or size == 0:
        _range_not_satisfiable(size)
    try:
        if start_text:
            start = _parse_u64(start_text)
            end = _parse_u64(end_text) if end_text else size - 1
        else:
            suffix = _parse_u64(end_text)
            if suffix == 0:
                raise ValueError
            start = max(size - suffix, 0)
            end = size - 1
    except ValueError:
        _range_not_satisfiable(size)
    if start >= size or end < start:
        _range_not_satisfiable(size)
    return start, min(end, size - 1)


def _attachment_disposition(destination: str) -> str:
    filename = destination.rsplit("/", maxsplit=1)[-1]
    if not filename or any(ord(character) < 32 for character in filename):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Download manifest source is unavailable",
        )
    fallback = filename.encode("ascii", errors="ignore").decode("ascii") or "download"
    fallback = fallback.replace("\\", "\\\\").replace('"', '\\"')
    return (
        f'attachment; filename="{fallback}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


def _lease_chunks(lease, start: int, length: int) -> Iterator[bytes]:
    try:
        yield from lease.iter_chunks(start, length)
    finally:
        lease.close()


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


@protected_route(
    router.get,
    "/download-manifests/{manifest_id}/files/{public_id}",
    [Scope.ROMS_READ],
    responses={status.HTTP_404_NOT_FOUND: {}},
)
async def get_download_manifest_member(
    request: Request, manifest_id: str, public_id: str
) -> StreamingResponse:
    """Stream one verified immutable manifest member without archive packaging."""
    persisted_member = db_download_manifest_handler.get_transfer_manifest_member(
        manifest_id, request.user.id, public_id
    )
    if persisted_member is None:
        _not_found()

    manifest = persisted_member.component.manifest
    assert_rom_visible(request, manifest.rom, not_found_detail=_NOT_FOUND)
    _valid_or_error(manifest)

    range_header = request.headers.get("range")
    if_match = request.headers.get("if-match")
    if if_match is not None and if_match != persisted_member.snapshot:
        _precondition_failed()
    if range_header is not None and if_match is None:
        _precondition_failed()
    bounds = _transfer_range_bounds(range_header, persisted_member.size_bytes)

    result = await fs_rom_handler.open_verified_download_manifest_member(
        manifest.rom, persisted_member
    )
    if result.state is not DownloadManifestTransferState.READY or result.lease is None:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={"code": "source_changed"},
        )

    lease = result.lease
    if (
        lease.size_bytes != persisted_member.size_bytes
        or lease.snapshot != persisted_member.snapshot
    ):
        lease.close()
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={"code": "source_changed"},
        )

    start, end = bounds if bounds is not None else (0, max(lease.size_bytes - 1, 0))
    content_length = end - start + 1 if lease.size_bytes else 0
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": _attachment_disposition(persisted_member.destination),
    }
    response_status = status.HTTP_200_OK
    if bounds is not None:
        response_status = status.HTTP_206_PARTIAL_CONTENT
        headers["Content-Range"] = f"bytes {start}-{end}/{lease.size_bytes}"

    return StreamingResponse(
        _lease_chunks(lease, start, content_length),
        status_code=response_status,
        media_type="application/octet-stream",
        headers=headers,
        background=BackgroundTask(lease.close),
    )
