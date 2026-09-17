from unittest.mock import Mock

import pytest

from tasks.scheduled.cleanup_download_transfer_sessions import (
    CleanupDownloadTransferSessionsTask,
)


def test_task_is_bounded_and_database_only():
    task = CleanupDownloadTransferSessionsTask()
    assert task.func == (
        "tasks.scheduled.cleanup_download_transfer_sessions."
        "cleanup_download_transfer_sessions_task.run"
    )
    assert task.cron_string == "15 * * * *"


@pytest.mark.asyncio
async def test_task_runs_handler_once_and_logs_aggregate(monkeypatch):
    task = CleanupDownloadTransferSessionsTask()
    cleanup = Mock(return_value={"staled": 1, "deleted": 2})
    monkeypatch.setattr(task, "cleanup", cleanup)
    await task.run()
    cleanup.assert_awaited_once_with()
