"""Operation-wide unknown retries share discovery and metadata dispatch."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tests.handler.test_scan_inventory_state import bound_game as bound_game
from tests.handler.test_scan_inventory_state import clear_inventory as clear_inventory
from tests.handler.test_scan_inventory_state import (
    inventory_attempt as inventory_attempt,
)
from tests.handler.test_windows_quick_execution import binding

from handler.scan_inventory_contracts import InventoryEvidence, QuickScanDecision
from handler.windows_quick_execution import WindowsQuickContext

pytest_plugins = ["tests.handler.test_scan_operations"]


def coordinator():
    from handler.scan_retry_execution import RetryCoordinator

    return RetryCoordinator(
        {"apis": ["igdb"]}, clock=lambda: datetime(2026, 10, 20, 12)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger", ["manual", "scheduled"])
@pytest.mark.parametrize("sources", [["igdb"], ["igdb", "moby"]])
async def test_retry_dispatch_uses_one_global_budget_and_metadata_only(
    monkeypatch, trigger, sources
):
    from dataclasses import replace

    from handler import scan_retry_execution as execution
    from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger

    retry = coordinator()
    retry.policy["apis"] = sources
    monkeypatch.setattr(execution, "configured_sources", lambda policy: sources)
    monkeypatch.setattr(execution, "load_retry_states", lambda binding: [])
    monkeypatch.setattr(
        execution, "baseline_completed_at", lambda binding: datetime(2026, 10, 1)
    )
    monkeypatch.setattr(execution, "check_worker_boundary", lambda: None)
    for index in range(8):
        current = replace(
            binding(),
            mapping_id=index + 1,
            rom_id=index + 10,
            game_relative_path=f"Game{index}",
        )
        rom = SimpleNamespace(id=current.rom_id, fs_name=f"Game{index}")
        quick = WindowsQuickContext(
            current,
            InventoryEvidence("c" * 64, 2, True),
            QuickScanDecision.METADATA_ONLY,
        )
        command = MappedScanCommand(
            current.mapping_id, 1, ScanTrigger(trigger), ScanScope.PLATFORM, "quick"
        )
        retry.consider(quick, rom, command)
    retry.revalidate = AsyncMock(return_value=True)
    dispatch = AsyncMock()
    await retry.run(dispatch)
    assert dispatch.await_count == 5
    assert len({call.kwargs["roms_ids"][0] for call in dispatch.await_args_list}) == 5
    for call in dispatch.await_args_list:
        assert call.args[0].scan_type == "complete"
        assert call.kwargs["metadata_only"] is True
        assert set(call.kwargs["metadata_sources"]) == set(sources)
    assert sum(
        item.assessment.reason == "budget_deferred" for item in retry.selection
    ) == 3 * len(sources)


@pytest.mark.asyncio
async def test_revoked_or_changed_inventory_never_dispatches(monkeypatch):
    from handler import scan_retry_execution as execution
    from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger

    retry = coordinator()
    monkeypatch.setattr(execution, "configured_sources", lambda policy: ["igdb"])
    monkeypatch.setattr(execution, "load_retry_states", lambda binding: [])
    monkeypatch.setattr(
        execution, "baseline_completed_at", lambda binding: datetime(2026, 10, 1)
    )
    monkeypatch.setattr(execution, "check_worker_boundary", lambda: None)
    quick = WindowsQuickContext(
        binding(), InventoryEvidence("c" * 64, 2, True), QuickScanDecision.METADATA_ONLY
    )
    retry.consider(
        quick,
        SimpleNamespace(id=3, fs_name="Game"),
        MappedScanCommand(1, 1, ScanTrigger.MANUAL, ScanScope.PLATFORM, "quick"),
    )
    retry.revalidate = AsyncMock(return_value=False)
    dispatch = AsyncMock()
    await retry.run(dispatch)
    dispatch.assert_not_awaited()


@pytest.mark.parametrize("cached", [True, False])
def test_observed_clocks_persist_without_fabricating_requests(
    bound_game, inventory_attempt, cached, monkeypatch
):
    from tests.handler.test_scan_write_fence import context

    from handler import scan_retry_execution as execution
    from handler.database.scan_inventory_state import load_retry_states
    from handler.database.scan_write_fence import bind_scan_write_context

    binding_value, _ = bound_game
    retry = coordinator()
    monkeypatch.setattr(execution, "configured_sources", lambda policy: ["igdb"])
    identity = retry.identity(binding_value, "igdb", "Game")
    retry.identities[(binding_value.rom_id, "igdb")] = identity
    observed = {
        "invoked": True,
        "cached": cached,
        "requests": 0 if cached else 2,
        "outcome": "no_match",
        "invoked_at": "2026-10-20T11:00:00",
        "request_at": None if cached else "2026-10-20T11:00:01",
        "retry_after_seconds": None,
    }
    with bind_scan_write_context(context(inventory_attempt)):
        retry.observe("igdb", SimpleNamespace(id=binding_value.rom_id), observed, None)
    row = load_retry_states(binding_value)[0]
    assert row.last_invoked_at == datetime(2026, 10, 20, 11)
    assert row.last_request_at == (None if cached else datetime(2026, 10, 20, 11, 0, 1))
    assert row.no_match_streak == (0 if cached else 1)
    assert row.outcome == ("cache_hit" if cached else "no_match")
    assert row.next_eligible_at > datetime(2026, 10, 20, 12)


def test_cancellation_rejects_retry_observation(
    bound_game, inventory_attempt, monkeypatch
):
    from tests.handler.test_scan_write_fence import context

    from handler import scan_retry_execution as execution
    from handler.database.base_handler import sync_session
    from handler.database.scan_inventory_state import load_retry_states
    from handler.database.scan_write_fence import (
        ScanWriteRejected,
        bind_scan_write_context,
    )
    from models.scan_operation import ScanOperation

    binding_value, _ = bound_game
    retry = coordinator()
    monkeypatch.setattr(execution, "configured_sources", lambda policy: ["igdb"])
    retry.identities[(binding_value.rom_id, "igdb")] = retry.identity(
        binding_value, "igdb", "Game"
    )
    with sync_session.begin() as session:
        session.get(ScanOperation, inventory_attempt.id).intentional_cancel = True
    with bind_scan_write_context(context(inventory_attempt)):
        with pytest.raises(ScanWriteRejected):
            retry.observe(
                "igdb",
                SimpleNamespace(id=binding_value.rom_id),
                {"invoked": True},
                None,
            )
    assert load_retry_states(binding_value) == []


@pytest.mark.parametrize("mode", ["complete", "hashes", "update"])
def test_explicit_refresh_invalidates_before_provider_work(
    bound_game, inventory_attempt, mode
):
    from dataclasses import replace

    from tests.handler.test_scan_inventory_state import evidence, save
    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_inventory_state import load_baseline
    from handler.database.scan_write_fence import bind_scan_write_context
    from handler.scan_operation_recovery import decode_command
    from handler.scan_retry_execution import invalidate_refresh_baselines

    binding_value, command_data = bound_game
    command_value = replace(decode_command(command_data["commands"][0]), scan_type=mode)
    with bind_scan_write_context(context(inventory_attempt)):
        assert save(binding_value)
        invalidate_refresh_baselines(command_value, {})
    assert load_baseline(binding_value, evidence()) is None


@pytest.mark.asyncio
async def test_empty_configuration_never_schedules_requests(monkeypatch):
    from handler import scan_retry_execution as execution
    from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger

    retry = coordinator()
    monkeypatch.setattr(execution, "configured_sources", lambda policy: [])
    monkeypatch.setattr(execution, "load_retry_states", lambda binding: [])
    quick = WindowsQuickContext(
        binding(), InventoryEvidence("c" * 64, 2, True), QuickScanDecision.METADATA_ONLY
    )
    retry.consider(
        quick,
        SimpleNamespace(id=3, fs_name="Game"),
        MappedScanCommand(1, 1, ScanTrigger.MANUAL, ScanScope.PLATFORM, "quick"),
    )
    dispatch = AsyncMock()
    await retry.run(dispatch)
    dispatch.assert_not_awaited()
    assert len(retry.attention_games) == 1
