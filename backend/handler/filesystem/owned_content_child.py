"""Exec-only verifier with exact read-only FD authority and no application imports."""

import array
import fcntl
import hashlib
import json
import os
import socket
import stat
import sys


def send(channel, value):
    frame = json.dumps(value, separators=(",", ":")).encode()
    if len(frame) > 4096:
        raise ValueError("content proof frame")
    channel.send(frame)


def identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def main():
    channel = socket.socket(fileno=int(sys.argv[1]))
    os.fstat(int(sys.argv[2]))
    send(channel, {"ready": 1})
    ordinal = 0
    while True:
        frame, ancillary, flags, _ = channel.recvmsg(4096, socket.CMSG_SPACE(4))
        if not frame:
            return
        descriptors = array.array("i")
        for level, kind, data in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                descriptors.frombytes(
                    data[: len(data) - len(data) % descriptors.itemsize]
                )
        try:
            request = json.loads(frame)
            if (
                flags
                or len(descriptors) != 1
                or set(request)
                != {
                    "nonce",
                    "operation",
                    "attempt",
                    "ordinal",
                    "digest",
                    "size",
                    "identity",
                }
            ):
                raise ValueError("content proof request")
            source = descriptors[0]
            if (
                request["ordinal"] != ordinal
                or type(request["size"]) is not int
                or request["size"] < 0
                or fcntl.fcntl(source, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY
            ):
                raise ValueError("content proof authority")
            before = os.fstat(source)
            if (
                not stat.S_ISREG(before.st_mode)
                or identity(before) != request["identity"]
            ):
                raise ValueError("content proof identity")
            digest, total = hashlib.sha256(), 0
            while total < request["size"]:
                chunk = os.pread(
                    source, min(1024 * 1024, request["size"] - total), total
                )
                if not chunk:
                    raise ValueError("content proof short read")
                digest.update(chunk)
                total += len(chunk)
            if (
                os.pread(source, 1, total)
                or identity(os.fstat(source)) != identity(before)
                or digest.hexdigest() != request["digest"]
            ):
                raise ValueError("content proof changed")
            send(channel, request)
            ordinal += 1
        finally:
            for descriptor in descriptors:
                os.close(descriptor)


if __name__ == "__main__":
    main()
