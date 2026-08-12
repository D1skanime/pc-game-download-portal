from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import FILE_NAME_MAX_LENGTH, BaseModel, utc_now
from models.storage import STORAGE_MAPPING_PATH_MAX_LENGTH

if TYPE_CHECKING:
    from models.assets import Save, State
    from models.play_session import PlaySession
    from models.rom import Rom


CATALOG_HASH_MAX_LENGTH = 100
CLEANUP_KIND_MAX_LENGTH = 32
CLEANUP_STATE_MAX_LENGTH = 16
CLEANUP_DEDUPLICATION_KEY_MAX_LENGTH = 128
CLEANUP_SAFE_ERROR_MAX_LENGTH = 1000


class OwnedCleanupKind(enum.StrEnum):
    COVER = "cover"
    MANUAL = "manual"
    SCREENSHOT = "screenshot"
    RESOURCE = "resource"


class OwnedCleanupState(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RetainedCatalogIdentity(BaseModel):
    __tablename__ = "retained_catalog_identities"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_retained_catalog_version"),
        Index(
            "ix_retained_catalog_platform_logical_path",
            "platform_id",
            "logical_path",
        ),
        Index("ix_retained_catalog_active_rom_id", "active_rom_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="RESTRICT")
    )
    detached_rom_id: Mapped[int] = mapped_column(Integer)
    active_rom_id: Mapped[int | None] = mapped_column(
        ForeignKey("roms.id", ondelete="SET NULL"), default=None
    )
    logical_path: Mapped[str] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    )
    file_name: Mapped[str] = mapped_column(String(length=FILE_NAME_MAX_LENGTH))
    crc_hash: Mapped[str | None] = mapped_column(
        String(length=CATALOG_HASH_MAX_LENGTH), default=None
    )
    md5_hash: Mapped[str | None] = mapped_column(
        String(length=CATALOG_HASH_MAX_LENGTH), default=None
    )
    sha1_hash: Mapped[str | None] = mapped_column(
        String(length=CATALOG_HASH_MAX_LENGTH), default=None
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    detached_by_user_id: Mapped[int] = mapped_column(Integer)
    detached_at: Mapped[datetime] = mapped_column(default=utc_now)
    reconnected_at: Mapped[datetime | None] = mapped_column(default=None)

    active_rom: Mapped[Rom | None] = relationship(
        lazy="raise", foreign_keys=[active_rom_id]
    )
    saves: Mapped[list[Save]] = relationship(
        lazy="raise", back_populates="retained_catalog"
    )
    states: Mapped[list[State]] = relationship(
        lazy="raise", back_populates="retained_catalog"
    )
    play_sessions: Mapped[list[PlaySession]] = relationship(
        lazy="raise", back_populates="retained_catalog"
    )
    cleanup_intents: Mapped[list[OwnedCleanupIntent]] = relationship(
        lazy="raise", back_populates="retained_catalog"
    )


class OwnedCleanupIntent(BaseModel):
    __tablename__ = "owned_cleanup_intents"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('cover', 'manual', 'screenshot', 'resource')",
            name="ck_owned_cleanup_intents_kind",
        ),
        CheckConstraint(
            "state IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_owned_cleanup_intents_state",
        ),
        CheckConstraint("version >= 1", name="ck_owned_cleanup_intents_version"),
        CheckConstraint(
            "attempt_count >= 0", name="ck_owned_cleanup_intents_attempt_count"
        ),
        UniqueConstraint(
            "deduplication_key",
            name="uq_owned_cleanup_intents_deduplication_key",
        ),
        Index(
            "ix_owned_cleanup_intents_state_next_attempt",
            "state",
            "next_attempt_at",
        ),
        Index("ix_owned_cleanup_intents_retained_catalog", "retained_catalog_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    retained_catalog_id: Mapped[int] = mapped_column(
        ForeignKey("retained_catalog_identities.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(length=CLEANUP_KIND_MAX_LENGTH))
    resource_id: Mapped[int | None] = mapped_column(Integer, default=None)
    relative_path: Mapped[str | None] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH), default=None
    )
    file_name: Mapped[str | None] = mapped_column(
        String(length=FILE_NAME_MAX_LENGTH), default=None
    )
    deduplication_key: Mapped[str] = mapped_column(
        String(length=CLEANUP_DEDUPLICATION_KEY_MAX_LENGTH)
    )
    state: Mapped[str] = mapped_column(
        String(length=CLEANUP_STATE_MAX_LENGTH),
        default=OwnedCleanupState.PENDING,
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    safe_error: Mapped[str | None] = mapped_column(
        String(length=CLEANUP_SAFE_ERROR_MAX_LENGTH), default=None
    )
    actor_user_id: Mapped[int] = mapped_column(Integer)
    next_attempt_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    retained_catalog: Mapped[RetainedCatalogIdentity] = relationship(
        lazy="raise", back_populates="cleanup_intents"
    )
