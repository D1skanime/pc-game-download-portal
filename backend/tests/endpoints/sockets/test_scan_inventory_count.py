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
    with bind_checkpoint_command(command):
        result = await scan.scan_platforms(
            platform_ids=[mapped.platform_id],
            metadata_sources=[],
            filesystem_platform_scope=["test_platform_slug"],
            filesystem_scope_path=scope,
        )
    assert result.total_roms == expected
