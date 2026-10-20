"""Connected acceptance assertions and inventory completion rollback contracts."""

import sys
from pathlib import Path

import pytest
from tests.handler.test_scan_inventory_state import bound_game as bound_game
from tests.handler.test_scan_inventory_state import clear_inventory as clear_inventory
from tests.handler.test_scan_inventory_state import (
    inventory_attempt as inventory_attempt,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from phase35_incremental_scan_probe import assert_warm  # noqa: E402

pytest_plugins = ["tests.handler.test_scan_operations"]


@pytest.mark.parametrize(
    "kind", ["hash", "enrichment", "components", "media_prepare", "provider_http"]
)
def test_warm_receipt_rejects_observed_expensive_work(kind):
    with pytest.raises(RuntimeError, match="warm"):
        assert_warm({"scan_stats": {"inventory_unchanged": 3}}, [{"kind": kind}])


def test_warm_receipt_requires_durable_inventory_fact():
    with pytest.raises(RuntimeError, match="inventory"):
        assert_warm({"scan_stats": {}}, [])


@pytest.mark.parametrize("revocation", ["cancel", "attempt", "lease"])
def test_revoked_completion_preserves_adopted_baseline(
    bound_game, inventory_attempt, revocation
):
    from datetime import datetime, timedelta

    from tests.handler.test_scan_inventory_state import evidence, repository, save
    from tests.handler.test_scan_write_fence import context

    from handler.database.base_handler import sync_session
    from handler.database.scan_write_fence import (
        ScanWriteRejected,
        bind_scan_write_context,
    )
    from models.scan_operation import ScanOperation

    binding, _ = bound_game
    bound = context(inventory_attempt)
    with bind_scan_write_context(bound):
        assert save(binding)
    with sync_session.begin() as session:
        row = session.get(ScanOperation, inventory_attempt.id)
        if revocation == "cancel":
            row.intentional_cancel = True
        elif revocation == "attempt":
            row.attempt_id = "foreign"
        else:
            row.lease_expires_at = datetime.now() - timedelta(seconds=1)
    with bind_scan_write_context(bound), pytest.raises(ScanWriteRejected):
        save(binding, before=evidence(digest="f" * 64), after=evidence(digest="f" * 64))
    assert repository().load_baseline(binding, evidence()).digest == evidence().digest


@pytest.mark.asyncio
async def test_detached_discovery_row_can_emit_warm_inventory(
    bound_game, inventory_attempt
):
    from unittest.mock import AsyncMock

    from tests.handler.test_scan_inventory_state import evidence
    from tests.handler.test_scan_write_fence import context

    from handler.database.scan_write_fence import bind_scan_write_context
    from handler.scan_inventory_contracts import QuickScanDecision
    from handler.scan_inventory_status import emit_inventory_status
    from handler.windows_quick_execution import WindowsQuickContext

    binding, _ = bound_game
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from handler.database.base_handler import sync_session
    from models.rom import Rom

    with sync_session() as session:
        lean = session.scalar(
            select(Rom)
            .options(selectinload(Rom.platform))
            .where(Rom.id == binding.rom_id)
        )
    manager = AsyncMock()
    quick = WindowsQuickContext(binding, evidence(), QuickScanDecision.REUSE)
    with bind_scan_write_context(context(inventory_attempt)):
        await emit_inventory_status(manager, quick, lean, existing_game=True)
    payload = manager.emit.call_args.args[1]
    assert payload["inventory"]["inventory_state"] == "unchanged"
    assert payload["is_identifying"] is False


@pytest.mark.asyncio
async def test_real_steam_transport_counts_requests_without_outer_fetch_marker():
    import threading
    from http.server import ThreadingHTTPServer

    from phase35_incremental_worker import Provider

    from adapters.services.steam import SteamService
    from utils.context import initialize_context
    from utils.scan_provider_observation import bind_provider_observation

    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        service = SteamService(base_url=f"http://127.0.0.1:{server.server_port}/api")
        async with initialize_context():
            with bind_provider_observation("steam", "Unknown") as observed:
                assert await service.search_apps("Unknown") == []
                assert observed.invoked is True
                assert observed.requests == 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_disposable_external_identity_change_preserves_orm_immutability(bound_game):
    from uuid import uuid4

    from phase35_incremental_barrier import replace_fixture_incarnation

    from handler.database.base_handler import sync_session
    from models.rom import Rom

    binding, _ = bound_game
    replacement = uuid4().hex
    with pytest.raises(ValueError, match="immutable"):
        with sync_session.begin() as session:
            session.get(Rom, binding.rom_id).incarnation_token = replacement
    with sync_session.begin() as session:
        replace_fixture_incarnation(
            session, binding.rom_id, binding.rom_incarnation, replacement
        )
    with sync_session() as session:
        assert session.get(Rom, binding.rom_id).incarnation_token == replacement
    with sync_session.begin() as session:
        with pytest.raises(RuntimeError, match="identity"):
            replace_fixture_incarnation(
                session, binding.rom_id, binding.rom_incarnation, uuid4().hex
            )
    with sync_session.begin() as session:
        replace_fixture_incarnation(
            session, binding.rom_id, replacement, binding.rom_incarnation
        )
    with sync_session() as session:
        assert (
            session.get(Rom, binding.rom_id).incarnation_token
            == binding.rom_incarnation
        )
