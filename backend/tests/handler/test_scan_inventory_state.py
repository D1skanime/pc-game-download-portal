"""Portable SQL inventory records, never a content publication authority."""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from tests.handler.test_scan_operations import command as command  # noqa: F401

from handler.database.base_handler import sync_session
from models.assets import Screenshot
from models.rom import Rom
from models.storage import PlatformStorageMapping


def models():
    from models.scan_inventory import ScanInventoryBaseline, ScanMetadataRetry

    return ScanInventoryBaseline, ScanMetadataRetry


def identity(rom):
    return dict(
        mapping_id=1,
        storage_root_id=1,
        mapping_relative_path="PC",
        mapping_revision=1,
        binding_digest="a" * 64,
        game_relative_path="Collection/Game",
        path_digest="b" * 64,
        rom_id=rom.id,
        rom_incarnation=rom.incarnation_token,
        inventory_version=1,
        classifier_version=1,
        policy_fingerprint="c" * 64,
        identity_digest="d" * 64,
    )


def test_portable_bounded_identity_constraints(rom):
    baseline, retry = models()
    with sync_session.begin() as session:
        inspector = inspect(session.bind)
        for model, name in (
            (baseline, "uq_scan_inventory_identity"),
            (retry, "uq_scan_metadata_retry_identity"),
        ):
            unique = inspector.get_unique_constraints(model.__tablename__)
            assert any(
                c["name"] == name and c["column_names"] == ["identity_digest"]
                for c in unique
            )
            assert model.__table__.c.identity_digest.type.length == 64
            assert model.__table__.c.game_relative_path.type.length == 700
            assert model.__table__.c.mapping_relative_path.type.length == 700
        session.add(
            baseline(
                **identity(rom),
                inventory_digest="e" * 64,
                entry_count=2,
                validated_at=rom.created_at,
                completed_at=rom.created_at
            )
        )
    with pytest.raises(IntegrityError):
        with sync_session.begin() as session:
            session.add(
                baseline(
                    **identity(rom),
                    inventory_digest="e" * 64,
                    entry_count=2,
                    validated_at=rom.created_at,
                    completed_at=rom.created_at
                )
            )
    with sync_session.begin() as session:
        assert session.get(Rom, rom.id).incarnation_token == rom.incarnation_token
        assert session.scalar(select(baseline)).entry_count == 2


@pytest.fixture(autouse=True)
def clear_inventory():
    baseline, retry = models()
    with sync_session.begin() as session:
        session.query(retry).delete()
        session.query(baseline).delete()
    yield
    with sync_session.begin() as session:
        session.query(retry).delete()
        session.query(baseline).delete()


def test_additive_migration_round_trip_preserves_catalog(rom, command, screenshot):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    baseline, retry = models()
    source = Path(__file__).parents[2] / "alembic/versions/0142_scan_inventory_state.py"
    spec = importlib.util.spec_from_file_location("inventory_migration", source)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with sync_session.begin() as session:
        engine = session.get_bind()
    with engine.begin() as connection:
        migration.__dict__["op"] = Operations(MigrationContext.configure(connection))
        migration.downgrade()
        assert "scan_inventory_baselines" not in inspect(connection).get_table_names()
        assert (
            connection.scalar(select(Rom.incarnation_token).where(Rom.id == rom.id))
            == rom.incarnation_token
        )
        mapping_id = command["commands"][0]["mapping_id"]
        assert (
            connection.scalar(
                select(PlatformStorageMapping.relative_path).where(
                    PlatformStorageMapping.id == mapping_id
                )
            )
            == "PC"
        )
        assert (
            connection.scalar(
                select(Screenshot.file_name).where(Screenshot.id == screenshot.id)
            )
            == screenshot.file_name
        )
        migration.upgrade()
    with sync_session.begin() as session:
        assert session.get(Rom, rom.id).incarnation_token == rom.incarnation_token
        assert session.scalar(select(baseline)) is None
        session.add(
            retry(
                **identity(rom),
                provider="igdb",
                normalized_query="game",
                locale="en-US",
                config_fingerprint="f" * 64,
                outcome="no_match"
            )
        )
    with sync_session.begin() as session:
        row = session.scalar(select(retry))
        assert row.provider == "igdb" and row.no_match_streak == 0


def repository():
    from importlib import import_module

    return import_module("handler.database.scan_inventory_state")


@pytest.fixture
def bound_game(rom, command):
    with sync_session.begin() as session:
        current = session.get(Rom, rom.id)
        current.fs_path, current.fs_name = "PC/Collection", "Game"
        mapping = session.get(
            PlatformStorageMapping, command["commands"][0]["mapping_id"]
        )
        binding = repository().InventoryBinding.from_mapping(
            mapping, current, "Collection/Game", "c" * 64
        )
    return binding, command


@pytest.fixture
def inventory_attempt(admin_user, bound_game):
    from tests.handler.test_scan_operations import repository as operations
    from tests.handler.test_scan_operations import running

    return running(operations(), admin_user, bound_game[1])


def evidence(**changes):
    from dataclasses import replace

    from handler.scan_inventory_contracts import InventoryEvidence

    return replace(InventoryEvidence("e" * 64, 2, True), **changes)


def save(binding, **changes):
    return repository().save_completed_baseline(
        binding,
        changes.pop("before", evidence()),
        changes.pop("after", evidence()),
        components_reconciled=changes.pop("components_reconciled", True),
        files_reconciled=changes.pop("files_reconciled", True),
        **changes
    )


def test_restart_reads_only_committed_advisory_evidence(bound_game, inventory_attempt):
    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import bind_scan_write_context

    binding, _ = bound_game
    assert repository().load_baseline(binding, evidence()) is None
    with bind_scan_write_context(context(inventory_attempt)):
        assert save(binding)
    assert repository().load_baseline(binding, evidence()) == evidence()
    assert (
        repository().load_baseline(binding, evidence(digest="f" * 64)).digest
        == "e" * 64
    )
    from handler.scan_operation_checkpoint import (
        SourceEvidenceRejected,
        validate_recovery_checkpoint,
    )

    with pytest.raises(SourceEvidenceRejected):
        validate_recovery_checkpoint({"checkpoint": {"inventory_digest": "e" * 64}})


@pytest.mark.parametrize(
    "failure", ["partial", "changed", "components", "files", "version"]
)
def test_incomplete_refresh_invalidates_reuse_preserves_catalog(
    bound_game, inventory_attempt, failure
):
    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import bind_scan_write_context

    binding, _ = bound_game
    with bind_scan_write_context(context(inventory_attempt)):
        assert save(binding)
        changes = {
            "partial": dict(after=evidence(complete=False)),
            "changed": dict(after=evidence(digest="f" * 64)),
            "components": dict(components_reconciled=False),
            "files": dict(files_reconciled=False),
            "version": dict(after=evidence(schema_version=2)),
        }
        assert not save(binding, **changes[failure])
    assert repository().load_baseline(binding, evidence()) is None
    with sync_session.begin() as session:
        assert (
            session.get(Rom, binding.rom_id).incarnation_token
            == binding.rom_incarnation
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("mapping_revision", 2),
        ("storage_root_id", 999),
        ("mapping_relative_path", "Other"),
        ("game_relative_path", "Other/Game"),
        ("rom_incarnation", "f" * 32),
        ("inventory_version", 2),
        ("classifier_version", 2),
        ("policy_fingerprint", "f" * 64),
    ],
)
def test_binding_changes_require_refresh(bound_game, inventory_attempt, field, value):
    from dataclasses import replace

    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import bind_scan_write_context

    binding, _ = bound_game
    with bind_scan_write_context(context(inventory_attempt)):
        assert save(binding)
    assert (
        repository().load_baseline(replace(binding, **{field: value}), evidence())
        is None
    )


def test_rollback_and_collision_checks(bound_game, inventory_attempt, monkeypatch):
    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import bind_scan_write_context

    binding, _ = bound_game
    with pytest.raises(RuntimeError, match="rollback"):
        with bind_scan_write_context(context(inventory_attempt)):
            with sync_session.begin() as session:
                assert save(binding, session=session)
                raise RuntimeError("rollback")
    assert repository().load_baseline(binding, evidence()) is None
    with bind_scan_write_context(context(inventory_attempt)):
        assert save(binding)
    baseline, _ = models()
    with sync_session.begin() as session:
        session.scalar(select(baseline)).game_relative_path = "collision"
    with pytest.raises(ValueError, match="collision"):
        repository().load_baseline(binding, evidence())


@pytest.mark.parametrize(
    "change", ["attempt", "owner", "cancel", "lease", "mapping", "root", "path", "rom"]
)
def test_revoked_writes_rejected(bound_game, inventory_attempt, change):
    from datetime import datetime, timedelta

    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import (
        ScanWriteRejected,
        bind_scan_write_context,
    )
    from models.scan_operation import ScanOperation
    from models.storage import StorageRoot

    binding, _ = bound_game
    bound = context(inventory_attempt)
    if change in {"attempt", "owner"}:
        bound = context(
            inventory_attempt,
            **(
                {"attempt_id": "foreign"}
                if change == "attempt"
                else {"lease_owner": "foreign"}
            )
        )
    else:
        with sync_session.begin() as session:
            if change == "cancel":
                session.get(ScanOperation, inventory_attempt.id).intentional_cancel = (
                    True
                )
            elif change == "lease":
                session.get(ScanOperation, inventory_attempt.id).lease_expires_at = (
                    datetime.now() - timedelta(seconds=1)
                )
            elif change == "mapping":
                session.get(PlatformStorageMapping, binding.mapping_id).version += 1
            elif change == "root":
                session.get(StorageRoot, binding.storage_root_id).active = False
            elif change == "path":
                session.get(Rom, binding.rom_id).fs_name = "Moved"
            else:
                previous = session.get(Rom, binding.rom_id)
                replacement = Rom(
                    id=previous.id,
                    platform_id=previous.platform_id,
                    name=previous.name,
                    slug=previous.slug,
                    fs_path=previous.fs_path,
                    fs_name=previous.fs_name,
                    incarnation_token="f" * 32,
                )
                session.execute(
                    Rom.__table__.delete().where(Rom.__table__.c.id == binding.rom_id)
                )
                session.expunge(previous)
                session.add(replacement)
    with pytest.raises(ScanWriteRejected):
        with bind_scan_write_context(bound):
            save(binding)
    assert repository().load_baseline(binding, evidence()) is None


@pytest.mark.parametrize("phase", ["flush", "commit"])
@pytest.mark.parametrize("target", ["revision", "mapping_path", "root", "rom_path"])
def test_binding_rechecked_at_transaction_boundary(
    bound_game, inventory_attempt, phase, target
):
    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import (
        ScanWriteRejected,
        bind_scan_write_context,
    )

    binding, _ = bound_game
    with pytest.raises(ScanWriteRejected):
        with sync_session.begin() as session:
            with bind_scan_write_context(context(inventory_attempt)):
                assert save(binding, session=session)
            from models.storage import StorageRoot

            model, identity, values = {
                "revision": (
                    PlatformStorageMapping,
                    binding.mapping_id,
                    {"version": 2},
                ),
                "mapping_path": (
                    PlatformStorageMapping,
                    binding.mapping_id,
                    {"relative_path": "Moved"},
                ),
                "root": (StorageRoot, binding.storage_root_id, {"active": False}),
                "rom_path": (Rom, binding.rom_id, {"fs_name": "Moved"}),
            }[target]
            assert isinstance(values, dict)
            session.execute(
                model.__table__.update().where(model.id == identity).values(**values)
            )
            if phase == "flush":
                session.get(Rom, binding.rom_id).name = "uncommitted"
                session.flush()
    assert repository().load_baseline(binding, evidence()) is None


def test_retry_clocks_and_normalized_collision_checked_identity(
    bound_game, inventory_attempt
):
    from datetime import datetime, timedelta

    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import bind_scan_write_context

    binding, _ = bound_game
    now = datetime(2026, 10, 20, 12, 0)
    with bind_scan_write_context(context(inventory_attempt)):
        repository().record_retry_outcome(
            binding,
            provider="igdb",
            query="  THE   Game ",
            locale="en_US",
            config_fingerprint="f" * 64,
            outcome="no_match",
            next_eligible_at=now + timedelta(hours=1),
            invoked_at=now,
            request_at=None,
            no_match_streak=1,
            transient_streak=0,
        )
    states = repository().load_retry_states(binding)
    assert len(states) == 1
    row = states[0]
    assert row.normalized_query == "the game" and row.locale == "en-us"
    assert row.last_invoked_at == now and row.last_request_at is None
    with bind_scan_write_context(context(inventory_attempt)):
        repository().record_retry_outcome(
            binding,
            provider="igdb",
            query="the game",
            locale="en-us",
            config_fingerprint="f" * 64,
            outcome="cache_hit",
            next_eligible_at=now,
            invoked_at=None,
            request_at=None,
            no_match_streak=1,
            transient_streak=0,
        )
    row = repository().load_retry_states(binding)[0]
    assert row.last_invoked_at == now and row.last_request_at is None
    with sync_session.begin() as session:
        session.scalar(select(models()[1])).normalized_query = "collision"
    with pytest.raises(ValueError, match="collision"):
        repository().load_retry_states(binding)


@pytest.mark.parametrize("reconciled", [True, False])
def test_game_completion_adopts_only_reconciled_baseline(
    bound_game, inventory_attempt, monkeypatch, reconciled
):
    from types import SimpleNamespace

    from tests.handler.test_scan_write_fence import context

    from handler import windows_quick_execution as execution
    from handler.database.scan_write_fence import bind_scan_write_context
    from handler.scan_collection_finalize import _complete
    from handler.scan_inventory_contracts import QuickScanDecision
    from handler.windows_quick_execution import WindowsQuickContext, bind_windows_quick

    binding, _ = bound_game
    quick = WindowsQuickContext(
        binding,
        evidence(),
        QuickScanDecision.REFRESH,
        files_reconciled=reconciled,
        components_reconciled=reconciled,
        after=evidence(),
    )
    monkeypatch.setattr(execution, "recheck_quick_inventory", lambda *args: None)
    with bind_scan_write_context(context(inventory_attempt)), bind_windows_quick(quick):
        with sync_session.begin() as session:
            rom = session.get(Rom, binding.rom_id)
            _complete(
                session,
                rom,
                SimpleNamespace(
                    mapping_id=binding.mapping_id,
                    expected_revision=binding.mapping_revision,
                ),
                None,
                None,
            )
    assert (repository().load_baseline(binding, evidence()) is not None) == reconciled
