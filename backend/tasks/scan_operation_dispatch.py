"""Reconcile committed scan intents into the existing RQ queues."""

from copy import deepcopy
from dataclasses import asdict
from uuid import uuid4

from redis.exceptions import RedisError
from rq.exceptions import DuplicateJobError, NoSuchJobError
from rq.job import Job, JobStatus

from config import SCAN_TIMEOUT, TASK_RESULT_TTL
from handler.database.scan_operations_handler import (
    DBScanOperationsHandler,
    OperationConflict,
)
from handler.redis_handler import high_prio_queue
from logger.logger import log
from tasks.tasks import PeriodicTask, TaskType

WORKER_FUNC = "handler.scan_operation_worker.run_scan_operation"


def dispatch_operation(identity, *, repository=None, queue=None):
    repository = repository or DBScanOperationsHandler()
    queue = queue or high_prio_queue
    state = repository.execution(identity)
    if (
        state["state"] not in {"accepted", "recovering"}
        or state["dispatch_due"] is None
    ):
        return False
    owner = str(uuid4())
    try:
        claimed = repository.claim_dispatch(identity, state["version"], owner)
    except OperationConflict:
        return False
    try:
        try:
            job = Job.fetch(claimed.job_id, connection=queue.connection)
        except NoSuchJobError:
            job = None
        if job is not None:
            if job.func_name != WORKER_FUNC or job.kwargs != {"operation_id": identity}:
                raise RuntimeError("scan_job_identity_conflict")
            if job.get_status(refresh=True) not in {
                JobStatus.QUEUED,
                JobStatus.STARTED,
                JobStatus.DEFERRED,
                JobStatus.SCHEDULED,
            }:
                repository.dispatch_failed(identity, owner)
                return False
        else:
            try:
                queue.enqueue(
                    WORKER_FUNC,
                    operation_id=identity,
                    job_id=claimed.job_id,
                    unique=True,
                    job_timeout=SCAN_TIMEOUT,
                    result_ttl=TASK_RESULT_TTL,
                    meta={
                        "task_name": "Library scan",
                        "task_type": "scan",
                        "operation_id": identity,
                    },
                )
            except DuplicateJobError:
                job = Job.fetch(claimed.job_id, connection=queue.connection)
                if job.func_name != WORKER_FUNC or job.kwargs != {
                    "operation_id": identity
                }:
                    raise RuntimeError("scan_job_identity_conflict") from None
        repository.mark_enqueued(identity, claimed.version, owner)
        return True
    except (RedisError, RuntimeError):
        repository.dispatch_failed(identity, owner)
        return False
    except OperationConflict:
        return False


def accept_commands(actor, commands, policies, *, request_key=None, repository=None):
    repository = repository or DBScanOperationsHandler()
    key = request_key or "scan-" + str(uuid4())
    accepted = repository.accept(
        actor,
        key,
        {"commands": [asdict(c) for c in commands], "request": deepcopy(policies)},
    )
    dispatch_operation(accepted.id, repository=repository)
    return repository.get_by_id(accepted.id, actor)


def system_actor():
    from sqlalchemy import select

    from handler.database.base_handler import sync_session
    from models.user import Role, User

    with sync_session() as session:
        return session.scalar(
            select(User.id).where(User.role == Role.ADMIN).order_by(User.id).limit(1)
        )


async def reconcile_scan_operations():
    from handler.scan_operation_recovery import recover_operation

    repository = DBScanOperationsHandler()
    for identity in repository.pending_execution():
        try:
            recover_operation(identity, repository=repository)
            dispatch_operation(identity, repository=repository)
        except (RedisError, OperationConflict):
            log.warning("Scan reconciliation deferred for operation %s", identity)


class ScanOperationReconciliationTask(PeriodicTask):
    def __init__(self):
        super().__init__(
            title="Scan reconciliation",
            description="Recover durable scan dispatch",
            task_type=TaskType.GENERIC,
            enabled=True,
            manual_run=False,
            cron_string="* * * * *",
            func="tasks.scan_operation_dispatch.reconcile_scan_operations",
        )

    async def run(self):
        await reconcile_scan_operations()


scan_operation_reconciliation_task = ScanOperationReconciliationTask()
