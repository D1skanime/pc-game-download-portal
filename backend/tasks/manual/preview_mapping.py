from handler.database.mapping_previews_handler import DBMappingPreviewsHandler
from handler.storage.preview import preview_mapping
from tasks.mapping_revision import MappingRevisionJob
from tasks.tasks import Task, TaskType


class PreviewMappingTask(Task):
    def __init__(self) -> None:
        super().__init__(
            title="Preview storage mapping",
            description="Builds a bounded storage mapping preview",
            task_type=TaskType.GENERIC,
            enabled=True,
            manual_run=True,
        )

    async def run(self, mapping_id: int, expected_revision: int) -> None:
        result = preview_mapping(
            MappingRevisionJob(mapping_id, expected_revision).read_context()
        )
        DBMappingPreviewsHandler().save_result(mapping_id, expected_revision, result)


preview_mapping_task = PreviewMappingTask()
