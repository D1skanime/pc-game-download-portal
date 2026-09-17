from logger.logger import log
from tasks.tasks import PeriodicTask, TaskType


class CleanupDownloadTransferSessionsTask(PeriodicTask):
    def __init__(self):
        super().__init__(
            title="Scheduled browser transfer history cleanup",
            description="Expires inactive browser transfer sessions and removes old history",
            task_type=TaskType.CLEANUP,
            enabled=True,
            manual_run=False,
            cron_string="15 * * * *",
            func=(
                "tasks.scheduled.cleanup_download_transfer_sessions."
                "cleanup_download_transfer_sessions_task.run"
            ),
        )

    def cleanup(self) -> dict[str, int]:
        from handler.database import db_download_transfer_handler

        return db_download_transfer_handler.cleanup_sessions()

    async def run(self) -> None:
        if not self.enabled:
            self.unschedule()
            return

        result = self.cleanup()
        if result["staled"] or result["deleted"]:
            log.info(
                "Browser transfer history cleanup: "
                f"{result['staled']} sessions expired, "
                f"{result['deleted']} terminal sessions deleted"
            )


cleanup_download_transfer_sessions_task = CleanupDownloadTransferSessionsTask()
