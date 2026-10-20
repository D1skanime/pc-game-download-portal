from unittest.mock import Mock

from handler import scan_operation_recovery as recovery


def execution(**changes):
    return {
        "state": "interrupted",
        "intentional_cancel": False,
        "version": 3,
        "attempt_id": "old",
        "dispatch_due": None,
        "checkpoint": {},
        "command": {"commands": []},
        **changes,
    }


def test_unprovable_interrupted_scope_blocks_without_dispatch(monkeypatch):
    monkeypatch.setattr(recovery, "worker_exit_confirmed", lambda execution: True)
    repository = Mock()
    repository.execution.return_value = execution()
    recovery.recover_operation("operation", repository=repository)
    repository.recovery_ready.assert_not_called()
    repository.transition.assert_called_once_with(
        "operation",
        3,
        "old",
        "blocked",
        cause_code="source_unverifiable",
        next_action="new_scan",
    )


def test_trusted_unchanged_fixture_resumes_after_revocation(monkeypatch):
    monkeypatch.setattr(recovery, "worker_exit_confirmed", lambda execution: True)
    repository = Mock()
    repository.execution.side_effect = [execution(state="running"), execution()]
    repository.fence_lost_worker.return_value = True
    recovery.recover_operation(
        "operation", repository=repository, checkpoint_validator=lambda value: value
    )
    repository.fence_lost_worker.assert_called_once_with("operation")
    repository.recovery_ready.assert_called_once_with("operation", 3)


def test_live_attempt_is_not_reclaimed():
    repository = Mock()
    repository.execution.return_value = execution(state="running")
    repository.fence_lost_worker.return_value = False
    recovery.recover_operation("operation", repository=repository)
    repository.recovery_ready.assert_not_called()
    repository.transition.assert_not_called()


def test_intentional_cancel_survives_restart():
    repository = Mock()
    repository.execution.return_value = execution(
        state="cancelled", intentional_cancel=True
    )
    recovery.recover_operation("operation", repository=repository)
    repository.recovery_ready.assert_not_called()
    repository.transition.assert_not_called()


def test_expired_lease_does_not_prove_worker_stopped(monkeypatch):
    monkeypatch.setattr(recovery, "worker_exit_confirmed", lambda value: False)
    repository = Mock()
    repository.execution.return_value = execution(
        state="stopping", lease_expires_at=None
    )
    recovery.recover_operation("operation", repository=repository)
    repository.confirm_stopped.assert_not_called()
    repository.note_execution_cause.assert_called_once_with(
        "operation", 3, "worker_stop_unconfirmed", "check_worker"
    )
