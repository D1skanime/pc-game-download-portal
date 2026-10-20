"""Bound verifier-result waiting, independently from OS mutation and SQL latency."""

import array
import fcntl
import json
import math
import os
import secrets
import select
import socket
import subprocess  # nosec B404, exec-only read verifier with fixed argv
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from exceptions.storage_exceptions import StorageResolutionError
from handler.filesystem.owned_writer_domain import lock_descriptor

_ACTIVE = ContextVar("owned_content_proof", default=None)


class OwnedContentProofRejected(StorageResolutionError):
    """Uncertain bytes confer no mutation authority."""


class OwnedContentProof:
    def __init__(self, *, seconds=2, limit=4096, operation="", attempt=""):
        self.seconds, self.limit = seconds, limit
        self.operation, self.attempt = operation, attempt
        self.ordinal = 0
        self.deadline = None
        self.channel = self.child = self.reservation = None
        self.nonce = secrets.token_hex(16)

    def __enter__(self):
        self.reservation = lock_descriptor("verifier")
        try:
            fcntl.flock(self.reservation, fcntl.LOCK_EX | fcntl.LOCK_NB)
            parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            self.channel = parent
            try:
                # Fixed interpreter/script with exact inherited read-only authority.
                self.child = subprocess.Popen(  # nosec B603
                    [
                        sys.executable,
                        "-I",
                        "-S",
                        "-B",
                        str(Path(__file__).with_name("owned_content_child.py")),
                        str(child.fileno()),
                        str(self.reservation),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    env={"LANG": "C.UTF-8"},
                    pass_fds=(child.fileno(), self.reservation),
                )
            finally:
                child.close()
            self.channel.setblocking(False)
            self.deadline = time.monotonic() + self.seconds
            if self._receive() != {"ready": 1}:
                raise OwnedContentProofRejected("Owned verifier readiness rejected")
            self.deadline = None
            return self
        except BaseException as error:
            self.close()
            if isinstance(error, OSError):
                raise OwnedContentProofRejected("Owned verifier unavailable") from error
            raise

    def _remaining(self):
        if self.deadline is None:
            self.deadline = time.monotonic() + self.seconds
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise OwnedContentProofRejected("Owned content verification timed out")
        return remaining

    def _receive(self):
        channel = self.channel
        if channel is None:
            raise OwnedContentProofRejected("Owned verifier is closed")
        if not select.select([channel], [], [], self._remaining())[0]:
            raise OwnedContentProofRejected("Owned content verification timed out")
        frame, _, flags, _ = channel.recvmsg(4096)
        if flags or not frame:
            raise OwnedContentProofRejected("Owned content proof incomplete")
        try:
            result = json.loads(frame)
        except (ValueError, UnicodeError) as error:
            raise OwnedContentProofRejected("Owned content proof malformed") from error
        self._remaining()
        return result

    def verify(self, descriptor, digest, size, identity):
        if self.channel is None or self.ordinal >= self.limit:
            raise OwnedContentProofRejected("Owned content proof exhausted")
        request = dict(
            nonce=self.nonce,
            operation=self.operation,
            attempt=self.attempt,
            ordinal=self.ordinal,
            digest=digest,
            size=size,
            identity=list(identity),
        )
        frame = json.dumps(request, separators=(",", ":")).encode()
        if len(frame) > 4096:
            raise OwnedContentProofRejected("Owned content proof frame")
        try:
            if not select.select([], [self.channel], [], self._remaining())[1]:
                raise OwnedContentProofRejected("Owned content verification timed out")
            sent = self.channel.sendmsg(
                [frame],
                [
                    (
                        socket.SOL_SOCKET,
                        socket.SCM_RIGHTS,
                        array.array("i", [descriptor]),
                    )
                ],
            )
            result = self._receive()
            if (
                sent != len(frame)
                or type(result) is not dict
                or set(result) != set(request)
                or any(
                    type(result[key]) is not type(value)
                    for key, value in request.items()
                )
                or any(type(value) is not int for value in result.get("identity", []))
                or result != request
            ):
                raise OwnedContentProofRejected("Owned content proof rejected")
            self.ordinal += 1
        except (OSError, ValueError) as error:
            self.close()
            raise OwnedContentProofRejected("Owned content proof failed") from error
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.child is not None:
            try:
                self.child.kill()
            except ProcessLookupError:
                pass
            try:
                self.child.wait(timeout=0.05)
            except subprocess.TimeoutExpired:
                pass
            self.child = None
        if self.reservation is not None:
            os.close(self.reservation)
            self.reservation = None

    def __exit__(self, *_args):
        self.close()


@contextmanager
def content_proof_scope(
    *, expected_bytes=0, expected_records=1, operation=None, attempt=None
):
    if _ACTIVE.get() is not None:
        yield _ACTIVE.get()
        return
    if expected_records == 0:
        yield None
        return
    from handler.database.scan_write_fence import current_scan_write_context

    context = current_scan_write_context()
    operation = (
        operation if operation is not None else context.operation_id if context else ""
    )
    attempt = attempt if attempt is not None else context.attempt_id if context else ""
    try:
        fixed = float(os.environ.get("SCAN_MEDIA_PROOF_FIXED_SECONDS", "2"))
        throughput = float(
            os.environ.get("SCAN_MEDIA_PROOF_BYTES_PER_SECOND", str(16 * 1024 * 1024))
        )
        per_record = float(os.environ.get("SCAN_MEDIA_PROOF_RECORD_SECONDS", "0.005"))
        if not (
            all(math.isfinite(value) for value in (fixed, throughput, per_record))
            and 0 < fixed <= 60
            and 0 < throughput
            and 0 <= per_record <= 1
        ):
            raise ValueError()
    except ValueError as error:
        raise OwnedContentProofRejected(
            "Owned proof budget configuration invalid"
        ) from error
    allowance = min(
        900, fixed + expected_bytes / throughput + expected_records * per_record
    )
    with OwnedContentProof(
        seconds=allowance, operation=operation, attempt=attempt
    ) as proof:
        token = _ACTIVE.set(proof)
        try:
            yield proof
        finally:
            _ACTIVE.reset(token)


def verify_owned_content(descriptor, digest, size, identity):
    if digest is None or size is None:
        raise OwnedContentProofRejected("Owned content has no expected digest")
    with content_proof_scope() as proof:
        proof.verify(descriptor, digest, size, identity)


def owned_verifier_idle():
    """Observe admission release; a returned caller alone does not prove child exit."""
    descriptor = lock_descriptor("verifier")
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True
    finally:
        os.close(descriptor)
