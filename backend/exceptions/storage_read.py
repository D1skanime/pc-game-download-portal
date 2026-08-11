from __future__ import annotations

from exceptions.storage_exceptions import StorageResolutionError

_MAX_STATE_LENGTH = 80


class MappedReadError(StorageResolutionError):
    """Bounded mapped-read failure with no filesystem details."""

    def __init__(
        self,
        code: str,
        mapping_id: int,
        expected_revision: int,
        safe_state: str,
    ) -> None:
        self.code = code
        self.mapping_id = mapping_id
        self.expected_revision = expected_revision
        self.safe_state = safe_state[:_MAX_STATE_LENGTH]
        super().__init__(
            f"{code}: mapping {mapping_id} at revision {expected_revision} "
            f"is {self.safe_state}"
        )


class StaleMappedReadError(MappedReadError):
    def __init__(self, mapping_id: int, expected_revision: int) -> None:
        super().__init__(
            "stale_storage_mapping",
            mapping_id,
            expected_revision,
            "stale",
        )


class UnreachableMappedStorageError(MappedReadError):
    def __init__(self, mapping_id: int, expected_revision: int) -> None:
        super().__init__(
            "unreachable_storage",
            mapping_id,
            expected_revision,
            "unreachable",
        )


class MissingMappedContentError(MappedReadError):
    def __init__(self, mapping_id: int, expected_revision: int) -> None:
        super().__init__(
            "missing_storage_content",
            mapping_id,
            expected_revision,
            "missing",
        )


class MappedReadDeniedError(MappedReadError):
    def __init__(self, mapping_id: int, expected_revision: int) -> None:
        super().__init__(
            "mapped_storage_access_denied",
            mapping_id,
            expected_revision,
            "denied",
        )
