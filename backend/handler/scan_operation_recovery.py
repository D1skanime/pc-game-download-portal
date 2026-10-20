"""Revoke lost ownership before considering any continuation."""

from exceptions.storage_read import StaleMappedReadError, UnreachableMappedStorageError
from handler.database.scan_operations_handler import DBScanOperationsHandler
from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger
from handler.scan_operation_checkpoint import (
    SourceEvidenceRejected,
    validate_recovery_checkpoint,
)
from handler.storage.read_context import MappingReadContext


def decode_command(data):
    return MappedScanCommand(
        **(
            data
            | {
                "trigger": ScanTrigger(data["trigger"]),
                "scope": ScanScope(data["scope"]),
                "options": tuple(tuple(v) for v in data.get("options", [])),
            }
        )
    )


def recover_operation(
    identity, *, repository=None, checkpoint_validator=validate_recovery_checkpoint
):
    repository = repository or DBScanOperationsHandler()
    execution = repository.execution(identity)
    if execution["state"] == "stopping":
        if worker_exit_confirmed(execution):
            repository.confirm_stopped(
                identity, execution["version"], execution["attempt_id"]
            )
        else:
            repository.note_execution_cause(
                identity,
                execution["version"],
                "worker_stop_unconfirmed",
                "check_worker",
            )
        return
    if execution["intentional_cancel"] or execution["state"] in {
        "cancelled",
        "completed",
        "completed-with-warnings",
        "failed",
        "blocked",
    }:
        return
    if execution["state"] == "queued":
        from redis.exceptions import RedisError
        from rq.exceptions import NoSuchJobError
        from rq.job import Job, JobStatus

        from handler.redis_handler import redis_client

        try:
            job = Job.fetch(execution["rq_job_id"], connection=redis_client)
            if job.get_status(refresh=True) in {
                JobStatus.QUEUED,
                JobStatus.STARTED,
                JobStatus.DEFERRED,
                JobStatus.SCHEDULED,
            }:
                return
        except RedisError:
            return
        except NoSuchJobError:
            pass
        repository.transition(
            identity,
            execution["version"],
            execution["attempt_id"],
            "interrupted",
            cause_code="worker_lost",
            next_action="verify_source",
        )
        execution = repository.execution(identity)
    if execution["state"] == "running":
        if not repository.fence_lost_worker(identity):
            return
        execution = repository.execution(identity)
    if (
        execution["state"] not in {"recovering", "interrupted"}
        or execution["dispatch_due"] is not None
    ):
        return
    if execution["state"] in {
        "interrupted",
        "recovering",
    } and not worker_exit_confirmed(execution):
        repository.note_execution_cause(
            identity, execution["version"], "worker_stop_unconfirmed", "check_worker"
        )
        return
    try:
        for data in execution["command"]["commands"]:
            command = decode_command(data)
            MappingReadContext(command.mapping_id, command.expected_revision).validate()
        retry_ids = [
            int(value)
            for value in execution["checkpoint"].get("retry_item_ids", "").split(",")
            if value
        ]
        if retry_ids:
            from handler.scan_operation_checkpoint import validate_game_evidence

            items = repository.retry_items(identity, retry_ids)
            if len(items) != len(set(retry_ids)):
                raise SourceEvidenceRejected()
            for item in items:
                command = next(
                    (
                        decode_command(data)
                        for data in execution["command"]["commands"]
                        if data["mapping_id"] == item["mapping_id"]
                    ),
                    None,
                )
                if command is None:
                    raise SourceEvidenceRejected()
                validate_game_evidence(command, item["source_evidence"])
        else:
            checkpoint_validator(execution)
    except StaleMappedReadError:
        cause, action = "mapping_changed", "new_scan"
    except UnreachableMappedStorageError:
        cause, action = "source_unavailable", "check_storage"
    except SourceEvidenceRejected as error:
        cause, action = error.code, "new_scan"
    else:
        repository.recovery_ready(identity, execution["version"])
        return
    repository.transition(
        identity,
        execution["version"],
        execution["attempt_id"],
        "blocked",
        cause_code=cause,
        next_action=action,
    )


def worker_exit_confirmed(execution):
    from redis.exceptions import RedisError
    from rq import Worker
    from rq.exceptions import NoSuchJobError
    from rq.job import Job, JobStatus

    from handler.filesystem.owned_content_proof import owned_verifier_idle
    from handler.redis_handler import redis_client

    if not owned_verifier_idle():
        return False
    checkpoint = execution.get("checkpoint", {})
    previous = checkpoint.get("previous_rq_job_id")
    identity = previous or execution["rq_job_id"]
    if (
        execution.get("attempt_id") is None
        or checkpoint.get("previous_never_started")
        or checkpoint.get("stopped_job_id") == identity
    ):
        return True
    try:
        job = Job.fetch(identity, connection=redis_client)
        if (
            job.get_status(refresh=True)
            not in {JobStatus.FINISHED, JobStatus.FAILED, JobStatus.STOPPED}
            or job.ended_at is None
        ):
            return False
        for worker in Worker.all(connection=redis_client):
            active = worker.get_current_job()
            if active is not None and active.id == job.id:
                return False
        return True
    except (RedisError, NoSuchJobError):
        return False
