"""Exact inventory game units and observed provider dispatch units."""

import pytest
from tests.handler.test_scan_inventory_state import bound_game as bound_game
from tests.handler.test_scan_inventory_state import (
    inventory_attempt as inventory_attempt,
)
from tests.handler.test_scan_operations import command as command

from handler.database.base_handler import sync_session
from handler.database.scan_operations_handler import DBScanOperationsHandler
from handler.database.scan_write_fence import (
    ScanWriteContext,
    ScanWriteRejected,
    bind_scan_write_context,
)
from models.rom import Rom
from models.scan_operation import ScanOperationItem
from models.storage import PlatformStorageMapping


def test_exact_units_and_replay():
    from handler.scan_inventory_status import aggregate_inventory

    games = [
        {
            "key": str(i),
            "inventory_state": state,
            "identified_windows": i == 0,
            "existing_game": i != 2,
        }
        for i, state in enumerate(
            ["unchanged", "changed", "refresh_required", "incomplete", "unchanged"]
        )
    ]
    observations = [
        {
            "key": "1",
            "provider": "igdb",
            "invoked": True,
            "requests": 2,
            "cached": False,
        },
        {
            "key": "1",
            "provider": "steam",
            "invoked": True,
            "requests": 3,
            "cached": False,
        },
        {
            "key": "2",
            "provider": "igdb",
            "invoked": True,
            "requests": 1,
            "cached": False,
        },
        {
            "key": "4",
            "provider": "igdb",
            "invoked": True,
            "requests": 0,
            "cached": True,
        },
    ]
    counts = aggregate_inventory(games + games, observations + observations)
    assert counts == {
        "inventory_checked": 5,
        "inventory_unchanged": 2,
        "inventory_changed": 1,
        "inventory_refresh_required": 1,
        "inventory_incomplete": 1,
        "unresolved_games": 4,
        "metadata_retry_games": 2,
        "provider_requests": 6,
        "metadata_cache_hits": 1,
    }
    assert counts["inventory_checked"] == sum(
        counts["inventory_" + state]
        for state in ("unchanged", "changed", "refresh_required", "incomplete")
    )


def test_eligibility_wrapper_and_unavailable_observations_are_not_requests():
    from handler.scan_inventory_status import aggregate_inventory

    game = {
        "key": "unknown",
        "inventory_state": "unchanged",
        "identified_windows": False,
        "existing_game": True,
        "retry_eligible": True,
    }
    result = aggregate_inventory(
        [game], [{"key": "unknown", "provider": "igdb", "outcome": "completed"}]
    )
    assert result["unresolved_games"] == 1
    assert result["metadata_retry_games"] == 0
    assert result["provider_requests"] == 0
    assert "metadata_cache_hits" not in result


def write_context(attempt):
    return bind_scan_write_context(
        ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    )


def test_sql_restores_unknown_and_global_counts_beyond_page(
    bound_game, inventory_attempt, admin_user
):
    from dataclasses import replace

    from handler.scan_inventory_status import record_inventory_status

    binding, _ = bound_game
    bindings = [binding]
    with sync_session.begin() as session:
        game = session.get(Rom, binding.rom_id)
        for index in range(104):
            child = Rom(
                fs_name="Game" + str(index),
                fs_path="PC/Other",
                platform_id=game.platform_id,
            )
            session.add(child)
            session.flush()
            bindings.append(
                replace(
                    binding,
                    rom_id=child.id,
                    rom_incarnation=child.incarnation_token,
                    game_relative_path="Other/" + child.fs_name,
                )
            )
    with write_context(inventory_attempt):
        for identity in bindings:
            record_inventory_status(
                identity,
                inventory_state="unchanged",
                identified_windows=False,
                existing_game=True,
                retry_state="cooldown",
                retry_eligible=False,
            )
        record_inventory_status(
            binding,
            inventory_state="unchanged",
            identified_windows=False,
            existing_game=True,
            retry_state="cooldown",
            retry_eligible=False,
        )
    repo = DBScanOperationsHandler()
    first = repo.get_by_id(inventory_attempt.id, admin_user.id)
    last = repo.get_by_id(first.id, admin_user.id, offset=100, limit=100)
    assert len(first.items) == 100 and len(last.items) == 5
    assert first.items_total == last.items_total == 105
    assert (
        first.scan_stats["inventory_checked"]
        == last.scan_stats["unresolved_games"]
        == 105
    )
    assert first.items[0].inventory.rom_id == binding.rom_id
    assert first.items[0].inventory.identified_windows is False
    assert first.items[0].inventory.is_identifying is False
    terminal = repo.transition(first.id, first.version, first.attempt_id, "completed")
    restored = repo.get_by_id(terminal.id, admin_user.id)
    assert restored.items[0].inventory == first.items[0].inventory
    public = restored.model_dump_json()
    for forbidden in (
        "policy_fingerprint",
        "incarnation",
        "/phase34",
        "source_evidence",
    ):
        assert forbidden not in public
    with pytest.raises(ValueError):
        repo.get_by_id(first.id, admin_user.id, limit=101)


@pytest.mark.parametrize(
    "mutation", ["revision", "incarnation", "path", "root", "cancel", "attempt"]
)
def test_status_rejects_revoked_identity(
    bound_game, inventory_attempt, mutation, admin_user
):
    from handler.scan_inventory_status import record_inventory_status

    binding, _ = bound_game
    if mutation == "incarnation":
        from dataclasses import replace

        binding = replace(binding, rom_incarnation="f" * 32)
    if mutation == "cancel":
        DBScanOperationsHandler().request_cancel(
            inventory_attempt.id,
            admin_user.id,
            inventory_attempt.version,
            "cancel-status",
        )
    elif mutation != "incarnation":
        from models.scan_operation import ScanOperation

        with sync_session.begin() as session:
            if mutation == "attempt":
                session.get(ScanOperation, inventory_attempt.id).attempt_id = (
                    "replacement"
                )
            elif mutation == "revision":
                session.get(PlatformStorageMapping, binding.mapping_id).version += 1
            elif mutation == "root":
                session.get(PlatformStorageMapping, binding.mapping_id).active = False
            else:
                game = session.get(Rom, binding.rom_id)
                if mutation == "incarnation":
                    game.incarnation_token = "f" * 32
                else:
                    game.fs_name = "Changed"
    with write_context(inventory_attempt), pytest.raises(ScanWriteRejected):
        record_inventory_status(
            binding,
            inventory_state="unchanged",
            identified_windows=False,
            existing_game=True,
        )
    with sync_session.begin() as session:
        assert session.query(ScanOperationItem).count() == 0


def test_safe_status_validation_and_stale_attempt_projection(
    bound_game, inventory_attempt, admin_user
):
    from handler.scan_inventory_status import record_inventory_status
    from models.scan_operation import ScanOperation

    binding, _ = bound_game
    with write_context(inventory_attempt):
        for invalid in (
            {"inventory_reason": "/host/secret"},
            {"inventory_state": "invented"},
            {"retry_state": "invented"},
            {"next_eligible_at": "not-a-timestamp"},
        ):
            args = {
                "inventory_state": "incomplete",
                "identified_windows": False,
                "existing_game": True,
            } | invalid
            with pytest.raises(ValueError):
                record_inventory_status(binding, **args)
        record_inventory_status(
            binding,
            inventory_state="incomplete",
            inventory_reason="inventory_unreadable",
            identified_windows=False,
            existing_game=True,
        )
    repo = DBScanOperationsHandler()
    snapshot = repo.get_by_id(inventory_attempt.id, admin_user.id)
    assert snapshot.items[0].inventory.inventory_reason == "inventory_unreadable"
    with sync_session.begin() as session:
        session.get(ScanOperation, snapshot.id).attempt_id = "replacement"
    fresh = repo.get_by_id(snapshot.id, admin_user.id)
    assert fresh.items_total == 0 and not fresh.items
    assert fresh.scan_stats.get("inventory_checked", 0) == 0


def test_sql_observations_count_dispatches_not_completed_wrappers(
    bound_game, inventory_attempt, admin_user
):
    from handler.scan_inventory_status import record_inventory_status

    binding, _ = bound_game
    repo = DBScanOperationsHandler()
    item = dict(
        target_key="provider-game",
        mapping_id=binding.mapping_id,
        expected_revision=binding.mapping_revision,
        relative_path=binding.game_relative_path,
        provider="igdb",
        outcome="completed",
    )
    with write_context(inventory_attempt):
        record_inventory_status(
            binding,
            inventory_state="unchanged",
            identified_windows=False,
            existing_game=True,
        )
        context = ScanWriteContext(
            inventory_attempt.id, inventory_attempt.attempt_id, "worker"
        )
        repo.record_worker_item(context, item, checkpoint={"rom_id": binding.rom_id})
        assert (
            repo.get_by_id(inventory_attempt.id, admin_user.id).scan_stats[
                "provider_requests"
            ]
            == 0
        )
        observation = {
            "invoked": True,
            "requests": 3,
            "cached": False,
            "outcome": "no_match",
        }
        for _ in range(2):
            repo.record_worker_item(
                context,
                item,
                checkpoint={
                    "rom_id": binding.rom_id,
                    "provider_observation": observation,
                },
            )
    snapshot = repo.get_by_id(inventory_attempt.id, admin_user.id)
    assert snapshot.scan_stats["provider_requests"] == 3
    assert snapshot.scan_stats["metadata_retry_games"] == 1
    assert snapshot.items[1].provider_execution.requests == 3
    assert snapshot.items[1].provider_execution.state == "no_match"


@pytest.mark.asyncio
@pytest.mark.parametrize("identified", [True, False])
async def test_terminal_event_matches_reloaded_inventory(
    bound_game, inventory_attempt, admin_user, identified
):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from handler.scan_inventory_contracts import InventoryEvidence, QuickScanDecision
    from handler.scan_inventory_status import emit_inventory_status
    from handler.windows_quick_execution import WindowsQuickContext

    binding, _ = bound_game
    quick = WindowsQuickContext(
        binding,
        InventoryEvidence("a" * 64, 1, True),
        QuickScanDecision.REUSE if identified else QuickScanDecision.METADATA_ONLY,
    )
    manager = SimpleNamespace(emit=AsyncMock())
    with sync_session.begin() as session:
        game = session.get(Rom, binding.rom_id)
        game.steam_id = 42 if identified else None
        for name in (
            "igdb_id",
            "moby_id",
            "ss_id",
            "ra_id",
            "launchbox_id",
            "hasheous_id",
            "flashpoint_id",
            "hltb_id",
            "gamelist_id",
            "libretro_id",
        ):
            setattr(game, name, None)
    from handler.database import db_rom_handler

    game = db_rom_handler.get_rom(binding.rom_id)
    with write_context(inventory_attempt):
        await emit_inventory_status(manager, quick, game, existing_game=True)
    snapshot = DBScanOperationsHandler().get_by_id(inventory_attempt.id, admin_user.id)
    event, payload = manager.emit.await_args.args
    assert event == "scan:scanning_rom"
    assert payload["id"] == game.id
    assert payload["inventory"] == snapshot.items[0].inventory.model_dump(mode="json")
    assert payload["is_identifying"] is False
    assert payload["inventory"]["identified_windows"] is identified
    before = manager.emit.await_count
    DBScanOperationsHandler().request_cancel(
        snapshot.id, admin_user.id, snapshot.version, "cancel-event"
    )
    with write_context(inventory_attempt), pytest.raises(ScanWriteRejected):
        await emit_inventory_status(manager, quick, game, existing_game=True)
    assert manager.emit.await_count == before


@pytest.mark.asyncio
@pytest.mark.parametrize("requests,expected", [(0, False), (1, True)])
async def test_worker_socket_identifying_requires_actual_work(
    monkeypatch, requests, expected
):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from handler import scan_operation_worker as worker
    from utils.scan_provider_observation import bind_provider_observation

    monkeypatch.setattr(worker, "check_worker_boundary", lambda: None)
    manager = SimpleNamespace(emit=AsyncMock())
    wrapped = worker.AttemptSocketManager(manager)
    await wrapped.emit("scan:scanning_rom", {"id": 1, "is_identifying": True})
    assert manager.emit.await_args.args[1]["is_identifying"] is False
    with bind_provider_observation("igdb", "Game") as observation:
        observation.invoked = True
        observation.requests = requests
        await wrapped.emit("scan:scanning_rom", {"id": 1, "is_identifying": True})
    assert manager.emit.await_args.args[1]["is_identifying"] is expected


def test_progress_preserves_completed_mapping_units(
    bound_game, inventory_attempt, admin_user
):
    from handler import scan_operation_worker as worker
    from handler.scan_inventory_status import record_inventory_status

    binding, _ = bound_game
    context = ScanWriteContext(
        inventory_attempt.id, inventory_attempt.attempt_id, "worker"
    )
    with write_context(inventory_attempt), worker.bind_worker_runtime(context):
        record_inventory_status(
            binding,
            inventory_state="unchanged",
            identified_windows=False,
            existing_game=True,
        )
        with worker.bind_scan_stats_base(
            {"scanned_roms": 4, "total_roms": 4}, total_known=False
        ):
            result = worker.persist_scan_stats({"scanned_roms": 2, "total_roms": 3})
        assert result["scanned_roms"] == 6 and "total_roms" not in result
        assert result["unresolved_games"] == 1
    restored = DBScanOperationsHandler().get_by_id(inventory_attempt.id, admin_user.id)
    assert restored.scan_stats == result
