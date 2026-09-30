from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel
from models.storage import STORAGE_MAPPING_PATH_MAX_LENGTH

OWNED_MEDIA_CLEANUP_ERROR_MAX_LENGTH = 100
OWNED_MEDIA_CLEANUP_ATTEMPT_LIMIT = 8


class OwnedMediaCleanupState(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OwnedMediaCleanupIntent(BaseModel):
    __tablename__ = "owned_media_cleanup_intents"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_owned_media_cleanup_intents_state",
        ),
        CheckConstraint(
            f"attempt_count >= 0 AND attempt_count <= {OWNED_MEDIA_CLEANUP_ATTEMPT_LIMIT}",
            name="ck_owned_media_cleanup_intents_attempt_count",
        ),
        CheckConstraint(
            "owned_path <> '' AND owned_path NOT LIKE '/%' AND owned_path NOT LIKE '%..%'",
            name="ck_owned_media_cleanup_intents_owned_path_relative",
        ),
        UniqueConstraint(
            "owned_path", name="uq_owned_media_cleanup_intents_owned_path"
        ),
        Index(
            "idx_owned_media_cleanup_intents_state_next_attempt",
            "state",
            "next_attempt_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    media_id: Mapped[int] = mapped_column(Integer)
    owned_path: Mapped[str] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    )
    state: Mapped[OwnedMediaCleanupState] = mapped_column(
        String(length=16), default=OwnedMediaCleanupState.PENDING
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(
        String(length=OWNED_MEDIA_CLEANUP_ERROR_MAX_LENGTH), default=None
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(default=None)
