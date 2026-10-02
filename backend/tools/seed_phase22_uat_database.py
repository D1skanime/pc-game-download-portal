#!/usr/bin/env python3
"""Seed the disposable Phase 22 UAT database without scanning fixtures."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi import HTTPException  # noqa: E402

from exceptions.storage_exceptions import (  # noqa: E402
    MissingPlatformStorageMappingError,
)
from handler.database import (  # noqa: E402
    db_platform_handler,
    db_storage_handler,
    db_user_handler,
)
from handler.filesystem import fs_platform_handler  # noqa: E402
from handler.filesystem.storage_resolver import check_storage_root_health  # noqa: E402
from handler.scan_handler import scan_platform  # noqa: E402
from models.storage import EXTERNAL_READ_ONLY_MODE  # noqa: E402

STORAGE_ROOT_NAME = "Phase 22 PC Automation UAT Library"
STORAGE_ROOT_PATH = "/romm/library/roms"
ADMIN_USERNAME = "e2e_admin"
WINDOWS_FS_SLUG = "win"
WINDOWS_RELATIVE_PATH = "win"


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


def _ensure_safe_root(root):
    check_storage_root_health(root)
    if (
        root.container_path != STORAGE_ROOT_PATH
        or root.mode != EXTERNAL_READ_ONLY_MODE
        or not root.active
        or not root.reachable
        or not root.readable
        or not root.non_writable
    ):
        raise RuntimeError("isolated UAT root is not safe for the isolated UAT")
    return root


async def _get_or_register_windows_platform():
    filesystem_platforms = await fs_platform_handler.get_platforms()
    if WINDOWS_FS_SLUG not in filesystem_platforms:
        raise RuntimeError("missing isolated fixture platform: win")

    platform = db_platform_handler.get_platform_by_fs_slug(WINDOWS_FS_SLUG)
    if platform is None:
        db_platform_handler.add_platform(
            await scan_platform(WINDOWS_FS_SLUG, filesystem_platforms)
        )
        platform = db_platform_handler.get_platform_by_fs_slug(WINDOWS_FS_SLUG)
    if platform is None:
        raise RuntimeError("could not register isolated Windows platform")
    return platform


def _ensure_compatible_mapping(platform, root, admin):
    try:
        mapping = db_storage_handler.get_active_mapping(platform.id)
    except MissingPlatformStorageMappingError:
        return db_storage_handler.create_mapping(
            platform.id,
            root.id,
            WINDOWS_RELATIVE_PATH,
            actor_user_id=admin.id,
            actor_display_name=admin.username,
        )

    if (
        mapping.storage_root_id != root.id
        or mapping.relative_path != WINDOWS_RELATIVE_PATH
        or not mapping.active
    ):
        raise RuntimeError("incompatible active mapping for isolated Windows platform")
    return mapping


async def main() -> int:
    await _wait_for_platform_table()
    admin = db_user_handler.get_user_by_username(ADMIN_USERNAME)
    if admin is None:
        raise RuntimeError("isolated UAT seed requires the e2e_admin user")

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
    root = _ensure_safe_root(root)
    platform = await _get_or_register_windows_platform()
    mapping = _ensure_compatible_mapping(platform, root, admin)
    print(
        json.dumps(
            {
                "root": {
                    "id": root.id,
                    "container_path": root.container_path,
                    "mode": root.mode,
                },
                "platform": {"id": platform.id, "fs_slug": WINDOWS_FS_SLUG},
                "mapping": {
                    "id": mapping.id,
                    "relative_path": mapping.relative_path,
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
