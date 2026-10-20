"""Provider inventories through real SQL, capabilities and deterministic HTTPX."""

from copy import deepcopy

from sqlalchemy import select

from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.roms_handler import SteamOwnedMediaInventoryItem
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import ensure_directory
from handler.filesystem.storage_access import OwnedCreate, open_owned_access
from handler.filesystem.storage_policy import StorageOperation
from models.rom import RomOwnedMedia, RomOwnedMediaRole, RomOwnedMediaState


def steam_patch(count):
    artwork = min(count, 500)
    return {
        "media": {
            "cover": [
                {"id": f"art-{i}", "url": f"https://fixture.invalid/art-{i}.png"}
                for i in range(artwork)
            ],
            "screenshots": [
                {"id": f"shot-{i}", "url": f"https://fixture.invalid/shot-{i}.png"}
                for i in range(count - artwork)
            ],
        }
    }


def seed_steam(rom, count, data):
    directory = f"{rom.fs_resources_path}/owned-media"
    ensure_directory(fs_resource_handler.storage, directory)
    inventory = []
    paths = []
    for i in range(count):
        path = f"{directory}/old-{'x' * 190}-{i}.png"
        with open_owned_access(
            fs_resource_handler.storage, StorageOperation.CREATE, path
        ) as access:
            assert isinstance(access, OwnedCreate)
            access.create(data)
        paths.append(path)
        inventory.append(
            SteamOwnedMediaInventoryItem(
                f"old-{i}",
                RomOwnedMediaRole.ARTWORK if i < 500 else RomOwnedMediaRole.SCREENSHOT,
                f"old-{i}.png",
                "image/png",
                path,
            )
        )
    current = db_rom_handler.get_rom(rom.id)
    assert (
        db_rom_handler.reconcile_steam_owned_media_inventory(
            rom.id, current.updated_at, inventory
        )
        is not None
    )
    return paths


def active_steam(rom):
    with sync_session.begin() as session:
        return {
            row.provider_media_id: row.owned_path
            for row in session.scalars(
                select(RomOwnedMedia).where(
                    RomOwnedMedia.rom_id == rom.id,
                    RomOwnedMedia.provider == "steam",
                    RomOwnedMedia.state == RomOwnedMediaState.ACTIVE,
                )
            )
        }


def badge_inventory(rom, template, count):
    values = []
    for i in range(count):
        item = deepcopy(template)
        item.update(
            id=i + 10,
            ra_id=i + 10,
            badge_id=str(i + 10),
            title=f"Badge {i}",
            badge_url=f"https://fixture.invalid/{i}.png",
            badge_url_lock=f"https://fixture.invalid/{i}_lock.png",
            badge_path=f"{rom.fs_resources_path}/retroachievements/badges/{i}.png",
            badge_path_lock=f"{rom.fs_resources_path}/retroachievements/badges/{i}_lock.png",
        )
        values.append(item)
    return values
