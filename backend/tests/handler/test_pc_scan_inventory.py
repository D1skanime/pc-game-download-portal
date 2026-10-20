from dataclasses import FrozenInstanceError

import pytest

from handler.scan_inventory_contracts import (
    InventoryAssessment,
    InventoryEntry,
    InventoryEvidence,
    QuickScanDecision,
)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Inventory contracts and descriptors do not require a database."""


@pytest.fixture(autouse=True)
def clear_database():
    """Override shared database cleanup for descriptor-only tests."""


def evidence(*, complete=True, digest="a" * 64, **kwargs):
    return InventoryEvidence(digest=digest, entry_count=1, complete=complete, **kwargs)


def test_partial_evidence_never_authorizes_equality():
    for current, baseline in [
        (evidence(complete=False), evidence()),
        (evidence(), evidence(complete=False)),
    ]:
        assert InventoryAssessment.compare(current, baseline).state == "incomplete"


def test_missing_and_obsolete_baselines_require_refresh():
    assert InventoryAssessment.compare(evidence(), None).state == "refresh_required"
    assert (
        InventoryAssessment.compare(evidence(), evidence(schema_version=2)).state
        == "refresh_required"
    )


def test_complete_comparison_and_decisions():
    assert InventoryAssessment.compare(evidence(), evidence()).state == "unchanged"
    assert (
        InventoryAssessment.compare(evidence(digest="b" * 64), evidence()).state
        == "changed"
    )
    assert {value.value for value in QuickScanDecision} == {
        "refresh",
        "reuse",
        "metadata_only",
        "incomplete",
    }


def test_contracts_are_immutable():
    item = InventoryEntry("dlc/one.bin", "file", 3, 1, 2, 3, 4)
    with pytest.raises(FrozenInstanceError):
        item.size = 9


@pytest.fixture
def game_tree(tmp_path):
    game = tmp_path / "Game"
    (game / "dlc" / "one").mkdir(parents=True)
    (game / "update").mkdir()
    (game / "empty").mkdir()
    (game / "base.bin").write_bytes(b"base")
    (game / "dlc" / "one" / "data.bin").write_bytes(b"dlc")
    (game / "update" / "patch.bin").write_bytes(b"patch")
    return game


def test_nested_fixture_has_stable_parent_timestamp(game_tree):
    before = game_tree.stat().st_mtime_ns
    nested = game_tree / "dlc" / "one" / "data.bin"
    observed = nested.stat()
    nested.write_bytes(b"changed-dlc")
    assert game_tree.stat().st_mtime_ns == before
    assert nested.stat().st_size != observed.st_size
    nested.unlink()
    assert game_tree.stat().st_mtime_ns == before
    assert (game_tree / "empty").is_dir()
