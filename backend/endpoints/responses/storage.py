import enum
from typing import Literal

from pydantic import Field

from endpoints.responses.base import BaseModel, UTCDatetime
from handler.filesystem.storage_resolver import (
    MAX_DIRECTORY_PAGE_SIZE,
    MAX_STORAGE_CURSOR_LENGTH,
)
from models.storage import (
    LEGACY_PROBLEM_CODE_MAX_LENGTH,
    STORAGE_AUDIT_ACTOR_MAX_LENGTH,
    STORAGE_MAPPING_PATH_MAX_LENGTH,
    STORAGE_ROOT_MODE_MAX_LENGTH,
    STORAGE_ROOT_NAME_MAX_LENGTH,
    STORAGE_ROOT_PATH_MAX_LENGTH,
    StorageMappingAuditAction,
)


class LegacyDetectionErrorCode(enum.StrEnum):
    MISSING = "legacy_detection_missing"
    STALE = "legacy_detection_stale"
    EXPIRED = "legacy_detection_expired"
    CROSS_PLATFORM = "legacy_detection_cross_platform"
    UNSELECTABLE = "legacy_detection_unselectable"
    INVALID_STATE = "legacy_detection_invalid_state"
    IMPACT_STALE = "legacy_impact_stale"


class LegacyDetectionErrorDetail(BaseModel):
    code: LegacyDetectionErrorCode
    message: str = Field(min_length=1, max_length=160)
    result_id: int | None = Field(default=None, gt=0)
    platform_id: int | None = Field(default=None, gt=0)
    current_version: int | None = Field(default=None, gt=0)


class LegacyDetectionErrorResponse(BaseModel):
    detail: LegacyDetectionErrorDetail


class LegacyDetectionRequestSchema(BaseModel):
    platform_id: int = Field(gt=0)
    storage_root_id: int = Field(gt=0)


class LegacyDetectionJobSchema(BaseModel):
    job_id: str = Field(min_length=1, max_length=255)
    platform_id: int = Field(gt=0)
    storage_root_id: int = Field(gt=0)
    state: Literal["pending"]


class LegacyDetectionResultSchema(BaseModel):
    id: int = Field(gt=0)
    platform_id: int = Field(gt=0)
    storage_root_id: int = Field(gt=0)
    state: Literal[
        "detected",
        "manual_mapping_required",
        "empty",
        "unreadable",
        "unreachable",
        "unsafe",
        "conflict",
    ]
    proposed_relative_path: str | None = Field(
        default=None, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH
    )
    observed_files: int = Field(ge=0)
    observed_bytes: int = Field(ge=0)
    lower_bound: bool
    selectable: bool
    safe_problem_code: str | None = Field(
        default=None, max_length=LEGACY_PROBLEM_CODE_MAX_LENGTH
    )
    observed_mapping_id: int | None = Field(default=None, gt=0)
    observed_mapping_version: int | None = Field(default=None, gt=0)
    version: int = Field(gt=0)
    created_at: UTCDatetime
    completed_at: UTCDatetime | None
    expires_at: UTCDatetime
    expired: bool
    source_immutable: Literal[True] = True
    authorizes_legacy_reads: Literal[False] = False


class LegacyImpactPreviewRequestSchema(BaseModel):
    platform_id: int = Field(gt=0)
    expected_result_version: int = Field(gt=0)


class LegacyImpactProblemSchema(BaseModel):
    code: str = Field(min_length=1, max_length=LEGACY_PROBLEM_CODE_MAX_LENGTH)
    count: int = Field(gt=0)


class LegacyImpactProposedMappingSchema(BaseModel):
    platform_id: int = Field(gt=0)
    storage_root_id: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)


class LegacyImpactPlannedEffectsSchema(BaseModel):
    mapping_create_count: int = Field(ge=0, le=1)
    catalog_reconnect_count: int = Field(ge=0)
    catalog_preserve_unmatched_count: int = Field(ge=0)
    audit_record_count: int = Field(ge=0, le=1)
    rollback_record_count: int = Field(ge=0, le=1)
    source_mutation_count: Literal[0] = 0


class LegacyImpactConfirmationSchema(BaseModel):
    detection_result_id: int = Field(gt=0)
    result_version: int = Field(gt=0)
    platform_id: int = Field(gt=0)
    storage_root_id: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    observed_mapping_id: int | None = Field(default=None, gt=0)
    observed_mapping_version: int | None = Field(default=None, gt=0)
    reconnectable_catalog_count: int = Field(ge=0)
    unmatched_catalog_count: int = Field(ge=0)
    expires_at: UTCDatetime


class LegacyMigrationResultSchema(BaseModel):
    state: Literal["completed"]
    migration_id: int = Field(gt=0)
    migration_version: int = Field(gt=0)
    mapping_id: int = Field(gt=0)
    mapping_version: int = Field(gt=0)
    platform_id: int = Field(gt=0)
    storage_root_id: int = Field(gt=0)
    reconnected_catalog_count: int = Field(ge=0)
    unmatched_catalog_count: int = Field(ge=0)
    source_immutable: Literal[True] = True
    legacy_fallback_enabled: Literal[False] = False


class LegacyImpactPreviewSchema(BaseModel):
    state: Literal["ready", "manual_mapping_required"]
    proposed_mapping: LegacyImpactProposedMappingSchema | None
    reconnectable_catalog_count: int = Field(ge=0)
    unmatched_catalog_count: int = Field(ge=0)
    problems: list[LegacyImpactProblemSchema] = Field(max_length=10)
    planned_owned_effects: LegacyImpactPlannedEffectsSchema
    confirmation: LegacyImpactConfirmationSchema | None
    source_immutable: Literal[True] = True
    legacy_fallback_enabled: Literal[False] = False


class StorageReadErrorCode(enum.StrEnum):
    INVALID_RELATIVE_PATH = "invalid_relative_path"
    INVALID_STORAGE_CURSOR = "invalid_storage_cursor"
    MISSING_STORAGE_ROOT = "missing_storage_root"
    MISSING_STORAGE_TARGET = "missing_storage_target"
    INACTIVE_STORAGE_ROOT = "inactive_storage_root"
    NON_DIRECTORY_STORAGE_TARGET = "non_directory_storage_target"
    UNREADABLE_STORAGE_TARGET = "unreadable_storage_target"
    UNSAFE_STORAGE_SYMLINK = "unsafe_storage_symlink"
    STORAGE_ESCAPE = "storage_escape"
    UNSAFE_WRITABLE_ROOT = "unsafe_writable_root"
    STORAGE_SCAN_LIMIT_EXCEEDED = "storage_scan_limit_exceeded"
    STORAGE_FILESYSTEM_ERROR = "storage_filesystem_error"
    STORAGE_RESOLUTION_ERROR = "storage_resolution_error"


class StorageErrorDetail(BaseModel):
    code: StorageReadErrorCode
    message: str = Field(min_length=1, max_length=160)


class StorageErrorResponse(BaseModel):
    detail: StorageErrorDetail


class StorageRootHealthSchema(BaseModel):
    reachable: bool
    readable: bool
    non_writable: bool | None
    checked_at: UTCDatetime
    error: str | None = Field(default=None, max_length=160)


class StorageRootSchema(BaseModel):
    id: int
    name: str = Field(max_length=STORAGE_ROOT_NAME_MAX_LENGTH)
    mode: Literal["external_read_only"]
    active: bool
    created_at: UTCDatetime
    updated_at: UTCDatetime
    health: StorageRootHealthSchema


class StorageDirectoryEntrySchema(BaseModel):
    name: str = Field(min_length=1, max_length=STORAGE_ROOT_PATH_MAX_LENGTH)
    relative_path: str = Field(min_length=1, max_length=STORAGE_ROOT_PATH_MAX_LENGTH)
    navigable: bool


class StorageDirectoryPageSchema(BaseModel):
    entries: list[StorageDirectoryEntrySchema] = Field(
        max_length=MAX_DIRECTORY_PAGE_SIZE
    )
    next_cursor: str | None = Field(default=None, max_length=MAX_STORAGE_CURSOR_LENGTH)


class StorageMappingCreateSchema(BaseModel):
    platform_id: int = Field(gt=0)
    storage_root_id: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)


class StorageMappingUpdateSchema(BaseModel):
    storage_root_id: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    expected_version: int = Field(gt=0)


class StorageMappingVersionSchema(BaseModel):
    expected_version: int = Field(gt=0)


class StorageMappingRemovalConfirmationSchema(BaseModel):
    expected_version: int = Field(gt=0)
    expected_unreachable_catalog_count: int = Field(ge=0)
    confirmed: Literal[True]


class StorageMappingRemovalConsequencesSchema(BaseModel):
    mapping_id: int
    platform_id: int
    mapping_version: int = Field(gt=0)
    retained_visible_unreachable_catalog_count: int = Field(ge=0)
    preserves_metadata: Literal[True] = True
    preserves_saves: Literal[True] = True
    preserves_states: Literal[True] = True
    preserves_play_history: Literal[True] = True
    source_immutable: Literal[True] = True
    mapping_revision_invalidated: bool
    cancels_mapping_work_at_safe_boundaries: Literal[True] = True


class StorageMappingSchema(BaseModel):
    id: int
    platform_id: int
    storage_root_id: int
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    active: bool
    version: int = Field(gt=0)


class StorageMappingTestSchema(BaseModel):
    platform_id: int
    storage_root_id: int
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    valid: Literal[True] = True


class StorageMappingPreviewSchema(BaseModel):
    mapping_id: int
    platform_id: int
    storage_root_id: int
    mapping_version: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    examined_entry_count: int = Field(ge=0)
    candidate_file_count: int = Field(ge=0)
    candidate_directory_count: int = Field(ge=0)
    truncated: bool
    next_cursor: str | None = Field(default=None, max_length=MAX_STORAGE_CURSOR_LENGTH)


class StorageMappingPreviewStateSchema(BaseModel):
    mapping_id: int
    mapping_version: int = Field(gt=0)
    health: StorageRootHealthSchema
    state: Literal["pending", "partial", "complete"]
    observed_files: int = Field(ge=0)
    observed_directories: int = Field(ge=0)
    observed_bytes: int = Field(ge=0)
    lower_bound: bool
    budget_reason: Literal["time_budget", "entry_budget"] | None = None
    timestamp: UTCDatetime | None = None
    problems: dict[str, int] = Field(default_factory=dict)
    stale: bool
    error_code: str | None = Field(default=None, max_length=64)


class StorageConflictErrorCode(enum.StrEnum):
    PLATFORM_MAPPING_MISSING = "platform_mapping_missing"
    DUPLICATE_STORAGE_MAPPING = "duplicate_storage_mapping"
    STORAGE_MAPPING_OVERLAP = "storage_mapping_overlap"
    STORAGE_MAPPING_STALE_VERSION = "storage_mapping_stale_version"
    STORAGE_MAPPING_CONSEQUENCES_CHANGED = "storage_mapping_consequences_changed"


class StorageConflictDetail(BaseModel):
    code: StorageConflictErrorCode
    message: str = Field(min_length=1, max_length=160)
    platform_id: int | None = None
    mapping_id: int | None = None
    current_version: int | None = Field(default=None, gt=0)


class StorageConflictResponse(BaseModel):
    detail: StorageConflictDetail


class StorageMappingSnapshotSchema(BaseModel):
    storage_root_id: int
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    version: int = Field(gt=0)
    active: bool


class StorageMappingAuditSchema(BaseModel):
    id: int
    actor_user_id: int
    actor_display_name: str = Field(
        min_length=1, max_length=STORAGE_AUDIT_ACTOR_MAX_LENGTH
    )
    platform_id: int
    mapping_id: int
    action: StorageMappingAuditAction
    old: StorageMappingSnapshotSchema | None
    new: StorageMappingSnapshotSchema | None
    created_at: UTCDatetime


class StorageMappingAuditPageSchema(BaseModel):
    entries: list[StorageMappingAuditSchema] = Field(max_length=100)
    next_cursor: str | None = Field(default=None, max_length=2048)
