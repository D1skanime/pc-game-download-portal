"""Independent publisher and canceller processes exercise stable owned output boundaries."""

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
from tests.handler.test_scan_operations import command as command
from tests.handler.test_scan_operations import running

from handler.database.scan_operations_handler import DBScanOperationsHandler
from handler.filesystem import fs_resource_handler
from handler.filesystem.owned_content_proof import owned_verifier_idle
from handler.filesystem.scan_media_publication import ensure_directory
from handler.filesystem.storage_access import OwnedReplace, open_owned_access
from handler.filesystem.storage_policy import StorageOperation

FAMILIES = ("ra", "gamelist", "pegasus")
PREFIX = """
from tools.phase34_target_guard import validate_target
validate_target()
import startup
import json,sys,time
from pathlib import Path
payload=json.load(sys.stdin)
base=Path(payload["barrier"])
def wait_release():
 deadline=time.monotonic()+12
 while not (base/"release").exists():
  if time.monotonic()>=deadline: raise RuntimeError("output barrier deadline")
  time.sleep(0.01)
"""

PUBLISHER = PREFIX + """
import hashlib
from handler.database.scan_write_fence import ScanWriteContext,ScanWriteRejected,bind_scan_write_context
from handler.filesystem import fs_resource_handler
from handler.filesystem.owned_publication import PreparedOwnedReplace
from handler.filesystem import owned_publication
from handler.filesystem.scan_output_publication import publish_scan_output
from utils.gamelist_exporter import GamelistExporter
from utils.pegasus_exporter import PegasusExporter
family,platform=payload["family"],payload["platform"]
if family=="ra":
 relative=f"roms/{platform}/ra_hashes_v2.json"
 content=json.dumps({"0123456789abcdef0123456789abcdef":7},indent=4).encode()
elif family=="gamelist":
 relative=f"gamelist_{platform}.xml"
 content=GamelistExporter(local_export=True).export_platform_to_xml(platform,None).encode()
else:
 relative=f"metadata_pegasus_{platform}.txt"
 content=PegasusExporter(local_export=True).export_platform_to_pegasus(platform,None).encode()
mode=payload["mode"]
seal=PreparedOwnedReplace.seal
publish=PreparedOwnedReplace.publish
replace=owned_publication.os.replace
def ready(capability):
 private=str(Path(relative).parent/capability.private_basename)
 (base/"ready").write_text(json.dumps({"private":private,
  "sha256":hashlib.sha256(content).hexdigest(),"size":len(content)}))
def sealed(capability):
 result=seal(capability)
 if mode=="prepared":
  ready(capability)
  wait_release()
 return result
def publishing(capability,**kwargs):
 if mode in {"locked","before_replace"}:
  ready(capability)
  wait_release()
 return publish(capability,**kwargs)
def replaced(source,destination,**kwargs):
 result=replace(source,destination,**kwargs)
 if mode=="after_replace":
  (base/"ready").write_text(json.dumps({"replaced":True}))
  wait_release()
 return result
PreparedOwnedReplace.seal=sealed
PreparedOwnedReplace.publish=publishing
owned_publication.os.replace=replaced
context=ScanWriteContext(payload["operation"],payload["attempt"],"worker")
try:
 with bind_scan_write_context(context):
  publish_scan_output(fs_resource_handler.storage,relative,content)
except ScanWriteRejected:
 (base/"rejected").write_text("rejected")
else:
 (base/"published").write_text("published")
"""

CANCELLER = PREFIX + """
from handler.database.scan_operations_handler import DBScanOperationsHandler
repository=DBScanOperationsHandler()
row=repository.get_by_id(payload["operation"],payload["actor"])
(base/"cancel_attempted").write_text("attempted")
repository.request_cancel(row.id,payload["actor"],row.version,"stable-output-cancel")
(base/"cancelled").write_text("acknowledged")
"""


def serialize_output(family, platform_id):
    if family == "ra":
        return (
            f"roms/{platform_id}/ra_hashes_v2.json",
            json.dumps({"0123456789abcdef0123456789abcdef": 7}, indent=4).encode(),
        )
    if family == "gamelist":
        from utils.gamelist_exporter import GamelistExporter

        return (
            f"gamelist_{platform_id}.xml",
            GamelistExporter(local_export=True)
            .export_platform_to_xml(platform_id, None)
            .encode(),
        )
    from utils.pegasus_exporter import PegasusExporter

    return (
        f"metadata_pegasus_{platform_id}.txt",
        PegasusExporter(local_export=True)
        .export_platform_to_pegasus(platform_id, None)
        .encode(),
    )


def spawn(source, payload):
    process = subprocess.Popen(  # nosec B603, fixed test-owned child source
        [sys.executable, "-c", source],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        close_fds=True,
    )
    assert process.stdin is not None
    process.stdin.write(json.dumps(payload))
    process.stdin.close()
    process.stdin = None
    return process


def wait_file(path, process, *, seconds=12):
    deadline = time.monotonic() + seconds
    while not path.exists():
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=2)
            pytest.fail((stdout + stderr)[-3000:])
        assert time.monotonic() < deadline, "independent output barrier deadline"
        time.sleep(0.01)


def finish(process):
    try:
        stdout, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=3)
        pytest.fail("independent output child did not finish")
    assert process.returncode == 0, (stdout + stderr)[-3000:]


def cleanup(processes, barrier, relative):
    (barrier / "release").touch()
    for process in processes:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=3)
    deadline = time.monotonic() + 3
    while not owned_verifier_idle():
        assert time.monotonic() < deadline, "read-only helper has not exited"
        time.sleep(0.01)
    final = fs_resource_handler.validate_path(relative)
    for path in final.parent.glob(f".{final.name}.*.tmp"):
        path.unlink()
    final.unlink(missing_ok=True)


def record_proof(family, order, expected, observed, serialized):
    path = Path("/phase34/evidence/stable-output-faults.json")
    receipt = (
        json.loads(path.read_text()) if path.exists() else {"schema": 1, "proofs": []}
    )
    proofs = receipt["proofs"]
    assert isinstance(proofs, list)
    proofs.append(
        dict(
            family=family,
            order=order,
            passed=True,
            expected_sha256=hashlib.sha256(expected).hexdigest(),
            observed_sha256=hashlib.sha256(observed).hexdigest(),
            serialized_sha256=hashlib.sha256(serialized).hexdigest(),
            verifier_exit_confirmed=owned_verifier_idle(),
        )
    )
    assert proofs[-1]["verifier_exit_confirmed"]
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2))


def seed_prior(relative):
    parent = relative.rpartition("/")[0]
    if parent:
        ensure_directory(fs_resource_handler.storage, parent)
    with open_owned_access(
        fs_resource_handler.storage, StorageOperation.OVERWRITE, relative
    ) as access:
        assert isinstance(access, OwnedReplace)
        access.replace(b"prior complete stable bytes")


def payload_for(attempt, actor, platform, family, barrier, mode):
    return dict(
        operation=attempt.id,
        attempt=attempt.attempt_id,
        actor=actor.id,
        platform=platform.id,
        family=family,
        barrier=str(barrier),
        mode=mode,
    )


@pytest.mark.parametrize("family", FAMILIES)
def test_stable_prepared_output_rejects_independent_cancel(
    admin_user, command, platform, family
):
    attempt = running(DBScanOperationsHandler(), admin_user, command)
    relative, expected = serialize_output(family, platform.id)
    seed_prior(relative)
    with tempfile.TemporaryDirectory(
        prefix="p34-stable-", dir="/phase34/owned"
    ) as temp:
        barrier = Path(temp)
        payload = payload_for(
            attempt, admin_user, platform, family, barrier, "prepared"
        )
        processes = []
        try:
            publisher = spawn(PUBLISHER, payload)
            processes.append(publisher)
            wait_file(barrier / "ready", publisher)
            record = json.loads((barrier / "ready").read_text())
            private = fs_resource_handler.validate_path(record["private"])
            assert private.read_bytes() == expected
            canceller = spawn(CANCELLER, payload)
            processes.append(canceller)
            finish(canceller)
            assert (barrier / "cancelled").exists()
            (barrier / "release").touch()
            finish(publisher)
            assert (barrier / "rejected").exists()
            assert not (barrier / "published").exists()
            assert (
                fs_resource_handler.validate_path(relative).read_bytes()
                == b"prior complete stable bytes"
            )
            observed = fs_resource_handler.validate_path(relative).read_bytes()
        finally:
            cleanup(processes, barrier, relative)
        record_proof(
            family,
            "stale_after_cancel",
            b"prior complete stable bytes",
            observed,
            expected,
        )


@pytest.mark.parametrize("family", FAMILIES)
def test_stable_output_lock_publishes_before_independent_cancel_ack(
    admin_user, command, platform, family
):
    attempt = running(DBScanOperationsHandler(), admin_user, command)
    relative, expected = serialize_output(family, platform.id)
    seed_prior(relative)
    with tempfile.TemporaryDirectory(
        prefix="p34-stable-", dir="/phase34/owned"
    ) as temp:
        barrier = Path(temp)
        payload = payload_for(attempt, admin_user, platform, family, barrier, "locked")
        processes = []
        try:
            publisher = spawn(PUBLISHER, payload)
            processes.append(publisher)
            wait_file(barrier / "ready", publisher)
            canceller = spawn(CANCELLER, payload)
            processes.append(canceller)
            wait_file(barrier / "cancel_attempted", canceller)
            time.sleep(0.1)
            assert canceller.poll() is None
            assert not (barrier / "cancelled").exists()
            (barrier / "release").touch()
            finish(publisher)
            finish(canceller)
            assert (barrier / "published").exists()
            assert (barrier / "cancelled").exists()
            assert fs_resource_handler.validate_path(relative).read_bytes() == expected
            observed = fs_resource_handler.validate_path(relative).read_bytes()
        finally:
            cleanup(processes, barrier, relative)
        record_proof(family, "fence_before_cancel_ack", expected, observed, expected)


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("mode", ["before_replace", "after_replace"])
def test_stable_output_process_crash_keeps_complete_old_or_new(
    admin_user, command, platform, family, mode
):
    attempt = running(DBScanOperationsHandler(), admin_user, command)
    relative, expected = serialize_output(family, platform.id)
    seed_prior(relative)
    with tempfile.TemporaryDirectory(
        prefix="p34-stable-", dir="/phase34/owned"
    ) as temp:
        barrier = Path(temp)
        payload = payload_for(attempt, admin_user, platform, family, barrier, mode)
        processes = []
        try:
            publisher = spawn(PUBLISHER, payload)
            processes.append(publisher)
            wait_file(barrier / "ready", publisher)
            publisher.kill()
            publisher.communicate(timeout=3)
            assert publisher.returncode == -9
            actual = fs_resource_handler.validate_path(relative).read_bytes()
            assert actual == (
                expected if mode == "after_replace" else b"prior complete stable bytes"
            )
            assert not (barrier / "published").exists()
        finally:
            cleanup(processes, barrier, relative)
        record_proof(
            family,
            "crash_" + mode,
            expected if mode == "after_replace" else b"prior complete stable bytes",
            actual,
            expected,
        )
