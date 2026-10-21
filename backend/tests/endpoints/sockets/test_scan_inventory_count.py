"""The public scan total counts the same selected games as scan execution."""

from unittest.mock import AsyncMock

import pytest
from tests.endpoints.test_scan_operations import mapped as mapped_fixture
from tests.handler.test_scan_collection_policy import (
    promotion_body as promotion_body_fixture,
)

from endpoints.responses.scan_operations import ScanOperationRequest
from endpoints.sockets import scan
from handler.database.base_handler import sync_session
from handler.filesystem.roms_handler import FSRomsHandler
from handler.scan_collection_policy import digest_path
from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger
from handler.scan_operation_checkpoint import bind_checkpoint_command
from handler.scan_operation_commands import normalize_scan_request
from models.scan_collection import ScanCollectionFolder
from models.storage import PlatformStorageMapping

mapped = mapped_fixture
promotion_body = promotion_body_fixture


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,expected", [("targeted", 1), ("classified", 2)])
async def test_scan_total_uses_selected_collection_inventory(
    promotion_body, mapped, admin_user, tmp_path, monkeypatch, kind, expected
):
    (tmp_path / "PC/Castlevania/Sibling").mkdir()
    (tmp_path / "PC/Castlevania/Sibling/game.rar").write_bytes(b"sibling")
    normalized = normalize_scan_request(
        ScanOperationRequest.model_validate(promotion_body)
    )
    intent = normalized["collection_promotion"]
    with sync_session.begin() as session:
        mapping = session.get(PlatformStorageMapping, mapped.id)
        if kind == "classified":
            session.add(
                ScanCollectionFolder(
                    mapping_id=mapped.id,
                    storage_root_id=mapped.storage_root_id,
                    mapping_relative_path="PC",
                    binding_digest=intent["binding_digest"],
                    parent_relative_path="Castlevania",
                    path_digest=digest_path("Castlevania"),
                    parent_rom_id=intent["parent_rom_id"],
                    parent_incarnation=intent["parent_incarnation"],
                    selected_child_relative_path="Castlevania/Belmonts.Curse",
                    actor_id=admin_user.id,
                    operation_id="count-test",
                    audit={},
                )
            )
    scope = "Castlevania/Belmonts.Curse" if kind == "targeted" else None
    handler = FSRomsHandler.for_mapping(mapping, scope)
    from handler.filesystem import use_fs_rom_handler

    monkeypatch.setattr(scan, "get_fs_rom_handler", lambda: handler)
    monkeypatch.setattr(scan, "require_scan_write_context", lambda: None)
    monkeypatch.setattr(scan, "_get_socket_manager", lambda: AsyncMock())

    async def identify(**kwargs):
        return kwargs["scan_stats"]

    monkeypatch.setattr(scan, "_identify_platform", identify)
    options = (("relative_path", scope),) if scope else ()
    command = MappedScanCommand(
        mapped.id,
        mapped.version,
        ScanTrigger.MANUAL,
        ScanScope.PLATFORM,
        "quick",
        options,
    )
    with bind_checkpoint_command(command), use_fs_rom_handler(handler):
        result = await scan.scan_platforms(
            platform_ids=[mapped.platform_id],
            metadata_sources=[],
            filesystem_platform_scope=["test_platform_slug"],
            filesystem_scope_path=scope,
        )
    assert result.total_roms == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("edit", ["bytes", "add", "delete", "race"])
async def test_quick_refresh_reconciles_files_and_components_together(
    promotion_body, mapped, rom, admin_user, tmp_path, monkeypatch, edit
):
    import os

    from sqlalchemy import select
    from tests.handler.test_scan_operations import repository, running
    from tests.handler.test_scan_write_fence import context

    from handler.database import db_rom_handler
    from handler.database.scan_write_fence import bind_scan_write_context
    from handler.filesystem import fs_resource_handler
    from handler.filesystem.pc_scan_inventory import InventoryIncomplete
    from handler.filesystem.scan_media_publication import ScanMediaBatch
    from handler.scan_inventory_contracts import QuickScanDecision
    from handler.storage.read_context import MappingReadContext
    from handler.windows_quick_execution import (
        WindowsQuickContext,
        inventory_binding,
        prepare_quick_refresh,
        reconcile_quick_files,
    )
    from models.rom import RomComponentManifestMember, RomFile

    command = MappedScanCommand(
        mapped.id, mapped.version, ScanTrigger.MANUAL, ScanScope.PLATFORM, "quick"
    )
    payload = {
        "commands": [
            {
                "mapping_id": mapped.id,
                "expected_revision": mapped.version,
                "trigger": "manual",
                "scope": "platform",
                "scan_type": "quick",
                "options": [],
            }
        ],
        "policies": {"apis": []},
    }
    attempt = running(repository(), admin_user, payload)
    mapping = MappingReadContext(mapped.id, mapped.version).validate()
    handler = FSRomsHandler.for_mapping(mapping)
    game = db_rom_handler.get_rom(rom.id)
    tree = tmp_path / "PC/Castlevania"
    (tree / "update").mkdir()
    patch = tree / "update/patch.bin"
    patch.write_bytes(b"old")
    parent_time = tree.stat().st_mtime_ns

    async def prepare():
        before = await handler.get_pc_inventory(game)
        quick = WindowsQuickContext(
            inventory_binding(game, "Castlevania"), before, QuickScanDecision.REFRESH
        )
        await prepare_quick_refresh(quick, handler, game, calculate_hashes=False)
        return quick

    def publish(quick):
        with ScanMediaBatch(
            game.id, game.platform_id, fs_resource_handler.storage
        ) as batch:
            return batch.publish_and_associate(
                lambda session: reconcile_quick_files(quick, handler, game, session)
            )

    with bind_scan_write_context(context(attempt)), bind_checkpoint_command(command):
        initial = await prepare()
        publish(initial)
        if edit == "delete":
            patch.unlink()
        elif edit == "add":
            (tree / "update/new.bin").write_bytes(b"new")
        else:
            patch.write_bytes(b"changed bytes")
        os.utime(tree, ns=(parent_time, parent_time))
        refreshed = await prepare()
        if edit == "race":
            patch.write_bytes(b"racing content")
            with pytest.raises(InventoryIncomplete):
                publish(refreshed)
        else:
            publish(refreshed)

    with sync_session.begin() as session:
        files = list(session.scalars(select(RomFile).where(RomFile.rom_id == game.id)))
        members = list(session.scalars(select(RomComponentManifestMember)))
        names = {f.file_name: f.file_size_bytes for f in files}
        component_sizes = {m.relative_path: m.size_bytes for m in members}
        if edit == "delete":
            assert "patch.bin" not in names
            assert "update/patch.bin" not in component_sizes
        elif edit == "add":
            assert names["new.bin"] == component_sizes["update/new.bin"] == 3
        elif edit == "race":
            assert names["patch.bin"] == component_sizes["update/patch.bin"] == 3
        else:
            assert names["patch.bin"] == component_sizes["update/patch.bin"] == 13
        assert tree.stat().st_mtime_ns == parent_time


@pytest.mark.asyncio
@pytest.mark.parametrize("identified", [True, False])
async def test_mapped_warm_inventory_performs_no_hash_or_publication(
    promotion_body, mapped, rom, monkeypatch, identified
):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from handler import windows_quick_execution as execution
    from handler.database import db_rom_handler
    from handler.storage.read_context import MappingReadContext

    command = MappedScanCommand(
        mapped.id, mapped.version, ScanTrigger.SCHEDULED, ScanScope.LIBRARY, "quick"
    )
    mapping = MappingReadContext(mapped.id, mapped.version).validate()
    handler = FSRomsHandler.for_mapping(mapping)
    game = db_rom_handler.get_rom(rom.id)
    game.platform.slug = "win"
    game.steam_id = 10 if identified else None
    for field in (
        "igdb_id",
        "moby_id",
        "ss_id",
        "ra_id",
        "launchbox_id",
        "hasheous_id",
        "flashpoint_id",
        "hltb_id",
        "gamelist_id",
        "libretro_id",
    ):
        setattr(game, field, None)
    monkeypatch.setattr(execution, "load_baseline", lambda binding, evidence: evidence)
    components = AsyncMock()
    files = AsyncMock()
    monkeypatch.setattr(FSRomsHandler, "get_pc_components", components)
    monkeypatch.setattr(FSRomsHandler, "get_rom_files", files)
    monkeypatch.setattr(execution, "get_fs_rom_handler", lambda: handler)
    with bind_checkpoint_command(command):
        result = await execution.inspect_discovered_game(
            SimpleNamespace(slug="win", fs_slug="test_platform_slug"),
            {"fs_name": "Castlevania", "nested": True},
            game,
            scan_type="quick",
            rom_ids=[],
            metadata_only=False,
        )
    assert result.decision.value == ("reuse" if identified else "metadata_only")
    assert result.binding.game_relative_path == "Castlevania"
    components.assert_not_awaited()
    files.assert_not_awaited()
