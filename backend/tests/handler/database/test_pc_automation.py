from datetime import timedelta

from sqlalchemy import select
from tests.conftest import session

from handler.database.pc_automation_handler import DBPcAutomationHandler
from models.pc_automation import (
    PcAutomationOutcome,
    PcAutomationQueue,
    PcAutomationQueueState,
    PcAutomationTargetKind,
)
from models.rom import RomComponent, RomComponentKind, RomComponentMetadata


def _handler() -> DBPcAutomationHandler:
    return DBPcAutomationHandler()


def _component(
    rom_id: int, kind: RomComponentKind = RomComponentKind.DLC
) -> RomComponent:
    component = RomComponent(
        rom_id=rom_id,
        relative_path="dlc/automation-test",
        kind=kind,
    )
    with session.begin() as db:
        db.add(component)
        db.flush()
    return component


def test_pending_parent_evidence_is_idempotent_and_preserves_skip(rom):
    handler = _handler()
    target = handler.get_parent_target(rom.id)
    assert target is not None

    first = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:100",
        candidate_title="Automation Test",
        provider="steam",
        provider_candidate_id="100",
    )
    assert first.outcome == PcAutomationOutcome.CREATED
    assert first.item is not None

    skipped = handler.mark_skipped(first.item.id, first.item.updated_at)
    assert skipped.outcome == PcAutomationOutcome.SKIPPED
    assert skipped.item is not None

    repeated = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:100",
        candidate_title="Automation Test",
        provider="steam",
        provider_candidate_id="100",
    )
    assert repeated.outcome == PcAutomationOutcome.UNCHANGED
    assert repeated.item is not None
    assert repeated.item.state == PcAutomationQueueState.SKIPPED

    with session() as db:
        assert db.scalar(
            select(PcAutomationQueue).where(PcAutomationQueue.rom_id == rom.id)
        )
        assert db.query(PcAutomationQueue).filter_by(rom_id=rom.id).count() == 1


def test_changed_fingerprint_reopens_the_same_target_for_review(rom):
    handler = _handler()
    target = handler.get_parent_target(rom.id)
    assert target is not None
    created = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:100",
    )
    assert created.item is not None
    skipped = handler.mark_skipped(created.item.id, created.item.updated_at)
    assert skipped.item is not None

    reopened = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:200",
    )
    assert reopened.outcome == PcAutomationOutcome.REOPENED
    assert reopened.item is not None
    assert reopened.item.id == created.item.id
    assert reopened.item.state == PcAutomationQueueState.PENDING


def test_component_queue_is_scoped_to_its_parent_and_dlc_kind(rom):
    component = _component(rom.id)
    handler = _handler()
    target = handler.get_component_target(rom.id, component.id)
    assert target is not None

    queued = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.COMPONENT,
        rom_id=rom.id,
        component_id=component.id,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation dlc",
        candidate_fingerprint="steam:dlc:100",
    )
    assert queued.outcome == PcAutomationOutcome.CREATED
    assert queued.item is not None

    wrong_parent = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.COMPONENT,
        rom_id=rom.id + 1,
        component_id=component.id,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation dlc",
        candidate_fingerprint="steam:dlc:100",
    )
    assert wrong_parent.outcome == PcAutomationOutcome.MISSING_TARGET

    unsupported = _component(rom.id, RomComponentKind.BASE)
    unsupported_target = handler.get_component_target(rom.id, unsupported.id)
    assert unsupported_target is None


def test_claim_rejects_a_stale_target_version(rom):
    handler = _handler()
    target = handler.get_parent_target(rom.id)
    assert target is not None
    queued = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:100",
    )
    assert queued.item is not None

    stale = handler.claim(
        queued.item.id,
        queued.item.updated_at,
        target.updated_at - timedelta(seconds=1),
    )
    assert stale.outcome == PcAutomationOutcome.STALE_TARGET
    assert stale.item is None


def test_manual_resolution_claims_only_the_exact_old_pending_target(rom):
    handler = _handler()
    target = handler.get_parent_target(rom.id)
    assert target is not None
    queued = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:100",
    )
    assert queued.item is not None

    with session.begin() as db:
        managed = db.get(type(rom), rom.id)
        assert managed is not None
        managed.summary = "Manual correction persisted"

    resolved = handler.resolve_after_manual_selection(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        consumed_target_updated_at=target.updated_at,
    )
    assert resolved.outcome == PcAutomationOutcome.CLAIMED
    assert resolved.item is not None
    assert resolved.item.id == queued.item.id
    assert resolved.item.state == PcAutomationQueueState.CLAIMED
    assert resolved.item.last_attempt_at is not None
    assert handler.list_pending()[1] == 0

    repeated = handler.resolve_after_manual_selection(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        consumed_target_updated_at=target.updated_at,
    )
    assert repeated.outcome == PcAutomationOutcome.UNCHANGED
    assert repeated.item is None


def test_manual_resolution_preserves_a_reopened_or_unrelated_pending_target(rom):
    handler = _handler()
    target = handler.get_parent_target(rom.id)
    assert target is not None
    queued = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:100",
    )
    assert queued.item is not None

    with session.begin() as db:
        managed = db.get(type(rom), rom.id)
        assert managed is not None
        managed.summary = "A newer target version"
    newer_target = handler.get_parent_target(rom.id)
    assert newer_target is not None
    reopened = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=newer_target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:200",
    )
    assert reopened.outcome == PcAutomationOutcome.REOPENED
    assert reopened.item is not None

    stale = handler.resolve_after_manual_selection(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        consumed_target_updated_at=target.updated_at,
    )
    assert stale.outcome == PcAutomationOutcome.UNCHANGED
    assert stale.item is None
    pending, total = handler.list_pending()
    assert total == 1
    assert [item.id for item in pending] == [reopened.item.id]


def test_manual_parent_or_component_is_never_queued(rom):
    handler = _handler()
    with session.begin() as db:
        managed = db.get(type(rom), rom.id)
        assert managed is not None
        managed.manual_metadata = {"name": True}
    parent = handler.get_parent_target(rom.id)
    assert parent is not None

    protected_parent = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=parent.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:100",
    )
    assert protected_parent.outcome == PcAutomationOutcome.PROTECTED_TARGET

    component = _component(rom.id)
    with session.begin() as db:
        db.add(
            RomComponentMetadata(component_id=component.id, metadata_source="manual")
        )
    target = handler.get_component_target(rom.id, component.id)
    assert target is not None
    protected_component = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.COMPONENT,
        rom_id=rom.id,
        component_id=component.id,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation dlc",
        candidate_fingerprint="steam:dlc:100",
    )
    assert protected_component.outcome == PcAutomationOutcome.PROTECTED_TARGET


def test_retry_requeue_and_pending_pagination_are_bounded(rom):
    handler = _handler()
    target = handler.get_parent_target(rom.id)
    assert target is not None
    queued = handler.upsert_pending(
        target_kind=PcAutomationTargetKind.PARENT,
        rom_id=rom.id,
        component_id=None,
        expected_target_updated_at=target.updated_at,
        normalized_query="automation test",
        candidate_fingerprint="steam:100",
    )
    assert queued.item is not None

    failed = handler.mark_retryable_failure(
        queued.item.id, queued.item.updated_at, retry_after_seconds=30
    )
    assert failed.outcome == PcAutomationOutcome.RETRY_SCHEDULED
    assert failed.item is not None
    assert failed.item.retry_count == 1
    assert failed.item.next_retry_at is not None

    requeued = handler.requeue(failed.item.id, failed.item.updated_at)
    assert requeued.outcome == PcAutomationOutcome.REQUEUED
    assert requeued.item is not None
    assert requeued.item.state == PcAutomationQueueState.PENDING

    page, total = handler.list_pending(limit=1, offset=0)
    assert total == 1
    assert [item.id for item in page] == [queued.item.id]
