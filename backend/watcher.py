import enum
import fnmatch
import json
import os
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path
from typing import cast

import sentry_sdk
from opentelemetry import trace
from rq import Worker
from rq.job import Job, JobStatus

from config import (
    ENABLE_RESCAN_ON_FILESYSTEM_CHANGE,
    SCAN_TIMEOUT,
    SENTRY_DSN,
    TASK_RESULT_TTL,
)
from config.config_manager import config_manager as cm
from endpoints.sockets.scan import execute_mapping_scan
from exceptions.storage_exceptions import MissingPlatformStorageMappingError
from handler.database import db_platform_handler, db_storage_handler
from handler.filesystem.storage_resolver import resolve_directory
from handler.metadata import (
    meta_flashpoint_handler,
    meta_hasheous_handler,
    meta_hltb_handler,
    meta_igdb_handler,
    meta_launchbox_handler,
    meta_libretro_handler,
    meta_moby_handler,
    meta_playmatch_handler,
    meta_ra_handler,
    meta_sgdb_handler,
    meta_ss_handler,
    meta_tgdb_handler,
)
from handler.redis_handler import low_prio_queue, redis_client
from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger
from handler.scan_handler import MetadataSource, ScanType
from logger.logger import log
from tasks.tasks import TaskType, tasks_scheduler
from utils import get_version

sentry_sdk.init(dsn=SENTRY_DSN, release=f"romm@{get_version()}")
tracer = trace.get_tracer(__name__)
WATCHER_DEBOUNCE_SECONDS = 30


@enum.unique
class EventType(enum.StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


VALID_EVENTS = frozenset((EventType.ADDED, EventType.DELETED))
Change = tuple[EventType, str]


def _metadata_sources() -> list[str]:
    source_mapping: dict[str, bool] = {
        MetadataSource.IGDB: meta_igdb_handler.is_enabled(),
        MetadataSource.SS: meta_ss_handler.is_enabled(),
        MetadataSource.MOBY: meta_moby_handler.is_enabled(),
        MetadataSource.RA: meta_ra_handler.is_enabled(),
        MetadataSource.LAUNCHBOX: meta_launchbox_handler.is_enabled(),
        MetadataSource.HASHEOUS: meta_hasheous_handler.is_enabled(),
        MetadataSource.PLAYMATCH: meta_playmatch_handler.is_enabled(),
        MetadataSource.SGDB: meta_sgdb_handler.is_enabled(),
        MetadataSource.FLASHPOINT: meta_flashpoint_handler.is_enabled(),
        MetadataSource.HLTB: meta_hltb_handler.is_enabled(),
        MetadataSource.TGDB: meta_tgdb_handler.is_enabled(),
        MetadataSource.LIBRETRO: meta_libretro_handler.is_enabled(),
    }
    return [source for source, enabled in source_mapping.items() if enabled]


def _active_mappings() -> list[object]:
    mappings = []
    for platform in db_platform_handler.get_platforms():
        try:
            mappings.append(db_storage_handler.get_active_mapping(platform.id))
        except MissingPlatformStorageMappingError:
            continue
    return mappings


def _mapping_for_event(event_path: str, mappings: Sequence[object]):
    """Resolve an event canonically and reject outside or symlink-escaped paths."""
    candidate = Path(os.fsdecode(event_path)).resolve(strict=False)
    matches = []
    for mapping in mappings:
        root = resolve_directory(mapping.storage_root, mapping.relative_path)
        try:
            relative = candidate.relative_to(root)
        except ValueError:
            continue
        matches.append((len(root.parts), mapping, relative))
    if not matches:
        return None
    _, mapping, relative = max(matches, key=lambda item: item[0])
    return mapping, relative


def _is_excluded(relative_path: Path) -> bool:
    cnfg = cm.get_config()
    patterns = (
        cnfg.EXCLUDED_SINGLE_FILES
        + cnfg.EXCLUDED_MULTI_FILES
        + cnfg.EXCLUDED_MULTI_PARTS_FILES
    )
    return any(
        part.startswith(".romm_tmp_")
        or any(
            part == pattern or fnmatch.fnmatch(part, pattern) for pattern in patterns
        )
        for part in relative_path.parts
    )


def get_pending_scan_jobs(mapping_id: int | None = None) -> list[Job]:
    """Return unique delayed, queued, and active mapped scan jobs."""
    jobs: dict[str, Job] = {}
    candidates = [*tasks_scheduler.get_jobs(), *low_prio_queue.get_jobs()]
    candidates.extend(
        job
        for worker in Worker.all(connection=redis_client)
        if (job := worker.get_current_job()) is not None
    )
    for job in candidates:
        if not isinstance(job, Job):
            continue
        if job.get_status() not in {
            JobStatus.SCHEDULED,
            JobStatus.QUEUED,
            JobStatus.STARTED,
        }:
            continue
        job_mapping_id = (job.meta or {}).get("mapping_id")
        if job_mapping_id is None:
            continue
        if mapping_id is None or job_mapping_id == mapping_id:
            jobs[job.id] = job
    return list(jobs.values())


def _enqueue_watcher_command(
    command: MappedScanCommand, metadata_sources: list[str]
) -> None:
    jobs = get_pending_scan_jobs(command.mapping_id)
    queued = [
        job
        for job in jobs
        if job.get_status() in {JobStatus.SCHEDULED, JobStatus.QUEUED}
    ]
    if queued:
        return
    tasks_scheduler.enqueue_in(
        timedelta(seconds=WATCHER_DEBOUNCE_SECONDS),
        execute_mapping_scan,
        command=command,
        metadata_sources=metadata_sources,
        timeout=SCAN_TIMEOUT,
        job_result_ttl=TASK_RESULT_TTL,
        meta={
            "task_name": "Watcher Scan",
            "task_type": TaskType.SCAN,
            "mapping_id": command.mapping_id,
            "expected_revision": command.expected_revision,
            "trigger": ScanTrigger.WATCHER.value,
            "authoritative": False,
        },
    )


def process_changes(changes: Sequence[Change]) -> None:
    if not ENABLE_RESCAN_ON_FILESYSTEM_CHANGE:
        return
    metadata_sources = _metadata_sources()
    if not metadata_sources:
        log.warning("No metadata sources enabled, skipping watcher scan")
        return
    mappings = _active_mappings()
    affected: dict[int, object] = {}
    with tracer.start_as_current_span("process_changes"):
        for event_type, event_path in changes:
            if event_type not in VALID_EVENTS:
                continue
            resolved = _mapping_for_event(event_path, mappings)
            if resolved is None:
                continue
            mapping, relative_path = resolved
            if _is_excluded(relative_path):
                continue
            affected[mapping.id] = mapping
        for mapping in affected.values():
            command = MappedScanCommand(
                mapping_id=mapping.id,
                expected_revision=mapping.version,
                trigger=ScanTrigger.WATCHER,
                scope=ScanScope.PLATFORM,
                scan_type=ScanType.QUICK.value,
            )
            _enqueue_watcher_command(command, metadata_sources)


if __name__ == "__main__":
    changes = cast(list[Change], json.loads(os.getenv("WATCHFILES_CHANGES", "[]")))
    if changes:
        process_changes(changes)
