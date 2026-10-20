import httpx
import pytest

from handler.database.scan_write_fence import ScanWriteRejected
from handler.scan_metadata_result import classify_provider_failure

pytest_plugins = ["tests.handler.test_scan_operations"]


@pytest.mark.parametrize(
    "error, code",
    [
        (TimeoutError(), "metadata_timeout"),
        (httpx.ConnectError("provider down"), "metadata_provider_unavailable"),
        (httpx.DecodingError("invalid bytes"), "malformed_provider_response"),
    ],
)
def test_provider_failures_have_safe_retry_codes(error, code):
    assert classify_provider_failure(error) == code


@pytest.mark.parametrize(
    "error",
    [
        ValueError("programming failure"),
        RuntimeError("failure"),
        ScanWriteRejected("revoked"),
    ],
)
def test_programming_and_authority_errors_propagate(error):
    with pytest.raises(type(error)):
        classify_provider_failure(error)


@pytest.mark.parametrize(
    "status, code",
    [(429, "metadata_rate_limited"), (503, "metadata_provider_unavailable")],
)
def test_retryable_http_errors(status, code):
    request = httpx.Request("GET", "https://provider.invalid")
    response = httpx.Response(status, request=request)
    assert (
        classify_provider_failure(
            httpx.HTTPStatusError("failed", request=request, response=response)
        )
        == code
    )


def test_provider_auth_error_is_terminal():
    request = httpx.Request("GET", "https://provider.invalid")
    response = httpx.Response(401, request=request)
    with pytest.raises(httpx.HTTPStatusError):
        classify_provider_failure(
            httpx.HTTPStatusError("unauthorized", request=request, response=response)
        )


def test_provider_diagnostics_persist_real_sql_and_keep_successful_items(
    admin_user, command
):
    from tests.handler.test_scan_operations import running

    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from handler.database.scan_write_fence import (
        ScanWriteContext,
        bind_scan_write_context,
    )
    from handler.scan_metadata_result import (
        bind_metadata_results,
        record_provider_result,
    )
    from handler.scan_operation_checkpoint import bind_checkpoint_command
    from handler.scan_operation_recovery import decode_command

    repository = DBScanOperationsHandler()
    attempt = running(repository, admin_user, command)
    context = ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    with bind_scan_write_context(context), bind_checkpoint_command(
        decode_command(command["commands"][0])
    ), bind_metadata_results():
        record_provider_result("igdb", "Affected.bin", error=TimeoutError())
        record_provider_result("igdb", "Healthy.bin")
    saved = repository.get_by_id(attempt.id, admin_user.id)
    assert len(saved.items) == 2
    assert {
        (item.relative_path, item.outcome, item.cause_code) for item in saved.items
    } == {
        ("Affected.bin", "warning", "metadata_timeout"),
        ("Healthy.bin", "completed", None),
    }
    assert repository.result_counts(attempt.id) == {
        "metadata_completed_items": 1,
        "metadata_warning_items": 1,
        "metadata_failed_items": 0,
    }


def test_worker_item_adapter_eliminates_heartbeat_snapshot_window(
    admin_user, command, monkeypatch
):
    from tests.handler.test_scan_operations import running

    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from handler.database.scan_write_fence import (
        ScanWriteContext,
        bind_scan_write_context,
    )
    from handler.scan_metadata_result import (
        bind_metadata_results,
        record_provider_result,
    )
    from handler.scan_operation_checkpoint import bind_checkpoint_command
    from handler.scan_operation_recovery import decode_command

    repository = DBScanOperationsHandler()
    attempt = running(repository, admin_user, command)
    heartbeat = repository.renew_lease(
        attempt.id, attempt.version, attempt.attempt_id, "worker"
    )
    original_execution = DBScanOperationsHandler.execution
    snapshots = []

    def interleave_heartbeat(self, identity):
        snapshot = original_execution(self, identity)
        self.renew_lease(
            identity, snapshot["version"], snapshot["attempt_id"], "worker"
        )
        snapshots.append(snapshot)
        return snapshot

    monkeypatch.setattr(DBScanOperationsHandler, "execution", interleave_heartbeat)
    context = ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    from handler.database.scan_operations_handler import OperationConflict

    def old_adapter(self, context, item, **kwargs):
        snapshot = self.execution(context.operation_id)
        return self.record_item(
            context.operation_id,
            snapshot["version"],
            context.attempt_id,
            item,
            **kwargs
        )

    with bind_scan_write_context(context), bind_checkpoint_command(
        decode_command(command["commands"][0])
    ), bind_metadata_results():
        with monkeypatch.context() as legacy:
            legacy.setattr(DBScanOperationsHandler, "record_worker_item", old_adapter)
            with pytest.raises(OperationConflict, match="stale_operation"):
                record_provider_result("igdb", "OldRace.bin", error=TimeoutError())
        assert snapshots
        snapshots.clear()
        record_provider_result("igdb", "Heartbeat.bin", error=TimeoutError())
    saved = repository.get_by_id(attempt.id, admin_user.id)
    assert saved.version == heartbeat.version + 1
    assert saved.items[0].cause_code == "metadata_timeout"
    assert not snapshots


def test_same_game_name_in_other_mapping_does_not_inherit_provider_warning(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from handler.database.scan_write_fence import (
        ScanWriteContext,
        bind_scan_write_context,
    )
    from handler.scan_metadata_result import (
        bind_metadata_results,
        record_auxiliary_warning,
        record_provider_result,
    )
    from handler.scan_operation_checkpoint import bind_checkpoint_command

    repository = SimpleNamespace(record_worker_item=Mock())
    monkeypatch.setattr(
        "handler.database.scan_operations_handler.DBScanOperationsHandler",
        lambda: repository,
    )
    with bind_metadata_results(), bind_scan_write_context(
        ScanWriteContext("operation", "attempt", "worker")
    ):
        with bind_checkpoint_command(
            SimpleNamespace(mapping_id=1, expected_revision=1, options=())
        ):
            record_auxiliary_warning("igdb", "Shared.bin", "metadata_timeout")
        with bind_checkpoint_command(
            SimpleNamespace(mapping_id=2, expected_revision=1, options=())
        ):
            record_provider_result("igdb", "Shared.bin")
    item = repository.record_worker_item.call_args.args[1]
    assert (
        item["mapping_id"] == 2
        and item["outcome"] == "completed"
        and item["cause_code"] is None
    )


@pytest.mark.asyncio
async def test_execution_distinguishes_guards_cache_match_fault_and_concurrency(
    monkeypatch,
):
    import asyncio

    from handler.scan_provider_execution import (
        bind_provider_results,
        gather_provider_results,
    )
    from utils.scan_provider_observation import (
        mark_provider_cached,
        mark_provider_invoked,
        observe_httpcore_trace,
    )

    async def fetch(mode):
        if mode == "noop":
            return {"igdb_id": None}
        mark_provider_invoked()
        await asyncio.sleep(0)
        if mode == "cache":
            mark_provider_cached()
            return {"igdb_id": 7}
        if mode == "fault":
            await observe_httpcore_trace("http11.send_request_headers.started", {})
            raise TimeoutError()
        if mode == "nomatch":
            await observe_httpcore_trace("http11.send_request_headers.started", {})
            return {"igdb_id": None}
        return {"igdb_id": 9}

    providers = ("disabled", "unsupported", "cached", "failed", "igdb", "matched")
    modes = ("noop", "noop", "cache", "fault", "nomatch", "match")
    with bind_provider_results() as observations:
        resolved = await gather_provider_results(
            providers,
            tuple((fetch(mode), {}) for mode in modes),
            "game",
            {"unsupported", "cached", "failed", "igdb", "matched"},
        )
    assert len(resolved) == 6 and resolved[3] == {}
    assert [
        (item.selected, item.invoked, item.cached, item.requests, item.outcome)
        for item in observations
    ] == [
        (False, False, False, 0, "not_invoked"),
        (True, False, False, 0, "not_invoked"),
        (True, True, True, 0, "matched"),
        (True, True, False, 1, "failed"),
        (True, True, False, 1, "no_match"),
        (True, True, False, 0, "matched"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [ValueError("bug"), ScanWriteRejected("stale")])
async def test_execution_keeps_unexpected_and_authority_failures_fatal(error):
    from handler.scan_provider_execution import gather_provider_results

    async def failure():
        raise error

    with pytest.raises(type(error)):
        await gather_provider_results(("igdb",), ((failure(), {}),), "game", {"igdb"})


@pytest.mark.asyncio
async def test_observation_uses_existing_checked_sql_write_and_rejects_cancel(
    admin_user, command
):
    from tests.handler.test_scan_operations import running

    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from handler.database.scan_write_fence import (
        ScanWriteContext,
        bind_scan_write_context,
    )
    from handler.scan_metadata_result import (
        bind_metadata_results,
        observe_provider_fetch,
        record_provider_result,
    )
    from handler.scan_operation_checkpoint import bind_checkpoint_command
    from handler.scan_operation_recovery import decode_command
    from utils.scan_provider_observation import (
        mark_provider_invoked,
        observe_httpcore_trace,
    )

    repository = DBScanOperationsHandler()
    attempt = running(repository, admin_user, command)
    context = ScanWriteContext(attempt.id, attempt.attempt_id, "worker")

    async def fetch():
        mark_provider_invoked()
        await observe_httpcore_trace("http11.send_request_headers.started", {})
        return {"igdb_id": None}

    with bind_scan_write_context(context), bind_checkpoint_command(
        decode_command(command["commands"][0])
    ), bind_metadata_results() as results:
        await observe_provider_fetch("igdb", fetch(), "Game.bin")
        record_provider_result("igdb", "Game.bin")
        observed = next(
            item["observation"] for item in results if "observation" in item
        )
        assert observed["requests"] == 1 and observed["outcome"] == "no_match"
        saved = repository.get_by_id(attempt.id, admin_user.id)
        assert (
            saved.items[0].outcome == "completed" and saved.items[0].cause_code is None
        )
        from sqlalchemy import select

        from handler.database.base_handler import sync_session
        from models.scan_operation import ScanOperationItem

        with sync_session.begin() as session:
            durable = session.scalar(
                select(ScanOperationItem).where(
                    ScanOperationItem.operation_id == attempt.id
                )
            )
            assert durable.checkpoint["provider_observation"] == observed
        repository.request_cancel(
            attempt.id, admin_user.id, saved.version, "cancel-observation"
        )
        with pytest.raises(ScanWriteRejected):
            record_provider_result("igdb", "Rejected.bin")
    assert len(repository.get_by_id(attempt.id, admin_user.id).items) == 1


def test_actual_gamelist_cache_hit_and_disabled_invocation():
    from pathlib import Path

    from handler.metadata.gamelist_handler import GamelistHandler
    from models.platform import Platform
    from utils.scan_provider_observation import (
        bind_provider_observation,
        mark_provider_invoked,
    )

    handler = GamelistHandler()
    cached = {"Game.bin": {"gamelist_id": "Game"}}
    handler._gamelist_cache[7] = cached
    with bind_provider_observation("gamelist", "Game.bin") as observation:
        mark_provider_invoked(enabled=False)
        assert not observation.invoked and not observation.eligible
        mark_provider_invoked(enabled=True)
        assert (
            handler._parse_gamelist_xml(Path("/never-read"), Platform(id=7)) is cached
        )
    assert observation.invoked and observation.cached and observation.requests == 0


@pytest.mark.asyncio
async def test_auxiliary_rate_limit_warning_is_failed_observation():
    from handler.scan_metadata_result import record_auxiliary_warning
    from handler.scan_provider_execution import bind_provider_results, execute_provider
    from utils.scan_provider_observation import mark_provider_invoked

    async def rate_limited():
        mark_provider_invoked()
        record_auxiliary_warning("ss", "Game.bin", "metadata_rate_limited")
        return {"ss_id": None}

    with bind_provider_results() as observations:
        await execute_provider("ss", rate_limited(), "Game.bin")
    assert observations[0].outcome == "failed"
    assert observations[0].requests == 0
