"""Safely reconcile complete Steam scan media into owned storage."""

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import status

from handler.database import db_rom_handler
from handler.database.roms_handler import SteamOwnedMediaInventoryItem
from handler.filesystem import fs_resource_handler
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


async def reconcile_steam_patch_media(rom, patch: Mapping[str, Any]) -> bool:
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
    try:
        active = db_rom_handler.get_steam_owned_media_inventory(rom.id, identities)
        inventory: list[SteamOwnedMediaInventoryItem] = []
        for candidate in candidates:
            mime_type: str | None
            owned_path = _reusable_owned_path(
                active.get(candidate.provider_media_id), candidate
            )
            if owned_path is None:
                owned_path, mime_type = await _download_candidate(rom, candidate)
                written_paths.append(owned_path)
            else:
                stored_mime_type = getattr(
                    active[candidate.provider_media_id], "mime_type", None
                )
                if not isinstance(stored_mime_type, str) or not stored_mime_type:
                    raise ValueError("Stored Steam media has no MIME type")
                mime_type = stored_mime_type
            if mime_type is None:
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

        reconciled = db_rom_handler.reconcile_steam_owned_media_inventory(
            rom.id, rom.updated_at, inventory
        )
        if reconciled is None:
            raise ValueError("Steam media catalog changed")
    except Exception:
        await _remove_uncommitted_paths(written_paths)
        return False

    for path in reconciled.unreferenced_owned_paths:
        try:
            db_rom_handler.create_owned_media_cleanup_intent(rom.id, 0, path)
        except Exception:
            log.warning("Unable to queue Steam media cleanup", extra={"path": path})
    return True
