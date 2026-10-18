"""Real SQL acceptance, cleanup and stale-writer regressions."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select

from handler.database.base_handler import sync_session
from models.scan_operation import ScanExecutionSlot, ScanOperation, ScanOperationItem
from models.storage import PlatformStorageMapping, StorageRoot


@pytest.fixture
def command(platform):
    with sync_session.begin() as session:
        root = StorageRoot(name="Fixture", container_path="/phase34/owned/library")
        session.add(root)
        session.flush()
        mapping = PlatformStorageMapping(
            platform_id=platform.id, storage_root_id=root.id, relative_path="PC"
        )
        session.add(mapping)
        session.flush()
        return {
            "commands": [
                {
                    "mapping_id": mapping.id,
                    "expected_revision": mapping.version,
                    "trigger": "manual",
                    "scope": "platform",
                    "scan_type": "quick",
                    "options": [],
                }
            ],
            "policies": {"apis": ["igdb"]},
        }


def repository():
    from handler.database.scan_operations_handler import DBScanOperationsHandler

    return DBScanOperationsHandler()


def assert_empty():
    with sync_session.begin() as session:
        assert session.scalar(select(func.count()).select_from(ScanOperation)) == 0
        assert session.scalar(select(func.count()).select_from(ScanOperationItem)) == 0
        slots = list(session.scalars(select(ScanExecutionSlot)))
        assert len(slots) == 1
        assert (
            slots[0].id == 1
            and slots[0].active_operation_id is None
            and slots[0].version == 0
        )


def leave_operation(user, command):
    repo = repository()
    row = repo.accept(user.id, "cleanup-pair", command)
    with sync_session.begin() as session:
        target = command["commands"][0]
        session.add(
            ScanOperationItem(
                operation_id=row.id,
                target_key="fixture",
                mapping_id=target["mapping_id"],
                expected_revision=1,
                relative_path="Phase34-Synthetic.bin",
                provider="igdb",
                outcome="indexed",
                attempt_id="fixture",
            )
        )
    return row


def test_cleanup_first_operation_creator(admin_user, command):
    assert_empty()
    leave_operation(admin_user, command)


def test_cleanup_second_operation_creator(admin_user, command):
    assert_empty()
    leave_operation(admin_user, command)


def test_acceptance_is_committed_before_enqueue(admin_user, command):
    repo = repository()
    accepted = repo.accept(admin_user.id, "lost-response", command)
    assert accepted.state == "accepted" and accepted.dispatch_pending
    assert accepted.attempt_id is None
    assert (
        repository().get_by_request_key(admin_user.id, "lost-response").id
        == accepted.id
    )
    assert repo.accept(admin_user.id, "lost-response", command) == accepted
    assert repo.find_active(admin_user.id).id == accepted.id


def test_payload_conflict_and_global_slot(admin_user, viewer_user, command):
    from handler.database.scan_operations_handler import OperationConflict

    repo = repository()
    repo.accept(admin_user.id, "stable-key", command)
    with pytest.raises(OperationConflict):
        repo.accept(
            admin_user.id, "stable-key", command | {"policies": {"apis": ["steam"]}}
        )
    with pytest.raises(OperationConflict):
        repo.accept(viewer_user.id, "different-key", command)
    with sync_session.begin() as session:
        assert session.scalar(select(func.count()).select_from(ScanOperation)) == 1


def test_concurrent_first_acceptance_connections(admin_user, command):
    repo = repository()
    barrier = Barrier(4)

    def submit(_):
        barrier.wait(timeout=10)
        return repo.accept(admin_user.id, "race-key", command).id

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(submit, range(4), timeout=20))
    assert len(set(ids)) == 1
    with sync_session.begin() as session:
        assert session.scalar(select(func.count()).select_from(ScanOperation)) == 1
        assert session.get(ScanExecutionSlot, 1).active_operation_id == ids[0]


def running(repo, user, command):
    row = repo.accept(user.id, "running-key", command)
    row = repo.claim_dispatch(row.id, row.version, "dispatcher")
    row = repo.mark_enqueued(row.id, row.version, "dispatcher")
    return repo.claim_attempt(row.id, row.version, "worker")


def test_cancel_confirm_resume_fences_stale_items(admin_user, command):
    from handler.database.scan_operations_handler import OperationConflict

    repo = repository()
    old = running(repo, admin_user, command)
    assert old.state == "running" and old.attempt_id
    stopping = repo.request_cancel(old.id, admin_user.id, old.version, "cancel-key")
    assert stopping.state == "stopping" and stopping.intentional_cancel
    with pytest.raises(OperationConflict):
        repo.transition(old.id, old.version, old.attempt_id, "completed")
    stopped = repo.confirm_stopped(stopping.id, stopping.version, old.attempt_id)
    assert stopped.state == "cancelled"
    resumed = repo.request_resume(
        stopped.id, admin_user.id, stopped.version, "resume-key"
    )
    assert resumed.attempt_id != old.attempt_id and resumed.state == "recovering"
    assert (
        repo.request_resume(stopped.id, admin_user.id, stopped.version, "resume-key")
        == resumed
    )
    item = dict(
        target_key="stale-item",
        mapping_id=command["commands"][0]["mapping_id"],
        expected_revision=1,
        relative_path="Phase34-Synthetic.bin",
        provider="igdb",
        outcome="indexed",
    )
    with pytest.raises(OperationConflict):
        repo.record_item(old.id, old.version, old.attempt_id, item)
    with sync_session.begin() as session:
        assert session.scalar(select(func.count()).select_from(ScanOperationItem)) == 0


def test_terminal_replay_and_global_slot_release(admin_user, command):
    repo = repository()
    row = running(repo, admin_user, command)
    done = repo.transition(row.id, row.version, row.attempt_id, "completed")
    assert repo.accept(admin_user.id, "running-key", command).state == "completed"
    assert not done.dispatch_pending
    assert repo.accept(admin_user.id, "new-key", command).id != row.id


def test_item_crud_lease_and_scope_are_fenced(admin_user, command):
    from handler.database.scan_operations_handler import OperationConflict

    repo = repository()
    row = running(repo, admin_user, command)
    row = repo.renew_lease(row.id, row.version, row.attempt_id, "worker")
    item = dict(
        target_key="game-1",
        mapping_id=command["commands"][0]["mapping_id"],
        expected_revision=1,
        relative_path="Phase34-Synthetic.bin",
        provider="igdb",
        outcome="warning",
        cause_code="provider_timeout",
    )
    saved = repo.record_item(row.id, row.version, row.attempt_id, item)
    assert saved.items_total == 1 and saved.items[0].outcome == "warning"
    with pytest.raises(OperationConflict):
        repo.record_item(row.id, row.version, row.attempt_id, item)
    for changes in (
        {"mapping_id": 999},
        {"expected_revision": 999},
        {"provider": "steam"},
    ):
        with pytest.raises(OperationConflict):
            repo.record_item(saved.id, saved.version, saved.attempt_id, item | changes)
    updated = repo.record_item(
        saved.id,
        saved.version,
        saved.attempt_id,
        item | {"outcome": "completed", "cause_code": None},
    )
    assert updated.items_total == 1 and updated.items[0].outcome == "completed"


def test_cancel_completion_race_has_one_winner(admin_user, command):
    from handler.database.scan_operations_handler import OperationConflict

    repo = repository()
    row = running(repo, admin_user, command)
    barrier = Barrier(2)

    def mutate(cancel):
        barrier.wait(timeout=10)
        try:
            if cancel:
                repo.request_cancel(row.id, admin_user.id, row.version, "race-cancel")
            else:
                repo.transition(row.id, row.version, row.attempt_id, "completed")
            return "committed"
        except OperationConflict:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(mutate, [True, False], timeout=20))
    assert sorted(results) == ["committed", "stale"]
    current = repo.get_by_id(row.id, admin_user.id)
    assert current.version == row.version + 1 and current.state in {
        "stopping",
        "completed",
    }


def test_stale_dispatch_claim_cannot_enqueue(admin_user, command):
    from handler.database.scan_operations_handler import OperationConflict

    repo = repository()
    row = repo.accept(admin_user.id, "dispatch-race", command)
    claim = repo.claim_dispatch(row.id, row.version, "dispatcher")
    with pytest.raises(OperationConflict):
        repo.claim_dispatch(claim.id, claim.version, "other-dispatcher")
    stopping = repo.request_cancel(
        claim.id, admin_user.id, claim.version, "cancel-dispatch"
    )
    with pytest.raises(OperationConflict):
        repo.mark_enqueued(claim.id, claim.version, "dispatcher")
    assert repo.get_by_id(row.id, admin_user.id).version == stopping.version


def test_lookup_masks_other_owner(admin_user, viewer_user, command):
    from handler.database.scan_operations_handler import OperationNotFound

    repo = repository()
    row = repo.accept(admin_user.id, "private-key", command)
    with pytest.raises(OperationNotFound):
        repo.get_by_id(row.id, viewer_user.id)
    assert repo.find_active(viewer_user.id) is None
    assert repo.get_by_id(row.id, viewer_user.id, admin=True).id == row.id
