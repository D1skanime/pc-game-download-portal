"""Retry durable deletion of parent owned-media objects only."""

from datetime import datetime, timedelta, timezone

from handler.database import db_rom_handler
from handler.filesystem import storage_composition
from handler.filesystem.storage_access import OwnedDelete, open_owned_access
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from logger.logger import log
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
        now = datetime.now(timezone.utc)
        for intent_id in db_rom_handler.get_due_owned_media_cleanup_intent_ids(now):
            intent = db_rom_handler.claim_owned_media_cleanup_intent(intent_id)
            if intent is None:
                continue
            try:
                with open_owned_access(
                    storage_composition.owned[OwnedStorageKind.RESOURCES],
                    StorageOperation.DELETE,
                    intent.owned_path,
                ) as access:
                    assert isinstance(access, OwnedDelete)
                    access.delete()
            except FileNotFoundError:
                pass
            except Exception as exc:
                delay = retry_delay(intent.attempt_count + 1)
                db_rom_handler.mark_owned_media_cleanup_failed(
                    intent.id, type(exc).__name__, now + timedelta(seconds=delay)
                )
                log.warning(f"Unable to clean owned media intent {intent.id}: {exc}")
            else:
                db_rom_handler.complete_owned_media_cleanup_intent(intent.id)


owned_media_cleanup_task = OwnedMediaCleanupTask()
