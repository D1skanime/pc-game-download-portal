from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.platform import Platform


STORAGE_ROOT_NAME_MAX_LENGTH = 400
STORAGE_ROOT_PATH_MAX_LENGTH = 700
STORAGE_ROOT_MODE_MAX_LENGTH = 32
STORAGE_ROOT_SAFE_ERROR_MAX_LENGTH = 1000
STORAGE_MAPPING_PATH_MAX_LENGTH = 700
STORAGE_AUDIT_ACTOR_MAX_LENGTH = 255
STORAGE_AUDIT_ACTION_MAX_LENGTH = 16
EXTERNAL_READ_ONLY_MODE = "external_read_only"


class StorageRoot(BaseModel):
    __tablename__ = "storage_roots"
    __table_args__ = (
        CheckConstraint(
            f"mode = '{EXTERNAL_READ_ONLY_MODE}'",
            name="ck_storage_roots_external_read_only_mode",
        ),
        UniqueConstraint("container_path", name="uq_storage_roots_container_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(length=STORAGE_ROOT_NAME_MAX_LENGTH))
    container_path: Mapped[str] = mapped_column(
        String(length=STORAGE_ROOT_PATH_MAX_LENGTH)
    )
    mode: Mapped[str] = mapped_column(
        String(length=STORAGE_ROOT_MODE_MAX_LENGTH),
        default=EXTERNAL_READ_ONLY_MODE,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    reachable: Mapped[bool | None] = mapped_column(Boolean, default=None)
    readable: Mapped[bool | None] = mapped_column(Boolean, default=None)
    non_writable: Mapped[bool | None] = mapped_column(Boolean, default=None)
    last_checked_at: Mapped[datetime | None] = mapped_column(default=None)
    safe_error: Mapped[str | None] = mapped_column(
        String(length=STORAGE_ROOT_SAFE_ERROR_MAX_LENGTH), default=None
    )

    platform_mappings: Mapped[list[PlatformStorageMapping]] = relationship(
        lazy="raise",
        back_populates="storage_root",
        passive_deletes=True,
    )


class PlatformStorageMapping(BaseModel):
    __tablename__ = "platform_storage_mappings"
    __table_args__ = (
        Index("ix_platform_storage_mappings_storage_root_id", "storage_root_id"),
        Index("ix_platform_storage_mappings_platform_id", "platform_id"),
        Index("ix_platform_storage_mappings_active_platform", "active", "platform_id"),
        Index(
            "ix_platform_storage_mappings_active_root_path",
            "active",
            "storage_root_id",
            "relative_path",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="CASCADE")
    )
    storage_root_id: Mapped[int] = mapped_column(
        ForeignKey("storage_roots.id", ondelete="RESTRICT")
    )
    relative_path: Mapped[str] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    platform: Mapped[Platform] = relationship(
        lazy="joined", back_populates="storage_mapping"
    )
    storage_root: Mapped[StorageRoot] = relationship(
        lazy="joined", back_populates="platform_mappings"
    )


class StorageMappingAuditAction(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    REMOVE = "remove"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"


class StorageMappingAudit(BaseModel):
    __tablename__ = "storage_mapping_audits"
    __table_args__ = (
        CheckConstraint(
            "action IN ('create', 'update', 'remove', 'activate', 'deactivate')",
            name="ck_storage_mapping_audits_action",
        ),
        Index(
            "ix_storage_mapping_audits_platform_created", "platform_id", "created_at"
        ),
        Index("ix_storage_mapping_audits_mapping_created", "mapping_id", "created_at"),
        Index("ix_storage_mapping_audits_action_created", "action", "created_at"),
    )

    updated_at = None
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int] = mapped_column(Integer)
    actor_display_name: Mapped[str] = mapped_column(
        String(length=STORAGE_AUDIT_ACTOR_MAX_LENGTH)
    )
    platform_id: Mapped[int] = mapped_column(Integer)
    mapping_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(length=STORAGE_AUDIT_ACTION_MAX_LENGTH))
    old_storage_root_id: Mapped[int | None] = mapped_column(Integer, default=None)
    old_relative_path: Mapped[str | None] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH), default=None
    )
    old_version: Mapped[int | None] = mapped_column(Integer, default=None)
    old_active: Mapped[bool | None] = mapped_column(Boolean, default=None)
    new_storage_root_id: Mapped[int | None] = mapped_column(Integer, default=None)
    new_relative_path: Mapped[str | None] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH), default=None
    )
    new_version: Mapped[int | None] = mapped_column(Integer, default=None)
    new_active: Mapped[bool | None] = mapped_column(Boolean, default=None)
