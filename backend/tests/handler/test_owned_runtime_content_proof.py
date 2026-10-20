"""Production read-only verification rejects changed bytes and bounds blocked reads."""

import hashlib
import os
import subprocess
import time
from pathlib import Path

import pytest

from handler.filesystem import owned_content_proof as runtime
from handler.filesystem.owned_content_proof import (
    OwnedContentProof,
    OwnedContentProofRejected,
    owned_verifier_idle,
)


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


@pytest.mark.parametrize("changed", [False, True])
def test_runtime_verifier_uses_original_digest_even_with_current_metadata(
    tmp_path, changed
):
    path = tmp_path / "owned.bin"
    original = b"original bytes"
    path.write_bytes(original)
    if changed:
        path.write_bytes(b"modified bytes")
    descriptor = os.open(path, os.O_RDONLY)
    try:
        with OwnedContentProof(operation="operation", attempt="attempt") as proof:

            def call():
                return proof.verify(
                    descriptor,
                    hashlib.sha256(original).hexdigest(),
                    len(original),
                    identity(os.fstat(descriptor)),
                )

            if changed:
                with pytest.raises(OwnedContentProofRejected):
                    call()
            else:
                call()
                assert proof.ordinal == 1
    finally:
        os.close(descriptor)
    assert owned_verifier_idle()


def test_blocked_content_read_returns_and_retains_admission_until_actual_exit(
    tmp_path, monkeypatch
):
    original_popen = subprocess.Popen
    source = Path(runtime.__file__).with_name("owned_content_child.py").read_text()
    source = source.replace(
        'if __name__ == "__main__":',
        "def blocked_read(*args):\n"
        "    read_fd, write_fd = os.pipe()\n"
        "    return os.read(read_fd, 1)\n"
        "os.pread = blocked_read\n\n"
        'if __name__ == "__main__":',
    )
    child_script = tmp_path / "blocked_child.py"
    child_script.write_text(source)
    children = []

    def launch(arguments, **kwargs):
        arguments = list(arguments)
        source_index = arguments.index(
            str(Path(runtime.__file__).with_name("owned_content_child.py"))
        )
        arguments[source_index] = str(child_script)
        child = original_popen(arguments, **kwargs)
        children.append(child)
        # A delayed termination must not release cross-process admission.
        monkeypatch.setattr(child, "kill", lambda: None)
        return child

    monkeypatch.setattr(runtime.subprocess, "Popen", launch)
    path = tmp_path / "owned.bin"
    path.write_bytes(b"owned bytes")
    descriptor = os.open(path, os.O_RDONLY)
    try:
        with OwnedContentProof(seconds=0.15) as proof:
            started = time.monotonic()
            with pytest.raises(OwnedContentProofRejected, match="timed out"):
                proof.verify(
                    descriptor,
                    hashlib.sha256(b"owned bytes").hexdigest(),
                    11,
                    identity(os.fstat(descriptor)),
                )
            assert time.monotonic() - started < 1
        assert not owned_verifier_idle()
        with pytest.raises(OwnedContentProofRejected, match="unavailable"):
            with OwnedContentProof():
                pass
        assert len(children) == 1
    finally:
        os.close(descriptor)
        for child in children:
            os.kill(child.pid, 9)
            child.wait(timeout=2)
    assert owned_verifier_idle()


def test_runtime_rejects_mismatched_nonce_before_authorizing_mutation(
    tmp_path, monkeypatch
):
    path = tmp_path / "owned.bin"
    path.write_bytes(b"owned bytes")
    descriptor = os.open(path, os.O_RDONLY)
    try:
        with OwnedContentProof() as proof:
            monkeypatch.setattr(proof, "_receive", lambda: {"nonce": "foreign"})
            with pytest.raises(OwnedContentProofRejected, match="rejected"):
                proof.verify(
                    descriptor,
                    hashlib.sha256(b"owned bytes").hexdigest(),
                    11,
                    identity(os.fstat(descriptor)),
                )
    finally:
        os.close(descriptor)
    assert owned_verifier_idle()


@pytest.mark.asyncio
async def test_other_async_task_cannot_reenter_explicit_writer_domain():
    import asyncio

    from exceptions.storage_exceptions import StorageResolutionError
    from handler.filesystem.owned_writer_domain import owned_writer_domain

    entered, release = asyncio.Event(), asyncio.Event()

    async def holder():
        with owned_writer_domain():
            entered.set()
            await release.wait()

    task = asyncio.create_task(holder())
    await entered.wait()
    try:
        with pytest.raises(StorageResolutionError, match="busy"):
            with owned_writer_domain():
                pytest.fail("another async task entered the same writer reservation")
    finally:
        release.set()
        await task


def test_same_sync_actor_can_nest_owned_writer_domain():
    from handler.filesystem.owned_writer_domain import owned_writer_domain

    with owned_writer_domain():
        with owned_writer_domain():
            pass


@pytest.mark.asyncio
async def test_same_async_actor_can_nest_owned_writer_domain():
    from handler.filesystem.owned_writer_domain import owned_writer_domain

    with owned_writer_domain():
        with owned_writer_domain():
            pass


def test_exec_read_verifier_does_not_inherit_application_authority(monkeypatch):
    monkeypatch.setenv("PGDP_TEST_PARENT_AUTHORITY", "synthetic-parent-only")
    with OwnedContentProof() as proof:
        assert proof.child is not None
        content = Path(f"/proc/{proof.child.pid}/environ").read_bytes()
        keys = {entry.split(b"=", 1)[0] for entry in content.split(b"\0") if entry}
        leaked = keys & {
            b"DB_PASSWD",
            b"DB_USER",
            b"REDIS_PASSWORD",
            b"ROMM_AUTH_SECRET_KEY",
            b"PGDP_TEST_PARENT_AUTHORITY",
        }
        assert not leaked, "read-only child inherited application authority"
