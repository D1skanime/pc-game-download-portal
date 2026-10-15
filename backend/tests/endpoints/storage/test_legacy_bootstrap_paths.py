from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from endpoints.responses.storage import StorageRootHealthSchema, StorageRootSchema
from endpoints.storage import _legacy_platform_slug_for_filesystem_slug


def _root(root_id: int, container_path: str):
    now = datetime(2026, 10, 15, tzinfo=timezone.utc)
    return SimpleNamespace(
        id=root_id,
        name="PC Windows library",
        container_path=container_path,
        mode="external_read_only",
        active=True,
        created_at=now,
        updated_at=now,
    )


def _root_schema(root):
    return StorageRootSchema(
        id=root.id,
        name=root.name,
        mode=root.mode,
        active=root.active,
        created_at=root.created_at,
        updated_at=root.updated_at,
        health=StorageRootHealthSchema(
            reachable=True,
            readable=True,
            non_writable=True,
            checked_at=root.updated_at,
        ),
    )


def _bootstrap_fixtures(monkeypatch, *, roots, mapping=None):
    from endpoints import storage as endpoint

    platform = SimpleNamespace(id=41, slug="win", fs_slug="win")
    config = SimpleNamespace(
        ROMS_FOLDER_NAME="Games",
        PLATFORMS_BINDING={},
        PLATFORMS_VERSIONS={},
    )
    calls = {"register": [], "create": [], "update": []}

    monkeypatch.setattr(endpoint, "assert_admin", lambda request: None)
    monkeypatch.setattr(endpoint.cm, "get_config", lambda: config)
    monkeypatch.setattr(
        endpoint.fs_platform_handler, "get_platforms", lambda: _async(["pc"])
    )
    monkeypatch.setattr(endpoint, "get_filesystem_platforms", lambda: _async([]))
    monkeypatch.setattr(
        endpoint.db_platform_handler, "get_platforms", lambda: [platform]
    )
    monkeypatch.setattr(
        endpoint.db_platform_handler,
        "get_platform_by_slug",
        lambda slug: platform if slug == "win" else None,
    )
    monkeypatch.setattr(endpoint, "_root_schema", _root_schema)
    monkeypatch.setattr(
        endpoint,
        "_actor",
        lambda request: {"actor_user_id": 1, "actor_display_name": "admin"},
    )

    def get_active_mapping(platform_id):
        if mapping is None:
            from exceptions.storage_exceptions import MissingPlatformStorageMappingError

            raise MissingPlatformStorageMappingError(platform_id)
        return mapping

    monkeypatch.setattr(
        endpoint.db_storage_handler, "get_active_mapping", get_active_mapping
    )
    monkeypatch.setattr(endpoint.db_storage_handler, "get_roots", lambda: roots)

    def register_root(name, container_path):
        calls["register"].append((name, container_path))
        root = _root(2, container_path)
        roots.append(root)
        return root

    monkeypatch.setattr(endpoint.db_storage_handler, "register_root", register_root)

    def create_mapping(platform_id, root_id, relative_path, **kwargs):
        calls["create"].append((platform_id, root_id, relative_path, kwargs))
        return SimpleNamespace(
            id=9,
            platform_id=platform_id,
            storage_root_id=root_id,
            relative_path=relative_path,
            active=True,
            version=1,
            storage_root=next(root for root in roots if root.id == root_id),
        )

    monkeypatch.setattr(endpoint.db_storage_handler, "create_mapping", create_mapping)

    def update_mapping(mapping_id, root_id, relative_path, **kwargs):
        calls["update"].append((mapping_id, root_id, relative_path, kwargs))
        mapping.storage_root_id = root_id
        mapping.relative_path = relative_path
        mapping.storage_root = next(root for root in roots if root.id == root_id)
        return mapping

    monkeypatch.setattr(endpoint.db_storage_handler, "update_mapping", update_mapping)
    request = SimpleNamespace(user=SimpleNamespace(id=1, username="admin"))
    return endpoint, request, calls


async def _async(value):
    return value


def test_pc_legacy_bootstrap_reuses_windows_platform_for_pc_folder():
    assert _legacy_platform_slug_for_filesystem_slug("pc", {"win": "Windows"}) == "win"


def test_legacy_bootstrap_does_not_alias_other_filesystem_platforms():
    assert (
        _legacy_platform_slug_for_filesystem_slug(
            "switch", {"switch": "Nintendo Switch"}
        )
        == "switch"
    )


@pytest.mark.asyncio
async def test_bootstrap_persists_games_root_and_pc_relative_path(monkeypatch):
    endpoint, request, calls = _bootstrap_fixtures(monkeypatch, roots=[])

    response = await endpoint.bootstrap_legacy_storage(request)

    assert calls["register"] == [("PC Windows library", "/romm/library/Games")]
    assert calls["create"][0][0:3] == (41, 2, "pc")
    assert response.mappings[0].platform_fs_slug == "win"
    assert response.mappings[0].relative_path == "pc"


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent_for_canonical_mapping(monkeypatch):
    root = _root(2, "/romm/library/Games")
    mapping = SimpleNamespace(
        id=9,
        platform_id=41,
        storage_root_id=2,
        relative_path="pc",
        active=True,
        version=3,
        storage_root=root,
    )
    endpoint, request, calls = _bootstrap_fixtures(
        monkeypatch, roots=[root], mapping=mapping
    )

    response = await endpoint.bootstrap_legacy_storage(request)

    assert calls["register"] == []
    assert calls["create"] == []
    assert calls["update"] == []
    assert response.mappings[0].mapping_id == 9
    assert response.mappings[0].relative_path == "pc"


@pytest.mark.asyncio
async def test_bootstrap_reconciles_old_games_pc_empty_mapping(monkeypatch):
    old_root = _root(1, "/romm/library/Games/pc")
    old_mapping = SimpleNamespace(
        id=9,
        platform_id=41,
        storage_root_id=1,
        relative_path="",
        active=True,
        version=3,
        storage_root=old_root,
    )
    endpoint, request, calls = _bootstrap_fixtures(
        monkeypatch, roots=[old_root], mapping=old_mapping
    )

    response = await endpoint.bootstrap_legacy_storage(request)

    assert calls["register"] == [("PC Windows library", "/romm/library/Games")]
    assert calls["update"][0][0:3] == (9, 2, "pc")
    assert response.storage_root.id == 2
    assert response.mappings[0].relative_path == "pc"
