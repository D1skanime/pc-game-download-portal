from pathlib import PurePath
from time import monotonic

from handler.database.legacy_migration_handler import DBLegacyMigrationHandler
from handler.filesystem.storage_policy import _create_external_descriptor
from handler.storage.legacy_migration import (
    LEGACY_OBSERVATION_DEADLINE_SECONDS,
    LegacyDetectionOutcome,
    detect_legacy_storage,
)
from models.storage import LegacyDetectionState
from tasks.tasks import Task, TaskType


class DetectLegacyStorageTask(Task):
    def __init__(self) -> None:
        super().__init__(
            title="Detect legacy storage",
            description="Detects one exact bounded legacy platform layout",
            task_type=TaskType.GENERIC,
            enabled=True,
            manual_run=True,
        )

    async def run(
        self, platform_id: int, storage_root_id: int, actor_user_id: int
    ) -> int:
        handler = DBLegacyMigrationHandler()
        context = handler.get_detection_context(platform_id, storage_root_id)
        if context.root_active:
            descriptor = _create_external_descriptor(
                context.storage_root_id, PurePath(context.container_path)
            )
            outcome = detect_legacy_storage(
                descriptor,
                platform_id=context.platform_id,
                storage_root_id=context.storage_root_id,
                fs_slug=context.fs_slug,
                time_budget=LEGACY_OBSERVATION_DEADLINE_SECONDS,
                monotonic=monotonic,
            )
        else:
            outcome = LegacyDetectionOutcome(
                platform_id=context.platform_id,
                storage_root_id=context.storage_root_id,
                state=LegacyDetectionState.UNREACHABLE.value,
                proposed_relative_path=None,
                observed_files=0,
                observed_bytes=0,
                lower_bound=False,
                selectable=False,
                safe_problem_code="inactive_storage_root",
            )
        result = handler.save_detection_result(
            context, outcome, actor_user_id=actor_user_id
        )
        return result.id


detect_legacy_storage_task = DetectLegacyStorageTask()
