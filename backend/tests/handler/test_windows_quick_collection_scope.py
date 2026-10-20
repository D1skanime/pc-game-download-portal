"""Discovery inventory preserves the shared mapped child identity."""

from types import SimpleNamespace

import pytest
from tests.endpoints.test_scan_operations import mapped as mapped
from tests.handler.test_scan_collection_policy import promotion_body as promotion_body

from handler.filesystem import use_fs_rom_handler
from handler.filesystem.roms_handler import FSRomsHandler
from handler.scan_inventory_contracts import QuickScanDecision
from handler.scan_operation_checkpoint import bind_checkpoint_command
from handler.storage.read_context import MappingReadContext
from handler.windows_quick_execution import inspect_discovered_game


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["quick", "complete", "update"])
@pytest.mark.parametrize("expanded", [False, True])
async def test_selected_collection_child_inventory_uses_mapping_relative_scope(
    promotion_body, mapped, mode, expanded, monkeypatch
):
    scope = "Castlevania/Belmonts.Curse"
    mapping = MappingReadContext(mapped.id, mapped.version).validate()
    handler = FSRomsHandler.for_mapping(mapping, None if expanded else scope)
    entry = {
        "fs_name": "Belmonts.Curse",
        "nested": True,
        "flat": False,
    }
    if expanded:
        entry.update(
            scan_relative_path=scope,
            logical_fs_path="PC/Castlevania",
        )
    paths = []
    original_open = MappingReadContext.open

    def observe_open(context, operation, relative_path="", **kwargs):
        paths.append(relative_path)
        return original_open(context, operation, relative_path, **kwargs)

    monkeypatch.setattr(MappingReadContext, "open", observe_open)
    command = SimpleNamespace(
        mapping_id=mapped.id,
        expected_revision=mapped.version,
        options=(("relative_path", scope),) if not expanded else (),
    )
    platform = SimpleNamespace(slug="win", fs_slug="win", id=mapped.platform_id)
    with bind_checkpoint_command(command), use_fs_rom_handler(handler):
        result = await inspect_discovered_game(
            platform, entry, None, scan_type=mode, rom_ids=[], metadata_only=False
        )
    assert entry.get("scan_relative_path") == scope
    assert paths[0] == scope
    assert result.before.complete, result.before.reason
    assert result.decision == QuickScanDecision.REFRESH
    assert result.before.entry_count == 2
