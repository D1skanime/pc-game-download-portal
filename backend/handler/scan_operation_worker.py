"""One durable attempt around the existing mapping scanner."""

import asyncio
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

from rq import get_current_job

from handler.database.scan_operations_handler import (
    DBScanOperationsHandler,
    OperationConflict,
    utc_now,
)
from handler.database.scan_write_fence import (
    ScanWriteContext,
    ScanWriteRejected,
    bind_scan_write_context,
    current_scan_write_context,
)
from handler.scan_metadata_result import bind_metadata_results
from handler.scan_operation_checkpoint import bind_checkpoint_command
from handler.scan_operation_recovery import decode_command
from utils.context import initialize_context

_RUNTIME = ContextVar("scan_operation_runtime", default=None)


@contextmanager
def bind_worker_runtime(context):
    token = _RUNTIME.set(context)
    try:
        yield context
    finally:
        _RUNTIME.reset(token)


def active_scan_worker():
    context = current_scan_write_context()
    return context is not None and _RUNTIME.get() == context


def check_worker_boundary():
    context = current_scan_write_context()
    if context is None:
        return
    state = DBScanOperationsHandler().execution(context.operation_id)
    if (
        state["state"] != "running"
        or state["intentional_cancel"]
        or state["attempt_id"] != context.attempt_id
        or state["lease_owner"] != context.lease_owner
        or state["lease_expires_at"] is None
        or state["lease_expires_at"] <= utc_now()
    ):
        raise ScanWriteRejected("scan_attempt_revoked")


def persist_scan_stats(stats):
    context = current_scan_write_context()
    if context is not None and active_scan_worker():
        DBScanOperationsHandler().worker_update(context, stats=stats)


class AttemptSocketManager:
    def __init__(self, manager):
        self.manager = manager

    async def emit(self, event, data=None, *args, **kwargs):
        check_worker_boundary()
        if event in {"scan:done", "scan:done_ko"}:
            return
        return await self.manager.emit(event, data, *args, **kwargs)


def _heartbeat(repository, context, stop, failures):
    while not stop.wait(10):
        try:
            repository.renew_worker_lease(context, seconds=60)
        except ScanWriteRejected:
            return
        except Exception as error:
            failures.append(error)
            return


def _finish(repository, identity, context, state, **kwargs):
    current = repository.execution(identity)
    if current["attempt_id"] != context.attempt_id:
        return None
    if current["state"] == "stopping":
        from handler.filesystem.owned_content_proof import owned_verifier_idle

        if not owned_verifier_idle():
            repository.note_execution_cause(
                identity, current["version"], "worker_stop_unconfirmed", "check_worker"
            )
            return None
        return repository.confirm_stopped(
            identity, current["version"], context.attempt_id
        )
    if current["state"] != "running":
        return None
    return repository.transition(
        identity, current["version"], context.attempt_id, state, **kwargs
    )


async def run_scan_operation(operation_id):
    from endpoints.sockets.scan import (
        ScanStats,
        _get_socket_manager,
        execute_mapping_scan,
    )
    from handler.scan_handler import ScanType

    repository = DBScanOperationsHandler()
    current = repository.execution(operation_id)
    job = get_current_job()
    if job is not None and job.id != current["rq_job_id"]:
        return
    if current["state"] not in {"accepted", "recovering", "queued"}:
        return
    try:
        claimed = repository.claim_attempt(
            operation_id, current["version"], str(uuid4())
        )
    except OperationConflict:
        return
    current = repository.execution(operation_id)
    context = ScanWriteContext(operation_id, claimed.attempt_id, current["lease_owner"])
    stop = threading.Event()
    heartbeat_failures: list[BaseException] = []
    heartbeat = None
    result = None
    failure: BaseException | None = None
    baseline_tasks = asyncio.all_tasks()
    try:
        with bind_scan_write_context(context), bind_worker_runtime(
            context
        ), bind_metadata_results() as outcomes:
            heartbeat = threading.Thread(
                target=_heartbeat,
                args=(repository, context, stop, heartbeat_failures),
                daemon=True,
            )
            heartbeat.start()
            async with initialize_context():
                combined = ScanStats()
                policy = current["command"].get("request", {})
                retry_ids = [
                    int(value)
                    for value in current["checkpoint"]
                    .get("retry_item_ids", "")
                    .split(",")
                    if value
                ]
                retry_items = (
                    repository.retry_items(operation_id, retry_ids) if retry_ids else []
                )
                batches = [(data, None) for data in current["command"]["commands"]]
                if retry_ids:
                    batches = [
                        (data, item)
                        for data in current["command"]["commands"]
                        for item in retry_items
                        if item["mapping_id"] == data["mapping_id"]
                    ]
                for data, retry_item in batches:
                    check_worker_boundary()
                    command = decode_command(data)
                    if retry_item is not None:
                        from dataclasses import replace

                        from handler.scan_operation_checkpoint import (
                            validate_game_evidence,
                        )

                        validate_game_evidence(command, retry_item["source_evidence"])
                        command = replace(command, scan_type=ScanType.COMPLETE.value)
                    with bind_checkpoint_command(command):
                        stats = await execute_mapping_scan(
                            command,
                            metadata_sources=(
                                [retry_item["provider"]]
                                if retry_item
                                else policy.get("apis", [])
                            ),
                            roms_ids=(
                                [retry_item["checkpoint"]["rom_id"]]
                                if retry_item
                                else policy.get("roms_ids", [])
                            ),
                            metadata_only=bool(retry_item)
                            or policy.get("metadata_only", False),
                            media_only=policy.get("media_only", False),
                            launchbox_remote_enabled=policy.get(
                                "launchbox_remote_enabled", True
                            ),
                            playmatch_enabled=policy.get("playmatch_enabled", True),
                            metadata_locale=policy.get("metadata_locale"),
                        )
                    for field, value in stats.to_dict().items():
                        setattr(combined, field, getattr(combined, field) + value)
                check_worker_boundary()
                counts = repository.result_counts(operation_id)
                final_stats = combined.to_dict()
                if retry_ids:
                    final_stats = current["scan_stats"] | {
                        "metadata_retry_scanned_roms": combined.scanned_roms
                    }
                final_stats |= counts
                persist_scan_stats(final_stats)
                has_warnings = (
                    counts["metadata_warning_items"]
                    or counts["metadata_failed_items"]
                    or any(v["outcome"] == "warning" for v in outcomes)
                )
                result = (
                    "completed-with-warnings" if has_warnings else "completed",
                    final_stats,
                )
    except ScanWriteRejected:
        result = None
    except Exception as error:
        failure = error
    finally:
        pending = asyncio.all_tasks() - baseline_tasks - {asyncio.current_task()}
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        stop.set()
        if heartbeat is not None:
            await asyncio.to_thread(heartbeat.join, 5)
            if heartbeat.is_alive():
                raise RuntimeError("scan_heartbeat_stop_unconfirmed")
    repository.record_worker_exit(context)
    if heartbeat_failures and failure is None:
        failure = heartbeat_failures[0]
    if failure is not None:
        state, cause, action = _failure_outcome(failure)
        _finish(
            repository,
            operation_id,
            context,
            state,
            cause_code=cause,
            next_action=action,
        )
        raise failure
    if result is None:
        _finish(
            repository,
            operation_id,
            context,
            "interrupted",
            cause_code="worker_lost",
            next_action="verify_source",
        )
        return
    final = _finish(repository, operation_id, context, result[0], scan_stats=result[1])
    if final is not None and final.state in {"completed", "completed-with-warnings"}:
        await _get_socket_manager().emit("scan:done", result[1])
    return result[1]


def _failure_outcome(error):
    from handler.scan_operation_checkpoint import SourceEvidenceRejected

    if isinstance(error, SourceEvidenceRejected):
        return "blocked", error.code, "new_scan"
    from exceptions.storage_read import (
        MissingMappedContentError,
        StaleMappedReadError,
        UnreachableMappedStorageError,
    )
    from handler.filesystem.storage_access import IndeterminateOwnedPublicationError

    if isinstance(error, StaleMappedReadError):
        return "blocked", "mapping_changed", "new_scan"
    if isinstance(error, UnreachableMappedStorageError):
        return "blocked", "source_unavailable", "check_storage"
    if isinstance(error, MissingMappedContentError):
        return "blocked", "source_changed", "new_scan"
    if isinstance(error, IndeterminateOwnedPublicationError):
        return "blocked", "indeterminate_owned_publication", "check_storage"
    return "failed", "worker_failed", "retry"
