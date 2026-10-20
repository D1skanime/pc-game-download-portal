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
        item.size = 9  # type: ignore[misc]


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


@pytest.fixture
def descriptor(game_tree):
    from handler.filesystem.storage_composition import (
        StorageCompositionConfig,
        build_storage_composition,
    )
    from handler.filesystem.storage_policy import OwnedStorageKind

    return build_storage_composition(
        StorageCompositionConfig(
            game_tree.parent,
            {
                kind: game_tree.parent.with_name(game_tree.parent.name + "-owned")
                / kind.value
                for kind in OwnedStorageKind
            },
        )
    ).legacy_external


def scan_capability(descriptor, path="Game"):
    from handler.filesystem.storage_access import open_storage_access
    from handler.filesystem.storage_policy import StorageOperation

    return open_storage_access(descriptor, StorageOperation.SCAN, path)


def test_bounded_scan_overflow_retains_only_budget(descriptor, game_tree):
    for number in range(300):
        (game_tree / f"{number}.bin").touch()
    with scan_capability(descriptor) as capability:
        result = capability.scan_bounded(3)
    assert not result.complete
    assert result.reason == "entry_limit"
    assert len(result.entries) == 3


def test_bounded_scan_never_uses_listdir(descriptor, monkeypatch):
    import os

    def deny(*args, **kwargs):
        raise AssertionError("unbounded listdir")

    monkeypatch.setattr(os, "listdir", deny)
    with scan_capability(descriptor) as capability:
        assert capability.scan_bounded(20).complete


def test_symlink_is_partial_without_body_access(descriptor, game_tree, monkeypatch):
    from handler.filesystem.storage_access import ReadCapability

    (game_tree / "escape").symlink_to("/etc/passwd")

    def deny(*args, **kwargs):
        raise AssertionError("body read")

    monkeypatch.setattr(ReadCapability, "read", deny)
    with scan_capability(descriptor) as capability:
        result = capability.scan_bounded(20)
    assert not result.complete
    assert result.reason == "unsupported_entry"


def test_scan_cancellation_closes_iterator_and_capability(descriptor):
    import os

    before = len(os.listdir("/proc/self/fd"))
    for _ in range(10):
        with pytest.raises(RuntimeError, match="cancelled"):
            with scan_capability(descriptor) as capability:
                capability.scan_bounded(
                    20, check=lambda: (_ for _ in ()).throw(RuntimeError("cancelled"))
                )
    assert len(os.listdir("/proc/self/fd")) == before


def test_scan_detects_directory_race(descriptor, game_tree):
    import os

    calls = 0

    def mutate():
        nonlocal calls
        calls += 1
        if calls == 2:
            (game_tree / "raced.bin").touch()
            metadata = game_tree.stat()
            os.utime(
                game_tree,
                ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000_000),
            )

    with scan_capability(descriptor) as capability:
        result = capability.scan_bounded(20, check=mutate)
    assert not result.complete
    assert result.reason == "unstable_directory"


def test_scan_unreadable_entry_is_partial(descriptor, monkeypatch):
    import os

    original = os.stat

    def fail(path, *args, **kwargs):
        if kwargs.get("dir_fd") is not None:
            raise PermissionError("private host path must not escape")
        return original(path, *args, **kwargs)

    with scan_capability(descriptor) as capability:
        monkeypatch.setattr(os, "stat", fail)
        result = capability.scan_bounded(20)
    assert not result.complete
    assert result.reason == "unreadable"


def test_scan_rejects_invalid_budget(descriptor):
    with scan_capability(descriptor) as capability:
        with pytest.raises(ValueError):
            capability.scan_bounded(-1)
