"""Bounded public identities and commands for durable scans."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from exceptions.storage_exceptions import StorageResolutionError
from handler.filesystem.storage_resolver import normalize_relative_path

RequestKey = Annotated[
    str, Field(min_length=1, max_length=96, pattern=r"^[a-z0-9][a-z0-9_-]*$")
]
SafeCode = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_:-]+$")]
PositiveId = Annotated[int, Field(strict=True, gt=0)]
ScanState = Literal[
    "accepted",
    "queued",
    "running",
    "stopping",
    "cancelled",
    "interrupted",
    "recovering",
    "blocked",
    "failed",
    "completed",
    "completed-with-warnings",
]


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ScanOperationRequest(StrictContract):
    request_key: RequestKey
    platforms: list[PositiveId] = Field(default_factory=list, max_length=256)
    platform_fs_slugs: list[Annotated[str, Field(min_length=1, max_length=100)]] = (
        Field(default_factory=list, max_length=256)
    )
    filesystem_scope_paths: dict[str, str] = Field(default_factory=dict, max_length=256)
    type: Literal[
        "new_platforms", "quick", "update", "unmatched", "complete", "hashes"
    ] = "quick"
    roms_ids: list[PositiveId] = Field(default_factory=list, max_length=1000)
    apis: list[
        Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_]+$")]
    ] = Field(default_factory=list, max_length=24)
    launchbox_remote_enabled: bool = True
    playmatch_enabled: bool = True
    metadata_locale: (
        Annotated[str, Field(max_length=16, pattern=r"^[a-zA-Z_-]+$")] | None
    ) = None
    metadata_only: bool = False
    media_only: bool = False

    @field_validator("filesystem_scope_paths")
    @classmethod
    def safe_paths(cls, paths):
        try:
            return {key: normalize_relative_path(value) for key, value in paths.items()}
        except StorageResolutionError:
            raise ValueError("invalid_relative_scope") from None

    @model_validator(mode="after")
    def compatible_policies(self):
        if self.metadata_only and self.media_only:
            raise ValueError("incompatible_scan_policies")
        return self


class ScanOperationMutationRequest(StrictContract):
    request_key: RequestKey
    expected_version: int = Field(ge=1, strict=True)
    item_ids: list[PositiveId] = Field(default_factory=list, max_length=100)


class ScanOperationItemResult(StrictContract):
    id: int
    target_key: RequestKey
    mapping_id: PositiveId
    expected_revision: PositiveId
    relative_path: str = Field(max_length=700)
    provider: str = Field(max_length=32)
    outcome: Literal["indexed", "completed", "warning", "failed", "skipped"]
    cause_code: SafeCode | None = None
    attempt_id: str


class ScanOperationSnapshot(StrictContract):
    id: str
    request_key: RequestKey
    job_id: str
    attempt_id: str | None
    version: int
    state: ScanState
    scan_stats: dict[str, int] = Field(default_factory=dict, max_length=32)
    cause_code: SafeCode | None = None
    next_action: SafeCode | None = None
    intentional_cancel: bool
    dispatch_pending: bool
    checkpoint: dict[str, int | str | bool] = Field(default_factory=dict, max_length=32)
    items: list[ScanOperationItemResult] = Field(default_factory=list, max_length=100)
    items_offset: int = 0
    items_total: int = 0
    queue_condition: Literal["available", "expired", "unavailable", "pending"] = (
        "pending"
    )
    created_at: datetime
    updated_at: datetime
