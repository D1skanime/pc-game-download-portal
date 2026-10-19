"""Strict streamed gzip completion before any resource association."""

import gzip
import hashlib
import signal
import zlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import select
from tests.handler.media_download_helpers import (
    Body,
)
from tests.handler.media_download_helpers import (
    owned_resource_files as owned_resource_files,
)
from tests.handler.media_download_helpers import (
    resource_snapshot,
)
from tests.handler.test_scan_media_publication import attempt as attempt
from tests.handler.test_scan_operations import command as command
from tests.handler.test_scan_write_fence import context

from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.scan_write_fence import bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import ScanMediaBatch, store_resource
from models.owned_media_cleanup import OwnedMediaCleanupIntent
from utils.context import ctx_httpx_client


@pytest.fixture(autouse=True)
def bounded_decode():
    previous = signal.getsignal(signal.SIGALRM)

    def deadline(_signum, _frame):
        raise AssertionError("resource decode exceeded five second deadline")

    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 5)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def gzip_parts(fault):
    payload = b"%PDF-1.4 complete resource\n" * 120000
    compressor = zlib.compressobj(wbits=16 + zlib.MAX_WBITS)
    first = compressor.compress(payload[:1500000]) + compressor.flush(zlib.Z_SYNC_FLUSH)
    last = compressor.compress(payload[1500000:]) + compressor.flush()
    if fault == "mislabeled":
        return payload, [payload[:1500000], payload[1500000:]]
    if fault == "truncated_second":
        return payload, [
            gzip.compress(payload[:1500000]),
            gzip.compress(payload[1500000:])[:-8],
        ]
    if fault == "truncated":
        last = last[:-8]
    elif fault == "checksum":
        last = last[:-8] + bytes([last[-8] ^ 255]) + last[-7:]
    elif fault == "later_corruption":
        last = b"\xff" * len(last)
    elif fault == "trailing":
        last += b"unencoded trailer"
    return payload, [first, last]


@asynccontextmanager
async def encoded_response(parts, encoding="gzip", mime="application/pdf"):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                stream=Body(parts),
                headers={"content-type": mime, "content-encoding": encoding},
            )
        )
    ) as client:
        token = ctx_httpx_client.set(client)
        try:
            yield
        finally:
            ctx_httpx_client.reset(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("family", ["manual", "video"])
@pytest.mark.parametrize(
    "fault",
    [
        "truncated",
        "checksum",
        "later_corruption",
        "trailing",
        "mislabeled",
        "truncated_second",
    ],
)
@pytest.mark.parametrize("scan", [True, False])
async def test_gzip_rejected_before_final_or_association(
    attempt, rom, family, fault, scan
):
    path = f"{rom.fs_resources_path}/{family}/fixture." + (
        "pdf" if family == "manual" else "mp4"
    )
    directory, filename = path.rsplit("/", 1)
    await fs_resource_handler.write_file(b"prior good bytes", directory, filename)
    field = (
        {"path_manual": path}
        if family == "manual"
        else {"ss_metadata": {"video_path": path}}
    )
    db_rom_handler.update_rom(rom.id, field)
    before = resource_snapshot(rom)
    _, parts = gzip_parts(fault)
    async with encoded_response(
        parts, mime="application/pdf" if family == "manual" else "video/mp4"
    ):
        if scan:
            with bind_scan_write_context(context(attempt)):
                with ScanMediaBatch(
                    rom.id, rom.platform_id, fs_resource_handler.storage
                ) as unit:
                    with pytest.raises(ValueError):
                        generated = await store_resource(
                            fs_resource_handler,
                            "https://fixture.invalid/media",
                            path,
                            ("application/pdf", "video/"),
                        )

                        def associate(session):
                            values = (
                                {"path_manual": generated}
                                if family == "manual"
                                else {"ss_metadata": {"video_path": generated}}
                            )
                            db_rom_handler.update_rom(rom.id, values, session=session)

                        unit.publish_and_associate(associate)
            assert all(output.digest is None for output in unit.outputs)
        else:
            result = await store_resource(
                fs_resource_handler,
                "https://fixture.invalid/media",
                path,
                ("application/pdf", "video/"),
            )
            assert result is None
    saved = db_rom_handler.get_rom(rom.id)
    assert (
        saved.path_manual if family == "manual" else saved.ss_metadata["video_path"]
    ) == path
    assert resource_snapshot(rom) == before
    with sync_session.begin() as session:
        assert session.scalar(select(OwnedMediaCleanupIntent.id)) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode", ["plain", "gzip", "concatenated", "empty", "split_header"]
)
async def test_complete_encoding_streams_exact_bytes(attempt, rom, mode):
    payload, parts = gzip_parts("valid")
    encoding = "gzip"
    if mode == "plain":
        parts, encoding = [payload], "identity"
    elif mode == "concatenated":
        parts = [gzip.compress(payload[:1000]), gzip.compress(payload[1000:])]
    elif mode == "empty":
        payload, parts = b"", [gzip.compress(b"")]
    elif mode == "split_header":
        wire = b"".join(parts)
        parts = [wire[:1], wire[1:7], wire[7:]]
    with bind_scan_write_context(context(attempt)):
        with ScanMediaBatch(
            rom.id, rom.platform_id, fs_resource_handler.storage
        ) as unit:
            async with encoded_response(parts, encoding=encoding):
                generated = await store_resource(
                    fs_resource_handler,
                    "https://fixture.invalid/manual",
                    f"{rom.fs_resources_path}/manual/{rom.id}.pdf",
                    ("application/pdf",),
                )
            unit.publish_and_associate(
                lambda session: db_rom_handler.update_rom(
                    rom.id, {"path_manual": generated}, session=session
                )
            )
    saved = db_rom_handler.get_rom(rom.id)
    assert saved.path_manual == generated
    assert fs_resource_handler.validate_path(generated).read_bytes() == payload


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["truncated", "checksum", "later_corruption"])
async def test_actual_special_scanner_rejects_corrupt_gzip(
    attempt, rom, platform, command, monkeypatch, fault
):
    from tests.handler.test_media_download_transport import configure_scanner, fs_input

    from endpoints.sockets import scan as scan_module
    from handler import scan_handler
    from handler.filesystem import fs_rom_handler, use_fs_rom_handler

    mapping, current = await configure_scanner(
        rom, platform, command, monkeypatch, "special"
    )
    before = resource_snapshot(rom)
    _, parts = gzip_parts(fault)
    async with encoded_response(parts, mime="video/mp4"):
        with use_fs_rom_handler(
            fs_rom_handler.for_mapping(mapping)
        ), bind_scan_write_context(context(attempt)):
            await scan_module._identify_rom(
                mapping.platform,
                fs_input(),
                current,
                scan_handler.ScanType.COMPLETE,
                [],
                ["ss"],
                False,
                False,
                AsyncMock(),
                scan_module.ScanStats(),
            )
    saved = db_rom_handler.get_rom(rom.id)
    assert saved.ss_metadata["video_path"] == current.ss_metadata["video_path"]
    assert resource_snapshot(rom) == before


@pytest.mark.asyncio
async def test_large_decoded_video_uses_bounded_writes(attempt, rom):
    from handler.filesystem.scan_media_publication import PreparedScanMedia

    # A spy on the real capability file observes writes without replacing authority.
    count, maximum, digest = 0, 0, hashlib.sha256()
    original = PreparedScanMedia.file.fget

    class Writer:
        def __init__(self, file):
            self.file = file

        def __getattr__(self, name):
            return getattr(self.file, name)

        def write(self, chunk):
            nonlocal count, maximum
            count += len(chunk)
            maximum = max(maximum, len(chunk))
            digest.update(chunk)
            return self.file.write(chunk)

    from unittest.mock import patch

    payload = b"bounded-output" * (4 * 1024 * 1024)
    parts = [gzip.compress(payload)]
    with patch.object(
        PreparedScanMedia, "file", property(lambda output: Writer(original(output)))
    ):
        with bind_scan_write_context(context(attempt)):
            with ScanMediaBatch(
                rom.id, rom.platform_id, fs_resource_handler.storage
            ) as unit:
                async with encoded_response(parts, mime="video/mp4"):
                    generated = await store_resource(
                        fs_resource_handler,
                        "https://fixture.invalid/video",
                        f"{rom.fs_resources_path}/video/fixture.mp4",
                        ("video/",),
                    )
                unit.publish_and_associate(
                    lambda session: db_rom_handler.update_rom(
                        rom.id,
                        {"ss_metadata": {"video_path": generated}},
                        session=session,
                    )
                )
    assert count == len(payload)
    assert maximum <= 1024 * 1024
    assert digest.hexdigest() == hashlib.sha256(payload).hexdigest()
