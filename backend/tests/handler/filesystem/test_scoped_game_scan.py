"""Targeted collection child scans preserve one game identity."""

import os
from types import SimpleNamespace

import pytest

from handler.filesystem.roms_handler import FSRomsHandler
from models.platform import Platform
from models.storage import StorageRoot


@pytest.mark.asyncio
async def test_selected_child_is_one_game_and_excludes_sibling(tmp_path, monkeypatch):
    child = tmp_path / "pc-Games/Castlevania/Belmonts.Curse"
    sibling = child.parent / "Lords.of.Shadow.2"
    child.mkdir(parents=True)
    sibling.mkdir()
    (child / "game.part01.rar").write_bytes(b"first archive part")
    (child / "game.part02.rar").write_bytes(b"second archive part")
    (sibling / "sibling.rar").write_bytes(b"sibling")
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    mapping = SimpleNamespace(
        id=1,
        storage_root_id=1,
        relative_path="pc-Games",
        storage_root=StorageRoot(
            id=1,
            name="Synthetic",
            container_path=str(tmp_path),
            active=True,
            mode="external_read_only",
        ),
    )
    access = os.access
    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: False if mode == os.W_OK else access(path, mode),
    )
    handler = FSRomsHandler.for_mapping(mapping, "Castlevania/Belmonts.Curse")
    games = await handler.get_roms(Platform(fs_slug="win"))
    assert [game["fs_name"] for game in games] == ["Belmonts.Curse"]
    assert games[0]["nested"] and not games[0]["flat"]
    assert handler.get_logical_roms_fs_structure("win") == "pc-Games/Castlevania"
    full = FSRomsHandler.for_mapping(mapping)
    assert [
        game["fs_name"] for game in await full.get_roms(Platform(fs_slug="win"))
    ] == ["Castlevania"]
    assert {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    } == before


@pytest.mark.asyncio
async def test_full_scan_checks_known_child_without_discovering_unknown_children(
    tmp_path, monkeypatch, mocker
):
    from unittest.mock import AsyncMock, Mock

    from endpoints.sockets import scan
    from handler.scan_handler import ScanType

    parent = tmp_path / "pc-Games/Castlevania"
    parent.mkdir(parents=True)
    (parent / "Belmonts.Curse").mkdir()
    (parent / "Unknown.Child").mkdir()
    mapping = SimpleNamespace(
        id=1,
        storage_root_id=1,
        relative_path="pc-Games",
        storage_root=StorageRoot(
            id=1,
            name="Synthetic",
            container_path=str(tmp_path),
            active=True,
            mode="external_read_only",
        ),
    )
    access = os.access
    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: False if mode == os.W_OK else access(path, mode),
    )
    handler = FSRomsHandler.for_mapping(mapping)
    mocker.patch.object(scan, "get_fs_rom_handler", return_value=handler)
    platform = Platform(id=1, name="Windows", slug="win", fs_slug="win")
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
    db.get_roms_scalar.return_value = [
        SimpleNamespace(fs_name="Belmonts.Curse", fs_path="pc-Games/Castlevania"),
        SimpleNamespace(fs_name="Gone.Child", fs_path="pc-Games/Castlevania"),
        SimpleNamespace(fs_name="Escape", fs_path="other-mapping/Castlevania"),
    ]
    keep_lists = []

    def record_keep(identity, names):
        keep_lists.append(set(names))
        return []

    db.mark_missing_roms.side_effect = record_keep
    identify = mocker.patch.object(scan, "_identify_rom", AsyncMock())
    await scan._identify_platform(
        platform_slug="win",
        scan_type=ScanType.QUICK,
        fs_platforms=["win"],
        roms_ids=[],
        metadata_sources=[],
        launchbox_remote_enabled=False,
        playmatch_enabled=False,
        socket_manager=AsyncMock(),
        scan_stats=AsyncMock(),
    )
    assert keep_lists == [{"Castlevania", "Belmonts.Curse"}] * 2
    assert [call.kwargs["fs_rom"]["fs_name"] for call in identify.await_args_list] == [
        "Castlevania"
    ]
