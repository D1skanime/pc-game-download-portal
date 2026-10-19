"""Large valid hierarchies and independent cleanup through the scheduler."""

import pytest
from sqlalchemy.exc import SQLAlchemyError
from tests.handler.media_recovery_helpers import (
    attempt,
    command,
    drain_until,
    orphan,
    read,
    seed_receipt,
    stop,
    template_for,
)
from tests.handler.test_media_recovery_validation import cleanup_file
from tests.handler.test_scan_media_publication import recovery

from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import RESERVED
from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task


@pytest.mark.asyncio
@pytest.mark.parametrize("hierarchy", ["batches", "operations"])
async def test_513_generated_directories_recover_incrementally(
    attempt, rom, admin_user, hierarchy
):
    unit, output = orphan(attempt, rom)
    template = template_for(unit)
    directories = [
        seed_receipt(
            template,
            operation=(
                f"{index + 1:08x}-0000-4000-8000-000000000000"
                if hierarchy == "operations"
                else None
            ),
        )
        for index in range(513)
    ]
    stop(attempt, admin_user)
    await drain_until(lambda: all(not path.exists() for path in directories), calls=100)
    assert not fs_resource_handler.validate_path(output.path).exists()
    assert not fs_resource_handler.validate_path(unit.manifest_directory).exists()
    for path in directories:
        assert not path.parent.exists(), "verified empty attempt ancestor was retained"
        assert (
            not path.parent.parent.exists()
        ), "verified empty operation ancestor was retained"


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [OSError, SQLAlchemyError])
async def test_outbox_pass_runs_after_recovery_failure(
    attempt, rom, monkeypatch, error_type
):
    path, _ = cleanup_file(rom)

    def fail(storage, *args, **kwargs):
        raise error_type("deterministic recovery failure")

    monkeypatch.setattr(
        "tasks.scheduled.owned_media_cleanup.reconcile_scan_media", fail
    )
    with pytest.raises(error_type):
        await owned_media_cleanup_task.run()
    assert not fs_resource_handler.validate_path(path).exists()
