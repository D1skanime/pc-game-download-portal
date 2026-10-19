"""Independent SQL/process, real RQ and first-game integration boundaries."""

import json
import subprocess
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from rq import Queue
from rq.job import Job
from sqlalchemy import func, select
from tests.handler.test_scan_operations import command as command_fixture
from tests.handler.test_scan_operations import running  # noqa: F401

from handler.database.base_handler import sync_session
from handler.database.scan_operations_handler import DBScanOperationsHandler, utc_now
from handler.redis_handler import redis_client
from models.platform import Platform
from models.rom import Rom
from models.scan_operation import ScanOperation
from tasks.scan_operation_dispatch import WORKER_FUNC, dispatch_operation

command = command_fixture

PREFIX = """
from tools.phase34_target_guard import validate_target
validate_target()
import startup
from handler.database.scan_operations_handler import DBScanOperationsHandler
repository=DBScanOperationsHandler()
"""


def child(source, payload, *, timeout=35):
    process = subprocess.Popen(
        [sys.executable, "-c", PREFIX + source],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        close_fds=True,
    )
    try:
        stdout, stderr = process.communicate(json.dumps(payload), timeout=timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=3)
        pytest.fail("bounded child scenario deadline")
    assert process.returncode == 0, (stdout + stderr)[-3000:]
    return stdout


@pytest.fixture
def real_queue():
    queue = Queue("phase34-integration-" + uuid4().hex, connection=redis_client)
    yield queue
    queue.delete(delete_jobs=True)


def count_roms():
    with sync_session() as session:
        return session.scalar(select(func.count()).select_from(Rom))


def test_committed_acceptance_visible_before_enqueue(admin_user, command):
    repository = DBScanOperationsHandler()
    accepted = repository.accept(admin_user.id, "process-acceptance", command)
    stdout = child(
        """
import json,sys
row=repository.execution(json.load(sys.stdin)["id"])
assert row["state"]=="accepted"
assert row["dispatch_due"] is not None
assert row["attempt_id"] is None
print("committed-before-queue")
""",
        {"id": accepted.id},
    )
    assert "committed-before-queue" in stdout


def test_real_rq_replay_has_one_job(admin_user, command, real_queue):
    repository = DBScanOperationsHandler()
    accepted = repository.accept(admin_user.id, "rq-replay", command)
    assert dispatch_operation(accepted.id, repository=repository, queue=real_queue)
    assert not dispatch_operation(accepted.id, repository=repository, queue=real_queue)
    assert real_queue.job_ids == [accepted.job_id]
    job = Job.fetch(accepted.job_id, connection=redis_client)
    assert job.func_name == WORKER_FUNC
    assert job.kwargs == {"operation_id": accepted.id}
    assert repository.execution(accepted.id)["state"] == "queued"


def test_dispatch_exit_after_enqueue_recovers_without_duplicate(
    admin_user, command, real_queue
):
    repository = DBScanOperationsHandler()
    accepted = repository.accept(admin_user.id, "enqueue-crash", command)
    child(
        """
import json,sys
from rq import Queue
from handler.redis_handler import redis_client
from tasks.scan_operation_dispatch import WORKER_FUNC
payload=json.load(sys.stdin)
row=repository.execution(payload["id"])
claim=repository.claim_dispatch(row["id"],row["version"],"test-dispatcher")
Queue(payload["queue"],connection=redis_client).enqueue(
 WORKER_FUNC,operation_id=row["id"],job_id=claim.job_id)
print("enqueued-without-ack")
""",
        {"id": accepted.id, "queue": real_queue.name},
    )
    with sync_session.begin() as session:
        session.get(ScanOperation, accepted.id).dispatch_claim_until = (
            utc_now() - timedelta(seconds=1)
        )
    assert dispatch_operation(accepted.id, repository=repository, queue=real_queue)
    assert real_queue.job_ids == [accepted.job_id]
    assert repository.execution(accepted.id)["state"] == "queued"


def test_cancel_before_worker_never_indexes(admin_user, command, real_queue):
    repository = DBScanOperationsHandler()
    accepted = repository.accept(admin_user.id, "cancel-before-worker", command)
    assert dispatch_operation(accepted.id, repository=repository, queue=real_queue)
    current = repository.get_by_id(accepted.id, admin_user.id)
    cancelled = repository.request_cancel(
        current.id, admin_user.id, current.version, "cancel-test"
    )
    assert cancelled.intentional_cancel
    before = count_roms()
    child(
        """
import asyncio,json,sys
from handler.scan_operation_worker import run_scan_operation
asyncio.run(run_scan_operation(json.load(sys.stdin)["id"]))
""",
        {"id": accepted.id},
    )
    assert count_roms() == before


def test_revoked_process_cannot_commit_catalog(admin_user, command, platform):
    repository = DBScanOperationsHandler()
    attempt = running(repository, admin_user, command)
    original = platform.name
    with tempfile.TemporaryDirectory(
        prefix="p34-barrier-", dir="/phase34/owned"
    ) as temp:
        barrier = Path(temp)
        script = PREFIX + """
import json,sys,time
from pathlib import Path
from handler.database.scan_write_fence import (
 ScanWriteContext,ScanWriteRejected,bind_scan_write_context)
from decorators.database import begin_session
from models.platform import Platform
payload=json.load(sys.stdin)
base=Path(payload["barrier"])
(base/"ready").write_text("ready")
deadline=time.monotonic()+10
while not (base/"release").exists():
 if time.monotonic()>=deadline: raise RuntimeError("barrier deadline")
 time.sleep(0.01)
@begin_session
def mutate(*,session=None):
 session.get(Platform,payload["platform"]).name="stale-child-write"
context=ScanWriteContext(payload["id"],payload["attempt"],"worker")
try:
 with bind_scan_write_context(context): mutate()
except ScanWriteRejected:
 (base/"rejected").write_text("rejected")
else:
 raise AssertionError("revoked process committed")
"""
        process = subprocess.Popen(
            [sys.executable, "-c", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            close_fds=True,
        )
        assert process.stdin is not None
        process.stdin.write(
            json.dumps(
                {
                    "barrier": str(barrier),
                    "platform": platform.id,
                    "id": attempt.id,
                    "attempt": attempt.attempt_id,
                }
            )
        )
        process.stdin.close()
        process.stdin = None
        try:
            deadline = time.monotonic() + 10
            while not (barrier / "ready").exists():
                assert time.monotonic() < deadline and process.poll() is None
                time.sleep(0.01)
            current = repository.get_by_id(attempt.id, admin_user.id)
            repository.request_cancel(
                current.id, admin_user.id, current.version, "revoke-process"
            )
            (barrier / "release").write_text("release")
            stdout, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, (stdout + stderr)[-3000:]
            assert (barrier / "rejected").exists()
        finally:
            (barrier / "release").touch()
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=3)
    with sync_session() as session:
        assert session.get(Platform, platform.id).name == original


@pytest.mark.parametrize("media_only", [False, True])
def test_real_rq_worker_indexes_first_generated_game(
    admin_user, command, real_queue, media_only, request
):
    if media_only:
        request.getfixturevalue("rom")
    repository = DBScanOperationsHandler()
    normalized = {
        **command,
        "request": {
            "apis": [],
            "type": "quick",
            "roms_ids": [],
            "metadata_only": False,
            "media_only": media_only,
            "launchbox_remote_enabled": False,
            "playmatch_enabled": False,
        },
    }
    accepted = repository.accept(admin_user.id, "first-real-game", normalized)
    assert dispatch_operation(accepted.id, repository=repository, queue=real_queue)
    child(
        """
import json,sys
from rq import Queue,Worker
from handler.redis_handler import redis_client
from adapters.services.igdb import IGDBService
from adapters.services.libretro_thumbnails import LibretroThumbnailsService
from handler.metadata import igdb_handler, meta_igdb_handler
meta_igdb_handler.get_platform=lambda slug:{"slug":slug,"igdb_id":4,"name":"Synthetic platform"}
async def external_metadata_forbidden(*args,**kwargs):
 raise AssertionError("empty_apis_must_not_fetch_external_metadata")
IGDBService._request=external_metadata_forbidden
igdb_handler.TwitchAuth._update_twitch_token=external_metadata_forbidden
LibretroThumbnailsService.fetch_listing=external_metadata_forbidden
igdb_handler.IGDB_CLIENT_ID="synthetic-configured-provider"
igdb_handler.IGDB_CLIENT_SECRET="synthetic-configured-provider"
payload=json.load(sys.stdin)
queue=Queue(payload["queue"],connection=redis_client)
Worker([queue],connection=redis_client,name=payload["worker"]).work(
 burst=True,max_jobs=1,logging_level="WARNING")
""",
        {"queue": real_queue.name, "worker": "phase34-worker-" + uuid4().hex},
        timeout=50,
    )
    current = repository.get_by_id(accepted.id, admin_user.id)
    assert current.state in {"completed", "completed-with-warnings"}, current
    assert count_roms() >= 1
    assert current.scan_stats.get("scanned_roms", 0) >= 1


def test_real_streaming_capabilities_expose_only_committed_bytes(
    admin_user, command, rom
):
    import asyncio
    import os

    import httpx

    from handler.database.scan_write_fence import (
        ScanWriteContext,
        bind_scan_write_context,
    )
    from handler.filesystem import fs_resource_handler
    from handler.filesystem.resource_download import store_resource
    from handler.filesystem.scan_media_publication import ScanMediaBatch
    from handler.filesystem.storage_access import OwnedReplace, open_owned_access
    from handler.filesystem.storage_policy import StorageOperation
    from utils.context import ctx_httpx_client

    repository = DBScanOperationsHandler()
    attempt = running(repository, admin_user, command)
    evidence = Path("/phase34/evidence")
    external_barrier = os.environ.get("PHASE34_HTTP_BARRIER") == "1"

    async def scenario():
        arrived = set()
        release = asyncio.Event()

        class ProviderBody(httpx.AsyncByteStream):
            def __init__(self, family):
                self.family = family

            async def __aiter__(self):
                yield b"private-sentinel-partial"
                arrived.add(self.family)
                await asyncio.wait_for(release.wait(), timeout=150)
                yield b"-complete"

        def respond(request):
            return httpx.Response(
                200,
                headers={"content-type": "image/png"},
                stream=ProviderBody(request.url.path),
            )

        context = ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
        positives = [
            f"{rom.fs_resources_path}/cover/committed.png",
            f"{rom.fs_resources_path}/manual/guide.pdf",
            f"{rom.fs_resources_path}/manual/readme.md",
        ]
        for path in positives:
            directory, filename = path.rsplit("/", 1)
            await fs_resource_handler.write_file(
                b"complete-public-sentinel", directory, filename
            )

        with bind_scan_write_context(context):
            with ScanMediaBatch(
                rom.id, rom.platform_id, fs_resource_handler.storage
            ) as unit:
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(respond)
                ) as client:
                    token = ctx_httpx_client.set(client)
                    tasks = []
                    stable = []
                    try:
                        for family in (
                            "cover",
                            "screenshots",
                            "dlc",
                            "soundtrack",
                            "manual",
                        ):
                            path = f"{rom.fs_resources_path}/{family}/stream.png"
                            tasks.append(
                                asyncio.create_task(
                                    store_resource(
                                        fs_resource_handler,
                                        "https://provider.example.test/" + family,
                                        path,
                                        ["image/png"],
                                    )
                                )
                            )
                        deadline = time.monotonic() + 15
                        while len(arrived) < 5:
                            assert time.monotonic() < deadline
                            for task in tasks:
                                if task.done():
                                    task.result()
                            await asyncio.sleep(0.01)
                        private = [
                            ".scan-media-staging",
                            unit.manifest_directory + "/receipt-0000.json",
                            *[output.private_path for output in unit.outputs],
                        ]
                        for family, extension in (
                            ("ra-cache", "json"),
                            ("gamelist", "xml"),
                            ("pegasus", "txt"),
                        ):
                            path = f"{rom.fs_resources_path}/{family}.{extension}"
                            with open_owned_access(
                                fs_resource_handler.storage,
                                StorageOperation.OVERWRITE,
                                path,
                            ) as access:
                                assert isinstance(access, OwnedReplace)
                                prepared = access.prepare_binary_file()
                            prepared.file.write(b"private-sentinel-stable")
                            prepared.seal()
                            stable.append(prepared)
                            private.append(
                                path.rpartition("/")[0]
                                + "/"
                                + prepared.private_basename
                            )
                        assert len(unit.outputs) == 5
                        for path in private:
                            assert fs_resource_handler.validate_path(path).exists()
                        if external_barrier:
                            (evidence / "http-files.json").write_text(
                                json.dumps(
                                    {
                                        "private": private,
                                        "positive": positives,
                                        "operation": attempt.id,
                                        "attempt": attempt.attempt_id,
                                        "worker_pid": os.getpid(),
                                        "manifest": unit.manifest_directory,
                                        "provider_streams": 5,
                                    }
                                )
                            )
                            (evidence / "http-stream-ready").write_text("ready")
                            while not (evidence / "http-stream-release").exists():
                                assert time.monotonic() < deadline + 130
                                await asyncio.sleep(0.02)
                        release.set()
                        paths = await asyncio.gather(*tasks)
                        assert len(paths) == 5
                        assert all(output.digest for output in unit.outputs)
                    finally:
                        release.set()
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
                        for prepared in stable:
                            prepared.abort()
                        ctx_httpx_client.reset(token)

    asyncio.run(scenario())


def test_real_worker_fatal_rom_error_cannot_report_completed(
    admin_user, command, real_queue
):
    repository = DBScanOperationsHandler()
    normalized = {
        **command,
        "request": {
            "apis": [],
            "type": "quick",
            "roms_ids": [],
            "launchbox_remote_enabled": False,
            "playmatch_enabled": False,
        },
    }
    accepted = repository.accept(admin_user.id, "fatal-real-game", normalized)
    assert dispatch_operation(accepted.id, repository=repository, queue=real_queue)
    child(
        """
import json,sys
from rq import Queue,Worker
from handler.redis_handler import redis_client
from endpoints.sockets import scan
async def fatal_rom(*args,**kwargs):
 raise RuntimeError("synthetic_fatal_catalog_error")
scan._identify_rom=fatal_rom
payload=json.load(sys.stdin)
Worker([Queue(payload["queue"],connection=redis_client)],connection=redis_client,
 name=payload["worker"]).work(burst=True,max_jobs=1,logging_level="WARNING")
""",
        {"queue": real_queue.name, "worker": "phase34-fatal-" + uuid4().hex},
        timeout=50,
    )
    current = repository.get_by_id(accepted.id, admin_user.id)
    assert current.state == "failed"
    assert current.cause_code == "worker_failed"


def test_real_worker_indexes_readable_game_despite_provider_timeout(
    admin_user, command, real_queue
):
    repository = DBScanOperationsHandler()
    normalized = {
        **command,
        "request": {
            "apis": ["igdb"],
            "type": "quick",
            "roms_ids": [],
            "launchbox_remote_enabled": False,
            "playmatch_enabled": False,
        },
    }
    accepted = repository.accept(admin_user.id, "provider-real-game", normalized)
    assert dispatch_operation(accepted.id, repository=repository, queue=real_queue)
    child(
        """
import json,sys
import httpx
from rq import Queue,Worker
from handler.redis_handler import redis_client
from handler.metadata import meta_igdb_handler
meta_igdb_handler.get_platform=lambda slug:{"slug":slug,"igdb_id":4,"name":"Synthetic platform"}
async def provider_timeout(*args,**kwargs):
 raise httpx.ReadTimeout("synthetic_provider_timeout")
meta_igdb_handler.get_rom=provider_timeout
meta_igdb_handler.get_rom_by_id=provider_timeout
payload=json.load(sys.stdin)
Worker([Queue(payload["queue"],connection=redis_client)],connection=redis_client,
 name=payload["worker"]).work(burst=True,max_jobs=1,logging_level="WARNING")
""",
        {"queue": real_queue.name, "worker": "phase34-provider-" + uuid4().hex},
        timeout=50,
    )
    current = repository.get_by_id(accepted.id, admin_user.id)
    assert current.state == "completed-with-warnings", current
    assert count_roms() >= 1
    assert current.scan_stats["scanned_roms"] >= 1
    assert any(
        item.provider == "igdb"
        and item.outcome == "warning"
        and item.cause_code == "metadata_timeout"
        for item in current.items
    )
