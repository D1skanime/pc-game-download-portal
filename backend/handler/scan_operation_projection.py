"""Safe durable snapshots, with an optional lazy projection from the existing RQ API."""

from datetime import timezone

from sqlalchemy import func, select

from endpoints.responses.scan_operations import (
    ScanOperationSnapshot,
)
from models.scan_operation import ScanOperationItem


def operation_snapshot(session, row, *, offset=0, limit=100):
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 100:
        raise ValueError("invalid_item_page")
    from handler.scan_inventory_status import inventory_counts, item_facts

    current = (
        ScanOperationItem.operation_id == row.id,
        ScanOperationItem.attempt_id == row.attempt_id,
    )
    items = list(
        session.scalars(
            select(ScanOperationItem)
            .where(*current)
            .order_by(ScanOperationItem.id)
            .offset(offset)
            .limit(limit)
        )
    )
    total = session.scalar(
        select(func.count()).select_from(ScanOperationItem).where(*current)
    )
    return ScanOperationSnapshot(
        id=row.id,
        request_key=row.request_key,
        job_id=row.rq_job_id,
        attempt_id=row.attempt_id,
        version=row.version,
        state=row.state,
        scan_stats={
            key: value
            for key, value in row.scan_stats.items()
            if key
            not in {
                "inventory_checked",
                "inventory_unchanged",
                "inventory_changed",
                "inventory_refresh_required",
                "inventory_incomplete",
                "unresolved_games",
                "metadata_retry_games",
                "provider_requests",
                "metadata_cache_hits",
            }
        }
        | inventory_counts(session, row),
        cause_code=row.cause_code,
        next_action=row.next_action,
        intentional_cancel=row.intentional_cancel,
        dispatch_pending=row.dispatch_due is not None,
        checkpoint=row.checkpoint,
        items=[item_facts(item) for item in items],
        items_offset=offset,
        items_total=total,
        created_at=row.created_at.replace(tzinfo=timezone.utc),
        updated_at=row.updated_at.replace(tzinfo=timezone.utc),
    )


def with_queue_projection(snapshot):
    if snapshot.dispatch_pending or snapshot.state in {"accepted", "recovering"}:
        return snapshot
    from redis.exceptions import RedisError
    from rq.exceptions import NoSuchJobError
    from rq.job import Job

    from endpoints.tasks import _build_task_status_response
    from handler.redis_handler import redis_client

    status = None
    try:
        job = Job.fetch(snapshot.job_id, connection=redis_client)
        task = _build_task_status_response(job)
        status = getattr(task["status"], "value", task["status"])
        condition = "available"
    except NoSuchJobError:
        condition = "expired"
    except RedisError:
        condition = "unavailable"
    return snapshot.model_copy(
        update={"queue_condition": condition, "queue_status": status}
    )
