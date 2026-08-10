"""Terminal storage-policy denial tests for background jobs."""

from unittest.mock import MagicMock

import pytest

from exceptions.storage_exceptions import StoragePolicyDenied
from handler.filesystem.storage_policy import StorageOperation, StoragePolicy
from tasks.scheduled.cleanup_orphaned_resources import cleanup_orphaned_resources_task
from tasks.scheduled.cleanup_upload_tmp import cleanup_upload_tmp_task
from tasks.scheduled.cleanup_zip_cache import cleanup_zip_cache_task
from tasks.tasks import update_job_meta


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    pass


@pytest.fixture(autouse=True)
def clear_database() -> None:
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task", "operation"),
    [
        (cleanup_orphaned_resources_task, StorageOperation.DELETE),
        (cleanup_upload_tmp_task, StorageOperation.DELETE),
        (cleanup_zip_cache_task, StorageOperation.DELETE),
    ],
)
async def test_cleanup_denial_is_terminal_before_io(monkeypatch, task, operation):
    denial = StoragePolicyDenied(operation.value, "owned:test", "test")
    authorize = MagicMock(side_effect=denial)
    monkeypatch.setattr(StoragePolicy, "authorize", authorize)

    with pytest.raises(StoragePolicyDenied) as caught:
        (
            await task.run(force=True)
            if task is cleanup_orphaned_resources_task
            else await task.run()
        )

    assert caught.value is denial
    authorize.assert_called_once()


def test_job_metadata_denial_is_not_swallowed(monkeypatch):
    denial = StoragePolicyDenied("overwrite", "owned:audit", "audit")
    monkeypatch.setattr("tasks.tasks.get_current_job", MagicMock(side_effect=denial))

    with pytest.raises(StoragePolicyDenied) as caught:
        update_job_meta({"status": "completed"})

    assert caught.value is denial
