from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from exceptions.storage_exceptions import (
    InvalidRelativePathError,
    InvalidStorageCursorError,
    MissingStorageRootError,
    SafeStorageFilesystemError,
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
