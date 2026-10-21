"""Bounded stat inventory and the shared PC component layout owner.

Deadlines are checked between syscalls. A blocked filesystem syscall cannot be
interrupted by this deadline. Observations never prove content equality.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import stat
import threading
import time
from collections.abc import Callable
from dataclasses import astuple, dataclass
from pathlib import PurePosixPath

from exceptions.storage_exceptions import StorageResolutionError
from exceptions.storage_read import (
    MappedReadDeniedError,
    MissingMappedContentError,
    StaleMappedReadError,
    UnreachableMappedStorageError,
)
from handler.filesystem.storage_access import ScanCapability, directory_signature
from handler.filesystem.storage_policy import StorageOperation
from handler.scan_inventory_contracts import InventoryEntry, InventoryEvidence
from models.rom import RomComponentKind

MAX_ENTRIES = 20_000
MAX_DEPTH = 64
DEADLINE_SECONDS = 2.0

PC_COMPONENT_LAYOUTS = {
    "base": RomComponentKind.BASE,
    "update": RomComponentKind.UPDATE,
    "dlc": RomComponentKind.DLC,
    "expansion": RomComponentKind.DLC,
    "expansions": RomComponentKind.DLC,
    "hotfix": RomComponentKind.HOTFIX,
    "language-pack": RomComponentKind.LANGUAGE_PACK,
    "extra": RomComponentKind.EXTRA,
}


def parse_pc_component_layout(relative_path: str) -> RomComponentKind:
    """Only exact top-level component names carry configured meaning."""
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts or not relative_path:
        raise ValueError("PC component path must be a non-empty relative path")
    if len(path.parts) != 1 or path.parts[0] in {".", ""}:
        return RomComponentKind.UNRESOLVED
    return PC_COMPONENT_LAYOUTS.get(path.parts[0].lower(), RomComponentKind.UNRESOLVED)


class InventoryIncomplete(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__("PC inventory incomplete: " + reason)


def digest_inventory(entries: tuple[InventoryEntry, ...]) -> str:
    records = sorted(astuple(entry) for entry in entries)
    encoded = json.dumps([1, 1, records], ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _entry(path: str, metadata: os.stat_result) -> InventoryEntry:
    return InventoryEntry(
        path,
        "directory" if stat.S_ISDIR(metadata.st_mode) else "file",
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        metadata.st_dev,
        metadata.st_ino,
    )


def _worker_check():
    from handler.scan_operation_worker import check_worker_boundary

    check_worker_boundary()


def collect_pc_inventory(
    open_access,
    relative_path: str,
    *,
    check: Callable[[], None] = _worker_check,
    max_entries: int = MAX_ENTRIES,
    max_depth: int = MAX_DEPTH,
    deadline_seconds: float = DEADLINE_SECONDS,
    monotonic=time.monotonic,
) -> InventoryEvidence:
    if type(max_entries) is not int or not 0 <= max_entries <= MAX_ENTRIES:
        raise ValueError("invalid inventory entry bound")
    if type(max_depth) is not int or not 0 <= max_depth <= MAX_DEPTH:
        raise ValueError("invalid inventory depth bound")
    if not 0 <= deadline_seconds <= DEADLINE_SECONDS:
        raise ValueError("invalid inventory deadline")
    deadline = monotonic() + deadline_seconds
    entries: list[InventoryEntry] = []
    directories: list[tuple[str, tuple[int, ...]]] = []
    pending: list[tuple[str, int, tuple[int, ...] | None]] = [("", 0, None)]
    checks = 0

    def poll(*, boundary=False):
        nonlocal checks
        checks += 1
        if boundary or checks % 128 == 0:
            check()
        if monotonic() >= deadline:
            raise InventoryIncomplete("deadline")

    def full_path(path):
        return "/".join(part for part in (relative_path, path) if part)

    try:
        poll(boundary=True)
        while pending:
            path, depth, expected = pending.pop()
            poll(boundary=True)
            if depth > max_depth:
                raise InventoryIncomplete("depth_limit")
            with open_access(StorageOperation.SCAN, full_path(path)) as capability:
                if not isinstance(capability, ScanCapability):
                    raise TypeError("inventory requires a scan capability")
                before = os.fstat(capability.fileno())
                if expected is not None and expected != directory_signature(before):
                    raise InventoryIncomplete("unstable_directory")
                directories.append((path, directory_signature(before)))
                if path == "":
                    if max_entries == 0:
                        raise InventoryIncomplete("entry_limit")
                    entries.append(_entry("", before))
                result = capability.scan_bounded(max_entries - len(entries), check=poll)
            for child in result.entries:
                child_path = "/".join(part for part in (path, child.name) if part)
                entries.append(_entry(child_path, child.metadata))
                if stat.S_ISDIR(child.metadata.st_mode):
                    pending.append(
                        (child_path, depth + 1, directory_signature(child.metadata))
                    )
            if not result.complete:
                raise InventoryIncomplete(result.reason)
        for path, signature in directories:
            poll(boundary=True)
            with open_access(StorageOperation.SCAN, full_path(path)) as capability:
                if signature != directory_signature(os.fstat(capability.fileno())):
                    raise InventoryIncomplete("unstable_directory")
        poll(boundary=True)
    except (StaleMappedReadError, MappedReadDeniedError):
        raise
    except (
        OSError,
        StorageResolutionError,
        MissingMappedContentError,
        UnreachableMappedStorageError,
    ):
        return InventoryEvidence("", len(entries), False, "unreadable", tuple(entries))
    except InventoryIncomplete as error:
        return InventoryEvidence("", len(entries), False, error.reason, tuple(entries))
    observations = tuple(sorted(entries, key=lambda entry: entry.relative_path))
    return InventoryEvidence(
        digest_inventory(observations), len(entries), True, observations=observations
    )


async def async_collect_pc_inventory(open_access, relative_path: str, **kwargs):
    cancelled = threading.Event()
    check = kwargs.pop("check", _worker_check)

    def boundary():
        if cancelled.is_set():
            raise InventoryIncomplete("cancelled")
        check()

    try:
        return await asyncio.to_thread(
            collect_pc_inventory, open_access, relative_path, check=boundary, **kwargs
        )
    finally:
        cancelled.set()


@dataclass(frozen=True, slots=True)
class ComponentInventory:
    relative_path: str
    kind: RomComponentKind
    members: tuple[InventoryEntry, ...]


def classify_components(evidence: InventoryEvidence) -> tuple[ComponentInventory, ...]:
    from handler.filesystem.roms_handler import category_matches
    from models.rom import RomFileCategory

    if not evidence.complete:
        raise InventoryIncomplete(evidence.reason or "incomplete_evidence")
    nested_dlc = {
        entry.relative_path.split("/")[0]
        for entry in evidence.observations
        if entry.kind == "directory"
        and len(entry.relative_path.split("/")) == 2
        and parse_pc_component_layout(entry.relative_path.split("/")[0])
        == RomComponentKind.DLC
    }
    grouped: dict[tuple[str, RomComponentKind], list[InventoryEntry]] = {}
    for entry in evidence.observations:
        if entry.kind != "file":
            continue
        parts = entry.relative_path.split("/")
        if len(parts) == 1:
            key = ("base", RomComponentKind.BASE)
        else:
            top = parts[0]
            if category_matches(RomFileCategory.SOUNDTRACK.value, [top.lower()]):
                continue
            kind = parse_pc_component_layout(top)
            if top in nested_dlc:
                key = (
                    (top, RomComponentKind.UNRESOLVED)
                    if len(parts) == 2
                    else ("/".join(parts[:2]), kind)
                )
            else:
                key = (top, kind)
        grouped.setdefault(key, []).append(entry)
    return tuple(
        ComponentInventory(
            path, kind, tuple(sorted(members, key=lambda item: item.relative_path))
        )
        for (path, kind), members in sorted(grouped.items())
    )
