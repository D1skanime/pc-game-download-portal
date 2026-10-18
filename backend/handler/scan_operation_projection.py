"""Safe durable snapshots, with an optional lazy projection from the existing RQ API."""

from datetime import timezone

from sqlalchemy import func, select

from endpoints.responses.scan_operations import (
    ScanOperationItemResult,
    ScanOperationSnapshot,
)
from models.scan_operation import ScanOperationItem


def operation_snapshot(session, row, *, offset=0, limit=100):
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 100:
        raise ValueError("invalid_item_page")
    items = list(
        session.scalars(
            select(ScanOperationItem)
            .where(ScanOperationItem.operation_id == row.id)
            .order_by(ScanOperationItem.id)
            .offset(offset)
            .limit(limit)
        )
    )
    total = session.scalar(
        select(func.count())
        .select_from(ScanOperationItem)
        .where(ScanOperationItem.operation_id == row.id)
    )
    return ScanOperationSnapshot(
        id=row.id,
        request_key=row.request_key,
        job_id=row.rq_job_id,
        attempt_id=row.attempt_id,
        version=row.version,
        state=row.state,
        scan_stats=row.scan_stats,
        cause_code=row.cause_code,
        next_action=row.next_action,
        intentional_cancel=row.intentional_cancel,
        dispatch_pending=row.dispatch_due is not None,
        checkpoint=row.checkpoint,
        items=[ScanOperationItemResult.model_validate(item) for item in items],
        items_offset=offset,
        items_total=total,
        created_at=row.created_at.replace(microsecond=0, tzinfo=timezone.utc),
        updated_at=row.updated_at.replace(microsecond=0, tzinfo=timezone.utc),
    )


def with_queue_projection(snapshot):
    if snapshot.dispatch_pending:
        return snapshot
    from redis.exceptions import RedisError
    from rq.exceptions import NoSuchJobError
    from rq.job import Job

    from endpoints.tasks import _build_task_status_response
    from handler.redis_handler import redis_client

    try:
        job = Job.fetch(snapshot.job_id, connection=redis_client)
        _build_task_status_response(job)
        condition = "available"
    except NoSuchJobError:
        condition = "expired"
    except RedisError:
        condition = "unavailable"
    return snapshot.model_copy(update={"queue_condition": condition})
