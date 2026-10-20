"""Explicit provider-media discovery for the parent owned-media catalog.

This module deliberately consumes persisted provider media only.  It never
starts a scan and it never grants filesystem authority.
"""

from contextlib import nullcontext
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import status

from handler.database import db_rom_handler
from handler.database.scan_write_fence import current_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import ScanMediaBatch
from models.rom import RomOwnedMediaRole, derive_owned_media_display_label
from utils.context import ctx_httpx_client

_MAX_PROVIDER_MEDIA = 500
_IMAGE_LIMIT = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ProviderMediaCandidate:
    provider: str
    provider_media_id: str
    role: RomOwnedMediaRole
    url: str
    display_label: str


@dataclass(frozen=True, slots=True)
class ProviderMediaFailure:
    """A single media item that could not be persisted during a refresh."""

    provider_media_id: str
    role: RomOwnedMediaRole
    reason: str


def normalize_provider_url(value: str) -> str:
    """Normalize an HTTPS URL to the stable identity used for refreshes."""
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.netloc or parsed.username:
        raise ValueError("Provider media must use HTTPS")
    path = parsed.path or "/"
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    return urlunsplit(("https", parsed.netloc.lower(), path, query, ""))


def _candidate(
    provider: str, value: object, role: RomOwnedMediaRole
) -> ProviderMediaCandidate:
    if isinstance(value, dict):
        raw_url = value.get("url")
        native_id = value.get("id")
    else:
        raw_url = value
        native_id = None
    if not isinstance(raw_url, str):
        raise ValueError("Provider media URL is invalid")
    url = normalize_provider_url(raw_url)
    identity = (
        str(native_id)
        if native_id not in (None, "")
        else f"url-sha256:{sha256(url.encode()).hexdigest()}"
    )
    label = derive_owned_media_display_label(
        PurePosixPath(urlsplit(url).path).name or "provider-media"
    )
    return ProviderMediaCandidate(provider, identity[:450], role, url, label)


def discover_provider_media(
    provider: str, media: dict[str, object]
) -> list[ProviderMediaCandidate]:
    """Return the complete persisted screenshot/artwork inventory for refresh."""
    if not provider or len(provider) > 100:
        raise ValueError("Provider is invalid")
    candidates: list[ProviderMediaCandidate] = []
    for key, role in (
        ("url_screenshots", RomOwnedMediaRole.SCREENSHOT),
        ("url_artworks", RomOwnedMediaRole.ARTWORK),
    ):
        values = media.get(key, [])
        if not isinstance(values, list) or len(values) > _MAX_PROVIDER_MEDIA:
            raise ValueError("Provider media list is invalid or exceeds the limit")
        candidates.extend(_candidate(provider, value, role) for value in values)
    return candidates


async def _download_provider_image(
    rom, candidate: ProviderMediaCandidate
) -> tuple[str, str]:
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


async def refresh_provider_owned_media(
    rom, expected_version, provider: str, *, restore_suppressed: bool = False
):
    """Refresh selected provider images within their publication transaction."""
    if not isinstance(provider, str) or not provider:
        raise ValueError("Provider is required")
    source = {
        "url_screenshots": rom.url_screenshots or [],
        "url_artworks": [rom.url_cover] if rom.url_cover else [],
    }
    failures: list[ProviderMediaFailure] = []
    for candidate in discover_provider_media(provider, source):
        path = None
        unit = None
        try:
            scope = (
                ScanMediaBatch(rom.id, rom.platform_id, fs_resource_handler.storage)
                if current_scan_write_context() is not None
                else nullcontext()
            )
            with scope as unit:
                path, mime_type = await _download_provider_image(rom, candidate)

                def reconcile(
                    session,
                    rom=rom,
                    expected_version=expected_version,
                    candidate=candidate,
                    mime_type=mime_type,
                    path=path,
                ):
                    kwargs = {"restore_suppressed": True} if restore_suppressed else {}
                    kwargs.update({"session": session} if session is not None else {})
                    applied = db_rom_handler.reconcile_provider_owned_media(
                        rom.id,
                        expected_version,
                        candidate.provider,
                        candidate.provider_media_id,
                        candidate.role,
                        candidate.display_label,
                        mime_type,
                        path,
                        **kwargs,
                    )
                    if applied is None:
                        raise ValueError("Media catalog changed")
                    return applied

                applied = (
                    unit.publish_and_associate(reconcile) if unit else reconcile(None)
                )
                expected_version = applied.rom.updated_at
                rom = applied.rom
        except (ValueError, OSError) as exc:
            if path is not None and unit is None:
                await fs_resource_handler.remove_file(path)
            failures.append(
                ProviderMediaFailure(
                    candidate.provider_media_id, candidate.role, str(exc)
                )
            )
    return rom, failures
