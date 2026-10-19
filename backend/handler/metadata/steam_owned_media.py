"""Safely reconcile complete Steam scan media into owned storage."""

import logging
from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from typing import Any

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError

from handler.database import db_rom_handler
from handler.database.roms_handler import SteamOwnedMediaInventoryItem
from handler.database.scan_write_fence import (
    ScanWriteRejected,
    current_scan_write_context,
)
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import ScanMediaBatch
from handler.filesystem.storage_access import IndeterminateOwnedPublicationError
from handler.metadata.rom_media import ProviderMediaCandidate, discover_provider_media
from models.rom import RomOwnedMediaState
from utils.context import ctx_httpx_client

_IMAGE_LIMIT = 10 * 1024 * 1024
log = logging.getLogger(__name__)


def _steam_media_source(patch: Mapping[str, Any]) -> dict[str, object] | None:
    """Translate a normalized Steam patch into a complete provider inventory."""
    media = patch.get("media")
    if not isinstance(media, Mapping):
        return None
    cover = media.get("cover")
    screenshots = media.get("screenshots")
    if not isinstance(cover, list) or not isinstance(screenshots, list):
        return None
    return {"url_artworks": cover, "url_screenshots": screenshots}


async def _download_candidate(
    rom, candidate: ProviderMediaCandidate
) -> tuple[str, str]:
    """Download bounded provider bytes before publishing them to owned storage."""
    client = ctx_httpx_client.get()
    async with client.stream("GET", candidate.url, timeout=30) as response:
        if response.status_code != status.HTTP_200_OK:
            raise ValueError("Steam media could not be downloaded")
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > _IMAGE_LIMIT:
                raise ValueError("Steam media exceeds the 10 MiB limit")
            chunks.append(chunk)
    return await fs_resource_handler.store_owned_media_image(
        rom, candidate.role, b"".join(chunks)
    )


async def _remove_uncommitted_paths(paths: Sequence[str]) -> None:
    """Best-effort cleanup for owned paths published by an unsuccessful attempt."""
    for path in paths:
        try:
            await fs_resource_handler.remove_file(path)
        except (OSError, ValueError):
            log.warning(
                "Unable to remove uncommitted Steam media", extra={"path": path}
            )


def _reusable_owned_path(
    media: object, candidate: ProviderMediaCandidate
) -> str | None:
    """Return a prior active matching path without changing catalog state."""
    if (
        getattr(media, "state", None) != RomOwnedMediaState.ACTIVE
        or getattr(media, "role", None) != candidate.role
    ):
        return None
    path = getattr(media, "owned_path", None)
    return path if isinstance(path, str) and path else None


async def reconcile_steam_patch_media(
    rom, patch: Mapping[str, Any], *, force: bool = False
) -> bool:
    """Persist a successful complete Steam media patch without scan-side mutations.

    Missing or invalid media is intentionally a no-op. Only an explicit complete
    inventory, including an explicitly empty one, reaches the batch repository
    operation that may tombstone stale Steam candidates.
    """
    source = _steam_media_source(patch)
    if source is None:
        return False

    try:
        candidates = discover_provider_media("steam", source)
    except ValueError:
        return False
    identities = [candidate.provider_media_id for candidate in candidates]
    if len(identities) != len(set(identities)):
        return False

    written_paths: list[str] = []
    unit = None
    association_started = False
    try:
        scope = (
            ScanMediaBatch(rom.id, rom.platform_id, fs_resource_handler.storage)
            if current_scan_write_context() is not None
            else nullcontext()
        )
        with scope as unit:
            active = db_rom_handler.get_steam_owned_media_inventory(rom.id, identities)
            inventory: list[SteamOwnedMediaInventoryItem] = []
            for candidate in candidates:
                mime_type: str | None
                owned_path = (
                    None
                    if force
                    else _reusable_owned_path(
                        active.get(candidate.provider_media_id), candidate
                    )
                )
                if owned_path is None:
                    owned_path, mime_type = await _download_candidate(rom, candidate)
                    written_paths.append(owned_path)
                else:
                    mime_type = getattr(
                        active[candidate.provider_media_id], "mime_type", None
                    )
                if not isinstance(mime_type, str) or not mime_type:
                    raise ValueError("Steam media has no MIME type")
                inventory.append(
                    SteamOwnedMediaInventoryItem(
                        candidate.provider_media_id,
                        candidate.role,
                        candidate.display_label,
                        mime_type,
                        owned_path,
                    )
                )

            def reconcile(session):
                nonlocal association_started
                association_started = True
                options = {"session": session} if session is not None else {}
                result = db_rom_handler.reconcile_steam_owned_media_inventory(
                    rom.id, rom.updated_at, inventory, **options
                )
                if result is None:
                    association_started = False
                    raise ValueError("Steam media catalog changed")
                for path in result.unreferenced_owned_paths:
                    db_rom_handler.create_owned_media_cleanup_intent(
                        rom.id, 0, path, **options
                    )
                return result

            if unit:
                unit.publish_and_associate(reconcile)
            else:
                reconcile(None)
    except (ScanWriteRejected, IndeterminateOwnedPublicationError, SQLAlchemyError):
        if current_scan_write_context() is not None:
            raise
        if not association_started:
            await _remove_uncommitted_paths(written_paths)
        return False
    except Exception:
        if unit is None and not association_started:
            await _remove_uncommitted_paths(written_paths)
        if unit is not None and unit.publication_started:
            raise
        return False
    return True
