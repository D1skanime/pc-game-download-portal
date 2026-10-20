"""Operation-wide unknown retries share discovery and metadata dispatch."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tests.handler.test_windows_quick_execution import binding

from handler.scan_inventory_contracts import InventoryEvidence, QuickScanDecision
from handler.windows_quick_execution import WindowsQuickContext


def coordinator():
    from handler.scan_retry_execution import RetryCoordinator

    return RetryCoordinator(
        {"apis": ["igdb"]}, clock=lambda: datetime(2026, 10, 20, 12)
    )


@pytest.mark.asyncio
async def test_retry_dispatch_uses_one_global_budget_and_metadata_only(monkeypatch):
    from dataclasses import replace

    from handler import scan_retry_execution as execution
    from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger

    retry = coordinator()
    monkeypatch.setattr(execution, "configured_sources", lambda policy: ["igdb"])
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
            current.mapping_id, 1, ScanTrigger.SCHEDULED, ScanScope.PLATFORM, "quick"
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
        assert call.kwargs["metadata_sources"] == ["igdb"]
    assert (
        sum(item.assessment.reason == "budget_deferred" for item in retry.selection)
        == 3
    )


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
