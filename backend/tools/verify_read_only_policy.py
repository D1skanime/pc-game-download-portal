#!/usr/bin/env python3
"""Prove storage-policy denial parity on writable and read-only mounts."""

from __future__ import annotations

import argparse
import builtins
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path, PurePath
from typing import Any
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "backend" / "docker-compose.policy-test.yml"
EXTERNAL_MOUNT = Path("/policy/external")
OWNED_MOUNT = Path("/policy/owned")


def _manifest(root: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        stat = path.lstat()
        entry = {
            "path": path.relative_to(root).as_posix(),
            "kind": "link" if path.is_symlink() else "dir" if path.is_dir() else "file",
            "mode": stat.st_mode,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
        if path.is_symlink():
            entry["target"] = os.readlink(path)
        elif path.is_file():
            entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(entry)
    return entries


def _probe() -> int:
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from exceptions.storage_exceptions import StoragePolicyDenied
    from handler.filesystem.storage_policy import (
        EXTERNAL_READ_OPERATIONS,
        StorageOperation,
        StoragePolicy,
        _create_external_descriptor,
    )

    descriptor = _create_external_descriptor(
        1701, PurePath(EXTERNAL_MOUNT), mapping_id=2901
    )
    attempts: list[object] = [
        *sorted(set(StorageOperation) - EXTERNAL_READ_OPERATIONS, key=str),
        "future-operation",
        object(),
    ]
    touched: list[str] = []

    def forbidden(name: str):
        def fail(*args: object, **kwargs: object) -> None:
            touched.append(name)
            raise AssertionError(f"filesystem access before denial: {name}")

        return fail

    targets = (
        (Path, "stat"),
        (Path, "lstat"),
        (Path, "open"),
        (Path, "iterdir"),
        (Path, "mkdir"),
        (Path, "unlink"),
        (Path, "rename"),
        (Path, "replace"),
        (os, "stat"),
        (os, "scandir"),
        (shutil, "copy"),
        (shutil, "copy2"),
        (shutil, "copytree"),
        (shutil, "move"),
        (tempfile, "NamedTemporaryFile"),
        (tempfile, "TemporaryFile"),
        (builtins, "open"),
    )
    outcomes = []
    with ExitStack() as stack:
        for owner, name in targets:
            stack.enter_context(
                patch.object(owner, name, forbidden(f"{owner.__name__}.{name}"))
            )
        for operation in attempts:
            try:
                StoragePolicy.authorize(operation, descriptor)
            except StoragePolicyDenied as denial:
                outcomes.append(
                    {
                        "operation": denial.operation,
                        "code": denial.code,
                        "storage_class": denial.storage_class,
                        "storage_id": denial.storage_id,
                    }
                )
            else:
                raise AssertionError(
                    f"operation unexpectedly authorized: {operation!r}"
                )
    if touched:
        raise AssertionError(f"denial tripwire calls observed: {touched}")
    (OWNED_MOUNT / "policy-owned-output.txt").write_text(
        "owned output remains writable\n", encoding="utf-8"
    )
    print(json.dumps({"outcomes": outcomes, "manifest": _manifest(EXTERNAL_MOUNT)}))
    return 0


def _run_service(service: str, fixture: Path, owned: Path) -> dict[str, Any]:
    owned.mkdir()
    environment = os.environ | {
        "POLICY_FIXTURE_SOURCE": str(fixture),
        "POLICY_OWNED_OUTPUT": str(owned),
        "POLICY_REPO_ROOT": str(REPO_ROOT),
    }
    completed = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "run", "--rm", service],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError(f"{service} produced no policy evidence")
    return json.loads(lines[-1])


def _verify() -> int:
    if not COMPOSE_FILE.is_file():
        raise AssertionError(f"missing dual-mount compose fixture: {COMPOSE_FILE}")
    with tempfile.TemporaryDirectory(prefix="romm-policy-") as temp:
        base = Path(temp)
        fixture = base / "external"
        fixture.mkdir()
        (fixture / "console").mkdir()
        (fixture / "console" / "game.rom").write_bytes(b"immutable archive bytes\n")
        (fixture / "metadata.txt").write_text("fixed fixture\n", encoding="utf-8")
        before = _manifest(fixture)
        results = {
            mode: _run_service(f"policy-{mode}", fixture, base / f"owned-{mode}")
            for mode in ("writable", "readonly")
        }
        after = _manifest(fixture)
        if before != after:
            raise AssertionError("external fixture manifest changed")
        if results["writable"] != results["readonly"]:
            raise AssertionError("writable and read-only policy evidence differs")
        if results["writable"]["manifest"] != before:
            raise AssertionError("container and host manifests differ")
        for mode in results:
            marker = base / f"owned-{mode}" / "policy-owned-output.txt"
            if marker.read_text(encoding="utf-8") != "owned output remains writable\n":
                raise AssertionError(f"{mode} owned output was not writable")
        print(
            "PASS: writable and :ro mounts produced identical pre-I/O typed denials, unchanged manifests, and writable owned output"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    return _probe() if args.probe else _verify()


if __name__ == "__main__":
    raise SystemExit(main())
