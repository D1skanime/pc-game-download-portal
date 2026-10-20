"""All mapping scan consumers use the same explicit collection inventory."""

from unittest.mock import AsyncMock, Mock

import pytest
from tests.endpoints.test_scan_operations import mapped as mapped
from tests.handler.test_scan_collection_policy import promotion_body as promotion_body

from endpoints.responses.scan_operations import ScanOperationRequest
from endpoints.sockets import scan
from handler.database.base_handler import sync_session
from handler.filesystem.roms_handler import FSRomsHandler
from handler.scan_collection_policy import digest_path
from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger
from handler.scan_handler import ScanType
from handler.scan_operation_checkpoint import bind_checkpoint_command
from handler.scan_operation_commands import normalize_scan_request
from models.scan_collection import ScanCollectionFolder
from models.storage import PlatformStorageMapping


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger", list(ScanTrigger))
async def test_confirmed_collection_discovers_only_direct_game_directories(
    promotion_body, mapped, admin_user, tmp_path, mocker, trigger
):
    normalized = normalize_scan_request(
        ScanOperationRequest.model_validate(promotion_body)
    )
    intent = normalized["collection_promotion"]
    (tmp_path / "PC/Castlevania/New.Sibling").mkdir()
    (tmp_path / "PC/Castlevania/New.Sibling/game.rar").write_bytes(b"sibling")
    (tmp_path / "PC/Castlevania/Belmonts.Curse/Extras").mkdir()
    with sync_session.begin() as session:
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
                operation_id="retained-operation",
                audit={},
            )
        )
        mapping = session.get(PlatformStorageMapping, mapped.id)
    handler = FSRomsHandler.for_mapping(mapping)
    mocker.patch.object(scan, "get_fs_rom_handler", return_value=handler)
    platform = mapping.platform
    mocker.patch.object(scan, "redis_client", Mock(get=Mock(return_value=None)))
    platforms = mocker.patch.object(scan, "db_platform_handler")
    platforms.get_platform_by_fs_slug.return_value = platform
    platforms.add_platform.return_value = platform
    mocker.patch.object(scan, "scan_platform", AsyncMock(return_value=platform))
    mocker.patch.object(
        scan.PlatformSchema,
        "model_validate",
        return_value=Mock(model_dump=Mock(return_value={})),
    )
    mocker.patch.object(
        scan.fs_firmware_handler, "get_firmware", AsyncMock(return_value=[])
    )
    mocker.patch.object(
        scan.db_firmware_handler, "mark_missing_firmware", return_value=[]
    )
    db = mocker.patch.object(scan, "db_rom_handler")
    db.get_missing_rom_ids.return_value = set()
    db.get_roms_by_fs_name.return_value = {}
    db.get_roms_by_filesystem_identity.return_value = {}
    db.get_roms_scalar.return_value = []
    db.mark_missing_roms.return_value = []
    identify = mocker.patch.object(scan, "_identify_rom", AsyncMock())
    command = MappedScanCommand(
        mapped.id, mapped.version, trigger, ScanScope.PLATFORM, "quick"
    )
    with bind_checkpoint_command(command):
        await scan._identify_platform(
            platform_slug=platform.fs_slug,
            scan_type=ScanType.QUICK,
            fs_platforms=[platform.fs_slug],
            roms_ids=[],
            metadata_sources=[],
            launchbox_remote_enabled=False,
            playmatch_enabled=False,
            socket_manager=AsyncMock(),
            scan_stats=AsyncMock(),
        )
    assert {call.kwargs["fs_rom"]["fs_name"] for call in identify.await_args_list} == {
        "Belmonts.Curse",
        "New.Sibling",
    }
