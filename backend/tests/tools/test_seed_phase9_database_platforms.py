from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "backend" / "tools" / "seed_phase9_database_platforms.py"


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """This Phase 9 seeder suite does not need a database."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """Override the shared database cleanup for this suite."""


def _load_module():
    spec = importlib.util.spec_from_file_location("seed_phase9_platforms", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_main_registers_the_read_only_fixture_storage_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = type("Root", (), {"id": 7, "container_path": "/romm/library/roms"})()
    registered: list[tuple[str, str]] = []

    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(
        module.fs_platform_handler, "get_platforms", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(module.db_platform_handler, "get_platforms", lambda: [])
    monkeypatch.setattr(
        module.db_platform_handler, "get_platform_by_fs_slug", lambda _: None
    )
    monkeypatch.setattr(
        module.db_storage_handler,
        "get_roots",
        lambda: [],
    )

    def register_root(name: str, path: str):
        registered.append((name, path))
        return root

    monkeypatch.setattr(module.db_storage_handler, "register_root", register_root)

    assert await module.main() == 0
    assert registered == [("Phase 9 Fixture Library", "/romm/library/roms")]


@pytest.mark.asyncio
async def test_main_seeds_an_arcade_mapping_for_the_browser_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = type("Root", (), {"id": 7, "container_path": "/romm/library/roms"})()
    platform = type("Platform", (), {"id": 11})()
    created: list[tuple[int, int, str]] = []
    scanned: list[tuple[list[int], list[str], object]] = []

    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(
        module.fs_platform_handler, "get_platforms", AsyncMock(return_value=["arcade"])
    )
    lookups = iter([None, platform])
    monkeypatch.setattr(
        module.db_platform_handler, "get_platform_by_fs_slug", lambda _: next(lookups)
    )
    monkeypatch.setattr(module.db_platform_handler, "add_platform", lambda _: platform)
    monkeypatch.setattr(module, "scan_platform", AsyncMock(return_value=object()))
    monkeypatch.setattr(
        module,
        "scan_platforms",
        AsyncMock(
            side_effect=lambda platform_ids, metadata_sources, scan_type: scanned.append(
                (platform_ids, metadata_sources, scan_type)
            )
        ),
    )
    monkeypatch.setattr(module.db_storage_handler, "get_roots", lambda: [root])
    monkeypatch.setattr(
        module.db_user_handler,
        "get_user_by_username",
        lambda _: type("User", (), {"id": 3, "username": "e2e_admin"})(),
    )
    monkeypatch.setattr(
        module.db_storage_handler,
        "get_active_mapping",
        lambda _: (_ for _ in ()).throw(module.MissingPlatformStorageMappingError(11)),
    )
    monkeypatch.setattr(
        module.db_storage_handler,
        "create_mapping",
        lambda platform_id, root_id, relative_path, **_: created.append(
            (platform_id, root_id, relative_path)
        ),
    )

    assert await module.main() == 0
    assert created == [(11, 7, "arcade")]
    assert scanned == [([11], [], module.ScanType.QUICK)]
