from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "backend" / "tools" / "seed_phase22_uat_database.py"


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """This isolated-seeder suite replaces database fixtures with mocks."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """This isolated-seeder suite never opens the configured database."""


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "seed_phase22_uat_database", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _install_happy_path(monkeypatch: pytest.MonkeyPatch, module):
    root = SimpleNamespace(
        id=7,
        container_path="/romm/library/roms",
        mode="external_read_only",
        active=True,
        reachable=True,
        readable=True,
        non_writable=True,
    )
    platform = SimpleNamespace(id=11, fs_slug="win")
    mapping = SimpleNamespace(
        id=13,
        storage_root_id=root.id,
        relative_path="win",
        active=True,
    )
    created: list[tuple[int, int, str]] = []

    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(
        module.db_user_handler,
        "get_user_by_username",
        lambda _: SimpleNamespace(id=3, username="e2e_admin"),
    )
    monkeypatch.setattr(module.db_storage_handler, "get_roots", lambda: [])
    monkeypatch.setattr(module.db_storage_handler, "register_root", lambda *_: root)
    monkeypatch.setattr(module, "check_storage_root_health", lambda item: item)
    monkeypatch.setattr(
        module.fs_platform_handler, "get_platforms", AsyncMock(return_value=["win"])
    )
    platform_lookups = iter([None, platform])
    monkeypatch.setattr(
        module.db_platform_handler,
        "get_platform_by_fs_slug",
        lambda _: next(platform_lookups),
    )
    monkeypatch.setattr(module, "scan_platform", AsyncMock(return_value=platform))
    monkeypatch.setattr(module.db_platform_handler, "add_platform", lambda _: None)
    monkeypatch.setattr(
        module.db_storage_handler,
        "get_active_mapping",
        lambda _: (_ for _ in ()).throw(module.MissingPlatformStorageMappingError(11)),
    )

    def create_mapping(platform_id, root_id, relative_path, **_):
        created.append((platform_id, root_id, relative_path))
        return mapping

    monkeypatch.setattr(module.db_storage_handler, "create_mapping", create_mapping)
    return root, platform, mapping, created


@pytest.mark.asyncio
async def test_main_registers_the_exact_read_only_root_and_win_mapping(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load_module()
    root, platform, mapping, created = _install_happy_path(monkeypatch, module)

    assert await module.main() == 0

    assert created == [(platform.id, root.id, "win")]
    assert json.loads(capsys.readouterr().out) == {
        "mapping": {"id": mapping.id, "relative_path": "win"},
        "platform": {"id": platform.id, "fs_slug": "win"},
        "root": {
            "id": root.id,
            "container_path": "/romm/library/roms",
            "mode": "external_read_only",
        },
    }


@pytest.mark.asyncio
async def test_main_reuses_a_correct_mapping_without_creating_audit_or_scan_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = SimpleNamespace(
        id=7,
        container_path="/romm/library/roms",
        mode="external_read_only",
        active=True,
        reachable=True,
        readable=True,
        non_writable=True,
    )
    platform = SimpleNamespace(id=11, fs_slug="win")
    mapping = SimpleNamespace(
        id=13, storage_root_id=root.id, relative_path="win", active=True
    )
    create_mapping = AsyncMock()

    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(
        module.db_user_handler,
        "get_user_by_username",
        lambda _: SimpleNamespace(id=3, username="e2e_admin"),
    )
    monkeypatch.setattr(module.db_storage_handler, "get_roots", lambda: [root])
    monkeypatch.setattr(module, "check_storage_root_health", lambda item: item)
    monkeypatch.setattr(
        module.fs_platform_handler, "get_platforms", AsyncMock(return_value=["win"])
    )
    monkeypatch.setattr(
        module.db_platform_handler, "get_platform_by_fs_slug", lambda _: platform
    )
    monkeypatch.setattr(
        module.db_storage_handler, "get_active_mapping", lambda _: mapping
    )
    monkeypatch.setattr(module.db_storage_handler, "create_mapping", create_mapping)

    assert await module.main() == 0
    create_mapping.assert_not_called()


@pytest.mark.asyncio
async def test_main_refuses_missing_admin_before_mutating_the_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    register_root = AsyncMock()
    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(module.db_user_handler, "get_user_by_username", lambda _: None)
    monkeypatch.setattr(module.db_storage_handler, "register_root", register_root)

    with pytest.raises(RuntimeError, match="e2e_admin"):
        await module.main()
    register_root.assert_not_called()


@pytest.mark.asyncio
async def test_main_refuses_an_incompatible_active_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = SimpleNamespace(
        id=7,
        container_path="/romm/library/roms",
        mode="external_read_only",
        active=True,
        reachable=True,
        readable=True,
        non_writable=True,
    )
    platform = SimpleNamespace(id=11, fs_slug="win")
    incompatible_mapping = SimpleNamespace(
        id=13, storage_root_id=99, relative_path="pc", active=True
    )
    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(
        module.db_user_handler,
        "get_user_by_username",
        lambda _: SimpleNamespace(id=3, username="e2e_admin"),
    )
    monkeypatch.setattr(module.db_storage_handler, "get_roots", lambda: [root])
    monkeypatch.setattr(module, "check_storage_root_health", lambda item: item)
    monkeypatch.setattr(
        module.fs_platform_handler, "get_platforms", AsyncMock(return_value=["win"])
    )
    monkeypatch.setattr(
        module.db_platform_handler, "get_platform_by_fs_slug", lambda _: platform
    )
    monkeypatch.setattr(
        module.db_storage_handler,
        "get_active_mapping",
        lambda _: incompatible_mapping,
    )

    with pytest.raises(RuntimeError, match="incompatible active mapping"):
        await module.main()


@pytest.mark.asyncio
async def test_main_refuses_a_missing_windows_fixture_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = SimpleNamespace(
        id=7,
        container_path="/romm/library/roms",
        mode="external_read_only",
        active=True,
        reachable=True,
        readable=True,
        non_writable=True,
    )
    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(
        module.db_user_handler,
        "get_user_by_username",
        lambda _: SimpleNamespace(id=3, username="e2e_admin"),
    )
    monkeypatch.setattr(module.db_storage_handler, "get_roots", lambda: [root])
    monkeypatch.setattr(module, "check_storage_root_health", lambda item: item)
    monkeypatch.setattr(
        module.fs_platform_handler, "get_platforms", AsyncMock(return_value=[])
    )

    with pytest.raises(RuntimeError, match="missing isolated fixture platform"):
        await module.main()


@pytest.mark.asyncio
async def test_main_refuses_a_root_that_is_not_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = SimpleNamespace(
        id=7,
        container_path="/romm/library/roms",
        mode="external_read_only",
        active=True,
        reachable=True,
        readable=True,
        non_writable=False,
    )
    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(
        module.db_user_handler,
        "get_user_by_username",
        lambda _: SimpleNamespace(id=3, username="e2e_admin"),
    )
    monkeypatch.setattr(module.db_storage_handler, "get_roots", lambda: [root])
    monkeypatch.setattr(module, "check_storage_root_health", lambda item: item)

    with pytest.raises(RuntimeError, match="not safe for the isolated UAT"):
        await module.main()


@pytest.mark.asyncio
async def test_main_refuses_an_unreachable_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = SimpleNamespace(
        id=7,
        container_path="/romm/library/roms",
        mode="external_read_only",
        active=True,
        reachable=False,
        readable=False,
        non_writable=None,
    )
    monkeypatch.setattr(module, "_wait_for_platform_table", AsyncMock())
    monkeypatch.setattr(
        module.db_user_handler,
        "get_user_by_username",
        lambda _: SimpleNamespace(id=3, username="e2e_admin"),
    )
    monkeypatch.setattr(module.db_storage_handler, "get_roots", lambda: [root])
    monkeypatch.setattr(module, "check_storage_root_health", lambda item: item)

    with pytest.raises(RuntimeError, match="not safe for the isolated UAT"):
        await module.main()
