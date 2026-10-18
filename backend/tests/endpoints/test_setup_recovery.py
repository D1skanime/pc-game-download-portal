"""Real HTTP recovery with production authentication, CSRF and disposable SQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.middleware.authentication import AuthenticationMiddleware

from config import LIBRARY_BASE_PATH, ROMM_AUTH_SECRET_KEY
from endpoints import auth, heartbeat, setup, user
from handler.auth.constants import SESSION_COOKIE_NAME
from handler.auth.hybrid_auth import HybridAuthBackend
from handler.auth.middleware.csrf_middleware import CSRFMiddleware
from handler.auth.middleware.redis_session_middleware import RedisSessionMiddleware
from handler.database import db_storage_handler, db_user_handler
from handler.database.base_handler import sync_session
from handler.redis_handler import redis_client
from handler.setup_folder_handler import setup_folder_handler
from models.scan_operation import ScanOperation
from models.storage import PlatformStorageMapping, StorageMappingAudit

BASE = "/api/setup"
SLUGS = {
    "GB GameBoy": "gb",
    "GBA GameBoy Advance": "gba",
    "Nintendo 64": "n64",
    "Nintendo Switch": "switch",
    "PC": "win",
    "PSP": "psp",
    "PlayStation 2": "ps2",
    "SNES Super Nintendo": "snes",
}
ASSIGNMENTS = [
    {"folder_name": name, "platform_slug": slug} for name, slug in SLUGS.items()
]


@pytest.fixture
def recovery_client():
    app = FastAPI()
    for router in (auth.router, heartbeat.router, setup.router, user.router):
        app.include_router(router, prefix="/api")
    app.add_middleware(
        CSRFMiddleware, secret=ROMM_AUTH_SECRET_KEY, cookie_name="romm_csrftoken"
    )
    app.add_middleware(AuthenticationMiddleware, backend=HybridAuthBackend())
    app.add_middleware(RedisSessionMiddleware, session_cookie=SESSION_COOKIE_NAME)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def login(client, username="test_admin", password="test_admin_password"):
    response = client.post("/api/login", auth=(username, password))
    assert response.status_code == 200, response.text
    client.get(BASE + "/status")
    return {"x-csrftoken": client.cookies.get("romm_csrftoken")}


def save(client, assignments, headers=None):
    return client.post(
        BASE + "/folders/assign", json={"assignments": assignments}, headers=headers
    )


def assert_no_scan():
    with sync_session.begin() as session:
        assert session.query(ScanOperation).count() == 0
    assert not redis_client.keys("rq:job:*")


def test_real_enrollment_failure_relogin_lost_response_and_completion(
    recovery_client, monkeypatch
):
    client = recovery_client
    initial = client.get("/api/heartbeat").json()
    assert initial["SYSTEM"]["SHOW_SETUP_WIZARD"]
    enrollment = {
        "username": "recover_admin",
        "password": "Recover_test_password42",
        "email": "",
        "role": "admin",
    }
    created = client.post(
        "/api/users",
        json=enrollment,
        headers={"x-csrftoken": client.cookies.get("romm_csrftoken")},
    )
    assert created.status_code == 201, created.text
    csrf = login(client, enrollment["username"], enrollment["password"])
    original = setup_folder_handler.assign

    def fail(*args, **kwargs):
        raise ValueError("injected failure")

    monkeypatch.setattr(setup_folder_handler, "assign", fail)
    failed = save(client, ASSIGNMENTS, csrf)
    assert failed.status_code == 409
    monkeypatch.setattr(setup_folder_handler, "assign", original)
    assert not client.get("/api/heartbeat").json()["SYSTEM"]["SHOW_SETUP_WIZARD"]
    client.cookies.clear()
    assert client.get(BASE + "/status").status_code in {401, 403}
    assert (
        client.post(
            "/api/users",
            json=enrollment | {"username": "second_admin"},
            headers={"x-csrftoken": client.cookies.get("romm_csrftoken")},
        ).status_code
        == 403
    )
    csrf = login(client, enrollment["username"], enrollment["password"])
    snapshot = client.get(BASE + "/status")
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["enrolled"] and not snapshot.json()["setup_complete"]
    committed = save(client, ASSIGNMENTS, csrf)
    assert committed.status_code == 200, committed.text
    # Discard the saved response and all client session memory.
    client.cookies.clear()
    csrf = login(client, enrollment["username"], enrollment["password"])
    reconciled = client.get(BASE + "/status").json()
    assert reconciled["setup_complete"] and reconciled["missing_assignments"] == []
    assert reconciled["next_action"] == "start_first_scan"
    assert len(db_user_handler.get_admin_users()) == 1
    replay = save(client, ASSIGNMENTS, csrf)
    assert replay.status_code == 200 and replay.json()["ready"]
    assert replay.json()["recovery"] == reconciled
    with sync_session.begin() as session:
        assert session.query(PlatformStorageMapping).count() == 8
        assert (
            session.query(StorageMappingAudit)
            .filter(
                StorageMappingAudit.mapping_id.in_(select(PlatformStorageMapping.id))
            )
            .count()
            == 8
        )
    assert_no_scan()


@pytest.mark.parametrize("path", ["/status", "/folders", "/folders/assign"])
@pytest.mark.parametrize("actor", ["anonymous", "viewer", "delegated"])
def test_post_enrollment_access_is_admin_only(
    recovery_client,
    admin_user,
    viewer_user,
    path,
    actor,
):
    client = recovery_client
    if actor != "anonymous":
        if actor == "delegated":
            from handler.database import db_permission_handler
            from models.permission import PermAction, PermEntity

            db_permission_handler.replace_user_overrides(
                viewer_user.id,
                [
                    (PermEntity.USERS, PermAction.WRITE, True, False),
                    (PermEntity.PLATFORMS, PermAction.READ, True, False),
                ],
            )
        csrf = login(client, "test_viewer", "test_viewer_password")
    else:
        csrf = {}
    response = (
        save(client, ASSIGNMENTS, csrf)
        if path.endswith("assign")
        else client.get(BASE + path)
    )
    assert response.status_code in {401, 403}
    assert (
        "saved_assignments" not in response.text and "GB GameBoy" not in response.text
    )
    assert_no_scan()


def test_cookie_assignment_requires_csrf(recovery_client, admin_user):
    login(recovery_client)
    response = save(recovery_client, ASSIGNMENTS)
    assert response.status_code == 403 and "CSRF" in response.text
    with sync_session.begin() as session:
        assert session.scalar(select(PlatformStorageMapping.id)) is None


def test_partial_persisted_batch_only_repeats_missing_work(
    recovery_client, admin_user, monkeypatch
):
    root = db_storage_handler.register_root("Games", LIBRARY_BASE_PATH)
    # A prior interrupted batch left one real, audited mapping.
    platform = setup_folder_handler._resolve_platform("win")
    mapping = db_storage_handler.create_mapping(
        platform.id,
        root.id,
        "PC",
        actor_user_id=admin_user.id,
        actor_display_name=admin_user.username,
    )
    csrf = login(recovery_client)
    status = recovery_client.get(BASE + "/status").json()
    assert status["saved_assignments"][0]["mapping_id"] == mapping.id
    missing = [
        row
        for row in ASSIGNMENTS
        if row["folder_name"]
        in {folder["name"] for folder in status["missing_assignments"]}
    ]
    response = save(recovery_client, missing, csrf)
    assert response.status_code == 200, response.text
    assert response.json()["recovery"]["setup_complete"]
    with sync_session.begin() as session:
        stored = session.get(PlatformStorageMapping, mapping.id)
        assert stored.version == mapping.version
        assert (
            session.query(StorageMappingAudit)
            .filter(
                StorageMappingAudit.mapping_id.in_(select(PlatformStorageMapping.id))
            )
            .count()
            == 8
        )
    assert_no_scan()


def test_conflicting_saved_request_is_not_rewritten(recovery_client, admin_user):
    csrf = login(recovery_client)
    assert save(recovery_client, ASSIGNMENTS, csrf).status_code == 200
    changed = [
        row | {"platform_slug": "linux"} if row["folder_name"] == "PC" else row
        for row in ASSIGNMENTS
    ]
    response = save(recovery_client, changed, csrf)
    assert response.status_code == 409
    snapshot = recovery_client.get(BASE + "/status").json()
    assert (
        next(
            row for row in snapshot["saved_assignments"] if row["folder_name"] == "PC"
        )["platform_slug"]
        == "win"
    )
    assert snapshot["setup_complete"]
    with sync_session.begin() as session:
        assert (
            session.query(StorageMappingAudit)
            .filter(
                StorageMappingAudit.mapping_id.in_(select(PlatformStorageMapping.id))
            )
            .count()
            == 8
        )


def test_concurrent_assignment_retries_are_idempotent(
    recovery_client, admin_user, access_token
):
    db_storage_handler.register_root("Games", LIBRARY_BASE_PATH)
    barrier = Barrier(2)

    def attempt():
        barrier.wait(timeout=10)
        return save(
            recovery_client, ASSIGNMENTS, {"Authorization": "Bearer " + access_token}
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result(timeout=25)
            for future in [pool.submit(attempt), pool.submit(attempt)]
        ]
    assert [response.status_code for response in results] == [200, 200], [
        r.text for r in results
    ]
    ids = [
        {row["mapping_id"] for row in response.json()["mappings"]}
        for response in results
    ]
    assert ids[0] == ids[1]
    with sync_session.begin() as session:
        assert session.query(PlatformStorageMapping).count() == 8
        assert (
            session.query(StorageMappingAudit)
            .filter(
                StorageMappingAudit.mapping_id.in_(select(PlatformStorageMapping.id))
            )
            .count()
            == 8
        )
    assert_no_scan()


@pytest.mark.parametrize(
    "condition,cause",
    [
        ("missing", "root_missing"),
        ("unreadable", "root_unreadable"),
        ("writable", "root_not_read_only"),
    ],
)
def test_safe_root_failure_and_retry(
    recovery_client, admin_user, monkeypatch, condition, cause
):
    from datetime import datetime, timezone

    import handler.setup_recovery as module
    from handler.filesystem.storage_resolver import StorageRootHealthSnapshot

    root = db_storage_handler.register_root("Games", LIBRARY_BASE_PATH)
    csrf = login(recovery_client)
    health = StorageRootHealthSnapshot(
        condition != "missing",
        condition not in {"missing", "unreadable"},
        False if condition == "writable" else None,
        datetime.now(timezone.utc),
        "/private/source credential",
    )
    with monkeypatch.context() as patch:
        patch.setattr(module, "get_storage_root_health_snapshot", lambda root: health)
        snapshot = recovery_client.get(BASE + "/status")
        assert snapshot.status_code == 200
        assert snapshot.json()["cause_code"] == cause
        assert snapshot.json()["next_action"] == "retry_check"
        assert "/private" not in snapshot.text
        response = save(recovery_client, ASSIGNMENTS, csrf)
        assert response.status_code == 409
        assert "/private" not in response.text
    assert save(recovery_client, ASSIGNMENTS, csrf).json()["ready"]
    assert db_storage_handler.get_root(root.id).active
    assert_no_scan()


def test_mid_batch_failure_rolls_back_and_retry_completes(
    recovery_client, admin_user, monkeypatch
):
    csrf = login(recovery_client)
    original = db_storage_handler.create_mapping
    calls = []

    def fail_third(*args, **kwargs):
        calls.append(args[0])
        if len(calls) == 3:
            raise ValueError("interrupted synthetic batch")
        return original(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(db_storage_handler, "create_mapping", fail_third)
        response = save(recovery_client, ASSIGNMENTS, csrf)
        assert response.status_code == 409
    assert len(calls) == 3
    with sync_session.begin() as session:
        assert session.query(PlatformStorageMapping).count() == 0
    snapshot = recovery_client.get(BASE + "/status").json()
    assert len(snapshot["missing_assignments"]) == 8
    assert snapshot["saved_assignments"] == []
    assert save(recovery_client, ASSIGNMENTS, csrf).json()["recovery"]["setup_complete"]
    assert len(db_user_handler.get_admin_users()) == 1
    assert_no_scan()
