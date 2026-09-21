from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel, utc_now

if TYPE_CHECKING:
    from models.download_manifest import DownloadManifest
    from models.rom import Rom
    from models.user import User


class DownloadTransferMode(enum.StrEnum):
    STANDARD = "standard"
    ENHANCED = "enhanced"


class DownloadTransferSessionStatus(enum.StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    EXPIRED = "expired"
    STALE = "stale"


class DownloadTransferSessionResult(enum.StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadTransferItemStatus(enum.StrEnum):
    QUEUED = "queued"
    ACTIVE = "active"
    HANDED_TO_BROWSER = "handed_to_browser"
    SERVED = "served"
    VERIFIED = "verified"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"
    STALE = "stale"


class DownloadTransferSession(BaseModel):
    __tablename__ = "download_transfer_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    rom_id: Mapped[int] = mapped_column(
        ForeignKey("roms.id", ondelete="CASCADE"), index=True
    )
    manifest_id: Mapped[str] = mapped_column(
        ForeignKey("download_manifests.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[DownloadTransferMode] = mapped_column(
        Enum(
            DownloadTransferMode,
            native_enum=False,
            create_constraint=True,
            length=16,
            name="downloadtransfermode",
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
    )
    status: Mapped[DownloadTransferSessionStatus] = mapped_column(
        Enum(
            DownloadTransferSessionStatus,
            native_enum=False,
            create_constraint=True,
            length=16,
            name="downloadtransfersessionstatus",
            values_callable=lambda values: [value.value for value in values],
        ),
        default=DownloadTransferSessionStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    result: Mapped[DownloadTransferSessionResult | None] = mapped_column(
        Enum(
            DownloadTransferSessionResult,
            native_enum=False,
            create_constraint=True,
            length=16,
            name="downloadtransfersessionresult",
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=True,
    )
    selected_items: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    observed_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(lazy="joined")
    rom: Mapped[Rom] = relationship(lazy="joined")
    manifest: Mapped[DownloadManifest] = relationship(lazy="joined")
    items: Mapped[list[DownloadTransferItem]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    events: Mapped[list[DownloadTransferEvent]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )


class DownloadTransferItem(BaseModel):
    __tablename__ = "download_transfer_items"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "manifest_member_id", name="uq_download_transfer_item_member"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("download_transfer_sessions.id", ondelete="CASCADE"), index=True
    )
    manifest_member_id: Mapped[int] = mapped_column(
        ForeignKey("download_manifest_members.id", ondelete="RESTRICT"), nullable=False
    )
    manifest_member_public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    expected_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expected_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[DownloadTransferItemStatus] = mapped_column(
        Enum(
            DownloadTransferItemStatus,
            native_enum=False,
            create_constraint=True,
            length=24,
            name="downloadtransferitemstatus",
            values_callable=lambda values: [value.value for value in values],
        ),
        default=DownloadTransferItemStatus.QUEUED,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    session: Mapped[DownloadTransferSession] = relationship(back_populates="items")
    events: Mapped[list[DownloadTransferEvent]] = relationship(
        back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )


class DownloadTransferEvent(BaseModel):
    __tablename__ = "download_transfer_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "ordinal", name="uq_download_transfer_event_ordinal"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("download_transfer_sessions.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("download_transfer_items.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    observed_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    session: Mapped[DownloadTransferSession] = relationship(back_populates="events")
    item: Mapped[DownloadTransferItem] = relationship(back_populates="events")
