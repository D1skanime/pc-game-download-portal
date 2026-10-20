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


def inventory(descriptor, **kwargs):
    from handler.filesystem.pc_scan_inventory import collect_pc_inventory
    from handler.filesystem.storage_access import open_storage_access

    return collect_pc_inventory(
        lambda operation, path: open_storage_access(descriptor, operation, path),
        "Game",
        check=lambda: None,
        **kwargs,
    )


def test_inventory_nested_change_removal_and_empty_directory(descriptor, game_tree):
    import os

    baseline = inventory(descriptor)
    parent_time = game_tree.stat().st_mtime_ns
    assert baseline.complete
    assert any(item.relative_path == "empty" for item in baseline.observations)
    nested = game_tree / "update" / "patch.bin"
    nested.write_bytes(b"new patch contents")
    assert game_tree.stat().st_mtime_ns == parent_time
    changed = inventory(descriptor)
    assert changed.complete
    assert changed.digest != baseline.digest
    nested.unlink()
    assert inventory(descriptor).digest != changed.digest
    (game_tree / "empty").rmdir()
    os.utime(game_tree, ns=(game_tree.stat().st_atime_ns, parent_time))
    assert inventory(descriptor).digest != baseline.digest


def test_inventory_uses_no_hash_or_body_reads(descriptor, monkeypatch):
    from handler.filesystem.storage_access import HashCapability, ReadCapability

    def deny(*args, **kwargs):
        raise AssertionError("inventory must not read bytes")

    monkeypatch.setattr(HashCapability, "hash", deny)
    monkeypatch.setattr(ReadCapability, "read", deny)
    assert inventory(descriptor).complete


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"max_entries": 2}, "entry_limit"),
        ({"max_depth": 0}, "depth_limit"),
        ({"deadline_seconds": 0}, "deadline"),
    ],
)
def test_inventory_limits_are_explicit(descriptor, kwargs, reason):
    result = inventory(descriptor, **kwargs)
    assert not result.complete
    assert result.reason == reason


def test_inventory_cancellation_and_authority_propagate(descriptor):
    from handler.database.scan_write_fence import ScanWriteRejected
    from handler.filesystem.pc_scan_inventory import collect_pc_inventory
    from handler.filesystem.storage_access import open_storage_access

    calls = 0

    def revoked():
        nonlocal calls
        calls += 1
        raise ScanWriteRejected("scan_attempt_revoked")

    with pytest.raises(ScanWriteRejected):
        collect_pc_inventory(
            lambda operation, path: open_storage_access(descriptor, operation, path),
            "Game",
            check=revoked,
        )
    assert calls == 1


def test_inventory_rechecks_mapping_at_each_open(descriptor):
    from exceptions.storage_read import StaleMappedReadError
    from handler.filesystem.pc_scan_inventory import collect_pc_inventory
    from handler.filesystem.storage_access import open_storage_access

    opens = 0

    def stale(operation, path):
        nonlocal opens
        opens += 1
        if opens == 2:
            raise StaleMappedReadError(1, 1)
        return open_storage_access(descriptor, operation, path)

    with pytest.raises(StaleMappedReadError):
        collect_pc_inventory(stale, "Game", check=lambda: None)


def test_unchanged_observations_are_advisory(descriptor, game_tree, monkeypatch):
    from handler.filesystem.pc_scan_inventory import digest_inventory
    from handler.filesystem.storage_access import HashCapability, open_storage_access
    from handler.filesystem.storage_policy import StorageOperation

    observed = inventory(descriptor)
    with open_storage_access(
        descriptor, StorageOperation.HASH, "Game/base.bin"
    ) as source:
        assert isinstance(source, HashCapability)
        before = source.hash()
    (game_tree / "base.bin").write_bytes(b"evil")
    with open_storage_access(
        descriptor, StorageOperation.HASH, "Game/base.bin"
    ) as source:
        assert isinstance(source, HashCapability)
        after = source.hash()
    assert digest_inventory(observed.observations) == observed.digest
    assert before != after


@pytest.mark.asyncio
async def test_components_share_inventory_classifier_and_keep_soundtrack(
    descriptor, game_tree
):
    from handler.filesystem.roms_handler import FSRomsHandler
    from models.rom import Rom, RomComponentKind

    (game_tree / "ost").mkdir()
    (game_tree / "ost" / "track.flac").write_bytes(b"music")
    (game_tree / "dlc" / "README.txt").write_bytes(b"documentation")
    handler = FSRomsHandler(descriptor)
    components = await handler.get_pc_components(Rom(fs_path="", fs_name="Game"))
    assert [(item.relative_path, item.kind) for item in components] == [
        ("base", RomComponentKind.BASE),
        ("dlc", RomComponentKind.UNRESOLVED),
        ("dlc/one", RomComponentKind.DLC),
        ("update", RomComponentKind.UPDATE),
    ]
    assert any(
        item.relative_path == "ost/track.flac"
        for item in inventory(descriptor).observations
    )
    assert [
        member.relative_path for item in components for member in item.manifest_members
    ] == ["base.bin", "dlc/README.txt", "dlc/one/data.bin", "update/patch.bin"]


@pytest.mark.asyncio
async def test_incomplete_inventory_cannot_produce_prunable_components(
    descriptor, game_tree
):
    from handler.filesystem.pc_scan_inventory import InventoryIncomplete
    from handler.filesystem.roms_handler import FSRomsHandler
    from models.rom import Rom

    (game_tree / "escape").symlink_to("/etc/passwd")
    with pytest.raises(InventoryIncomplete):
        await FSRomsHandler(descriptor).get_pc_components(
            Rom(fs_path="", fs_name="Game")
        )
