"""Cooperating writer serialization through filesystem and SQL acknowledgement."""

import asyncio
import fcntl
import hashlib
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from exceptions.storage_exceptions import StorageResolutionError

_LOCAL = threading.local()
_GATE = threading.RLock()
_KEY = hashlib.sha256(str(Path(__file__).resolve().parents[3]).encode()).hexdigest()[
    :20
]


def lock_descriptor(kind):
    # trunk-ignore(bandit/B108): Persistent lock, no-follow open and verified owner.
    path = f"/tmp/pgdp-owned-{os.getuid()}-{_KEY}-{kind}.lock"
    descriptor = os.open(
        path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600
    )
    info = os.fstat(descriptor)
    if info.st_uid != os.getuid() or info.st_nlink != 1:
        os.close(descriptor)
        raise StorageResolutionError("Owned writer reservation is invalid")
    return descriptor


def _actor():
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    return threading.get_ident(), task


@contextmanager
def owned_writer_domain():
    actor = _actor()
    if getattr(_LOCAL, "depth", 0) and _LOCAL.actor != actor:
        raise StorageResolutionError("Owned writer is busy")
    if not _GATE.acquire(timeout=2):
        raise StorageResolutionError("Owned writer is busy")
    try:
        depth = getattr(_LOCAL, "depth", 0)
        if depth == 0:
            descriptor = lock_descriptor("writers")
            deadline = time.monotonic() + 2
            try:
                while True:
                    try:
                        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            raise StorageResolutionError(
                                "Owned writer is busy"
                            ) from None
                        time.sleep(0.005)
            except BaseException:
                os.close(descriptor)
                raise
            _LOCAL.descriptor = descriptor
            _LOCAL.actor = actor
        _LOCAL.depth = depth + 1
        try:
            yield
        finally:
            _LOCAL.depth -= 1
            if _LOCAL.depth == 0:
                os.close(_LOCAL.descriptor)
                del _LOCAL.descriptor
                del _LOCAL.actor
    finally:
        _GATE.release()
