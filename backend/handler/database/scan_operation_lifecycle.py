"""Short, serialized transactions for dispatch and worker lifecycle."""

from datetime import timedelta
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from handler.database.scan_operations_handler import DBScanOperationsHandler
from uuid import uuid4

from sqlalchemy import select, update

from decorators.database import begin_session
from models.scan_operation import ScanExecutionSlot, ScanOperation, ScanOperationItem


class ScanOperationLifecycle:
    @begin_session
    def execution(self, identity, *, session=None):
        from handler.database.scan_operations_handler import OperationNotFound

        row = session.get(ScanOperation, identity)
        if row is None:
            raise OperationNotFound("operation_not_found")
        return {
            key: getattr(row, key)
            for key in (
                "id",
                "actor_id",
                "version",
                "state",
                "attempt_id",
                "lease_owner",
                "lease_expires_at",
                "intentional_cancel",
                "rq_job_id",
                "command",
                "checkpoint",
                "scan_stats",
                "dispatch_due",
                "dispatch_claim_until",
            )
        }

    @begin_session
    def pending_execution(self, *, limit=32, session=None):
        slot = session.get(ScanExecutionSlot, 1)
        return [slot.active_operation_id] if slot and slot.active_operation_id else []

    @begin_session
    def dispatch_failed(self, identity, owner, *, session=None):
        from handler.database.scan_operations_handler import _cas, _row, _slot, utc_now

        _slot(session)
        row = _row(session, identity)
        if row.dispatch_owner != owner or row.state not in {"accepted", "recovering"}:
            return
        _cas(
            session,
            row,
            row.version,
            dispatch_owner=None,
            dispatch_claim_until=None,
            dispatch_due=utc_now() + timedelta(seconds=5),
            cause_code="dispatch_unavailable",
            next_action="retry_dispatch",
        )

    @begin_session
    def worker_update(self, context, *, stats=None, checkpoint=None, session=None):
        from handler.database.scan_write_fence import (
            bind_scan_write_context,
            checked_scan_write,
        )
        from handler.scan_operation_projection import operation_snapshot

        with bind_scan_write_context(context), checked_scan_write(session) as row:
            changes = {}
            if stats is not None:
                changes["scan_stats"] = stats
            if checkpoint is not None:
                changes["checkpoint"] = checkpoint
            observe_execution(session, row, changes)
            return operation_snapshot(session, row)

    @begin_session
    def renew_worker_lease(self, context, *, seconds=60, session=None):
        from handler.database.scan_operations_handler import utc_now
        from handler.database.scan_write_fence import (
            bind_scan_write_context,
            checked_scan_write,
        )

        if not 1 <= seconds <= 300:
            raise ValueError("invalid_lease")
        with bind_scan_write_context(context), checked_scan_write(session) as row:
            observe_execution(
                session,
                row,
                {"lease_expires_at": utc_now() + timedelta(seconds=seconds)},
            )

    @begin_session
    def fence_lost_worker(self, identity, *, session=None):
        from handler.database.scan_operations_handler import _alive, _cas, _row, _slot

        _slot(session)
        row = _row(session, identity)
        if row.state != "running" or _alive(row.lease_expires_at):
            return False
        _cas(
            session,
            row,
            row.version,
            row.attempt_id,
            state="interrupted",
            lease_owner=None,
            lease_expires_at=None,
            cause_code="worker_lost",
            next_action="verify_source",
        )
        return True

    @begin_session
    def recovery_ready(self, identity, version, *, automatic=False, session=None):
        from handler.database.scan_operations_handler import (
            OperationConflict,
            _alive,
            _cas,
            _row,
            _slot,
            utc_now,
        )

        slot = _slot(session)
        row = _row(session, identity)
        if (
            row.state not in {"interrupted", "recovering"}
            or row.intentional_cancel
            or _alive(row.lease_expires_at)
            or slot.active_operation_id != identity
        ):
            raise OperationConflict("execution_not_fenced")
        _cas(
            session,
            row,
            version,
            state="recovering",
            attempt_id=row.attempt_id if row.state == "recovering" else str(uuid4()),
            rq_job_id=(
                row.rq_job_id
                if row.state == "recovering"
                else "scan-" + identity + "-" + str(uuid4())
            ),
            dispatch_due=utc_now(),
            dispatch_owner=None,
            dispatch_claim_until=None,
            cause_code=None,
            next_action=None,
        )

    @begin_session
    def retry_items(self, identity, item_ids, *, session=None):
        return [
            {
                key: getattr(item, key)
                for key in (
                    "id",
                    "target_key",
                    "mapping_id",
                    "expected_revision",
                    "relative_path",
                    "provider",
                    "outcome",
                    "source_evidence",
                    "checkpoint",
                )
            }
            for item in session.scalars(
                select(ScanOperationItem).where(
                    ScanOperationItem.operation_id == identity,
                    ScanOperationItem.id.in_(item_ids),
                )
            )
        ]

    @begin_session
    def note_execution_cause(self, identity, version, cause, action, *, session=None):
        from handler.database.scan_operations_handler import _cas, _row, _slot

        _slot(session)
        row = _row(session, identity)
        _cas(session, row, version, cause_code=cause, next_action=action)

    @begin_session
    def record_worker_exit(self, context, *, session=None):
        from handler.database.scan_operations_handler import _cas, _row, _slot

        _slot(session)
        row = _row(session, context.operation_id)
        if row.attempt_id != context.attempt_id:
            return
        _cas(
            session,
            row,
            row.version,
            context.attempt_id,
            checkpoint=row.checkpoint | {"stopped_job_id": row.rq_job_id},
        )

    @begin_session
    def result_counts(self, identity, *, session=None):
        from sqlalchemy import func

        rows = session.execute(
            select(ScanOperationItem.outcome, func.count())
            .where(ScanOperationItem.operation_id == identity)
            .group_by(ScanOperationItem.outcome)
        )
        counts = {outcome: total for outcome, total in rows}
        return {
            "metadata_completed_items": counts.get("completed", 0),
            "metadata_warning_items": counts.get("warning", 0),
            "metadata_failed_items": counts.get("failed", 0),
        }

    def record_worker_item(
        self, context, item, *, checkpoint=None, source_evidence=None
    ):
        from handler.filesystem.owned_writer_domain import owned_writer_domain

        with owned_writer_domain():
            return self._record_worker_item(
                context, item, checkpoint=checkpoint, source_evidence=source_evidence
            )

    @begin_session
    def _record_worker_item(
        self, context, item, *, checkpoint=None, source_evidence=None, session=None
    ):
        from handler.database.scan_write_fence import (
            bind_scan_write_context,
            checked_scan_write,
        )

        with bind_scan_write_context(context), checked_scan_write(session) as row:
            return cast("DBScanOperationsHandler", self).record_item(
                context.operation_id,
                row.version,
                context.attempt_id,
                item,
                checkpoint=checkpoint,
                source_evidence=source_evidence,
                _advance_version=False,
                session=session,
            )


def observe_execution(session, row, changes):
    from handler.database.scan_operations_handler import OperationConflict, utc_now

    result = session.execute(
        update(ScanOperation)
        .where(
            ScanOperation.id == row.id,
            ScanOperation.attempt_id == row.attempt_id,
            ScanOperation.version == row.version,
        )
        .values(**changes, updated_at=utc_now())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise OperationConflict("stale_operation")
    session.refresh(row)
