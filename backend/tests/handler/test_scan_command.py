from dataclasses import FrozenInstanceError

import pytest

from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger


def test_scan_command_is_immutable_and_identity_bearing():
    command = MappedScanCommand(
        mapping_id=41,
        expected_revision=7,
        trigger=ScanTrigger.MANUAL,
        scope=ScanScope.PLATFORM,
        scan_type="quick",
        options=(("metadata", "igdb"),),
    )
    assert command.mapping_id == 41
    assert command.expected_revision == 7
    with pytest.raises(FrozenInstanceError):
        command.mapping_id = 42


@pytest.mark.parametrize("value", ("/romm/library", "C:\\roms", "../roms"))
def test_scan_command_rejects_path_bearing_options(value: str):
    with pytest.raises(ValueError):
        MappedScanCommand(
            mapping_id=41,
            expected_revision=7,
            trigger=ScanTrigger.WATCHER,
            scope=ScanScope.PLATFORM,
            scan_type="quick",
            options=(("source", value),),
        )
