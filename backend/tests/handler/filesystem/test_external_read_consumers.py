from __future__ import annotations

import ast
from pathlib import Path

import pytest

from handler.filesystem.base_handler import ExternalFSHandler
from handler.filesystem.firmware_handler import FSFirmwareHandler
from handler.filesystem.storage_composition import (
    StorageCompositionConfig,
    build_storage_composition,
)
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation


def _composition(root: Path):
    owned = {kind: root.parent / kind.value for kind in OwnedStorageKind}
    return build_storage_composition(StorageCompositionConfig(root, owned))


def test_external_handler_binds_caller_paths_to_composition_descriptor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "library"
    root.mkdir()
    descriptor = _composition(root).legacy_external
    handler = ExternalFSHandler(root, descriptor)
    access = handler.open_access(StorageOperation.LIST, "")
    try:
        assert access._descriptor is not None
        assert handler.storage is descriptor
    finally:
        access.close()


def test_external_handler_rejects_path_descriptor_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "library"
    root.mkdir()
    descriptor = _composition(root).legacy_external
    with pytest.raises(ValueError):
        ExternalFSHandler(tmp_path / "caller-controlled", descriptor)


@pytest.mark.asyncio
async def test_firmware_hashes_use_read_capability(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "library"
    root.mkdir()
    descriptor = _composition(root).legacy_external
    handler = FSFirmwareHandler(descriptor)
    calls = []

    class Read:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"firmware"

    def open_access(operation, path):
        calls.append((operation, path))
        return Read()

    monkeypatch.setattr(handler, "open_access", open_access)
    hashes = await handler.calculate_file_hashes("bios", "firmware.bin")
    assert calls == [(StorageOperation.READ, "bios/firmware.bin")]
    assert set(hashes) == {"crc_hash", "md5_hash", "sha1_hash"}


def test_enumeration_and_scan_modules_declare_exact_capabilities() -> None:
    expected = {
        "backend/handler/scan_handler.py": "SCAN",
        "backend/endpoints/sockets/scan.py": "SCAN",
        "backend/watcher.py": "LIST",
        "backend/endpoints/heartbeat.py": "LIST",
        "backend/config/config_manager.py": "LIST",
    }
    repo = Path(__file__).parents[4]
    for relative, operation in expected.items():
        tree = ast.parse((repo / relative).read_text())
        attributes = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        assert operation in attributes, f"{relative} lacks {operation} capability"
        assert "legacy_external_storage" in (repo / relative).read_text()


@pytest.mark.parametrize(
    ("relative", "operation"),
    [
        ("backend/handler/filesystem/roms_handler.py", "READ"),
        ("backend/endpoints/streaming.py", "STREAM"),
        ("backend/endpoints/roms/files.py", "DOWNLOAD"),
        ("backend/endpoints/roms/__init__.py", "DOWNLOAD"),
    ],
)
def test_rom_consumers_declare_exact_capabilities(
    relative: str, operation: str
) -> None:
    repo = Path(__file__).parents[4]
    source = (repo / relative).read_text()
    tree = ast.parse(source)
    attributes = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    assert operation in attributes
    assert "legacy_external_storage" in source


def test_external_downloads_do_not_construct_path_responses() -> None:
    repo = Path(__file__).parents[4]
    files_source = (repo / "backend/endpoints/roms/files.py").read_text()
    assert "StreamingResponse" in files_source
    assert "open_storage_access" in files_source
