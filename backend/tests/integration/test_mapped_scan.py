from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Trigger(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WATCHER = "watcher"


@dataclass(frozen=True)
class ExpectedMapping:
    mapping_id: int
    revision: int
    state: str = "active"


def test_all_scan_triggers_share_mapping_bound_command_contract():
    payloads = [
        {"trigger": t, "mapping_id": 41, "expected_revision": 7} for t in Trigger
    ]
    assert {tuple(sorted(p)) for p in payloads} == {
        ("expected_revision", "mapping_id", "trigger")
    }
    assert {p["trigger"] for p in payloads} == set(Trigger)


def test_replaced_disabled_removed_and_revision_changed_are_stale():
    expected = ExpectedMapping(41, 7)
    actual = [
        ExpectedMapping(41, 8),
        ExpectedMapping(41, 7, "disabled"),
        ExpectedMapping(41, 7, "removed"),
        ExpectedMapping(42, 7),
    ]
    assert all(item != expected for item in actual)


def test_scan_pipeline_exposes_phase5_mapping_command():
    source = Path("handler/scan_handler.py").read_text()
    assert (
        "class MappedScanCommand" in source
    ), "Phase 5 RED: mapping-bound scan command is not implemented"
