from typing import Literal

from pydantic import BaseModel, Field


class SetupFolderSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    relative_path: str = Field(min_length=1, max_length=700)
    association: Literal["known", "unknown"]
    suggested_platform: str | None = Field(default=None, max_length=100)


class SetupPlatformOptionSchema(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)


class SetupFoldersResponse(BaseModel):
    root_label: str = Field(min_length=1, max_length=100)
    folders: list[SetupFolderSchema] = Field(max_length=100)
    platform_options: list[SetupPlatformOptionSchema] = Field(max_length=200)


class SetupFolderAssignmentSchema(BaseModel):
    folder_name: str = Field(min_length=1, max_length=255)
    platform_slug: str = Field(min_length=1, max_length=100)


class SetupFolderAssignmentRequest(BaseModel):
    assignments: list[SetupFolderAssignmentSchema] = Field(max_length=100)


class SetupRootHealthSchema(BaseModel):
    reachable: bool
    readable: bool
    non_writable: bool | None


class SetupFolderMappingSchema(BaseModel):
    folder_name: str = Field(min_length=1, max_length=255)
    platform_slug: str = Field(min_length=1, max_length=100)
    mapping_id: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=700)


class SetupRecoverySnapshot(BaseModel):
    enrolled: bool
    setup_complete: bool
    current_step: Literal["account", "folders", "complete"]
    saved_assignments: list[SetupFolderMappingSchema] = Field(max_length=100)
    missing_assignments: list[SetupFolderSchema] = Field(max_length=100)
    root_health: SetupRootHealthSchema
    cause_code: (
        Literal[
            "root_missing",
            "root_unreadable",
            "root_not_read_only",
            "root_inactive",
            "root_discovery_failed",
            "assignments_missing",
            "mapping_conflict",
        ]
        | None
    )
    next_action: Literal[
        "create_admin",
        "retry_check",
        "assign_missing",
        "resolve_conflicts",
        "start_first_scan",
    ]


class SetupFolderAssignmentResponse(BaseModel):
    mappings: list[SetupFolderMappingSchema] = Field(max_length=100)
    ready: bool
    root_health: SetupRootHealthSchema
    recovery: SetupRecoverySnapshot
