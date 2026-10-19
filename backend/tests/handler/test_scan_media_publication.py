"""Publication protocol with real SQL, capabilities, and process boundaries."""

import hashlib
import importlib
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import select
from tests.handler.test_scan_operations import (  # noqa: F401
    command,
    repository,
    running,
)
from tests.handler.test_scan_write_fence import context

from handler.database import db_rom_handler
from handler.database.base_handler import sync_engine, sync_session
from handler.database.scan_write_fence import ScanWriteRejected, bind_scan_write_context
from handler.filesystem import fs_resource_handler
from models.owned_media_cleanup import OwnedMediaCleanupIntent
from models.rom import Rom


def publication():
    try:
        return importlib.import_module("handler.filesystem.scan_media_publication")
    except ImportError:
        pytest.fail("scan media publication API is missing")


def recovery():
    return importlib.import_module("handler.filesystem.scan_media_recovery")


@pytest.fixture
def attempt(admin_user, command):
    return running(repository(), admin_user, command)


def read(path):
    return fs_resource_handler.validate_path(path).read_bytes()


def reference(rom):
    with sync_session.begin() as session:
        return session.get(Rom, rom.id).path_cover_l


def associate(rom, path, old=None):
    def apply(session):
        db_rom_handler.update_rom(rom.id, {"path_cover_l": path}, session=session)
        if old:
            db_rom_handler.create_owned_media_cleanup_intent(
                rom.id, 0, old, session=session
            )

    return apply


def batch(rom):
    return publication().ScanMediaBatch(
        rom.id, rom.platform_id, fs_resource_handler.storage
    )


def prepare(unit, rom, data=b"complete fixture"):
    output = unit.prepare(f"{rom.fs_resources_path}/cover/big.png")
    output.file.write(data)
    unit.finish(output)
    return output


def cancel(attempt, admin_user):
    return repository().request_cancel(
        attempt.id, admin_user.id, attempt.version, "media-cancel"
    )


def test_publication_protocol_capability_old_reference_survives(attempt, rom):
    with bind_scan_write_context(context(attempt)):
        first = batch(rom)
        old = prepare(first, rom, b"old valid")
        first.publish_and_associate(associate(rom, old.path))
        second = batch(rom)
        new = prepare(second, rom, b"new valid")
        assert reference(rom) == old.path
        assert read(old.path) == b"old valid"
        assert not fs_resource_handler.validate_path(new.path).exists()
        assert new.private_basename.startswith(".")
        assert read(new.private_path) == b"new valid"
        assert first.manifest_directory.startswith(".scan-media-staging/")
        second.publish_and_associate(associate(rom, new.path, old.path))
        assert reference(rom) == new.path
        assert read(new.path) == b"new valid"
    with sync_session.begin() as session:
        assert session.scalar(select(OwnedMediaCleanupIntent.owned_path)) == old.path


def test_publication_protocol_stream_cancel_has_no_final(attempt, rom, admin_user):
    started, finish = Event(), Event()

    def stream():
        with bind_scan_write_context(context(attempt)):
            unit = batch(rom)
            output = unit.prepare(f"{rom.fs_resources_path}/cover/big.png")
            try:
                output.file.write(b"first chunk")
                output.file.flush()
                started.set()
                assert finish.wait(10)
                output.file.write(b"last chunk")
                unit.finish(output)
                with pytest.raises(ScanWriteRejected):
                    unit.publish_and_associate(associate(rom, output.path))
                return output.path
            finally:
                unit.abort()

    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(stream)
        assert started.wait(10)
        cancel(attempt, admin_user)
        finish.set()
        path = work.result(timeout=15)
    assert not fs_resource_handler.validate_path(path).exists()
    assert reference(rom) in (None, "")


def test_publication_protocol_association_failure_preserves_old(attempt, rom):
    with bind_scan_write_context(context(attempt)):
        first = batch(rom)
        old = prepare(first, rom, b"old")
        first.publish_and_associate(associate(rom, old.path))
        unit = batch(rom)
        output = prepare(unit, rom, b"orphan")

        def fail(session):
            associate(rom, output.path, old.path)(session)
            raise ValueError("association fault")

        with pytest.raises(ValueError, match="association fault"):
            unit.publish_and_associate(fail)
        assert read(output.path) == b"orphan"
        assert reference(rom) == old.path
        assert read(old.path) == b"old"
        with sync_session.begin() as session:
            assert session.scalar(select(OwnedMediaCleanupIntent.id)) is None


@pytest.mark.parametrize("boundary", ["prepared", "streamed", "published", "committed"])
def test_publication_protocol_process_crash(attempt, rom, admin_user, boundary):
    publication()
    rx, tx = multiprocessing.get_context("fork").Pipe(duplex=False)

    def child():
        sync_engine.dispose(close=False)
        with bind_scan_write_context(context(attempt)):
            unit = batch(rom)
            output = unit.prepare(f"{rom.fs_resources_path}/cover/big.png")
            tx.send((unit.manifest_directory, output.path, output.private_path))
            if boundary == "prepared":
                os._exit(41)
            output.file.write(b"complete child bytes")
            unit.finish(output)
            if boundary == "streamed":
                os._exit(41)

            def apply(session):
                if boundary == "published":
                    os._exit(41)
                associate(rom, output.path)(session)

            unit.publish_and_associate(apply)
            os._exit(41)

    process = multiprocessing.get_context("fork").Process(target=child)
    process.start()
    assert rx.poll(15)
    directory, path, private = rx.recv()
    process.join(15)
    if process.is_alive():
        process.kill()
        process.join(5)
        pytest.fail("crash child exceeded deadline")
    assert process.exitcode == 41
    stopping = cancel(attempt, admin_user)
    repository().confirm_stopped(stopping.id, stopping.version, attempt.attempt_id)
    recovery().reconcile_scan_media(fs_resource_handler.storage)
    assert not fs_resource_handler.validate_path(private).exists()
    if boundary == "committed":
        assert reference(rom) == path
        assert (
            hashlib.sha256(read(path)).hexdigest()
            == hashlib.sha256(b"complete child bytes").hexdigest()
        )
    else:
        assert not fs_resource_handler.validate_path(path).exists()
        assert reference(rom) in (None, "")
    recovery().reconcile_scan_media(fs_resource_handler.storage)


def test_publication_protocol_recovery_skips_live_and_keeps_references(
    attempt, rom, admin_user
):
    with bind_scan_write_context(context(attempt)):
        unit = batch(rom)
        output = prepare(unit, rom)
        unit.publish_and_associate(associate(rom, output.path))
        abandoned = batch(rom)
        unused = prepare(abandoned, rom)
        recovery().reconcile_scan_media(fs_resource_handler.storage)
        assert fs_resource_handler.validate_path(unused.private_path).exists()
        abandoned.abort()
    stopping = cancel(attempt, admin_user)
    repository().confirm_stopped(stopping.id, stopping.version, attempt.attempt_id)
    recovery().reconcile_scan_media(fs_resource_handler.storage)
    assert read(output.path) == b"complete fixture"
    assert reference(rom) == output.path


def test_publication_protocol_unknown_commit_queries_catalog(attempt, rom, admin_user):
    from sqlalchemy import event

    with bind_scan_write_context(context(attempt)):
        unit = batch(rom)
        output = prepare(unit, rom, b"committed despite lost acknowledgement")

        def lost_ack(session):
            raise RuntimeError("commit acknowledgement lost")

        with pytest.raises(RuntimeError, match="acknowledgement"):
            with sync_session.begin() as session:
                event.listen(session, "after_commit", lost_ack, once=True)
                unit.publish_and_associate(associate(rom, output.path), session=session)
        unit.abort()
    stopping = cancel(attempt, admin_user)
    repository().confirm_stopped(stopping.id, stopping.version, attempt.attempt_id)
    recovery().reconcile_scan_media(fs_resource_handler.storage)
    assert reference(rom) == output.path
    assert read(output.path) == b"committed despite lost acknowledgement"


@pytest.mark.parametrize(
    "processing,missing,referenced",
    [
        (False, False, False),
        (True, False, False),
        (True, True, False),
        (True, False, True),
    ],
)
def test_publication_protocol_exact_cleanup_claims(
    attempt, rom, processing, missing, referenced
):
    from models.owned_media_cleanup import OwnedMediaCleanupState

    with bind_scan_write_context(context(attempt)):
        unit = batch(rom)
        output = prepare(unit, rom)
        unit.publish_and_associate(associate(rom, output.path))
        if not referenced:
            db_rom_handler.update_rom(rom.id, {"path_cover_l": None})
        intent = db_rom_handler.create_owned_media_cleanup_intent(
            rom.id, 0, output.path
        )
    if processing:
        db_rom_handler.claim_owned_media_cleanup_intent(intent.id)
    if missing:
        fs_resource_handler.validate_path(output.path).unlink()
    assert (
        recovery().reconcile_cleanup_intent(fs_resource_handler.storage, intent.id)
        is not referenced
    )
    with sync_session.begin() as session:
        saved = session.get(OwnedMediaCleanupIntent, intent.id)
        assert (saved.state == OwnedMediaCleanupState.COMPLETED) is not referenced
    assert fs_resource_handler.validate_path(output.path).exists() is referenced
    assert (
        recovery().reconcile_cleanup_intent(fs_resource_handler.storage, intent.id)
        is False
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["scan_rom", "execute_mapped_scan"])
async def test_scan_media_families_require_context(entry, rom, platform):
    from handler import scan_handler
    from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger

    with pytest.raises(ScanWriteRejected, match="context"):
        if entry == "scan_rom":
            await scan_handler.scan_rom(
                scan_handler.ScanType.COMPLETE, platform, rom, {}, [], False
            )
        else:
            await scan_handler.execute_mapped_scan(
                MappedScanCommand(
                    1, 1, ScanTrigger.MANUAL, ScanScope.PLATFORM, "quick"
                ),
                lambda *args: None,
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["igdb", "steam"])
async def test_scan_media_families_parent_association(attempt, rom, provider):
    from io import BytesIO

    import httpx
    from PIL import Image

    from handler.metadata.rom_media import refresh_provider_owned_media
    from handler.metadata.steam_owned_media import reconcile_steam_patch_media
    from models.rom import RomOwnedMedia
    from utils.context import ctx_httpx_client

    image = BytesIO()
    Image.new("RGB", (16, 16), (80, 70, 60)).save(image, "PNG")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, content=image.getvalue(), headers={"content-type": "image/png"}
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        token = ctx_httpx_client.set(client)
        try:
            with bind_scan_write_context(context(attempt)):
                rom = db_rom_handler.update_rom(
                    rom.id, {"url_cover": "https://fixture.invalid/cover.png"}
                )
                if provider == "igdb":
                    _, failures = await refresh_provider_owned_media(
                        rom, rom.updated_at, provider
                    )
                    assert failures == []
                else:
                    assert await reconcile_steam_patch_media(
                        rom,
                        {
                            "media": {
                                "cover": ["https://fixture.invalid/cover.png"],
                                "screenshots": [],
                            }
                        },
                    )
        finally:
            ctx_httpx_client.reset(token)
    with sync_session.begin() as session:
        media = session.scalar(
            select(RomOwnedMedia).where(RomOwnedMedia.rom_id == rom.id)
        )
        assert media is not None
        assert ".scan-" in media.owned_path
        assert read(media.owned_path) == image.getvalue()
