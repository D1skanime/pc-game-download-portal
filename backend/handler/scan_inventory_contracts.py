"""Advisory inventory observations, never content or write authority."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    relative_path: str
    kind: Literal["file", "directory"]
    size: int
    mtime_ns: int
    ctime_ns: int
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class InventoryEvidence:
    digest: str
    entry_count: int
    complete: bool
    reason: str = ""
    observations: tuple[InventoryEntry, ...] = ()
    schema_version: int = 1
    classifier_version: int = 1


@dataclass(frozen=True, slots=True)
class InventoryAssessment:
    state: Literal["unchanged", "changed", "refresh_required", "incomplete"]
    reason: str = ""

    @classmethod
    def compare(
        cls, current: InventoryEvidence, baseline: InventoryEvidence | None
    ) -> "InventoryAssessment":
        if not current.complete or (baseline is not None and not baseline.complete):
            return cls("incomplete", current.reason or "incomplete_evidence")
        if baseline is None:
            return cls("refresh_required", "missing_baseline")
        versions = (current.schema_version, current.classifier_version)
        if versions != (1, 1) or versions != (
            baseline.schema_version,
            baseline.classifier_version,
        ):
            return cls("refresh_required", "inventory_version_changed")
        if (
            current.digest != baseline.digest
            or current.entry_count != baseline.entry_count
        ):
            return cls("changed")
        return cls("unchanged")


class QuickScanDecision(StrEnum):
    REFRESH = "refresh"
    REUSE = "reuse"
    METADATA_ONLY = "metadata_only"
    INCOMPLETE = "incomplete"
