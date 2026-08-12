from __future__ import annotations

import stat
import time
from dataclasses import dataclass

from exceptions.storage_exceptions import (
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    StorageResolutionError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
)
from handler.filesystem.storage_access import open_storage_access
from handler.filesystem.storage_policy import (
    ExternalStorageDescriptor,
    StorageOperation,
)
from handler.filesystem.storage_resolver import normalize_relative_path
from models.storage import LegacyDetectionState

LEGACY_DETECTION_TIME_BUDGET_SECONDS = 5.0
LEGACY_DETECTION_ENTRY_BUDGET = 10_000
LEGACY_DETECTION_TTL_HOURS = 24


@dataclass(frozen=True, slots=True)
class LegacyDetectionOutcome:
    platform_id: int
    storage_root_id: int
    state: str
    proposed_relative_path: str | None
    observed_files: int
    observed_bytes: int
    lower_bound: bool
    selectable: bool
    safe_problem_code: str | None


@dataclass(frozen=True, slots=True)
class _CandidateObservation:
    relative_path: str
    present: bool
    state: str | None = None
    observed_files: int = 0
    observed_bytes: int = 0
    lower_bound: bool = False
    safe_problem_code: str | None = None


def build_legacy_candidate_paths(fs_slug: str) -> tuple[str, str]:
    try:
        normalized = normalize_relative_path(fs_slug)
    except StorageResolutionError:
        raise ValueError("platform fs_slug must be one safe path segment") from None
    if not fs_slug or "/" in fs_slug or "\\" in fs_slug or normalized != fs_slug:
        raise ValueError("platform fs_slug must be one safe path segment")
    return f"roms/{fs_slug}", f"{fs_slug}/roms"


def _inspect_candidate(
    storage: ExternalStorageDescriptor,
    relative_path: str,
    *,
    time_budget: float,
    entry_budget: int,
    monotonic,
) -> _CandidateObservation:
    started = monotonic()
    inspected = files = size = 0
    pending = [relative_path]

    def budget_reason() -> str | None:
        if inspected >= entry_budget:
            return "entry_budget"
        if monotonic() - started >= time_budget:
            return "time_budget"
        return None

    while pending:
        reason = budget_reason()
        if reason is not None:
            return _CandidateObservation(
                relative_path,
                True,
                LegacyDetectionState.DETECTED.value,
                files,
                size,
                True,
                reason,
            )
        directory = pending.pop()
        try:
            with open_storage_access(
                storage, StorageOperation.LIST, directory
            ) as listing:
                entries = listing.list()
        except MissingStorageTargetError:
            if directory == relative_path:
                return _CandidateObservation(relative_path, False)
            return _CandidateObservation(
                relative_path,
                True,
                LegacyDetectionState.UNREADABLE.value,
                files,
                size,
                False,
                "unreadable_entry",
            )
        except MissingStorageRootError:
            return _CandidateObservation(
                relative_path,
                True,
                LegacyDetectionState.UNREACHABLE.value,
                safe_problem_code="storage_root_unreachable",
            )
        except (UnsafeSymlinkError, NonDirectoryStorageTargetError):
            return _CandidateObservation(
                relative_path,
                True,
                LegacyDetectionState.UNSAFE.value,
                files,
                size,
                False,
                "unsafe_entry",
            )
        except (UnreadableStorageTargetError, StorageResolutionError):
            return _CandidateObservation(
                relative_path,
                True,
                LegacyDetectionState.UNREADABLE.value,
                files,
                size,
                False,
                "unreadable_directory",
            )

        for name in entries:
            reason = budget_reason()
            if reason is not None:
                return _CandidateObservation(
                    relative_path,
                    True,
                    LegacyDetectionState.DETECTED.value,
                    files,
                    size,
                    True,
                    reason,
                )
            inspected += 1
            logical_path = f"{directory}/{name}"
            try:
                with open_storage_access(
                    storage, StorageOperation.STAT, logical_path
                ) as metadata:
                    item = metadata.stat()
            except UnsafeSymlinkError:
                return _CandidateObservation(
                    relative_path,
                    True,
                    LegacyDetectionState.UNSAFE.value,
                    files,
                    size,
                    False,
                    "unsafe_entry",
                )
            except StorageResolutionError:
                return _CandidateObservation(
                    relative_path,
                    True,
                    LegacyDetectionState.UNREADABLE.value,
                    files,
                    size,
                    False,
                    "unreadable_entry",
                )
            if stat.S_ISDIR(item.st_mode):
                pending.append(logical_path)
            elif stat.S_ISREG(item.st_mode):
                files += 1
                size += item.st_size
            else:
                return _CandidateObservation(
                    relative_path,
                    True,
                    LegacyDetectionState.UNSAFE.value,
                    files,
                    size,
                    False,
                    "unsupported_entry",
                )

    if files == 0:
        return _CandidateObservation(
            relative_path,
            True,
            LegacyDetectionState.EMPTY.value,
            safe_problem_code="canonical_layout_empty",
        )
    return _CandidateObservation(
        relative_path,
        True,
        LegacyDetectionState.DETECTED.value,
        files,
        size,
    )


def detect_legacy_storage(
    storage: ExternalStorageDescriptor,
    *,
    platform_id: int,
    storage_root_id: int,
    fs_slug: str,
    time_budget: float = LEGACY_DETECTION_TIME_BUDGET_SECONDS,
    entry_budget: int = LEGACY_DETECTION_ENTRY_BUDGET,
    monotonic=time.monotonic,
) -> LegacyDetectionOutcome:
    if type(platform_id) is not int or platform_id <= 0:
        raise ValueError("platform_id must be a positive integer")
    if type(storage_root_id) is not int or storage_root_id <= 0:
        raise ValueError("storage_root_id must be a positive integer")
    if storage.root_id != storage_root_id or storage.mapping_id is not None:
        raise TypeError("legacy detection requires its selected root descriptor")
    if time_budget <= 0 or entry_budget <= 0:
        raise ValueError("legacy detection budgets must be positive")

    try:
        candidates = build_legacy_candidate_paths(fs_slug)
    except ValueError:
        return LegacyDetectionOutcome(
            platform_id,
            storage_root_id,
            LegacyDetectionState.UNSAFE.value,
            None,
            0,
            0,
            False,
            False,
            "unsafe_platform_identity",
        )

    observations: list[_CandidateObservation] = []
    for candidate in candidates:
        observation = _inspect_candidate(
            storage,
            candidate,
            time_budget=time_budget,
            entry_budget=entry_budget,
            monotonic=monotonic,
        )
        if observation.state == LegacyDetectionState.UNREACHABLE.value:
            return LegacyDetectionOutcome(
                platform_id,
                storage_root_id,
                observation.state,
                None,
                0,
                0,
                False,
                False,
                observation.safe_problem_code,
            )
        observations.append(observation)

    present = [item for item in observations if item.present]
    if len(present) > 1:
        return LegacyDetectionOutcome(
            platform_id,
            storage_root_id,
            LegacyDetectionState.MANUAL_MAPPING_REQUIRED.value,
            None,
            0,
            0,
            False,
            False,
            "multiple_canonical_layouts",
        )
    if not present:
        return LegacyDetectionOutcome(
            platform_id,
            storage_root_id,
            LegacyDetectionState.MANUAL_MAPPING_REQUIRED.value,
            None,
            0,
            0,
            False,
            False,
            "canonical_layout_missing",
        )

    selected = present[0]
    return LegacyDetectionOutcome(
        platform_id,
        storage_root_id,
        selected.state or LegacyDetectionState.MANUAL_MAPPING_REQUIRED.value,
        selected.relative_path,
        selected.observed_files,
        selected.observed_bytes,
        selected.lower_bound,
        selected.state == LegacyDetectionState.DETECTED.value,
        selected.safe_problem_code,
    )
