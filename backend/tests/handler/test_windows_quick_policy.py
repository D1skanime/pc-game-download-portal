"""Focused Windows quick-scan policy truth tables."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from handler.database.scan_inventory_state import InventoryBinding
from handler.scan_inventory_contracts import InventoryEvidence, QuickScanDecision
from handler.windows_quick_policy import decide_windows_quick, is_identified_windows


def binding(path="Collection/Game", **changes):
    return replace(
        InventoryBinding(1, 2, "PC", 3, path, 4, "a" * 32, "b" * 64), **changes
    )


def rom(**changes):
    return SimpleNamespace(
        platform_slug="win", is_identified=False, steam_id=None, **changes
    )


def decide(**changes):
    values = dict(
        scan_type="quick",
        platform_slug="win",
        current_binding=binding(),
        baseline_binding=binding(),
        current=InventoryEvidence("a" * 64, 3, True),
        baseline=InventoryEvidence("a" * 64, 3, True),
        identified=True,
        collection_expanded=True,
    )
    values.update(changes)
    return decide_windows_quick(**values)


@pytest.mark.parametrize(
    "steam,expected",
    [
        (1, True),
        (123, True),
        (0, False),
        (-1, False),
        (True, False),
        ("123", False),
        (None, False),
    ],
)
def test_positive_persisted_steam_identity(steam, expected):
    item = rom()
    item.steam_id = steam
    assert is_identified_windows(item) is expected


def test_existing_identity_and_other_platforms():
    item = rom()
    item.is_identified = True
    assert is_identified_windows(item)
    item.platform_slug = "linux"
    assert not is_identified_windows(item)
    assert not is_identified_windows(None)


@pytest.mark.parametrize(
    "mode", ["complete", "hashes", "update", "unmatched", "new_platforms"]
)
def test_explicit_modes_bypass(mode):
    assert decide(scan_type=mode) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"platform_slug": "linux"},
        {"rom_ids": (4,)},
        {"selected_provider_work": True},
        {"selected_media_work": True},
        {"targeted_retry": True},
        {"collection_expanded": False},
    ],
)
def test_scope_exclusions_preserve_caller_predicate(changes):
    assert decide(**changes) is None


def test_complete_inventory_assessments():
    assert decide() == QuickScanDecision.REUSE
    assert decide(identified=False) == QuickScanDecision.METADATA_ONLY
    assert decide(baseline=None, baseline_binding=None) == QuickScanDecision.REFRESH
    assert (
        decide(current=InventoryEvidence("c" * 64, 3, True))
        == QuickScanDecision.REFRESH
    )
    assert (
        decide(current=InventoryEvidence("", 1, False)) == QuickScanDecision.INCOMPLETE
    )
    assert (
        decide(baseline=InventoryEvidence("", 1, False)) == QuickScanDecision.INCOMPLETE
    )


@pytest.mark.parametrize(
    "change",
    [
        {"mapping_id": 7},
        {"storage_root_id": 7},
        {"mapping_revision": 7},
        {"mapping_relative_path": "Other"},
        {"game_relative_path": "Other/Game"},
        {"rom_incarnation": "c" * 32},
        {"policy_fingerprint": "d" * 64},
        {"inventory_version": 2},
        {"classifier_version": 2},
    ],
)
def test_stale_full_binding_never_reuses(change):
    assert decide(baseline_binding=binding(**change)) == QuickScanDecision.REFRESH


def test_duplicate_child_basenames_and_missing_authority():
    assert decide(baseline_binding=binding("Other/Game")) == QuickScanDecision.REFRESH
    assert decide(current_binding=None) == QuickScanDecision.INCOMPLETE
    assert decide(authority_current=False) == QuickScanDecision.INCOMPLETE
