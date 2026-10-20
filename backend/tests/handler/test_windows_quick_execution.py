"""Mapped Windows quick execution preserves complete inventory boundaries."""

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
    monkeypatch.setattr(execution, "inventory_binding", lambda *args: current)
    monkeypatch.setattr(
        execution, "load_baseline", lambda *args: evidence if baseline else None
    )
    rom = SimpleNamespace(platform_slug="win", is_identified=identified, steam_id=None)
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
