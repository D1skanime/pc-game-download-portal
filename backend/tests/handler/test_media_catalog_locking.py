"""Real catalog locks, immutable publication and exact cleanup on each SQL dialect."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import select
from tests.handler.test_scan_media_publication import (
    associate,
)
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_media_publication import (
    batch,
)
from tests.handler.test_scan_media_publication import command as command
from tests.handler.test_scan_media_publication import (
    prepare,
    read,
)
from tests.handler.test_scan_write_fence import context

from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_recovery import reconcile_cleanup_intent
from models.owned_media_cleanup import OwnedMediaCleanupIntent, OwnedMediaCleanupState
from models.rom import Rom
from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task


@pytest.mark.asyncio
async def test_catalog_publication_and_scheduler_cleanup(attempt, rom):
    with bind_scan_write_context(context(attempt)):
        with batch(rom) as unit:
            old = prepare(unit, rom, b"old complete bytes")
            unit.publish_and_associate(associate(rom, old.path))
        with batch(rom) as unit:
            new = prepare(unit, rom, b"new complete bytes")
            unit.publish_and_associate(associate(rom, new.path))
    with sync_session.begin() as session:
        assert session.get(Rom, rom.id).path_cover_l == new.path
        intent = session.scalar(select(OwnedMediaCleanupIntent))
        assert intent.owned_path == old.path
        identity = intent.id
    await owned_media_cleanup_task.run()
    assert not fs_resource_handler.validate_path(old.path).exists()
    assert read(new.path) == b"new complete bytes"
    with sync_session.begin() as session:
        assert (
            session.get(OwnedMediaCleanupIntent, identity).state
            == OwnedMediaCleanupState.COMPLETED
        )


def test_reference_lock_serializes_reassociation_and_cleanup(attempt, rom):
    with bind_scan_write_context(context(attempt)):
        with batch(rom) as unit:
            output = prepare(unit, rom)
            unit.publish_and_associate(lambda session: None)
    intent = db_rom_handler.create_owned_media_cleanup_intent(rom.id, 0, output.path)
    held, entered, done, release = Event(), Event(), Event(), Event()

    def reassociate():
        with sync_session.begin() as session:
            db_rom_handler.locked_scan_media_references(rom.id, session=session)
            held.set()
            assert release.wait(10)
            db_rom_handler.update_rom(
                rom.id, {"path_cover_l": output.path}, session=session
            )

    def cleanup():
        entered.set()
        result = reconcile_cleanup_intent(fs_resource_handler.storage, intent.id)
        done.set()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(reassociate)
        try:
            assert held.wait(10)
            cleaner = pool.submit(cleanup)
            assert entered.wait(10)
            assert not done.wait(0.2), "cleanup passed the held parent lock"
        finally:
            release.set()
        writer.result(timeout=15)
        assert cleaner.result(timeout=15) is False
    assert read(output.path) == b"complete fixture"
    assert db_rom_handler.get_rom(rom.id).path_cover_l == output.path
