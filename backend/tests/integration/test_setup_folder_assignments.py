from types import SimpleNamespace
from unittest.mock import Mock

from endpoints.sockets import scan as scan_module
from handler.scan_command import ScanScope, ScanTrigger
from handler.scan_handler import ScanType


def test_setup_assignment_identity_becomes_mapping_bound_scan_command(monkeypatch):
    platform = SimpleNamespace(id=17, fs_slug="windows")
    mapping = SimpleNamespace(
        id=41,
        version=9,
        storage_root=SimpleNamespace(mode="external_read_only"),
    )

    monkeypatch.setattr(
        scan_module.db_platform_handler, "get_platforms", lambda: [platform]
    )
    monkeypatch.setattr(
        scan_module.db_storage_handler, "get_active_mapping", lambda _id: mapping
    )
    monkeypatch.setattr(
        scan_module,
        "get_storage_root_health_snapshot",
        lambda _root: SimpleNamespace(non_writable=True),
    )

    commands = scan_module.mapping_scan_commands(
        [platform.id],
        trigger=ScanTrigger.MANUAL,
        scope=ScanScope.PLATFORM,
        scan_type=ScanType.QUICK,
    )

    assert [
        (command.mapping_id, command.expected_revision) for command in commands
    ] == [(mapping.id, mapping.version)]


def test_browser_paths_are_not_resolved_as_platform_selections(monkeypatch):
    platform = SimpleNamespace(id=17, fs_slug="windows")
    get_mapping = Mock()
    monkeypatch.setattr(
        scan_module.db_storage_handler, "get_active_mapping", get_mapping
    )
    monkeypatch.setattr(
        scan_module.db_platform_handler, "get_platforms", lambda: [platform]
    )

    commands = scan_module.mapping_scan_commands(
        [],
        trigger=ScanTrigger.MANUAL,
        scope=ScanScope.PLATFORM,
        scan_type=ScanType.QUICK,
        platform_fs_slugs=["/etc", "../outside", "C:\\Games\\Windows"],
    )

    assert commands == []
