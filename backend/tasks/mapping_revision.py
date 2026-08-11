from __future__ import annotations

from dataclasses import dataclass

from handler.storage.read_context import MappingReadContext


@dataclass(frozen=True, slots=True)
class MappingRevisionJob:
    """Queue-safe storage identity with no reusable filesystem path."""

    mapping_id: int
    expected_revision: int

    def read_context(self) -> MappingReadContext:
        return MappingReadContext(self.mapping_id, self.expected_revision)
