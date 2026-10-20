"""Real SQL commit fencing against claimed durable attempts."""

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import datetime, timedelta
from threading import Event
from uuid import uuid4

import pytest
from tests.handler.test_scan_operations import command as command  # noqa: F401
from tests.handler.test_scan_operations import (
    repository,
    running,
)

from decorators.database import begin_session
from handler.database.base_handler import sync_session
from models.platform import Platform
from models.scan_operation import ScanExecutionSlot, ScanOperation


def api():
    try:
        from handler.database import scan_write_fence
    except ImportError:
        pytest.fail("claimed scan has no transaction fence API")
    return scan_write_fence


@pytest.fixture
def attempt(admin_user, command):
    return running(repository(), admin_user, command)


def context(row, **changes):
    values = dict(operation_id=row.id, attempt_id=row.attempt_id, lease_owner="worker")
    return api().ScanWriteContext(**(values | changes))


@begin_session
def mutate(identity, name, *, session=None):
    session.get(Platform, identity).name = name


@begin_session
def nested(identity, name, *, session=None):
    mutate(identity, name, session=session)


def name(identity):
    with sync_session.begin() as session:
        return session.get(Platform, identity).name


@pytest.mark.parametrize("explicit", [False, True])
def test_running_commit_uses_actual_transaction(attempt, platform, explicit):
    fence = api()
    with fence.bind_scan_write_context(context(attempt)):
        if explicit:
            with sync_session.begin() as session:
                nested(platform.id, "committed", session=session)
        else:
            nested(platform.id, "committed")
    assert name(platform.id) == "committed"
    with pytest.raises(fence.ScanWriteRejected, match="context"):
        fence.require_scan_write_context()


def test_unrelated_transaction_preserves_contract(platform):
    mutate(platform.id, "non-scan")
    assert name(platform.id) == "non-scan"


@pytest.mark.parametrize(
    "invalid", ["attempt", "owner", "lease", "slot", "state", "stop", "version"]
)
def test_revoked_before_mutation_and_autoflush(attempt, platform, invalid):
    fence = api()
    bound = context(attempt)
    with sync_session.begin() as session:
        row = session.get(ScanOperation, attempt.id)
        if invalid == "lease":
            row.lease_expires_at = datetime.now() - timedelta(seconds=1)
        elif invalid == "slot":
            session.get(ScanExecutionSlot, 1).active_operation_id = None
        elif invalid == "state":
            row.state = "interrupted"
        elif invalid == "stop":
            row.intentional_cancel = True
    if invalid == "attempt":
        bound = context(attempt, attempt_id=str(uuid4()))
    elif invalid == "owner":
        bound = context(attempt, lease_owner="foreign-worker")
    before = name(platform.id)
    with pytest.raises(fence.ScanWriteRejected):
        with fence.bind_scan_write_context(bound):
            with sync_session.begin() as session:
                session.get(Platform, platform.id).name = "must-not-autoflush"
                with fence.checked_scan_write(
                    session, expected_version=0 if invalid == "version" else None
                ):
                    session.flush()
    assert name(platform.id) == before


def test_before_commit_rechecks_after_binding_exit(attempt, platform):
    fence = api()
    before = name(platform.id)
    with pytest.raises(fence.ScanWriteRejected):
        with sync_session.begin() as session:
            with fence.bind_scan_write_context(context(attempt)):
                mutate(platform.id, "uncommitted", session=session)
            # Simulate expiration after work, before the actual outer commit.
            session.execute(
                ScanOperation.__table__.update()
                .where(ScanOperation.id == attempt.id)
                .values(lease_expires_at=datetime.now() - timedelta(seconds=1))
            )
    assert name(platform.id) == before


def test_latest_locked_version_survives_heartbeat(attempt, platform):
    fence = api()
    updated = repository().renew_lease(
        attempt.id, attempt.version, attempt.attempt_id, "worker"
    )
    with fence.bind_scan_write_context(context(attempt)):
        with sync_session.begin() as session:
            with fence.checked_scan_write(session) as row:
                assert row.version == updated.version
                nested(platform.id, "after-heartbeat", session=session)
    assert name(platform.id) == "after-heartbeat"


@pytest.mark.parametrize("cancel_first", [True, False])
def test_two_connection_cancel_commit_order(
    attempt, platform, admin_user, cancel_first
):
    fence = api()
    ready, release = Event(), Event()
    before = name(platform.id)

    def writer():
        with fence.bind_scan_write_context(context(attempt)):
            if cancel_first:
                ready.set()
                assert release.wait(10)
                with pytest.raises(fence.ScanWriteRejected):
                    mutate(platform.id, "revoked")
            else:
                with sync_session.begin() as session:
                    with fence.checked_scan_write(session):
                        nested(platform.id, "valid-commit", session=session)
                        ready.set()
                        assert release.wait(10)

    with ThreadPoolExecutor(max_workers=2) as pool:
        work = pool.submit(writer)
        assert ready.wait(10)
        if cancel_first:
            repository().request_cancel(
                attempt.id, admin_user.id, attempt.version, "cancel-first"
            )
            release.set()
        else:
            # Cancellation begins on another connection while the writer holds the slot.
            cancel_started = Event()

            def cancel():
                cancel_started.set()
                return repository().request_cancel(
                    attempt.id, admin_user.id, attempt.version, "commit-first"
                )

            cancellation = pool.submit(cancel)
            assert cancel_started.wait(10)
            release.set()
            cancellation.result(timeout=15)
        work.result(timeout=15)
    assert name(platform.id) == (before if cancel_first else "valid-commit")
    with fence.bind_scan_write_context(context(attempt)):
        with pytest.raises(fence.ScanWriteRejected):
            mutate(platform.id, "late-write")


def test_context_disposal_and_explicit_thread_propagation(attempt):
    fence = api()
    with pytest.raises(RuntimeError, match="deliberate"):
        with fence.bind_scan_write_context(context(attempt)):
            raise RuntimeError("deliberate")
    with pytest.raises(fence.ScanWriteRejected):
        fence.require_scan_write_context()
    with fence.bind_scan_write_context(context(attempt)):
        copied = copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with pytest.raises(fence.ScanWriteRejected):
                pool.submit(fence.require_scan_write_context).result(timeout=10)
            assert pool.submit(copied.run, fence.require_scan_write_context).result(
                timeout=10
            ) == context(attempt)
    with pytest.raises(fence.ScanWriteRejected):
        fence.require_scan_write_context()
