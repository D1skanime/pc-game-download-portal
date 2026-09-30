"""Backfill legacy RomM-owned media into the parent media catalog.

Revision ID: 0129_backfill_legacy_rom_owned_media
Revises: 0128_owned_media_role_and_display_label
"""

import hashlib
import json
import posixpath
from collections.abc import Iterable
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0129_backfill_legacy_rom_owned_media"
down_revision = "0128_owned_media_role_and_display_label"
branch_labels = None
depends_on = None

_LEGACY_PROVIDER = "romm-legacy-owned-v1"
_IMAGE_MIME_TYPES = {
    ".avif": "image/avif",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _owned_image_path(value: object) -> bool:
    """Accept only bounded, relative RomM resource image identifiers."""
    if not isinstance(value, str) or not value or len(value) > 700:
        return False
    if "\\" in value or any(ord(char) < 32 for char in value):
        return False
    if not value.startswith("roms/") or value.startswith("/"):
        return False
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return posixpath.splitext(value)[1].lower() in _IMAGE_MIME_TYPES


def _legacy_identity(role: str, owned_path: str) -> str:
    digest = hashlib.sha256(
        f"romm-owned-media-legacy-v1\\0{role}\\0{owned_path}".encode()
    ).hexdigest()
    return f"legacy-{digest}"


def _display_label(owned_path: str) -> str:
    return posixpath.basename(owned_path)[:255]


def _screenshot_paths(value: object) -> Iterable[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return ()
    if not isinstance(value, list):
        return ()
    return (path for path in value if _owned_image_path(path))


def _legacy_rows(
    rom_id: int, screenshots: object, path_cover_s: object, path_cover_l: object
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for position, owned_path in enumerate(_screenshot_paths(screenshots)):
        key = ("screenshot", owned_path)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "rom_id": rom_id,
                "role": "screenshot",
                "owned_path": owned_path,
                "provider_media_id": _legacy_identity("screenshot", owned_path),
                "display_label": _display_label(owned_path),
                "mime_type": _IMAGE_MIME_TYPES[
                    posixpath.splitext(owned_path)[1].lower()
                ],
                "overview_position": position,
            }
        )
    for owned_path in (path_cover_s, path_cover_l):
        if not _owned_image_path(owned_path):
            continue
        key = ("artwork", owned_path)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "rom_id": rom_id,
                "role": "artwork",
                "owned_path": owned_path,
                "provider_media_id": _legacy_identity("artwork", owned_path),
                "display_label": _display_label(owned_path),
                "mime_type": _IMAGE_MIME_TYPES[
                    posixpath.splitext(owned_path)[1].lower()
                ],
                "overview_position": None,
            }
        )
    return rows


def _table(name: str, metadata: sa.MetaData, bind: sa.Connection) -> sa.Table:
    return sa.Table(name, metadata, autoload_with=bind)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    roms = _table("roms", metadata, bind)
    media = _table("rom_owned_media", metadata, bind)
    placements = _table("rom_owned_media_placements", metadata, bind)

    rom_rows = bind.execute(
        sa.select(
            roms.c.id,
            roms.c.path_screenshots,
            roms.c.path_cover_s,
            roms.c.path_cover_l,
        )
    ).mappings()
    for rom in rom_rows:
        legacy_rows = _legacy_rows(
            rom["id"],
            rom["path_screenshots"],
            rom["path_cover_s"],
            rom["path_cover_l"],
        )
        existing_overview_count = bind.scalar(
            sa.select(sa.func.count())
            .select_from(placements)
            .where(
                sa.and_(
                    placements.c.rom_id == rom["id"],
                    placements.c.surface == "overview",
                )
            )
        )
        has_existing_overview = bool(existing_overview_count)
        for row in legacy_rows:
            existing_media = (
                bind.execute(
                    sa.select(media.c.id, media.c.state).where(
                        sa.and_(
                            media.c.rom_id == row["rom_id"],
                            media.c.provider == _LEGACY_PROVIDER,
                            media.c.provider_media_id == row["provider_media_id"],
                        )
                    )
                )
                .mappings()
                .first()
            )
            media_id = existing_media["id"] if existing_media is not None else None
            if media_id is None:
                bind.execute(
                    media.insert().values(
                        rom_id=row["rom_id"],
                        origin="provider",
                        role=row["role"],
                        state="active",
                        mime_type=row["mime_type"],
                        owned_path=row["owned_path"],
                        provider=_LEGACY_PROVIDER,
                        provider_media_id=row["provider_media_id"],
                        display_label=row["display_label"],
                    )
                )
                media_id = bind.scalar(
                    sa.select(media.c.id).where(
                        sa.and_(
                            media.c.rom_id == row["rom_id"],
                            media.c.provider == _LEGACY_PROVIDER,
                            media.c.provider_media_id == row["provider_media_id"],
                        )
                    )
                )
            if (
                row["overview_position"] is None
                or media_id is None
                or (
                    existing_media is not None
                    and existing_media["state"] == "tombstoned"
                )
            ):
                continue
            placement_exists = bind.scalar(
                sa.select(placements.c.id).where(
                    sa.and_(
                        placements.c.media_id == media_id,
                        placements.c.surface == "overview",
                    )
                )
            )
            if placement_exists is not None:
                continue
            position = (
                int(row["overview_position"])
                if not has_existing_overview
                else int(existing_overview_count)
            )
            bind.execute(
                placements.insert().values(
                    rom_id=row["rom_id"],
                    media_id=media_id,
                    surface="overview",
                    position=position,
                )
            )
            existing_overview_count = int(existing_overview_count or 0) + 1


def downgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    media = _table("rom_owned_media", metadata, bind)
    placements = _table("rom_owned_media_placements", metadata, bind)
    media_ids = list(
        bind.scalars(sa.select(media.c.id).where(media.c.provider == _LEGACY_PROVIDER))
    )
    if not media_ids:
        return
    bind.execute(placements.delete().where(placements.c.media_id.in_(media_ids)))
    bind.execute(media.delete().where(media.c.id.in_(media_ids)))
