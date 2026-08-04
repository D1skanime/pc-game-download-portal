from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.platform import Platform


STORAGE_ROOT_NAME_MAX_LENGTH = 400
STORAGE_ROOT_PATH_MAX_LENGTH = 1000
STORAGE_ROOT_MODE_MAX_LENGTH = 32
STORAGE_ROOT_SAFE_ERROR_MAX_LENGTH = 1000
STORAGE_MAPPING_PATH_MAX_LENGTH = 700
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
        UniqueConstraint(
            "platform_id", name="uq_platform_storage_mappings_platform_id"
        ),
        UniqueConstraint(
            "storage_root_id",
            "relative_path",
            name="uq_platform_storage_mappings_root_relative_path",
        ),
        Index("ix_platform_storage_mappings_storage_root_id", "storage_root_id"),
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

    platform: Mapped[Platform] = relationship(
        lazy="joined", back_populates="storage_mapping"
    )
    storage_root: Mapped[StorageRoot] = relationship(
        lazy="joined", back_populates="platform_mappings"
    )
