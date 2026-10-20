"""Retry exact, reference-safe owned-media and scan receipt cleanup."""

from datetime import datetime, timezone

from handler.database import db_rom_handler
from handler.filesystem import storage_composition
from handler.filesystem.catalog_collection_cleanup import (
    process_pending_collection_cleanup,
)
from handler.filesystem.scan_media_recovery import (
    reconcile_cleanup_intent,
    reconcile_scan_media,
)
from handler.filesystem.storage_policy import OwnedStorageKind
from tasks.tasks import PeriodicTask, TaskType


def retry_delay(attempt: int) -> int:
    return min(60 * (2 ** max(0, attempt - 1)), 3600)


class OwnedMediaCleanupTask(PeriodicTask):
    def __init__(self) -> None:
        super().__init__(
            title="Cleanup owned media",
            description="Retries deletion of owned parent-ROM media",
            task_type=TaskType.CLEANUP,
            enabled=True,
            manual_run=False,
            cron_string="*/10 * * * *",
            func="tasks.scheduled.owned_media_cleanup.owned_media_cleanup_task.run",
        )

    async def run(self) -> None:
        storage = storage_composition.owned[OwnedStorageKind.RESOURCES]
        try:
            reconcile_scan_media(storage)
        finally:
            try:
                for intent_id in db_rom_handler.get_due_owned_media_cleanup_intent_ids(
                    datetime.now(timezone.utc)
                ):
                    reconcile_cleanup_intent(storage, intent_id)
            finally:
                process_pending_collection_cleanup()


owned_media_cleanup_task = OwnedMediaCleanupTask()
