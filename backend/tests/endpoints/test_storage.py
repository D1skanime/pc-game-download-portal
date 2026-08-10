from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from exceptions.storage_exceptions import (
    DuplicateStorageMappingError,
    InvalidRelativePathError,
    InvalidStorageCursorError,
    MissingStorageRootError,
    SafeStorageFilesystemError,
    StaleStorageMappingVersionError,
    StorageMappingOverlapError,
    StorageScanLimitError,
    UnsafeSymlinkError,
)
from handler.filesystem.storage_resolver import (
    StorageDirectoryEntry,
    StorageDirectoryPage,
    StorageRootHealthSnapshot,
)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _root(root_id=7):
    return SimpleNamespace(
        id=root_id,
        name="Archive",
        container_path="/sentinel/absolute/nas/library",
        mode="external_read_only",
        active=True,
        reachable=False,
        readable=False,
        non_writable=None,
        last_checked_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        safe_error="RAW OS ERROR /sentinel/absolute/nas/library",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        platform_mappings=[{"relative_path": "unrelated-secret-mapping"}],
    )


def _mapping(mapping_id=11, *, active=True, version=3):
    return SimpleNamespace(
        id=mapping_id,
        platform_id=5,
        storage_root_id=7,
        relative_path="Nintendo/SNES",
        active=active,
        version=version,
    )


def _audit(audit_id=21):
    return SimpleNamespace(
        id=audit_id,
        actor_user_id=1,
        actor_display_name="admin",
        platform_id=5,
        mapping_id=11,
        action="update",
        old_storage_root_id=7,
        old_relative_path="Nintendo/SNES",
        old_version=2,
        old_active=True,
        new_storage_root_id=7,
        new_relative_path="Nintendo/Super Nintendo",
        new_version=3,
        new_active=True,
        created_at=datetime(2026, 4, 6, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/storage/roots",
        "/api/storage/roots/7",
        "/api/storage/roots/7/browse?parent=&limit=2",
    ],
)
@pytest.mark.parametrize("kind", ["anonymous", "viewer"])
def test_storage_auth_precedes_lookup(
    client, viewer_access_token, monkeypatch, path, kind
):
    def forbidden(*args, **kwargs):
        raise AssertionError("lookup or filesystem observation executed")

    monkeypatch.setattr(
        "handler.database.db_storage_handler.get_roots", forbidden, raising=False
    )
    monkeypatch.setattr(
        "handler.database.db_storage_handler.get_root", forbidden, raising=False
    )
    monkeypatch.setattr(
        "handler.filesystem.storage_resolver.get_storage_root_health_snapshot",
        forbidden,
    )
    monkeypatch.setattr(
        "handler.filesystem.storage_resolver.browse_storage_directories", forbidden
    )
    headers = {} if kind == "anonymous" else _auth(viewer_access_token)
    assert client.get(path, headers=headers).status_code == (
        401 if kind == "anonymous" else 403
    )


def test_admin_root_list_uses_live_allowlisted_health(
    client, access_token, monkeypatch
):
    from endpoints import storage as endpoint

    root = _root()
    monkeypatch.setattr(endpoint.db_storage_handler, "get_roots", lambda: [root])
    monkeypatch.setattr(
        endpoint,
        "get_storage_root_health_snapshot",
        lambda item: StorageRootHealthSnapshot(
            True, True, True, datetime(2026, 4, 5, tzinfo=timezone.utc), None
        ),
    )
    response = client.get("/api/storage/roots", headers=_auth(access_token))
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 7,
            "name": "Archive",
            "mode": "external_read_only",
            "active": True,
            "created_at": "2026-01-02T00:00:00+00:00",
            "updated_at": "2026-01-03T00:00:00+00:00",
            "health": {
                "reachable": True,
                "readable": True,
                "non_writable": True,
                "checked_at": "2026-04-05T00:00:00+00:00",
                "error": None,
            },
        }
    ]
    assert root.reachable is False
    assert not any(
        value in response.text
        for value in ("/sentinel/absolute", "unrelated-secret-mapping", "RAW OS ERROR")
    )


def test_admin_root_detail_does_not_mutate_stored_status(
    client, access_token, monkeypatch
):
    from endpoints import storage as endpoint

    root = _root()
    before = root.__dict__.copy()
    monkeypatch.setattr(endpoint.db_storage_handler, "get_root", lambda root_id: root)
    monkeypatch.setattr(
        endpoint,
        "get_storage_root_health_snapshot",
        lambda item: StorageRootHealthSnapshot(
            True, True, True, datetime(2026, 4, 5, tzinfo=timezone.utc), None
        ),
    )
    response = client.get("/api/storage/roots/7", headers=_auth(access_token))
    assert response.status_code == 200
    assert root.__dict__ == before
    assert response.json()["health"]["checked_at"] != root.last_checked_at.isoformat()


def test_admin_browse_returns_minimal_page(client, access_token, monkeypatch):
    from endpoints import storage as endpoint

    monkeypatch.setattr(
        endpoint.db_storage_handler, "get_root", lambda root_id: _root()
    )
    monkeypatch.setattr(
        endpoint,
        "browse_storage_directories",
        lambda item, parent, limit, cursor: StorageDirectoryPage(
            (
                StorageDirectoryEntry("Alpha", "Parent/Alpha", True),
                StorageDirectoryEntry("Zulu", "Parent/Zulu", True),
            ),
            "next-safe-cursor",
        ),
    )
    response = client.get(
        "/api/storage/roots/7/browse?parent=Parent&limit=2", headers=_auth(access_token)
    )
    assert response.status_code == 200
    assert response.json() == {
        "entries": [
            {"name": "Alpha", "relative_path": "Parent/Alpha", "navigable": True},
            {"name": "Zulu", "relative_path": "Parent/Zulu", "navigable": True},
        ],
        "next_cursor": "next-safe-cursor",
    }


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (InvalidRelativePathError(), 400, "invalid_relative_path"),
        (InvalidStorageCursorError(), 400, "invalid_storage_cursor"),
        (MissingStorageRootError(7), 404, "missing_storage_root"),
        (UnsafeSymlinkError(), 422, "unsafe_storage_symlink"),
        (StorageScanLimitError(7), 422, "storage_scan_limit_exceeded"),
        (SafeStorageFilesystemError(7), 422, "storage_filesystem_error"),
    ],
)
def test_browse_has_bounded_path_safe_errors(
    client, access_token, monkeypatch, caplog, error, status_code, code
):
    from endpoints import storage as endpoint

    monkeypatch.setattr(
        endpoint.db_storage_handler, "get_root", lambda root_id: _root()
    )

    def fail(*args, **kwargs):
        raise error from OSError(
            "RAW OS ERROR /sentinel/absolute/nas/library unrelated-secret-mapping SQL SELECT"
        )

    monkeypatch.setattr(endpoint, "browse_storage_directories", fail)
    response = client.get(
        "/api/storage/roots/7/browse?parent=Parent&limit=2", headers=_auth(access_token)
    )
    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code
    assert 1 <= len(response.json()["detail"]["message"]) <= 160
    combined = response.text + caplog.text
    assert not any(
        value in combined
        for value in (
            "/sentinel/absolute",
            "nas/library",
            "unrelated-secret-mapping",
            "RAW OS ERROR",
            "SQL SELECT",
        )
    )


def test_storage_openapi_excludes_sensitive_fields(client):
    schema = client.get("/openapi.json").json()
    assert "/api/storage/roots" in schema["paths"]
    assert "/api/storage/roots/{storage_root_id}/browse" in schema["paths"]
    serialized = str(
        {
            name: value
            for name, value in schema["components"]["schemas"].items()
            if name.startswith("Storage")
        }
    )
    assert not any(
        field in serialized
        for field in (
            "container_path",
            "safe_error",
            "platform_mappings",
            "absolute_path",
            "mapping",
        )
    )


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/storage/mappings/platforms/5", None),
        (
            "post",
            "/api/storage/mappings/test",
            {"platform_id": 5, "storage_root_id": 7, "relative_path": "Nintendo/SNES"},
        ),
        (
            "post",
            "/api/storage/mappings",
            {"platform_id": 5, "storage_root_id": 7, "relative_path": "Nintendo/SNES"},
        ),
        (
            "put",
            "/api/storage/mappings/11",
            {
                "storage_root_id": 7,
                "relative_path": "Nintendo/SNES",
                "expected_version": 3,
            },
        ),
        ("post", "/api/storage/mappings/11/deactivate", {"expected_version": 3}),
        ("delete", "/api/storage/mappings/11", {"expected_version": 3}),
        ("post", "/api/storage/mappings/11/activate", {"expected_version": 3}),
        ("get", "/api/storage/mapping-audits?platform_id=5&limit=2", None),
    ],
)
@pytest.mark.parametrize("kind", ["anonymous", "viewer"])
def test_mapping_routes_authorize_before_handler(
    client, viewer_access_token, monkeypatch, method, path, body, kind
):
    from endpoints import storage as endpoint

    def forbidden(*args, **kwargs):
        raise AssertionError("mapping handler executed before admin authorization")

    for name in (
        "get_active_mapping",
        "test_mapping",
        "create_mapping",
        "update_mapping",
        "deactivate_mapping",
        "remove_mapping",
        "reactivate_mapping",
        "list_mapping_audits",
    ):
        monkeypatch.setattr(endpoint.db_storage_handler, name, forbidden, raising=False)
    headers = {} if kind == "anonymous" else _auth(viewer_access_token)
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == (401 if kind == "anonymous" else 403)


def test_mapping_test_is_non_mutating_and_allowlisted(
    client, access_token, monkeypatch
):
    from endpoints import storage as endpoint

    calls = []
    monkeypatch.setattr(
        endpoint.db_storage_handler,
        "test_mapping",
        lambda platform_id, storage_root_id, relative_path: calls.append(
            (platform_id, storage_root_id, relative_path)
        )
        or _mapping(version=1),
        raising=False,
    )
    response = client.post(
        "/api/storage/mappings/test",
        headers=_auth(access_token),
        json={"platform_id": 5, "storage_root_id": 7, "relative_path": "Nintendo/SNES"},
    )
    assert response.status_code == 200
    assert calls == [(5, 7, "Nintendo/SNES")]
    assert response.json() == {
        "platform_id": 5,
        "storage_root_id": 7,
        "relative_path": "Nintendo/SNES",
        "valid": True,
    }


def test_mapping_mutations_capture_authenticated_actor_and_version(
    client, access_token, monkeypatch
):
    from endpoints import storage as endpoint

    captured = {}

    def update(mapping_id, storage_root_id, relative_path, **kwargs):
        captured.update(
            mapping_id=mapping_id,
            storage_root_id=storage_root_id,
            relative_path=relative_path,
            **kwargs,
        )
        return _mapping(version=4)

    monkeypatch.setattr(
        endpoint.db_storage_handler, "update_mapping", update, raising=False
    )
    response = client.put(
        "/api/storage/mappings/11",
        headers=_auth(access_token),
        json={
            "storage_root_id": 7,
            "relative_path": "Nintendo/SNES",
            "expected_version": 3,
        },
    )
    assert response.status_code == 200
    assert captured["expected_version"] == 3
    assert captured["actor_user_id"] > 0
    assert captured["actor_display_name"]
    assert response.json()["version"] == 4


@pytest.mark.parametrize(
    ("error", "code", "extra"),
    [
        (DuplicateStorageMappingError(5, 7), "duplicate_storage_mapping", {}),
        (
            StorageMappingOverlapError(7, platform_id=8, mapping_id=12),
            "storage_mapping_overlap",
            {"platform_id": 8, "mapping_id": 12},
        ),
        (
            StaleStorageMappingVersionError(11, 4),
            "storage_mapping_stale_version",
            {"mapping_id": 11, "current_version": 4},
        ),
    ],
)
def test_mapping_conflicts_are_stable_path_safe(
    client, access_token, monkeypatch, error, code, extra
):
    from endpoints import storage as endpoint

    def fail(*args, **kwargs):
        raise error from OSError("RAW /sentinel/absolute/nas/library SQL SELECT")

    monkeypatch.setattr(
        endpoint.db_storage_handler, "update_mapping", fail, raising=False
    )
    response = client.put(
        "/api/storage/mappings/11",
        headers=_auth(access_token),
        json={
            "storage_root_id": 7,
            "relative_path": "Nintendo/SNES",
            "expected_version": 3,
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail == {"code": code, "message": detail["message"], **extra}
    assert len(detail["message"]) <= 160
    assert not any(
        value in response.text for value in ("sentinel", "nas/library", "SQL SELECT")
    )


def test_mapping_audit_page_is_filter_bound_and_allowlisted(
    client, access_token, monkeypatch
):
    from endpoints import storage as endpoint

    captured = {}

    def audits(**kwargs):
        captured.update(kwargs)
        return [_audit()], "bound-next"

    monkeypatch.setattr(
        endpoint.db_storage_handler, "list_mapping_audits", audits, raising=False
    )
    response = client.get(
        "/api/storage/mapping-audits?platform_id=5&mapping_id=11&action=update&limit=2&cursor=bound",
        headers=_auth(access_token),
    )
    assert response.status_code == 200
    assert captured == {
        "platform_id": 5,
        "mapping_id": 11,
        "action": "update",
        "cursor": "bound",
        "limit": 2,
    }
    payload = response.json()
    assert payload["next_cursor"] == "bound-next"
    assert list(payload["entries"][0]) == [
        "id",
        "actor_user_id",
        "actor_display_name",
        "platform_id",
        "mapping_id",
        "action",
        "old",
        "new",
        "created_at",
    ]
    assert payload["entries"][0]["old"] == {
        "storage_root_id": 7,
        "relative_path": "Nintendo/SNES",
        "version": 2,
        "active": True,
    }
