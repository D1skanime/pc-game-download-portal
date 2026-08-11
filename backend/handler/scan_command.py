from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath

_MAX_OPTIONS = 24
_MAX_OPTION_LENGTH = 256


class ScanTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WATCHER = "watcher"


class ScanScope(StrEnum):
    LIBRARY = "library"
    PLATFORM = "platform"
    ROM = "rom"


@dataclass(frozen=True, slots=True)
class MappedScanCommand:
    mapping_id: int
    expected_revision: int
    trigger: ScanTrigger
    scope: ScanScope
    scan_type: str
    options: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if type(self.mapping_id) is not int or self.mapping_id <= 0:
            raise ValueError("mapping_id must be a positive integer")
        if type(self.expected_revision) is not int or self.expected_revision <= 0:
            raise ValueError("expected_revision must be a positive integer")
        if not isinstance(self.trigger, ScanTrigger):
            raise TypeError("trigger must be a ScanTrigger")
        if not isinstance(self.scope, ScanScope):
            raise TypeError("scope must be a ScanScope")
        if not self.scan_type or len(self.scan_type) > _MAX_OPTION_LENGTH:
            raise ValueError("scan_type must be bounded")
        if len(self.options) > _MAX_OPTIONS:
            raise ValueError("scan options exceed the bounded limit")
        for key, value in self.options:
            if (
                not key
                or len(key) > _MAX_OPTION_LENGTH
                or not value
                or len(value) > _MAX_OPTION_LENGTH
            ):
                raise ValueError("scan options must be bounded")
            path = PurePath(value)
            if path.is_absolute() or value.startswith(("/", "\\")):
                raise ValueError("scan options cannot contain source paths")
            if any(part == ".." for part in path.parts) or "\\" in value:
                raise ValueError("scan options cannot contain source paths")
