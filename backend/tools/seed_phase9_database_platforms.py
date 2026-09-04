#!/usr/bin/env python3
"""Seed Phase 9 probe platforms into the database without mutating source mounts."""

from __future__ import annotations

import asyncio
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
    db_storage_handler,
    db_user_handler,
)
from handler.filesystem import fs_platform_handler  # noqa: E402
from handler.scan_handler import scan_platform  # noqa: E402

PHASE9_FIXTURE_STORAGE_ROOT_NAME = "Phase 9 Fixture Library"
PHASE9_FIXTURE_STORAGE_ROOT_PATH = "/romm/library/roms"
PHASE9_E2E_ADMIN_USERNAME = "e2e_admin"


async def _wait_for_platform_table(timeout_seconds: int = 30) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    last_error: Exception | None = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            db_platform_handler.get_platforms()
            return
        except HTTPException as exc:
            last_error = exc
            detail = str(exc.detail)
            if "doesn't exist" not in detail and "ProgrammingError" not in detail:
                raise
        await asyncio.sleep(1)
    if last_error is not None:
        raise last_error
    raise TimeoutError("platform table did not become ready in time")


async def main() -> int:
    await _wait_for_platform_table()
    root = next(
        (
            item
            for item in db_storage_handler.get_roots()
            if item.container_path == PHASE9_FIXTURE_STORAGE_ROOT_PATH
        ),
        None,
    )
    if root is None:
        root = db_storage_handler.register_root(
            PHASE9_FIXTURE_STORAGE_ROOT_NAME,
            PHASE9_FIXTURE_STORAGE_ROOT_PATH,
        )
    fs_platforms = await fs_platform_handler.get_platforms()
    for fs_slug in fs_platforms:
        if db_platform_handler.get_platform_by_fs_slug(fs_slug):
            continue
        scanned_platform = await scan_platform(fs_slug, fs_platforms)
        db_platform_handler.add_platform(scanned_platform)
    arcade = db_platform_handler.get_platform_by_fs_slug("arcade")
    if arcade is not None:
        try:
            db_storage_handler.get_active_mapping(arcade.id)
        except MissingPlatformStorageMappingError as error:
            admin = db_user_handler.get_user_by_username(PHASE9_E2E_ADMIN_USERNAME)
            if admin is None:
                raise RuntimeError(
                    "Phase 9 browser seed requires the e2e admin user"
                ) from error
            db_storage_handler.create_mapping(
                arcade.id,
                root.id,
                "arcade",
                actor_user_id=admin.id,
                actor_display_name=admin.username,
            )
        await scan_platforms(
            platform_ids=[arcade.id],
            metadata_sources=[],
            scan_type=ScanType.QUICK,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
