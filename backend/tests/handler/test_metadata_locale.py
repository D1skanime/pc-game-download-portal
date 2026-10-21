"""Durable locale contracts against the existing SQL operation owner."""

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tests.handler.test_scan_operations import command as command

from config.config_manager import config_manager as cm
from handler.database.base_handler import sync_session
from handler.database.scan_operations_handler import (
    DBScanOperationsHandler,
    OperationConflict,
    payload_digest,
)
from handler.scan_operation_recovery import decode_command
from models.scan_operation import ScanOperation
from tasks import scan_operation_dispatch as dispatch


@pytest.fixture
def preference(monkeypatch):
    config = copy.deepcopy(cm.get_config())
    config.SCAN_LANGUAGE_PRIORITY = ["fr", "en"]
    monkeypatch.setattr(cm, "get_config", lambda: config)
    return config


@pytest.fixture
def committed_preference(tmp_path, monkeypatch):
    prior = copy.deepcopy(cm.__dict__)
    path = tmp_path / "config.yml"
    path.write_text("scan:\n  priority:\n    language: [en]\n")
    monkeypatch.setattr(cm, "config_file", str(path))
    monkeypatch.setattr(cm, "_config_file_writable", True)
    cm.get_config()
    try:
        assert cm.update_scan_language(["fr"], ["en"]) == ["fr", "en"]
        yield path
    finally:
        cm.__dict__.clear()
        cm.__dict__.update(prior)


def request(command, policy):
    return {
        "commands": copy.deepcopy(command["commands"]),
        "request": copy.deepcopy(policy),
    }


def queued(repository, accepted):
    claim = repository.claim_dispatch(accepted.id, accepted.version, "dispatcher")
    return repository.mark_enqueued(claim.id, claim.version, "dispatcher")


@pytest.mark.parametrize(
    "explicit,priorities,expected",
    [
        ("de-CH", ["fr"], "de"),
        ("german", ["fr"], "de"),
        ("fr_CA", ["de"], "fr"),
        (None, ["bad", "french"], "fr"),
        ("", ["de"], "de"),
        ("bogus", ["fr"], "fr"),
        (None, [], "en"),
        (None, ["unsupported"], "en"),
    ],
)
def test_acceptance_captures_normalized_preference(
    admin_user, command, preference, explicit, priorities, expected
):
    preference.SCAN_LANGUAGE_PRIORITY = priorities
    envelope = request(command, {"metadata_locale": explicit, "apis": ["steam"]})
    original = copy.deepcopy(envelope)
    repository = DBScanOperationsHandler()
    accepted = repository.accept(admin_user.id, "captured-locale", envelope)
    stored = repository.execution(accepted.id)["command"]
    assert stored["request"]["metadata_locale"] == expected
    assert envelope == original
    with sync_session.begin() as session:
        assert session.get(ScanOperation, accepted.id).payload_digest == payload_digest(
            original["request"]
        )


def test_replay_preserves_snapshot_but_explicit_locale_change_conflicts(
    admin_user, command, preference
):
    repository = DBScanOperationsHandler()
    envelope = request(command, {"apis": ["steam"]})
    accepted = repository.accept(
        admin_user.id, "same-key", envelope, payload_digest(envelope["request"])
    )
    preference.SCAN_LANGUAGE_PRIORITY = ["de"]
    assert repository.accept(admin_user.id, "same-key", envelope).id == accepted.id
    assert (
        repository.execution(accepted.id)["command"]["request"]["metadata_locale"]
        == "fr"
    )
    with pytest.raises(OperationConflict, match="request_payload_conflict"):
        repository.accept(
            admin_user.id,
            "same-key",
            request(command, {"apis": ["steam"], "metadata_locale": "de"}),
        )


def test_explicit_client_locale_remains_part_of_request_identity(
    admin_user, command, preference
):
    repository = DBScanOperationsHandler()
    repository.accept(
        admin_user.id, "explicit-key", request(command, {"metadata_locale": "de-CH"})
    )
    with pytest.raises(OperationConflict, match="request_payload_conflict"):
        repository.accept(
            admin_user.id, "explicit-key", request(command, {"metadata_locale": "fr"})
        )


def test_legacy_snapshot_is_version_fenced_and_survives_resume(
    admin_user, command, preference
):
    repository = DBScanOperationsHandler()
    accepted = repository.accept(
        admin_user.id, "legacy-key", request(command, {"apis": ["steam"]})
    )
    ready = queued(repository, accepted)
    with sync_session.begin() as session:
        row = session.get(ScanOperation, accepted.id)
        legacy = copy.deepcopy(row.command)
        legacy["request"].pop("metadata_locale", None)
        row.command = legacy
        digest = row.payload_digest
    with pytest.raises(OperationConflict, match="stale_operation"):
        repository.claim_attempt(ready.id, ready.version - 1, "stale")
    assert "metadata_locale" not in repository.execution(ready.id)["command"]["request"]
    preference.SCAN_LANGUAGE_PRIORITY = ["de"]
    running = repository.claim_attempt(ready.id, ready.version, "worker")
    assert running.version == ready.version + 1
    assert (
        repository.execution(ready.id)["command"]["request"]["metadata_locale"] == "de"
    )
    preference.SCAN_LANGUAGE_PRIORITY = ["fr"]
    stopping = repository.request_cancel(
        running.id, admin_user.id, running.version, "cancel-locale"
    )
    stopped = repository.confirm_stopped(
        stopping.id, stopping.version, running.attempt_id
    )
    resumed = repository.request_resume(
        stopped.id, admin_user.id, stopped.version, "resume-locale"
    )
    repository.recovery_ready(resumed.id, resumed.version)
    resumed = repository.get_by_id(resumed.id, admin_user.id)
    again = queued(repository, resumed)
    repository.claim_attempt(again.id, again.version, "replacement")
    assert (
        repository.execution(again.id)["command"]["request"]["metadata_locale"] == "de"
    )
    with sync_session.begin() as session:
        assert session.get(ScanOperation, ready.id).payload_digest == digest


@pytest.mark.asyncio
async def test_actual_scheduled_acceptance_uses_global_not_actor_profile(
    admin_user, command, committed_preference, monkeypatch
):
    from models.user import User
    from tasks.scheduled import scan_library

    with sync_session.begin() as session:
        session.get(User, admin_user.id).ui_settings = {"locale": "de-CH"}
    monkeypatch.setattr(scan_library, "ENABLE_SCHEDULED_RESCAN", True)
    monkeypatch.setattr(
        scan_library,
        "mapping_scan_commands",
        lambda *args, **kwargs: [
            decode_command(command["commands"][0] | {"trigger": "scheduled"})
        ],
    )
    monkeypatch.setattr(dispatch, "dispatch_operation", lambda *args, **kwargs: False)
    result = await scan_library.scan_library_task.run()
    repository = DBScanOperationsHandler()
    state = repository.execution(result["operation_id"])
    assert state["actor_id"] == admin_user.id
    assert state["command"]["request"]["metadata_locale"] == "fr"
    assert cm.update_scan_language(["de"], ["fr", "en"]) == ["de", "en", "fr"]
    assert (
        repository.execution(result["operation_id"])["command"]["request"][
            "metadata_locale"
        ]
        == "fr"
    )


@pytest.mark.asyncio
async def test_actual_worker_and_retry_use_only_accepted_snapshot(
    admin_user, command, preference, monkeypatch
):
    from tests.handler.test_windows_quick_execution import binding

    from endpoints.sockets import scan
    from handler import scan_operation_worker as worker
    from handler import scan_retry_execution as retry

    repository = DBScanOperationsHandler()
    accepted = repository.accept(
        admin_user.id,
        "worker-locale",
        request(command, {"apis": ["steam"], "metadata_locale": "de-CH"}),
    )
    ready = queued(repository, accepted)
    preference.SCAN_LANGUAGE_PRIORITY = ["fr"]
    observed = []

    async def scan_mapping(*args, **kwargs):
        observed.append(kwargs["metadata_locale"])
        preference.SCAN_LANGUAGE_PRIORITY = ["en"]
        return scan.ScanStats()

    async def run_retries(self, scanner):
        before = self.identity(binding(), "steam", "Synthetic")
        preference.SCAN_LANGUAGE_PRIORITY = ["fr"]
        after = self.identity(binding(), "steam", "Synthetic")
        assert before == after
        assert after.locale == "de"

    monkeypatch.setattr(scan, "execute_mapping_scan", scan_mapping)
    monkeypatch.setattr(
        scan, "_get_socket_manager", lambda: SimpleNamespace(emit=AsyncMock())
    )
    monkeypatch.setattr(worker, "_heartbeat", lambda *args: None)
    monkeypatch.setattr(retry, "invalidate_refresh_baselines", lambda *args: None)
    monkeypatch.setattr(retry.RetryCoordinator, "run", run_retries)
    await worker.run_scan_operation(ready.id)
    assert observed == ["de"]
    assert repository.execution(ready.id)["state"] == "completed"
    assert (
        repository.execution(ready.id)["command"]["request"]["metadata_locale"] == "de"
    )
