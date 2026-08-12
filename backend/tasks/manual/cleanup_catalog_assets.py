from __future__ import annotations

from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
from handler.filesystem import fs_asset_handler, fs_resource_handler
from models.catalog_lifecycle import OwnedCleanupKind
from tasks.tasks import Task, TaskType


class CleanupCatalogAssetsTask(Task):
    def __init__(self) -> None:
        super().__init__(
            title="Cleanup detached catalog assets",
            description="Retries allowlisted RomM-owned catalog asset cleanup",
            task_type=TaskType.CLEANUP,
            enabled=True,
            manual_run=True,
            cron_string=None,
        )
        self.lifecycle = CatalogLifecycleHandler()

    @staticmethod
    async def _cleanup_intent(
        *,
        kind: str,
        relative_path: str | None,
        file_name: str | None,
    ) -> None:
        if kind == OwnedCleanupKind.RESOURCE:
            if not relative_path:
                raise ValueError("resource cleanup target is missing")
            await fs_resource_handler.remove_directory(relative_path)
            return
        if kind == OwnedCleanupKind.SCREENSHOT:
            if not relative_path or not file_name:
                raise ValueError("screenshot cleanup target is missing")
            await fs_asset_handler.remove_file(f"{relative_path}/{file_name}")
            return
        raise ValueError("cleanup kind is not allowlisted")

    async def run(self, limit: int = 100) -> dict[str, int]:
        if limit < 1 or limit > 1000:
            raise ValueError("cleanup limit must be between 1 and 1000")

        completed = 0
        failed = 0
        for intent in self.lifecycle.claim_cleanup_intents(limit=limit):
            try:
                await self._cleanup_intent(
                    kind=intent.kind,
                    relative_path=intent.relative_path,
                    file_name=intent.file_name,
                )
            except FileNotFoundError:
                self.lifecycle.complete_cleanup_intent(
                    intent.id, expected_version=intent.version
                )
                completed += 1
            except (OSError, ValueError):
                self.lifecycle.fail_cleanup_intent(
                    intent.id, expected_version=intent.version
                )
                failed += 1
            else:
                self.lifecycle.complete_cleanup_intent(
                    intent.id, expected_version=intent.version
                )
                completed += 1

        return {
            "completed": completed,
            "failed": failed,
            "pending": self.lifecycle.count_pending_cleanup(),
        }


cleanup_catalog_assets_task = CleanupCatalogAssetsTask()
