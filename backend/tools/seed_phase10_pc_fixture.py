#!/usr/bin/env python3
"""Seed and scan the isolated Phase 10 Windows fixture."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi import HTTPException  # noqa: E402

from endpoints.sockets.scan import ScanType, scan_platforms  # noqa: E402
from exceptions.storage_exceptions import (  # noqa: E402
    MissingPlatformStorageMappingError,
)
from handler.database import (  # noqa: E402
    db_platform_handler,
    db_rom_handler,
    db_storage_handler,
    db_user_handler,
)
from handler.filesystem import fs_platform_handler  # noqa: E402
from handler.scan_handler import scan_platform  # noqa: E402

STORAGE_ROOT_NAME = "Phase 10 PC Fixture Library"
STORAGE_ROOT_PATH = "/romm/library/roms"
ADMIN_USERNAME = "e2e_admin"
PC_FS_SLUG = "win"
PC_ROM_FS_NAME = "Cyberpunk2077"


async def _wait_for_platform_table(timeout_seconds: int = 30) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    last_error: Exception | None = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            db_platform_handler.get_platforms()
            return
        except HTTPException as error:
            last_error = error
            if "doesn't exist" not in str(
                error.detail
            ) and "ProgrammingError" not in str(error):
                raise
        await asyncio.sleep(1)
    if last_error:
        raise last_error
    raise TimeoutError("platform table did not become ready in time")


async def main() -> int:
    await _wait_for_platform_table()
    root = next(
        (
            item
            for item in db_storage_handler.get_roots()
            if item.container_path == STORAGE_ROOT_PATH
        ),
        None,
    )
    if root is None:
        root = db_storage_handler.register_root(STORAGE_ROOT_NAME, STORAGE_ROOT_PATH)

    fs_platforms = await fs_platform_handler.get_platforms()
    if PC_FS_SLUG not in fs_platforms:
        raise RuntimeError(f"missing isolated fixture platform: {PC_FS_SLUG}")
    platform = db_platform_handler.get_platform_by_fs_slug(PC_FS_SLUG)
    if platform is None:
        platform = await scan_platform(PC_FS_SLUG, fs_platforms)
        db_platform_handler.add_platform(platform)
        platform = db_platform_handler.get_platform_by_fs_slug(PC_FS_SLUG)
    if platform is None:
        raise RuntimeError("could not register isolated Windows platform")

    try:
        db_storage_handler.get_active_mapping(platform.id)
    except MissingPlatformStorageMappingError as error:
        admin = db_user_handler.get_user_by_username(ADMIN_USERNAME)
        if admin is None:
            raise RuntimeError(
                "Phase 10 browser seed requires the e2e admin user"
            ) from error
        db_storage_handler.create_mapping(
            platform.id,
            root.id,
            PC_FS_SLUG,
            actor_user_id=admin.id,
            actor_display_name=admin.username,
        )

    await scan_platforms(
        platform_ids=[platform.id], metadata_sources=[], scan_type=ScanType.QUICK
    )
    rom = db_rom_handler.get_roms_by_fs_name(platform.id, {PC_ROM_FS_NAME}).get(
        PC_ROM_FS_NAME
    )
    if rom is None:
        raise RuntimeError("isolated Cyberpunk fixture was not scanned")
    print(json.dumps({"rom_id": rom.id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
