"""Mapped Windows quick execution preserves complete inventory boundaries."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from handler.database.scan_inventory_state import InventoryBinding
from handler.scan_inventory_contracts import InventoryEvidence, QuickScanDecision
from handler.windows_quick_execution import inspect_windows_quick


def binding(path="Game"):
    return InventoryBinding(1, 2, "PC", 1, path, 3, "a" * 32, "b" * 64)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identified,baseline,expected",
    [
        (True, True, QuickScanDecision.REUSE),
        (False, True, QuickScanDecision.METADATA_ONLY),
        (True, False, QuickScanDecision.REFRESH),
    ],
)
async def test_complete_inventory_advice(monkeypatch, identified, baseline, expected):
    from handler import windows_quick_execution as execution

    evidence = InventoryEvidence("c" * 64, 1, True)
    handler = SimpleNamespace(get_pc_inventory=AsyncMock(return_value=evidence))
    current = binding()
    monkeypatch.setattr(
        "handler.database.scan_inventory_state.save_completed_baseline", Mock()
    )
    monkeypatch.setattr(execution, "inventory_binding", lambda *args: current)
    monkeypatch.setattr(
        execution, "load_baseline", lambda *args: evidence if baseline else None
    )
    rom = SimpleNamespace(
        id=3, platform_slug="win", is_identified=identified, steam_id=None
    )
    result = await inspect_windows_quick(
        handler,
        rom,
        scan_type="quick",
        platform_slug="win",
        rom_ids=[],
        relative_path="Game",
        collection_expanded=True,
    )
    assert result.decision == expected
    assert result.binding == current
    handler.get_pc_inventory.assert_awaited_once_with(rom)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,platform,ids,expanded",
    [
        ("complete", "win", [], True),
        ("hashes", "win", [], True),
        ("quick", "snes", [], True),
        ("quick", "win", [3], True),
        ("quick", "win", [], False),
    ],
)
async def test_explicit_and_other_platform_bypass(mode, platform, ids, expanded):
    handler = Mock()
    result = await inspect_windows_quick(
        handler,
        Mock(),
        scan_type=mode,
        platform_slug=platform,
        rom_ids=ids,
        relative_path="Game",
        collection_expanded=expanded,
    )
    assert result is None
    handler.get_pc_inventory.assert_not_called()


@pytest.mark.asyncio
async def test_incomplete_never_loads_baseline(monkeypatch):
    from handler import windows_quick_execution as execution

    evidence = InventoryEvidence("", 2, False, "unreadable")
    handler = SimpleNamespace(get_pc_inventory=AsyncMock(return_value=evidence))
    monkeypatch.setattr(execution, "inventory_binding", lambda *args: binding())
    load = Mock()
    monkeypatch.setattr(execution, "load_baseline", load)
    result = await inspect_windows_quick(
        handler,
        Mock(),
        scan_type="quick",
        platform_slug="win",
        rom_ids=[],
        relative_path="Game",
        collection_expanded=True,
    )
    assert result.decision == QuickScanDecision.INCOMPLETE
    load.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["component", "files", "after", "changed"])
async def test_refresh_failure_preserves_unreconciled_context(failure):
    from handler.filesystem.pc_scan_inventory import InventoryIncomplete

    execution = import_module("handler.windows_quick_execution")
    WindowsQuickContext = execution.WindowsQuickContext
    prepare_quick_refresh = execution.prepare_quick_refresh

    before = InventoryEvidence("c" * 64, 2, True)
    after = InventoryEvidence("d" * 64, 2, True) if failure == "changed" else before
    handler = SimpleNamespace(
        get_pc_components=AsyncMock(return_value=[]),
        get_rom_files=AsyncMock(return_value=Mock()),
        get_pc_inventory=AsyncMock(return_value=after),
    )
    if failure == "component":
        handler.get_pc_components.side_effect = OSError("synthetic")
    elif failure == "files":
        handler.get_rom_files.side_effect = OSError("synthetic")
    elif failure == "after":
        handler.get_pc_inventory.return_value = InventoryEvidence(
            "", 1, False, "unreadable"
        )
    quick = WindowsQuickContext(binding(), before, QuickScanDecision.REFRESH)
    with pytest.raises(InventoryIncomplete):
        await prepare_quick_refresh(quick, handler, Mock(), calculate_hashes=False)
    assert not quick.files_reconciled
    assert not quick.components_reconciled


@pytest.mark.asyncio
async def test_refresh_prepares_from_same_complete_evidence():
    execution = import_module("handler.windows_quick_execution")
    WindowsQuickContext = execution.WindowsQuickContext
    prepare_quick_refresh = execution.prepare_quick_refresh

    before = InventoryEvidence("c" * 64, 2, True)
    handler = SimpleNamespace(
        get_pc_components=AsyncMock(return_value=["component"]),
        get_rom_files=AsyncMock(return_value="files"),
        get_pc_inventory=AsyncMock(return_value=before),
    )
    quick = WindowsQuickContext(binding(), before, QuickScanDecision.REFRESH)
    candidate = Mock()
    await prepare_quick_refresh(quick, handler, candidate, calculate_hashes=False)
    handler.get_pc_components.assert_awaited_once_with(candidate, inventory=before)
    handler.get_rom_files.assert_awaited_once_with(candidate, calculate_hashes=False)
    assert quick.components == ["component"]
    assert quick.files == "files"
    assert not quick.files_reconciled
    assert not quick.components_reconciled


def test_reconciliation_checks_evidence_before_any_database_write(monkeypatch):
    from handler.filesystem.pc_scan_inventory import InventoryIncomplete

    execution = import_module("handler.windows_quick_execution")

    quick = execution.WindowsQuickContext(
        binding(), InventoryEvidence("c" * 64, 2, True), QuickScanDecision.REFRESH
    )
    quick.components = []
    quick.files = SimpleNamespace(rom_files=[])
    monkeypatch.setattr(
        execution,
        "recheck_quick_inventory",
        Mock(side_effect=InventoryIncomplete("unstable_file")),
    )
    repository = Mock()
    monkeypatch.setattr(execution, "db_rom_handler", repository)
    with pytest.raises(InventoryIncomplete):
        execution.reconcile_quick_files(quick, Mock(), Mock(), object())
    repository.sync_rom_files.assert_not_called()
    repository.sync_rom_components.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "descriptions,enabled,selected,expected",
    [
        ({}, True, True, 1),
        ({"de": "Manual German", "en": "Manual English"}, True, True, 0),
        ({}, False, True, 0),
        ({}, True, False, 0),
    ],
)
async def test_warm_reuse_offers_only_missing_selected_descriptions(
    monkeypatch, descriptions, enabled, selected, expected
):
    from datetime import datetime

    from handler import scan_description_retry as repair
    from handler import scan_retry_execution as retry
    from handler import windows_quick_execution as execution

    evidence = InventoryEvidence("c" * 64, 1, True)
    current = binding("Collection/Game")
    handler = SimpleNamespace(
        get_pc_inventory=AsyncMock(return_value=evidence),
        get_pc_components=AsyncMock(),
        get_rom_files=AsyncMock(),
    )
    monkeypatch.setattr(execution, "inventory_binding", lambda rom, path: current)
    monkeypatch.setattr(execution, "load_baseline", lambda *args: evidence)
    monkeypatch.setattr(repair, "get_description_retry_state", lambda identity: None)
    monkeypatch.setattr(
        repair, "get_description_component_page", lambda *a, **kw: ([], None)
    )
    monkeypatch.setattr(
        retry,
        "configured_sources",
        lambda policy: ["steam"] if enabled and selected else [],
    )
    coordinator = retry.RetryCoordinator(
        {
            "apis": ["steam"] if selected else [],
            "metadata_locale": "de-DE",
            "description_languages": ["de", "en"],
        }
    )
    rom = SimpleNamespace(
        id=3,
        platform_slug="win",
        is_identified=True,
        steam_id=1245620,
        fs_name="Game",
        updated_at=datetime(2026, 10, 22),
        steam_metadata={},
        manual_metadata={"descriptions": descriptions},
        summary="Legacy English",
    )
    command = object()
    monkeypatch.setattr(execution, "current_checkpoint_command", lambda: command)
    with retry.bind_retry_coordinator(coordinator):
        result = await inspect_windows_quick(
            handler,
            rom,
            scan_type="quick",
            platform_slug="win",
            rom_ids=[],
            relative_path="Collection/Game",
            collection_expanded=True,
        )
    assert result.decision == QuickScanDecision.REUSE
    assert len(coordinator.candidates) == expected
    if expected:
        work = next(iter(coordinator.work.values()))
        assert work.quick is result
        assert work.command is command
        assert work.quick.binding.game_relative_path == "Collection/Game"
        assert coordinator.candidates[0].identity.purpose == "description"
        assert coordinator.candidates[0].identity.locale == "de"
    handler.get_pc_inventory.assert_awaited_once_with(rom)
    handler.get_pc_components.assert_not_called()
    handler.get_rom_files.assert_not_called()
