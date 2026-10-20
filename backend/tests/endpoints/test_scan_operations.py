"""Authenticated HTTP commands against real disposable operation persistence."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.authentication import AuthenticationMiddleware

from config import ROMM_AUTH_SECRET_KEY
from endpoints.auth import router as auth_router
from endpoints.responses.scan_operations import ScanOperationSnapshot
from handler.auth import oauth_handler
from handler.auth.constants import SESSION_COOKIE_NAME
from handler.auth.hybrid_auth import HybridAuthBackend
from handler.auth.middleware.csrf_middleware import CSRFMiddleware
from handler.auth.middleware.redis_session_middleware import RedisSessionMiddleware
from handler.database import db_permission_handler
from handler.database.base_handler import sync_session
from models.permission import PermAction, PermEntity
from models.scan_operation import ScanOperation
from models.storage import PlatformStorageMapping, StorageRoot

BASE = "/api/scan-operations"
IDENTITY = "00000000-0000-0000-0000-000000000001"
ROUTES = [
    ("get", "/active"),
    ("get", "/by-request/request-key"),
    ("get", "/" + IDENTITY),
    ("post", ""),
    ("post", "/" + IDENTITY + "/cancel"),
    ("post", "/" + IDENTITY + "/resume"),
    ("post", "/" + IDENTITY + "/retry-metadata"),
]


@pytest.fixture
def mapped(platform):
    with sync_session.begin() as session:
        root = StorageRoot(name="Synthetic", container_path="/phase34/owned/library")
        session.add(root)
        session.flush()
        mapping = PlatformStorageMapping(
            platform_id=platform.id, storage_root_id=root.id, relative_path="PC"
        )
        session.add(mapping)
        session.flush()
        return mapping


@pytest.fixture
def headers(access_token):
    return {"Authorization": "Bearer " + access_token}


@pytest.fixture
def other_headers(viewer_user):
    db_permission_handler.replace_user_overrides(
        viewer_user.id, [(PermEntity.TASKS, PermAction.WRITE, True, False)]
    )
    token = oauth_handler.create_access_token(
        data={"sub": viewer_user.username, "iss": "romm:oauth", "scopes": "tasks.run"},
        expires_delta=timedelta(minutes=10),
    )
    return {"Authorization": "Bearer " + token}


def request_body(mapped, **changes):
    return {
        "request_key": "request-key",
        "platforms": [mapped.platform_id],
        "apis": ["igdb"],
        **changes,
    }


@pytest.mark.parametrize("method,path", ROUTES)
def test_anonymous_routes_fail_closed(client, method, path):
    payload = (
        {"request_key": "request-key"}
        if not path
        else {"request_key": "control-key", "expected_version": 1, "item_ids": [1]}
    )
    response = getattr(client, method)(
        BASE + path, **({"json": payload} if method == "post" else {})
    )
    assert response.status_code in {401, 403}


@pytest.mark.parametrize("method,path", ROUTES)
def test_viewer_routes_fail_closed(client, viewer_access_token, method, path):
    payload = (
        {"request_key": "request-key"}
        if not path
        else {"request_key": "control-key", "expected_version": 1, "item_ids": [1]}
    )
    response = getattr(client, method)(
        BASE + path,
        headers={"Authorization": "Bearer " + viewer_access_token},
        **({"json": payload} if method == "post" else {})
    )
    assert response.status_code == 403


def test_duplicate_and_lost_response_reconcile(client, headers, mapped):
    first = client.post(BASE, headers=headers, json=request_body(mapped))
    assert first.status_code == 202, first.text
    snapshot = first.json()
    assert snapshot["state"] == "queued" and not snapshot["dispatch_pending"]
    assert (
        client.post(BASE, headers=headers, json=request_body(mapped)).json() == snapshot
    )
    assert (
        client.get(BASE + "/by-request/request-key", headers=headers).json() == snapshot
    )
    assert client.get(BASE + "/active", headers=headers).json()["id"] == snapshot["id"]
    assert (
        client.get(BASE + "/" + snapshot["id"], headers=headers).json()["version"]
        == snapshot["version"]
    )
    conflict = client.post(
        BASE, headers=headers, json=request_body(mapped, apis=["steam"])
    )
    assert conflict.status_code == 409
    with sync_session.begin() as session:
        assert session.query(ScanOperation).count() == 1
    assert (
        "command" not in snapshot
        and "lease_owner" not in snapshot
        and "actor_id" not in snapshot
    )


@pytest.mark.parametrize("suffix", ["", "/cancel", "/resume", "/retry-metadata"])
def test_foreign_owner_is_masked(client, headers, other_headers, mapped, suffix):
    accepted = client.post(BASE, headers=headers, json=request_body(mapped)).json()
    kwargs = {"headers": other_headers}
    if suffix:
        kwargs["json"] = {
            "request_key": "control-key",
            "expected_version": accepted["version"],
            "item_ids": [1],
        }
    response = getattr(client, "post" if suffix else "get")(
        BASE + "/" + accepted["id"] + suffix, **kwargs
    )
    assert response.status_code == 404
    assert client.get(BASE + "/active", headers=other_headers).json() is None
    assert (
        client.get(BASE + "/by-request/request-key", headers=other_headers).status_code
        == 404
    )


def test_admin_can_discover_and_cancel_foreign_operation(
    client, headers, other_headers, mapped
):
    accepted = client.post(
        BASE, headers=other_headers, json=request_body(mapped)
    ).json()
    assert client.get(BASE + "/" + accepted["id"], headers=headers).status_code == 200
    response = client.post(
        BASE + "/" + accepted["id"] + "/cancel",
        headers=headers,
        json={"request_key": "admin-cancel", "expected_version": accepted["version"]},
    )
    assert response.status_code == 200
    assert (
        response.json()["state"] == "cancelled"
        and response.json()["intentional_cancel"]
    )


@pytest.mark.parametrize(
    "scope", ["/etc", "C:/games", "\\\\server\\games", "../PC", "PC/../../etc"]
)
def test_unsafe_scope_rejected_before_acceptance(client, headers, mapped, scope):
    response = client.post(
        BASE,
        headers=headers,
        json=request_body(mapped, filesystem_scope_paths={"test_platform_slug": scope}),
    )
    assert response.status_code == 422
    with sync_session.begin() as session:
        assert session.query(ScanOperation).count() == 0


def test_missing_and_symlink_scope_do_not_reach_scanner(
    client, headers, mapped, monkeypatch, tmp_path
):
    from endpoints.sockets import scan

    called = []
    monkeypatch.setattr(
        scan, "execute_mixed_scans", lambda *a, **k: called.append(True)
    )
    with sync_session.begin() as session:
        root = session.get(StorageRoot, mapped.storage_root_id)
        root.container_path = str(tmp_path)
    (tmp_path / "PC").mkdir()
    (tmp_path / "PC/escape").symlink_to("/etc", target_is_directory=True)
    # Force the root-health observation only; the actual no-follow resolver remains live.
    from handler.filesystem.storage_resolver import StorageRootHealthSnapshot
    from handler.storage import read_context

    monkeypatch.setattr(
        read_context,
        "get_storage_root_health_snapshot",
        lambda root: StorageRootHealthSnapshot(
            True, True, True, datetime.now(timezone.utc), None
        ),
    )
    monkeypatch.setattr(
        scan,
        "get_storage_root_health_snapshot",
        lambda root: StorageRootHealthSnapshot(
            True, True, True, datetime.now(timezone.utc), None
        ),
    )
    import os

    from handler.filesystem import storage_resolver

    original_access = os.access
    monkeypatch.setattr(
        storage_resolver.os,
        "access",
        lambda path, mode: False if mode == os.W_OK else original_access(path, mode),
    )
    for scope in ("escape", "missing"):
        response = client.post(
            BASE,
            headers=headers,
            json=request_body(
                mapped, filesystem_scope_paths={"test_platform_slug": scope}
            ),
        )
        assert response.status_code == 409
    assert not called


def test_owner_resume_replays_one_fenced_continuation(client, other_headers, mapped):
    accepted = client.post(
        BASE, headers=other_headers, json=request_body(mapped)
    ).json()
    url = BASE + "/" + accepted["id"]
    stopped = client.post(
        url + "/cancel",
        headers=other_headers,
        json={"request_key": "stop-key", "expected_version": accepted["version"]},
    ).json()
    assert stopped["state"] == "cancelled"
    assert stopped["intentional_cancel"] is True
    payload = {"request_key": "resume-key", "expected_version": stopped["version"]}
    resumed = client.post(url + "/resume", headers=other_headers, json=payload)
    assert resumed.status_code == 200
    assert (
        resumed.json()["state"] == "recovering"
        and not resumed.json()["dispatch_pending"]
    )
    assert (
        client.post(url + "/resume", headers=other_headers, json=payload).json()
        == resumed.json()
    )
    assert (
        client.post(
            url + "/resume",
            headers=other_headers,
            json=payload | {"request_key": "other-resume"},
        ).status_code
        == 409
    )


@pytest.mark.parametrize("admin_control", [False, True])
def test_metadata_retry_is_bounded_to_failed_items(
    client, other_headers, headers, mapped, admin_control
):
    from handler.database.scan_operations_handler import DBScanOperationsHandler

    repo = DBScanOperationsHandler()
    accepted = client.post(
        BASE, headers=other_headers, json=request_body(mapped)
    ).json()
    row = ScanOperationSnapshot.model_validate(accepted)
    row = repo.claim_attempt(row.id, row.version, "worker")
    row = repo.record_item(
        row.id,
        row.version,
        row.attempt_id,
        dict(
            target_key="fixture",
            mapping_id=mapped.id,
            expected_revision=1,
            relative_path="Phase34-Synthetic.bin",
            provider="igdb",
            outcome="warning",
            cause_code="provider_timeout",
        ),
    )
    row = repo.transition(
        row.id, row.version, row.attempt_id, "completed-with-warnings"
    )
    control = headers if admin_control else other_headers
    url = BASE + "/" + row.id + "/retry-metadata"
    body = {
        "request_key": "retry-key",
        "expected_version": row.version,
        "item_ids": [row.items[0].id],
    }
    assert (
        client.post(
            url, headers=control, json=body | {"item_ids": [999999]}
        ).status_code
        == 409
    )
    result = client.post(url, headers=control, json=body)
    assert result.status_code == 200 and result.json()["state"] == "recovering"
    assert client.post(url, headers=control, json=body).json() == result.json()
    assert (
        client.post(
            url, headers=control, json=body | {"item_ids": [999999]}
        ).status_code
        == 409
    )


def test_existing_rq_projection_reports_real_job_status(client, headers, mapped):
    from rq.job import Job

    from handler.redis_handler import redis_client
    from tasks.tasks import TaskType

    accepted = client.post(BASE, headers=headers, json=request_body(mapped)).json()
    row = ScanOperationSnapshot.model_validate(accepted)
    job = Job.fetch(row.job_id, connection=redis_client)
    assert job.func_name == "handler.scan_operation_worker.run_scan_operation"
    job.meta.update({"task_type": TaskType.SCAN, "scan_stats": {"total_roms": 1}})
    job.save_meta()
    response = client.get(BASE + "/" + row.id, headers=headers)
    assert response.status_code == 200
    assert response.json()["queue_condition"] == "available"
    assert response.json()["queue_status"] == "queued"
    assert (
        response.json()["state"] == "queued"
        and response.json()["version"] == row.version
    )


def test_enqueued_redis_outage_is_distinct_from_job_expiry(
    client, headers, mapped, monkeypatch
):
    from redis.exceptions import ConnectionError
    from rq.exceptions import NoSuchJobError
    from rq.job import Job

    accepted = client.post(BASE, headers=headers, json=request_body(mapped)).json()
    row = ScanOperationSnapshot.model_validate(accepted)
    url = BASE + "/" + row.id
    for error, expected in [
        (ConnectionError(), "unavailable"),
        (NoSuchJobError(), "expired"),
    ]:
        monkeypatch.setattr(
            Job, "fetch", lambda *a, error=error, **k: (_ for _ in ()).throw(error)
        )
        response = client.get(url, headers=headers)
        assert (
            response.status_code == 200
            and response.json()["queue_condition"] == expected
        )
        assert response.json()["state"] == "queued" and response.json()["id"] == row.id


def test_pending_acceptance_survives_redis_failure(
    client, headers, mapped, monkeypatch
):
    from redis.exceptions import ConnectionError
    from rq.job import Job

    monkeypatch.setattr(
        Job, "fetch", lambda *a, **k: (_ for _ in ()).throw(ConnectionError())
    )
    accepted = client.post(BASE, headers=headers, json=request_body(mapped))
    assert accepted.status_code == 202
    assert client.get(BASE + "/by-request/request-key", headers=headers).json()[
        "dispatch_pending"
    ]


@pytest.fixture
def csrf_client(admin_user):
    from endpoints.scan_operations import router

    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    app.include_router(router, prefix="/api")
    app.add_middleware(
        CSRFMiddleware, secret=ROMM_AUTH_SECRET_KEY, cookie_name="romm_csrftoken"
    )
    app.add_middleware(AuthenticationMiddleware, backend=HybridAuthBackend())
    app.add_middleware(RedisSessionMiddleware, session_cookie=SESSION_COOKIE_NAME)
    with TestClient(app) as client:
        login = client.post("/api/login", auth=("test_admin", "test_admin_password"))
        assert login.status_code == 200
        client.get(BASE + "/active")
        yield client


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/" + IDENTITY + "/cancel",
        "/" + IDENTITY + "/resume",
        "/" + IDENTITY + "/retry-metadata",
    ],
)
def test_cookie_mutations_require_real_csrf(csrf_client, mapped, path):
    payload = (
        request_body(mapped)
        if not path
        else {"request_key": "control-key", "expected_version": 1, "item_ids": [1]}
    )
    response = csrf_client.post(BASE + path, json=payload)
    assert response.status_code == 403 and "CSRF" in response.text


def test_cookie_acceptance_with_valid_csrf(csrf_client, mapped):
    token = csrf_client.cookies.get("romm_csrftoken")
    response = csrf_client.post(
        BASE, headers={"x-csrftoken": token}, json=request_body(mapped)
    )
    assert response.status_code == 202


def test_subfolder_and_provider_policies_are_frozen_and_replayable(
    client, headers, mapped
):
    with sync_session.begin() as session:
        session.get(PlatformStorageMapping, mapped.id).relative_path = ""
    body = request_body(
        mapped,
        type="update",
        apis=["steam", "igdb"],
        metadata_only=True,
        metadata_locale="de_DE",
        filesystem_scope_paths={"test_platform_slug": "PC"},
    )
    response = client.post(BASE, headers=headers, json=body)
    assert response.status_code == 202
    identity = response.json()["id"]
    with sync_session.begin() as session:
        stored = session.get(ScanOperation, identity).command
        assert (
            stored["request"]["metadata_only"]
            and stored["request"]["metadata_locale"] == "de_DE"
        )
        assert stored["request"]["apis"] == ["igdb", "steam"]
        assert stored["commands"][0]["options"] == [["relative_path", "PC"]]
        assert stored["commands"][0]["expected_revision"] == 1
        session.get(PlatformStorageMapping, mapped.id).version += 1
    assert (
        client.post(
            BASE, headers=headers, json=body | {"apis": ["igdb", "steam"]}
        ).json()
        == response.json()
    )
    assert (
        client.get(BASE + "/" + identity + "?limit=0", headers=headers).status_code
        == 422
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"platforms": [999999]},
        {"apis": ["unknown_provider"]},
        {"filesystem_scope_paths": {"unselected": "PC"}},
    ],
)
def test_invalid_selection_cannot_create_partial_intent(
    client, headers, mapped, changes
):
    response = client.post(BASE, headers=headers, json=request_body(mapped, **changes))
    assert response.status_code == 409
    with sync_session.begin() as session:
        assert session.query(ScanOperation).count() == 0


def test_malformed_identity_and_extra_authority(client, headers, mapped):
    for key in ("../x", "A", "x" * 97):
        assert (
            client.post(
                BASE, headers=headers, json=request_body(mapped, request_key=key)
            ).status_code
            == 422
        )
    assert (
        client.post(
            BASE, headers=headers, json=request_body(mapped, actor_id=1)
        ).status_code
        == 422
    )
    assert client.get(BASE + "/not-a-uuid", headers=headers).status_code == 422
    assert client.get(BASE + "/" + str(uuid4()), headers=headers).status_code == 404
