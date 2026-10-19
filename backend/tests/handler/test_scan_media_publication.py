"""Publication protocol with real SQL, capabilities, and process boundaries."""

# Synchronous file checks are bounded fault-test instrumentation.
# ruff: noqa: ASYNC240

import hashlib
import importlib
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import select
from tests.handler import test_scan_operations
from tests.handler.test_scan_operations import (
    repository,
    running,
)
from tests.handler.test_scan_write_fence import context

from config.config_manager import MetadataMediaType
from handler.database import db_rom_handler
from handler.database.base_handler import sync_engine, sync_session
from handler.database.scan_write_fence import ScanWriteRejected, bind_scan_write_context
from handler.filesystem import fs_resource_handler
from models.owned_media_cleanup import OwnedMediaCleanupIntent
from models.rom import Rom

command = test_scan_operations.command


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


def test_publication_protocol_getters_ignore_unassociated_generations(attempt, rom):
    from handler.filesystem.base_handler import CoverSize

    with bind_scan_write_context(context(attempt)):
        with batch(rom) as unit:
            cover = prepare(unit, rom)
            screenshot = unit.prepare(f"{rom.fs_resources_path}/screenshots/0.jpg")
            screenshot.file.write(b"complete unassociated screenshot")
            unit.finish(screenshot)

            def fail(session):
                raise ValueError("association rollback")

            with pytest.raises(ValueError, match="association rollback"):
                unit.publish_and_associate(fail)
    assert read(cover.path) and read(screenshot.path)
    current = db_rom_handler.get_rom(rom.id)
    assert current.path_cover_l in (None, "")
    assert fs_resource_handler._get_cover_path(current, CoverSize.BIG) is None
    assert fs_resource_handler.cover_exists(current, CoverSize.BIG) is False
    assert fs_resource_handler.screenshots_exist(current) is False


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
    from handler.scan_command import ScanScope, ScanTrigger
    from handler.scan_handler import MappedScanCommand

    with pytest.raises(ScanWriteRejected, match="context"):
        if entry == "scan_rom":
            await scan_handler.scan_rom(
                scan_handler.ScanType.COMPLETE,
                platform,
                rom,
                dict(
                    fs_name="",
                    flat=True,
                    nested=False,
                    files=[],
                    crc_hash="",
                    md5_hash="",
                    sha1_hash="",
                    ra_hash="",
                ),
                [],
                False,
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


_MEDIA_FAMILIES = [
    "cover-small",
    "cover-big",
    "screenshot",
    "manual",
    "badge",
    "badge-lock",
    "parent",
    "steam",
    "dlc",
] + ["special:" + value.value for value in MetadataMediaType]


@pytest.mark.parametrize("family", _MEDIA_FAMILIES)
@pytest.mark.parametrize("cancel_first", [True, False])
def test_scan_media_families_real_stream_orders(
    attempt, rom, admin_user, family, cancel_first
):
    import asyncio
    from io import BytesIO
    from uuid import UUID

    import httpx
    from PIL import Image

    from handler.filesystem.base_handler import CoverSize
    from handler.metadata.rom_media import refresh_provider_owned_media
    from handler.metadata.steam_owned_media import reconcile_steam_patch_media
    from models.rom import (
        RomComponent,
        RomComponentKind,
        RomComponentOwnedMediaRole,
    )
    from utils.context import ctx_httpx_client

    image = BytesIO()
    Image.new("RGB", (16, 16), (60, 70, 80)).save(image, "PNG")
    video = family in {"special:video", "special:video_normalized"}
    manual = family in {"manual", "special:manual"}
    data = (
        b"%PDF-1.4 fixture" + bytes([10])
        if manual
        else b"complete-video-fixture" if video else image.getvalue()
    )
    mime = "application/pdf" if manual else "video/mp4" if video else "image/png"
    started, release = Event(), Event()
    component = None
    if family == "dlc":
        with sync_session.begin() as session:
            component = RomComponent(
                rom_id=rom.id, relative_path="DLC/fixture", kind=RomComponentKind.DLC
            )
            session.add(component)
            session.flush()
            session.refresh(component)

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield data[: len(data) // 2]
            if cancel_first:
                started.set()
                assert release.wait(10)
            yield data[len(data) // 2 :]

    async def run():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200, stream=Stream(), headers={"content-type": mime}
            )
        )
        async with httpx.AsyncClient(transport=transport) as client:
            token = ctx_httpx_client.set(client)
            try:
                with bind_scan_write_context(context(attempt)):
                    if family in {"parent", "steam"}:
                        current = db_rom_handler.update_rom(
                            rom.id, {"url_cover": "https://fixture.invalid/image"}
                        )
                        if family == "parent":
                            await refresh_provider_owned_media(
                                current, current.updated_at, "igdb"
                            )
                        else:
                            await reconcile_steam_patch_media(
                                current,
                                {
                                    "media": {
                                        "cover": ["https://fixture.invalid/image"],
                                        "screenshots": [],
                                    }
                                },
                            )
                    else:
                        with batch(rom) as unit:
                            url = "https://fixture.invalid/media"
                            if family.startswith("cover-"):
                                size = (
                                    CoverSize.SMALL
                                    if family == "cover-small"
                                    else CoverSize.BIG
                                )
                                path = await fs_resource_handler._store_cover(
                                    rom, url, size
                                )
                                field = (
                                    "path_cover_s"
                                    if size == CoverSize.SMALL
                                    else "path_cover_l"
                                )

                                def apply(session):
                                    return db_rom_handler.update_rom(
                                        rom.id, {field: path}, session=session
                                    )

                            elif family == "screenshot":
                                paths = await fs_resource_handler.get_rom_screenshots(
                                    rom, True, [url]
                                )

                                def apply(session):
                                    return db_rom_handler.update_rom(
                                        rom.id,
                                        {"path_screenshots": paths},
                                        session=session,
                                    )

                            elif family == "manual":
                                path = await fs_resource_handler.get_manual(
                                    rom, True, url
                                )

                                def apply(session):
                                    return db_rom_handler.update_rom(
                                        rom.id, {"path_manual": path}, session=session
                                    )

                            elif family.startswith("badge"):
                                path = await fs_resource_handler.store_ra_badge(
                                    url,
                                    f"{rom.fs_resources_path}/retroachievements/badges/fixture{'_lock' if family.endswith('lock') else ''}.png",
                                )

                                def apply(session):
                                    return db_rom_handler.update_rom(
                                        rom.id,
                                        {
                                            "ra_metadata": {
                                                "achievements": [
                                                    {"id": 1, "badge_path": path}
                                                ]
                                            }
                                        },
                                        session=session,
                                    )

                            elif family == "dlc":
                                assert component is not None
                                path, content_type, digest = (
                                    await fs_resource_handler.store_pc_component_provider_image(
                                        rom,
                                        component.id,
                                        "igdb",
                                        RomComponentOwnedMediaRole.COVER,
                                        url,
                                    )
                                )

                                def apply(session):
                                    assert component is not None
                                    return db_rom_handler.import_pc_component_provider_media(
                                        rom.id,
                                        component.id,
                                        component.updated_at,
                                        RomComponentOwnedMediaRole.COVER,
                                        content_type,
                                        path,
                                        "igdb",
                                        "fixture",
                                        digest,
                                        session=session,
                                    )

                            else:
                                kind = family.split(":")[1]
                                extension = (
                                    "mp4" if video else "pdf" if manual else "png"
                                )
                                path = await fs_resource_handler.store_media_file(
                                    url,
                                    f"{rom.fs_resources_path}/{kind}/fixture.{extension}",
                                )

                                def apply(session):
                                    return db_rom_handler.update_rom(
                                        rom.id,
                                        {"ss_metadata": {kind + "_path": path}},
                                        session=session,
                                    )

                            unit.publish_and_associate(apply)
            finally:
                ctx_httpx_client.reset(token)

    def writer():
        try:
            asyncio.run(run())
        except ScanWriteRejected:
            assert cancel_first
        else:
            assert not cancel_first
            started.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(writer)
        assert started.wait(12)
        cancel(attempt, admin_user)
        release.set()
        work.result(timeout=15)
    generation = UUID(attempt.attempt_id).hex
    files = [
        path
        for path in fs_resource_handler.validate_path(rom.fs_resources_path).rglob("*")
        if path.is_file()
        and ".scan-" + generation in path.name
        and not path.name.startswith(".")
    ]
    with sync_session.begin() as session:
        values = db_rom_handler.locked_scan_media_references(rom.id, session=session)
    if cancel_first:
        assert files == []
    else:
        assert files
        for path in files:
            relative = str(path.relative_to(fs_resource_handler.base_path))
            assert recovery()._contains(values, relative)
            assert path.stat().st_size > 0
        if family == "manual":
            current = db_rom_handler.get_rom(rom.id)
            assert (
                fs_resource_handler._validated_manual_path(current)
                == current.path_manual
            )
            assert fs_resource_handler._get_manual_path(current) == current.path_manual


@pytest.mark.asyncio
async def test_scan_media_families_local_copy_and_complete_failure(
    attempt, rom, command
):
    import hashlib
    from pathlib import Path

    import httpx

    from handler.database import db_storage_handler
    from handler.filesystem import fs_rom_handler, use_fs_rom_handler
    from handler.filesystem.scan_media_publication import publish_rom_resources
    from utils.context import ctx_httpx_client

    source = Path("/phase34/owned/library/PC/soundtracks/cover.png")
    before = (source.stat().st_ino, hashlib.sha256(source.read_bytes()).hexdigest())
    mapping = db_storage_handler.get_mapping(command["commands"][0]["mapping_id"])
    with use_fs_rom_handler(fs_rom_handler.for_mapping(mapping)):
        with bind_scan_write_context(context(attempt)):
            current = db_rom_handler.update_rom(
                rom.id,
                {
                    "url_cover": "file://soundtracks/" + source.name,
                    "url_manual": "file://soundtracks/manual.pdf",
                },
            )
            await publish_rom_resources(
                fs_resource_handler, current, current, complete=True
            )
            current = db_rom_handler.get_rom(rom.id)
            assert current.path_cover_l and current.path_cover_s
            assert (
                read(current.path_manual) == source.with_name("manual.pdf").read_bytes()
            )
            assert (
                fs_resource_handler._validated_manual_path(current)
                == current.path_manual
            )
            assert (
                fs_resource_handler.validate_path(current.path_cover_l).stat().st_ino
                != source.stat().st_ino
            )
            transport = httpx.MockTransport(lambda request: httpx.Response(503))
            async with httpx.AsyncClient(transport=transport) as client:
                token = ctx_httpx_client.set(client)
                try:
                    failing = db_rom_handler.update_rom(
                        rom.id, {"url_cover": "https://fixture.invalid/unavailable"}
                    )
                    with pytest.raises(ValueError):
                        await publish_rom_resources(
                            fs_resource_handler, failing, failing, complete=True
                        )
                finally:
                    ctx_httpx_client.reset(token)
            retained = db_rom_handler.get_rom(rom.id)
            assert retained.path_cover_l == current.path_cover_l
            assert retained.path_cover_s == current.path_cover_s
            assert read(current.path_cover_l)
    assert (
        source.stat().st_ino,
        hashlib.sha256(source.read_bytes()).hexdigest(),
    ) == before


@pytest.mark.parametrize("cancel_first", [True, False])
def test_scan_media_families_soundtrack_real_source(
    attempt, rom, command, admin_user, monkeypatch, cancel_first
):
    from pathlib import Path

    from handler.database import db_storage_handler
    from handler.filesystem import fs_rom_handler, use_fs_rom_handler
    from handler.scan_handler import persist_soundtrack_cover
    from models.rom import RomFile, RomFileCategory, TrackMeta
    from utils import audio_tags

    source = Path("/phase34/owned/library/PC/soundtracks/track.flac")
    image = source.with_name("cover.png").read_bytes()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    with sync_session.begin() as session:
        track = RomFile(
            rom_id=rom.id,
            file_name=source.name,
            file_path="soundtracks",
            file_size_bytes=source.stat().st_size,
            category=RomFileCategory.SOUNDTRACK,
        )
        track.track_meta = TrackMeta(rom_id=rom.id, has_embedded_cover=True)
        session.add(track)
        session.flush()
    mapping = db_storage_handler.get_mapping(command["commands"][0]["mapping_id"])
    mapped = fs_rom_handler.for_mapping(mapping)
    original = audio_tags.extract_embedded_cover
    started, release = Event(), Event()

    def extract(path):
        import fcntl

        assert hasattr(
            path, "fileno"
        ), "scan extraction requires an open source capability"
        assert fcntl.fcntl(path.fileno(), fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
        result = original(path)
        assert result is not None
        if cancel_first:
            started.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(audio_tags, "extract_embedded_cover", extract)

    def writer():
        with use_fs_rom_handler(mapped), bind_scan_write_context(context(attempt)):
            if cancel_first:
                with pytest.raises(ScanWriteRejected):
                    persist_soundtrack_cover(track, rom)
            else:
                persist_soundtrack_cover(track, rom)
                started.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(writer)
        assert started.wait(12)
        cancel(attempt, admin_user)
        release.set()
        work.result(timeout=15)
    with sync_session.begin() as session:
        reference = session.get(TrackMeta, track.id).cover_path
    if cancel_first:
        assert reference is None
    else:
        assert read(reference) == image
        assert (
            fs_resource_handler.validate_path(reference).stat().st_ino
            != source.stat().st_ino
        )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_publication_protocol_old_attempt_cleanup_protects_new(
    attempt, rom, admin_user
):
    with bind_scan_write_context(context(attempt)):
        old = batch(rom)
        large = prepare(old, rom, b"old large")
        small = old.prepare(f"{rom.fs_resources_path}/cover/small.png")
        small.file.write(b"old small")
        old.finish(small)
        old.publish_and_associate(
            lambda session: db_rom_handler.update_rom(
                rom.id,
                {"path_cover_l": large.path, "path_cover_s": small.path},
                session=session,
            )
        )
    stopping = cancel(attempt, admin_user)
    stopped = repository().confirm_stopped(
        stopping.id, stopping.version, attempt.attempt_id
    )
    resumed = repository().request_resume(
        stopped.id, admin_user.id, stopped.version, "resume-media"
    )
    queued = repository().transition(
        resumed.id, resumed.version, resumed.attempt_id, "queued"
    )
    replacement = repository().claim_attempt(queued.id, queued.version, "worker")
    with bind_scan_write_context(context(replacement)):
        new = batch(rom)
        output = prepare(new, rom, b"new large")
        new.publish_and_associate(associate(rom, output.path))
    assert recovery().reconcile_manifest(
        fs_resource_handler.storage, old.manifest_directory
    )
    assert read(output.path) == b"new large"
    assert read(small.path) == b"old small"
    assert not fs_resource_handler.validate_path(large.path).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["commit_ack", "cleanup_intent"])
async def test_scan_media_families_nonscan_unknown_commit_keeps_references(
    rom, monkeypatch, fault
):
    from io import BytesIO

    import httpx
    from PIL import Image
    from sqlalchemy.exc import SQLAlchemyError

    from handler.metadata.steam_owned_media import reconcile_steam_patch_media
    from models.rom import RomOwnedMedia
    from utils.context import ctx_httpx_client

    content = BytesIO()
    Image.new("RGB", (16, 16), (80, 70, 60)).save(content, "PNG")
    patch = {"media": {"cover": ["https://fixture.invalid/old"], "screenshots": []}}
    original = db_rom_handler.reconcile_steam_owned_media_inventory

    def lost_ack(*args, **kwargs):
        original(*args, **kwargs)
        raise SQLAlchemyError("lost commit acknowledgement")

    def failed_cleanup(*args, **kwargs):
        raise SQLAlchemyError("cleanup intent unavailable")

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, content=content.getvalue(), headers={"content-type": "image/png"}
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        token = ctx_httpx_client.set(client)
        try:
            if fault == "cleanup_intent":
                assert await reconcile_steam_patch_media(rom, patch)
                rom = db_rom_handler.get_rom(rom.id)
                patch["media"]["cover"] = ["https://fixture.invalid/new"]
                monkeypatch.setattr(
                    db_rom_handler, "create_owned_media_cleanup_intent", failed_cleanup
                )
            else:
                monkeypatch.setattr(
                    db_rom_handler, "reconcile_steam_owned_media_inventory", lost_ack
                )
            assert await reconcile_steam_patch_media(rom, patch) is False
        finally:
            ctx_httpx_client.reset(token)
    with sync_session.begin() as session:
        media = session.scalars(
            select(RomOwnedMedia).where(RomOwnedMedia.rom_id == rom.id)
        ).all()
    live = [item for item in media if item.state.value == "active"]
    assert len(live) == 1
    assert read(live[0].owned_path) == content.getvalue()


def test_publication_protocol_bound_recovery_hashes_outside_sql_locks(
    attempt, rom, admin_user, monkeypatch
):
    with bind_scan_write_context(context(attempt)):
        unit = batch(rom)
        output = prepare(unit, rom, b"recovery bytes")
        unit.publish_and_associate(associate(rom, output.path))
    original = recovery()._digest_matches
    started, release = Event(), Event()

    def digest(storage, record):
        result = original(storage, record)
        started.set()
        assert release.wait(8)
        return result

    monkeypatch.setattr(recovery(), "_digest_matches", digest)

    def reconcile():
        with bind_scan_write_context(context(attempt)):
            return recovery().reconcile_manifest(
                fs_resource_handler.storage, unit.manifest_directory
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        work = pool.submit(reconcile)
        assert started.wait(10)
        cancellation = pool.submit(cancel, attempt, admin_user)
        try:
            stopping = cancellation.result(timeout=3)
        finally:
            release.set()
        try:
            work.result(timeout=10)
        except ScanWriteRejected:
            pass
    assert stopping.state == "stopping"
    assert reference(rom) == output.path
    assert read(output.path) == b"recovery bytes"


@pytest.mark.asyncio
async def test_scan_media_families_parent_inventory_suppression_upload_and_empty(
    attempt, rom
):
    from pathlib import Path

    import httpx

    from handler.metadata.steam_owned_media import reconcile_steam_patch_media
    from models.rom import (
        RomOwnedMedia,
        RomOwnedMediaOrigin,
        RomOwnedMediaRole,
        RomOwnedMediaState,
    )
    from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task
    from utils.context import ctx_httpx_client

    image = Path("/phase34/owned/library/PC/soundtracks/cover.png").read_bytes()
    upload, mime = await fs_resource_handler.store_owned_media_image(
        rom, RomOwnedMediaRole.ARTWORK, image
    )
    added = db_rom_handler.create_owned_upload_media(
        rom.id, rom.updated_at, RomOwnedMediaRole.ARTWORK, "Upload", mime, upload
    )
    assert added is not None
    patch = {
        "media": {
            "cover": ["https://fixture.invalid/a"],
            "screenshots": ["https://fixture.invalid/b"],
        }
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, content=image, headers={"content-type": "image/png"}
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        token = ctx_httpx_client.set(client)
        try:
            with bind_scan_write_context(context(attempt)):
                current = db_rom_handler.get_rom(rom.id)
                assert await reconcile_steam_patch_media(current, patch)
                current = db_rom_handler.get_rom(rom.id)
                providers = [
                    item
                    for item in current.owned_media
                    if item.origin == RomOwnedMediaOrigin.PROVIDER
                ]
                suppressed = providers[0]
                deleted = db_rom_handler.delete_owned_media(
                    rom.id, suppressed.id, current.updated_at
                )
                assert deleted is not None
                current = db_rom_handler.get_rom(rom.id)
                assert await reconcile_steam_patch_media(current, patch, force=True)
                current = db_rom_handler.get_rom(rom.id)
                held = next(
                    item for item in current.owned_media if item.id == suppressed.id
                )
                assert (
                    held.operator_suppressed
                    and held.state == RomOwnedMediaState.TOMBSTONED
                )
                active_paths = [
                    item.owned_path
                    for item in current.owned_media
                    if item.origin == RomOwnedMediaOrigin.PROVIDER and item.owned_path
                ]
                assert await reconcile_steam_patch_media(
                    current, {"media": {"cover": [], "screenshots": []}}
                )
                assert all(read(path) == image for path in active_paths)
        finally:
            ctx_httpx_client.reset(token)
    await owned_media_cleanup_task.run()
    assert read(upload) == image
    assert all(
        not fs_resource_handler.validate_path(path).exists() for path in active_paths
    )
    with sync_session.begin() as session:
        rows = session.scalars(
            select(RomOwnedMedia).where(RomOwnedMedia.rom_id == rom.id)
        ).all()
    assert [
        item.owned_path for item in rows if item.origin == RomOwnedMediaOrigin.UPLOAD
    ] == [upload]
    assert all(
        item.state == RomOwnedMediaState.TOMBSTONED
        for item in rows
        if item.origin == RomOwnedMediaOrigin.PROVIDER
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("orphan", [False, True])
async def test_scan_media_families_soundtrack_removal_and_orphan_cleanup(
    attempt, rom, command, orphan
):
    from pathlib import Path

    from handler.database import db_storage_handler
    from handler.filesystem import fs_rom_handler, use_fs_rom_handler
    from handler.scan_handler import persist_soundtrack_cover
    from models.rom import RomFile, RomFileCategory, TrackMeta
    from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task

    source = Path("/phase34/owned/library/PC/soundtracks/track.flac")
    with sync_session.begin() as session:
        track = RomFile(
            rom_id=rom.id,
            file_name=source.name,
            file_path="soundtracks",
            file_size_bytes=source.stat().st_size,
            category=RomFileCategory.SOUNDTRACK,
        )
        track.track_meta = TrackMeta(rom_id=rom.id, has_embedded_cover=True)
        session.add(track)
        session.flush()
    mapping = db_storage_handler.get_mapping(command["commands"][0]["mapping_id"])
    with use_fs_rom_handler(
        fs_rom_handler.for_mapping(mapping)
    ), bind_scan_write_context(context(attempt)):
        persist_soundtrack_cover(track, rom)
        with sync_session.begin() as session:
            cover = session.get(TrackMeta, track.id).cover_path
        assert read(cover) == source.with_name("cover.png").read_bytes()
        if orphan:
            with batch(rom) as unit:
                unit.publish_and_associate(
                    lambda session: db_rom_handler.sync_rom_files(
                        rom.id, [], session=session
                    )
                )
        else:
            track.track_meta.has_embedded_cover = False
            persist_soundtrack_cover(track, rom)
        assert read(cover)
    with sync_session.begin() as session:
        metadata = session.get(TrackMeta, track.id)
        assert metadata is None if orphan else metadata.cover_path is None
        intent = session.scalar(
            select(OwnedMediaCleanupIntent).where(
                OwnedMediaCleanupIntent.owned_path == cover
            )
        )
        assert intent is not None
    await owned_media_cleanup_task.run()
    assert not fs_resource_handler.validate_path(cover).exists()


@pytest.mark.parametrize(
    "unsafe", ["traversal", "outside_rom", "private", "unknown_child", "final_symlink"]
)
def test_publication_protocol_unsafe_recovery_preserves_bytes(
    attempt, rom, admin_user, unsafe
):
    import json

    with bind_scan_write_context(context(attempt)):
        unit = batch(rom)
        output = prepare(unit, rom, b"protected")
        unit.publish_and_associate(associate(rom, output.path))
    stopping = cancel(attempt, admin_user)
    repository().confirm_stopped(stopping.id, stopping.version, attempt.attempt_id)
    directory = fs_resource_handler.validate_path(unit.manifest_directory)
    receipt = max(directory.glob("receipt-*.json"))
    document = json.loads(receipt.read_bytes())
    sentinel = directory.parent / "protected-upload.png"
    sentinel.write_bytes(b"upload must survive")
    if unsafe == "traversal":
        document["outputs"][0]["final"] = "../protected-upload.png"
    elif unsafe == "outside_rom":
        document["rom"] = rom.id + 100
    elif unsafe == "private":
        document["outputs"][0]["private"] = str(sentinel)
    elif unsafe == "unknown_child":
        (directory / "unknown").write_bytes(b"retain receipt")
    else:
        fs_resource_handler.validate_path(output.path).unlink()
        fs_resource_handler.validate_path(output.path).symlink_to(sentinel)
    receipt.write_text(json.dumps(document))
    from exceptions.storage_exceptions import StorageResolutionError

    with pytest.raises((ValueError, StorageResolutionError)):
        recovery().reconcile_manifest(
            fs_resource_handler.storage, unit.manifest_directory
        )
    assert sentinel.read_bytes() == b"upload must survive"
    assert receipt.exists()
    assert reference(rom) == output.path


@pytest.mark.asyncio
async def test_scan_media_families_actual_complete_scanner_preserves_old_until_publish(
    attempt, rom, platform
):
    from handler import scan_handler

    with bind_scan_write_context(context(attempt)):
        unit = batch(rom)
        old = prepare(unit, rom, b"old valid image")
        unit.publish_and_associate(associate(rom, old.path))
        current = db_rom_handler.get_rom(rom.id)
        scanned = await scan_handler.scan_rom(
            scan_handler.ScanType.COMPLETE,
            platform,
            current,
            {
                "fs_name": rom.fs_name,
                "files": [],
                "nested": False,
                "flat": True,
                "crc_hash": "",
                "md5_hash": "",
                "sha1_hash": "",
                "ra_hash": "",
            },
            [],
            False,
            launchbox_remote_enabled=False,
            playmatch_enabled=False,
        )
        assert reference(rom) == old.path
        assert scanned.path_cover_l == old.path
        db_rom_handler.add_rom(scanned)
        assert reference(rom) == old.path
        assert read(old.path) == b"old valid image"


@pytest.mark.asyncio
async def test_scan_media_families_complete_entry_source_and_provider_failure(
    attempt, rom, platform, command
):
    from unittest.mock import AsyncMock

    from endpoints.sockets.scan import ScanStats, _identify_rom
    from handler.database import db_storage_handler
    from handler.filesystem import fs_rom_handler, use_fs_rom_handler
    from handler.scan_handler import ScanType

    mapping = db_storage_handler.get_mapping(command["commands"][0]["mapping_id"])
    with use_fs_rom_handler(
        fs_rom_handler.for_mapping(mapping)
    ), bind_scan_write_context(context(attempt)):
        current = db_rom_handler.update_rom(
            rom.id, {"fs_name": "Phase34-Synthetic.bin", "fs_path": "PC"}
        )
        with batch(rom) as unit:
            old = prepare(unit, rom, b"old valid cover")
            manual = unit.prepare(f"{rom.fs_resources_path}/manual/{rom.id}.pdf")
            manual.file.write(b"%PDF-old-valid")
            unit.finish(manual)
            unit.publish_and_associate(
                lambda session: db_rom_handler.update_rom(
                    rom.id,
                    {
                        "path_cover_l": old.path,
                        "path_manual": manual.path,
                        "url_cover": "https://fixture.invalid/missing",
                    },
                    session=session,
                )
            )
        current = db_rom_handler.get_rom(rom.id)
        stats = ScanStats()
        await _identify_rom(
            platform,
            {
                "fs_name": current.fs_name,
                "files": [],
                "nested": False,
                "flat": True,
                "crc_hash": "",
                "md5_hash": "",
                "sha1_hash": "",
                "ra_hash": "",
            },
            current,
            ScanType.COMPLETE,
            [],
            [],
            False,
            False,
            AsyncMock(),
            stats,
        )
    saved = db_rom_handler.get_rom(rom.id)
    assert saved.path_cover_l == old.path
    assert saved.path_manual == manual.path
    assert read(old.path) == b"old valid cover"
    assert read(manual.path) == b"%PDF-old-valid"
    assert stats.scanned_roms == 1
    assert saved.files
    assert saved.files[0].file_size_bytes == len(b"phase34 synthetic fixture\n")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [ValueError("invalid optional image"), OSError("stream unavailable")]
)
async def test_scan_media_families_steam_optional_failure_retains_prior(
    attempt, rom, monkeypatch, error
):
    from handler.metadata import steam_owned_media
    from models.rom import RomOwnedMedia

    async def failed(*_args):
        raise error

    monkeypatch.setattr(steam_owned_media, "_download_candidate", failed)
    with bind_scan_write_context(context(attempt)):
        assert (
            await steam_owned_media.reconcile_steam_patch_media(
                rom,
                {
                    "media": {
                        "cover": ["https://fixture.invalid/failure"],
                        "screenshots": [],
                    }
                },
            )
            is False
        )
    with sync_session.begin() as session:
        assert (
            session.scalar(
                select(RomOwnedMedia.id).where(RomOwnedMedia.rom_id == rom.id)
            )
            is None
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["ss", "gamelist", "launchbox"])
async def test_scan_media_families_actual_scanner_special_inventory(
    attempt, rom, platform, command, monkeypatch, source
):
    from pathlib import Path
    from unittest.mock import AsyncMock

    import httpx

    from endpoints.sockets import scan as scan_module
    from handler import scan_handler
    from handler.database import db_storage_handler
    from handler.filesystem import fs_rom_handler, use_fs_rom_handler
    from utils.context import ctx_httpx_client

    image = Path("/phase34/owned/library/PC/soundtracks/cover.png").read_bytes()
    desired = {}
    for kind in MetadataMediaType:
        extension = (
            "mp4"
            if kind.value in {"video", "video_normalized"}
            else "pdf" if kind.value == "manual" else "png"
        )
        desired[kind.value + "_url"] = "https://fixture.invalid/special." + extension
        desired[kind.value + "_path"] = (
            f"{rom.fs_resources_path}/{kind.value}/fixture.{extension}"
        )
    response = {
        source + "_id": 101,
        "name": "Synthetic",
        source + "_metadata": desired,
        "url_cover": "https://fixture.invalid/cover.png",
        "url_screenshots": ["https://fixture.invalid/screenshot.png"],
        "url_manual": "https://fixture.invalid/manual.pdf",
    }
    provider = getattr(scan_handler, "meta_" + source + "_handler")
    monkeypatch.setattr(provider, "get_rom", AsyncMock(return_value=response))
    if source == "ss":
        monkeypatch.setattr(
            provider, "lookup_rom", AsyncMock(return_value=(response, False))
        )
    monkeypatch.setattr(
        scan_module, "get_preferred_media_types", lambda: list(MetadataMediaType)
    )
    monkeypatch.setattr(
        scan_handler.meta_ra_handler,
        "get_rom",
        AsyncMock(
            return_value={
                "ra_id": 201,
                "ra_metadata": {
                    "achievements": [
                        {
                            "id": 1,
                            "badge_url": "https://fixture.invalid/badge.png",
                            "badge_url_lock": "https://fixture.invalid/lock.png",
                            "badge_path": f"{rom.fs_resources_path}/retroachievements/badges/1.png",
                            "badge_path_lock": f"{rom.fs_resources_path}/retroachievements/badges/1_lock.png",
                        }
                    ]
                },
            }
        ),
    )
    with sync_session.begin() as session:
        row = session.get(type(platform), platform.id)
        row.ss_id, row.ra_id = 1, 1
    platform = db_storage_handler.get_mapping(
        command["commands"][0]["mapping_id"]
    ).platform

    def respond(request):
        suffix = request.url.path.rsplit(".", 1)[-1]
        data, mime = (
            (b"%PDF-1.4 fixture", "application/pdf")
            if suffix == "pdf"
            else (
                (b"complete video fixture", "video/mp4")
                if suffix == "mp4"
                else (image, "image/png")
            )
        )

        class Body(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield data

        return httpx.Response(200, stream=Body(), headers={"content-type": mime})

    mapping = db_storage_handler.get_mapping(command["commands"][0]["mapping_id"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        token = ctx_httpx_client.set(client)
        try:
            with use_fs_rom_handler(
                fs_rom_handler.for_mapping(mapping)
            ), bind_scan_write_context(context(attempt)):
                current = db_rom_handler.update_rom(
                    rom.id, {"fs_name": "Phase34-Synthetic.bin", "fs_path": "PC"}
                )
                await scan_module._identify_rom(
                    platform,
                    {
                        "fs_name": current.fs_name,
                        "files": [],
                        "flat": True,
                        "nested": False,
                        "crc_hash": "",
                        "md5_hash": "",
                        "sha1_hash": "",
                        "ra_hash": "",
                    },
                    current,
                    scan_handler.ScanType.COMPLETE,
                    [],
                    [source, "ra"],
                    False,
                    False,
                    AsyncMock(),
                    scan_module.ScanStats(),
                )
        finally:
            ctx_httpx_client.reset(token)
    current = db_rom_handler.get_rom(rom.id)
    for kind in MetadataMediaType:
        path = getattr(current, source + "_metadata")[kind.value + "_path"]
        assert ".scan-" in path
        assert read(path)
    assert read(current.path_manual).startswith(b"%PDF-")
    assert read(current.path_cover_l) and read(current.path_cover_s)
    assert (
        len(current.path_screenshots) == 1
        and read(current.path_screenshots[0]) == image
    )
    for key in ("badge_path", "badge_path_lock"):
        assert read(current.ra_metadata["achievements"][0][key]) == image


@pytest.mark.parametrize("cancel_first", [True, False])
def test_scan_media_families_actual_dlc_stream_orders(
    attempt, rom, admin_user, monkeypatch, cancel_first
):
    import asyncio
    from pathlib import Path
    from unittest.mock import AsyncMock

    import httpx

    from endpoints.sockets.scan import (
        _enrich_pc_dlc_from_igdb,
        pc_metadata_match_handler,
    )
    from handler.metadata.pc_match_handler import PcMetadataCandidate
    from models.rom import RomComponent, RomComponentKind, RomComponentOwnedMedia
    from utils.context import ctx_httpx_client

    image = Path("/phase34/owned/library/PC/soundtracks/cover.png").read_bytes()
    with sync_session.begin() as session:
        component = RomComponent(
            rom_id=rom.id, relative_path="DLC/Synthetic", kind=RomComponentKind.DLC
        )
        session.add(component)
        session.flush()
        session.refresh(component)
    candidate = PcMetadataCandidate(
        "fixture",
        "igdb",
        "Synthetic DLC",
        {"igdb_id": 101},
        False,
        [{"kind": "cover", "url": "https://fixture.invalid/dlc.png"}],
        {"igdb_id": 101, "name": "Synthetic DLC"},
    )
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "fetch_unique_related_igdb_candidate",
        AsyncMock(return_value=candidate),
    )
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "fetch_validated_steam_dlc",
        AsyncMock(return_value=None),
    )
    started, release = Event(), Event()

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield image[:10]
            if cancel_first:
                started.set()
                assert release.wait(10)
            yield image[10:]

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, stream=Stream(), headers={"content-type": "image/png"}
                )
            )
        ) as client:
            token = ctx_httpx_client.set(client)
            try:
                with bind_scan_write_context(context(attempt)):
                    await _enrich_pc_dlc_from_igdb(rom, component)
            finally:
                ctx_httpx_client.reset(token)

    def writer():
        try:
            asyncio.run(run())
        except ScanWriteRejected:
            assert cancel_first
        else:
            assert not cancel_first
            started.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(writer)
        assert started.wait(12)
        cancel(attempt, admin_user)
        release.set()
        work.result(timeout=15)
    with sync_session.begin() as session:
        media = session.scalars(
            select(RomComponentOwnedMedia).where(
                RomComponentOwnedMedia.component_id == component.id
            )
        ).all()
    assert len(media) == (0 if cancel_first else 1)
    for item in media:
        assert read(item.owned_path) == image
