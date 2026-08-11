from __future__ import annotations

import stat
import time
from dataclasses import dataclass

from exceptions.storage_exceptions import StorageResolutionError
from handler.filesystem.storage_policy import StorageOperation
from handler.storage.read_context import MappingReadContext

PREVIEW_TIME_BUDGET_SECONDS = 5.0
PREVIEW_ENTRY_BUDGET = 10_000
MAX_PROBLEM_CATEGORIES = 10


@dataclass(frozen=True, slots=True)
class MappingPreviewResult:
    state: str
    observed_files: int
    observed_directories: int
    observed_bytes: int
    lower_bound: bool
    budget_reason: str | None
    problems: dict[str, int]


def preview_mapping(
    context: MappingReadContext,
    *,
    time_budget: float = PREVIEW_TIME_BUDGET_SECONDS,
    entry_budget: int = PREVIEW_ENTRY_BUDGET,
    monotonic=time.monotonic,
) -> MappingPreviewResult:
    started = monotonic()
    inspected = files = directories = size = 0
    problems: dict[str, int] = {}
    pending = [""]
    budget_reason: str | None = None

    def exhausted() -> str | None:
        if inspected >= entry_budget:
            return "entry_budget"
        if monotonic() - started >= time_budget:
            return "time_budget"
        return None

    def problem(category: str) -> None:
        if category in problems:
            problems[category] += 1
        elif len(problems) < MAX_PROBLEM_CATEGORIES:
            problems[category] = 1

    while pending:
        if budget_reason := exhausted():
            break
        directory = pending.pop()
        try:
            with context.open(StorageOperation.LIST, directory) as listing:
                entries = listing.list()
        except StorageResolutionError:
            problem("unreadable_directory")
            continue
        for name in entries:
            if budget_reason := exhausted():
                break
            inspected += 1
            relative = f"{directory}/{name}" if directory else name
            try:
                with context.open(StorageOperation.STAT, relative) as metadata:
                    item = metadata.stat()
            except StorageResolutionError:
                problem("unreadable_entry")
                continue
            if stat.S_ISLNK(item.st_mode):
                problem("unsafe_entry")
            elif stat.S_ISDIR(item.st_mode):
                directories += 1
                pending.append(relative)
            elif stat.S_ISREG(item.st_mode):
                files += 1
                size += item.st_size
            else:
                problem("unsupported_entry")
    partial = budget_reason is not None or bool(problems)
    return MappingPreviewResult(
        "partial" if partial else "complete",
        files,
        directories,
        size,
        partial,
        budget_reason,
        problems,
    )
