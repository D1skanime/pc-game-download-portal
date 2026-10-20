from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from tests.handler.test_scan_operations import command as command

from handler import scan_operation_worker as worker
from handler.database.scan_operations_handler import utc_now
from handler.database.scan_write_fence import (
    ScanWriteContext,
    ScanWriteRejected,
    bind_scan_write_context,
)


def state(**changes):
    return {
        "state": "running",
        "attempt_id": "attempt",
        "lease_owner": "owner",
        "intentional_cancel": False,
        "lease_expires_at": utc_now() + timedelta(seconds=30),
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "stopping"},
        {"attempt_id": "replacement"},
        {"lease_owner": "other"},
        {"lease_expires_at": utc_now() - timedelta(seconds=1)},
        {"intentional_cancel": True},
    ],
)
def test_stale_worker_boundary_rejects_before_progress(monkeypatch, changes):
    repository = SimpleNamespace(execution=lambda identity: state(**changes))
    monkeypatch.setattr(worker, "DBScanOperationsHandler", lambda: repository)
    with bind_scan_write_context(ScanWriteContext("operation", "attempt", "owner")):
        with pytest.raises(ScanWriteRejected):
            worker.check_worker_boundary()


def test_finish_never_mutates_replacement_attempt():
    repository = SimpleNamespace(
        execution=lambda identity: state(attempt_id="replacement"), transition=Mock()
    )
    assert (
        worker._finish(
            repository,
            "operation",
            ScanWriteContext("operation", "attempt", "owner"),
            "completed",
        )
        is None
    )
    repository.transition.assert_not_called()


def test_stopped_acknowledgement_uses_latest_version(monkeypatch):
    monkeypatch.setattr(
        "handler.filesystem.owned_content_proof.owned_verifier_idle", lambda: True
    )
    repository = SimpleNamespace(
        execution=lambda identity: state(state="stopping", version=7),
        confirm_stopped=Mock(),
    )
    worker._finish(
        repository,
        "operation",
        ScanWriteContext("operation", "attempt", "owner"),
        "completed",
    )
    repository.confirm_stopped.assert_called_once_with("operation", 7, "attempt")


@pytest.mark.asyncio
async def test_inner_scanner_cannot_emit_terminal_completion(monkeypatch):
    from unittest.mock import AsyncMock

    monkeypatch.setattr(worker, "check_worker_boundary", lambda: None)
    manager = SimpleNamespace(emit=AsyncMock())
    wrapped = worker.AttemptSocketManager(manager)
    await wrapped.emit("scan:done", {"scanned_roms": 1})
    manager.emit.assert_not_awaited()
    await wrapped.emit("scan:scanning_rom", {"id": 1})
    manager.emit.assert_awaited_once()


def test_stop_is_not_acknowledged_while_verifier_exit_is_uncertain(monkeypatch):
    monkeypatch.setattr(
        "handler.filesystem.owned_content_proof.owned_verifier_idle", lambda: False
    )
    repository = SimpleNamespace(
        execution=lambda identity: state(state="stopping", version=7),
        confirm_stopped=Mock(),
        note_execution_cause=Mock(),
    )
    worker._finish(
        repository,
        "operation",
        ScanWriteContext("operation", "attempt", "owner"),
        "completed",
    )
    repository.confirm_stopped.assert_not_called()
    repository.note_execution_cause.assert_called_once_with(
        "operation", 7, "worker_stop_unconfirmed", "check_worker"
    )


@pytest.mark.parametrize(
    "reject, commit_fail", [(True, False), (False, True), (False, False)]
)
def test_stable_output_preserves_linearization_point(monkeypatch, reject, commit_fail):
    from contextlib import contextmanager, nullcontext
    from io import BytesIO

    from sqlalchemy.exc import SQLAlchemyError

    from handler.filesystem import scan_output_publication as publication
    from handler.filesystem.storage_access import IndeterminateOwnedPublicationError

    stable = {"bytes": b"old"}

    class Prepared:
        def __init__(self):
            self.file = BytesIO()

        def seal(self):
            pass

        def publish(self, *, final_authority_check=None):
            if final_authority_check is not None:
                final_authority_check()
            stable["bytes"] = self.file.getvalue()

        def abort(self):
            pass

    prepared = Prepared()
    destination = SimpleNamespace(prepare_binary_file=lambda: prepared)

    @contextmanager
    def transaction():
        yield object()
        if commit_fail:
            raise SQLAlchemyError("acknowledgement failure")

    @contextmanager
    def checked(session):
        if reject:
            raise ScanWriteRejected("revoked")
        yield

    monkeypatch.setattr(
        publication, "content_proof_scope", lambda **kwargs: nullcontext()
    )
    monkeypatch.setattr(publication, "owned_writer_domain", nullcontext)
    monkeypatch.setattr(
        publication, "open_owned_access", lambda *args: nullcontext(destination)
    )
    monkeypatch.setattr(publication, "sync_session", SimpleNamespace(begin=transaction))
    monkeypatch.setattr(publication, "checked_scan_write", checked)
    monkeypatch.setattr(publication, "current_scan_write_context", lambda: object())
    if reject:
        with pytest.raises(ScanWriteRejected):
            publication.publish_scan_output(object(), "stable.json", b"complete-new")
        assert stable["bytes"] == b"old"
    elif commit_fail:
        with pytest.raises(IndeterminateOwnedPublicationError):
            publication.publish_scan_output(object(), "stable.json", b"complete-new")
        assert stable["bytes"] == b"complete-new"
    else:
        publication.publish_scan_output(object(), "stable.json", b"complete-new")
        assert stable["bytes"] == b"complete-new"


def test_indeterminate_publication_is_blocked_for_reconciliation():
    from handler.filesystem.storage_access import IndeterminateOwnedPublicationError

    assert worker._failure_outcome(IndeterminateOwnedPublicationError()) == (
        "blocked",
        "indeterminate_owned_publication",
        "check_storage",
    )


def test_live_progress_and_heartbeat_preserve_cancel_command_version(
    admin_user, command
):
    from tests.handler.test_scan_operations import running

    from handler.database.scan_operations_handler import DBScanOperationsHandler

    repository = DBScanOperationsHandler()
    attempt = running(repository, admin_user, command)
    context = ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    with bind_scan_write_context(context):
        worker.persist_scan_stats({"scanned_roms": 2})
    assert repository.get_by_id(attempt.id, admin_user.id).scan_stats == {}
    with bind_scan_write_context(context), worker.bind_worker_runtime(context):
        worker.persist_scan_stats({"scanned_roms": 3})
        repository.renew_worker_lease(context)
    current = repository.get_by_id(attempt.id, admin_user.id)
    assert current.version == attempt.version
    assert current.scan_stats == {"scanned_roms": 3}
    stopped = repository.request_cancel(
        attempt.id, admin_user.id, attempt.version, "cancel-after-progress"
    )
    assert stopped.state == "stopping"
