from __future__ import annotations

import hashlib
import stat
import struct
import time
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from exceptions.storage_exceptions import (
    DescriptorHashBudgetError,
    DescriptorHashDeadlineError,
    DescriptorHashError,
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    StorageResolutionError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
)
from handler.filesystem.storage_access import (
    ListCapability,
    StatCapability,
    hash_descriptor_file,
    open_storage_access,
)
from handler.filesystem.storage_policy import (
    ExternalStorageDescriptor,
    StorageOperation,
)
from handler.filesystem.storage_resolver import normalize_relative_path
from models.storage import LegacyDetectionState

LEGACY_DETECTION_TIME_BUDGET_SECONDS = 5.0
LEGACY_DETECTION_ENTRY_BUDGET = 10_000
LEGACY_DETECTION_TTL_HOURS = 24
LEGACY_DETECTION_FILE_BYTE_BUDGET = 256 * 1024**3
LEGACY_DETECTION_AGGREGATE_BYTE_BUDGET = 1024**4
LEGACY_OBSERVATION_DEADLINE_SECONDS = 240.0


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

    source_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class LegacyImpactProblem:
    code: str
    count: int


@dataclass(frozen=True, slots=True)
class LegacyImpactProposedMapping:
    platform_id: int
    storage_root_id: int
    relative_path: str


@dataclass(frozen=True, slots=True)
class LegacyImpactPlannedEffects:
    mapping_create_count: int
    catalog_reconnect_count: int
    catalog_preserve_unmatched_count: int
    audit_record_count: int
    rollback_record_count: int
    source_mutation_count: int = 0


@dataclass(frozen=True, slots=True)
class LegacyImpactConfirmation:
    detection_result_id: int
    result_version: int
    platform_id: int
    storage_root_id: int
    relative_path: str
    observed_mapping_id: int | None
    observed_mapping_version: int | None
    reconnectable_catalog_count: int
    unmatched_catalog_count: int
    source_fingerprint: str
    catalog_fingerprint: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class LegacyMigrationImpact:
    state: str
    proposed_mapping: LegacyImpactProposedMapping | None
    reconnectable_catalog_count: int
    unmatched_catalog_count: int
    problems: tuple[LegacyImpactProblem, ...]
    planned_owned_effects: LegacyImpactPlannedEffects
    confirmation: LegacyImpactConfirmation | None
    source_immutable: bool = True
    legacy_fallback_enabled: bool = False


@dataclass(frozen=True, slots=True)
class _CandidateObservation:
    relative_path: str
    present: bool
    state: str | None = None
    observed_files: int = 0
    observed_bytes: int = 0
    lower_bound: bool = False
    safe_problem_code: str | None = None

    source_fingerprint: str | None = None


def build_legacy_candidate_paths(fs_slug: str) -> tuple[str, str]:
    try:
        normalized = normalize_relative_path(fs_slug)
    except StorageResolutionError:
        raise ValueError("platform fs_slug must be one safe path segment") from None
    if not fs_slug or "/" in fs_slug or "\\" in fs_slug or normalized != fs_slug:
        raise ValueError("platform fs_slug must be one safe path segment")
    return f"roms/{fs_slug}", f"{fs_slug}/roms"


def _fingerprint_record(*parts: bytes) -> bytes:
    return b"".join(struct.pack(">Q", len(part)) + part for part in parts)


def _inspect_candidate(
    storage: ExternalStorageDescriptor,
    relative_path: str,
    *,
    deadline_monotonic: float,
    entry_budget: int,
    per_file_byte_budget: int,
    aggregate_byte_budget: int,
    monotonic,
) -> _CandidateObservation:
    inspected = files = size = 0
    pending = [relative_path]

    records: list[tuple[bytes, bytes]] = []

    def budget_reason() -> str | None:
        if inspected >= entry_budget:
            return "entry_budget"
        if monotonic() >= deadline_monotonic:
            return "time_budget"
        return None

    def budget_observation(reason: str) -> _CandidateObservation:
        return _CandidateObservation(
            relative_path=relative_path,
            present=True,
            state=LegacyDetectionState.DETECTED.value,
            observed_files=files,
            observed_bytes=size,
            lower_bound=True,
            safe_problem_code=reason,
        )

    while pending:
        reason = budget_reason()
        if reason is not None:
            return budget_observation(reason)
        directory = pending.pop()
        try:
            with open_storage_access(
                storage, StorageOperation.LIST, directory
            ) as listing:
                entries = cast(ListCapability, listing).list()
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
                return budget_observation(reason)
            inspected += 1
            logical_path = f"{directory}/{name}"
            relative_name = logical_path[len(relative_path) + 1 :]
            name_bytes = relative_name.encode("utf-8", errors="surrogateescape")

            try:
                with open_storage_access(
                    storage, StorageOperation.STAT, logical_path
                ) as metadata:
                    item = cast(StatCapability, metadata).stat()
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
                records.append(
                    (
                        name_bytes,
                        _fingerprint_record(name_bytes, b"directory", b"0", b""),
                    )
                )
            elif stat.S_ISREG(item.st_mode):
                if item.st_size > per_file_byte_budget:
                    return budget_observation("file_byte_budget")
                if size + item.st_size > aggregate_byte_budget:
                    return budget_observation("aggregate_byte_budget")
                remaining = aggregate_byte_budget - size
                if remaining <= 0:
                    return budget_observation("aggregate_byte_budget")
                hash_cap = min(per_file_byte_budget, remaining)
                try:
                    hashed = hash_descriptor_file(
                        storage,
                        logical_path,
                        max_bytes=hash_cap,
                        deadline_monotonic=deadline_monotonic,
                        monotonic=monotonic,
                    )
                except DescriptorHashBudgetError:
                    return budget_observation(
                        (
                            "aggregate_byte_budget"
                            if hash_cap == remaining
                            else "file_byte_budget"
                        )
                    )
                except DescriptorHashDeadlineError:
                    return budget_observation("time_budget")
                except (DescriptorHashError, StorageResolutionError):
                    return _CandidateObservation(
                        relative_path,
                        True,
                        LegacyDetectionState.DETECTED.value,
                        files,
                        size,
                        False,
                        "hash_incomplete",
                    )
                if hashed.bytes_read > remaining:
                    return budget_observation("aggregate_byte_budget")
                if hashed.bytes_read > hash_cap:
                    return budget_observation("file_byte_budget")
                files += 1
                size += hashed.bytes_read
                records.append(
                    (
                        name_bytes,
                        _fingerprint_record(
                            name_bytes,
                            b"regular",
                            str(hashed.bytes_read).encode("ascii"),
                            bytes.fromhex(hashed.sha256),
                        ),
                    )
                )
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
    fingerprint = hashlib.sha256(b"romm-legacy-source-v1\0")
    for _name, record in sorted(records, key=lambda item: item[0]):
        fingerprint.update(record)
    return _CandidateObservation(
        relative_path,
        True,
        LegacyDetectionState.DETECTED.value,
        files,
        size,
        False,
        None,
        fingerprint.hexdigest(),
    )


def detect_legacy_storage(
    storage: ExternalStorageDescriptor,
    *,
    platform_id: int,
    storage_root_id: int,
    fs_slug: str,
    time_budget: float = LEGACY_DETECTION_TIME_BUDGET_SECONDS,
    entry_budget: int = LEGACY_DETECTION_ENTRY_BUDGET,
    per_file_byte_budget: int = LEGACY_DETECTION_FILE_BYTE_BUDGET,
    aggregate_byte_budget: int = LEGACY_DETECTION_AGGREGATE_BYTE_BUDGET,
    monotonic=time.monotonic,
) -> LegacyDetectionOutcome:
    if type(platform_id) is not int or platform_id <= 0:
        raise ValueError("platform_id must be a positive integer")
    if type(storage_root_id) is not int or storage_root_id <= 0:
        raise ValueError("storage_root_id must be a positive integer")
    if storage.root_id != storage_root_id or storage.mapping_id is not None:
        raise TypeError("legacy detection requires its selected root descriptor")
    if (
        time_budget <= 0
        or entry_budget <= 0
        or per_file_byte_budget <= 0
        or aggregate_byte_budget <= 0
    ):
        raise ValueError("legacy detection budgets must be positive")

    deadline_monotonic = monotonic() + time_budget
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
            deadline_monotonic=deadline_monotonic,
            entry_budget=entry_budget,
            monotonic=monotonic,
            per_file_byte_budget=per_file_byte_budget,
            aggregate_byte_budget=aggregate_byte_budget,
        )
        if observation.safe_problem_code == "time_budget":
            return LegacyDetectionOutcome(
                platform_id,
                storage_root_id,
                observation.state or LegacyDetectionState.DETECTED.value,
                observation.relative_path,
                observation.observed_files,
                observation.observed_bytes,
                observation.lower_bound,
                False,
                observation.safe_problem_code,
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
        selected.source_fingerprint is not None,
        selected.safe_problem_code,
        selected.source_fingerprint,
    )
