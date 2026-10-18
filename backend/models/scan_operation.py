"""Durable scan intent, execution fence and bounded per-item results."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
from sqlalchemy.dialects.mysql import TIMESTAMP as MYSQL_TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from handler.scan_operation_state import STATES
from models.base import BaseModel, utc_now

_PRECISE_TIME = DateTime().with_variant(MYSQL_DATETIME(fsp=6), "mysql", "mariadb")
_PRECISE_TIMESTAMP = TIMESTAMP(timezone=True).with_variant(
    MYSQL_TIMESTAMP(fsp=6), "mysql", "mariadb"
)


class ScanTimestamps:
    created_at: Mapped[datetime] = mapped_column(_PRECISE_TIMESTAMP, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        _PRECISE_TIMESTAMP, default=utc_now, onupdate=utc_now
    )


class ScanOperation(ScanTimestamps, BaseModel):
    __tablename__ = "scan_operations"
    __table_args__ = (
        UniqueConstraint("actor_id", "request_key", name="uq_scan_operation_actor_key"),
        CheckConstraint(
            "state IN (" + ", ".join(repr(s) for s in STATES) + ")",
            name="ck_scan_operation_state",
        ),
        CheckConstraint("version >= 1", name="ck_scan_operation_version"),
        Index("ix_scan_operation_dispatch", "dispatch_due", "dispatch_claim_until"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    request_key: Mapped[str] = mapped_column(String(96))
    payload_digest: Mapped[str] = mapped_column(String(64))
    command: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(24), default="accepted")
    version: Mapped[int] = mapped_column(Integer, default=1)
    attempt_id: Mapped[str | None] = mapped_column(String(36), default=None)
    lease_owner: Mapped[str | None] = mapped_column(String(64), default=None)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        _PRECISE_TIME, default=None
    )
    dispatch_due: Mapped[datetime | None] = mapped_column(_PRECISE_TIME, default=None)
    dispatch_claim_until: Mapped[datetime | None] = mapped_column(
        _PRECISE_TIME, default=None
    )
    dispatch_owner: Mapped[str | None] = mapped_column(String(64), default=None)
    rq_job_id: Mapped[str] = mapped_column(String(100), unique=True)
    intentional_cancel: Mapped[bool] = mapped_column(Boolean, default=False)
    cause_code: Mapped[str | None] = mapped_column(String(64), default=None)
    next_action: Mapped[str | None] = mapped_column(String(64), default=None)
    scan_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    mutation_keys: Mapped[dict] = mapped_column(JSON, default=dict)


class ScanOperationItem(ScanTimestamps, BaseModel):
    __tablename__ = "scan_operation_items"
    __table_args__ = (
        UniqueConstraint(
            "operation_id", "target_key", "provider", name="uq_scan_operation_item"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    operation_id: Mapped[str] = mapped_column(
        ForeignKey("scan_operations.id", ondelete="CASCADE")
    )
    target_key: Mapped[str] = mapped_column(String(96))
    mapping_id: Mapped[int] = mapped_column(ForeignKey("platform_storage_mappings.id"))
    expected_revision: Mapped[int] = mapped_column(Integer)
    relative_path: Mapped[str] = mapped_column(String(700))
    provider: Mapped[str] = mapped_column(String(32))
    outcome: Mapped[str] = mapped_column(String(24))
    cause_code: Mapped[str | None] = mapped_column(String(64), default=None)
    attempt_id: Mapped[str] = mapped_column(String(36))
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    source_evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class ScanExecutionSlot(ScanTimestamps, BaseModel):
    __tablename__ = "scan_execution_slot"
    __table_args__ = (CheckConstraint("id = 1", name="ck_scan_execution_singleton"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    active_operation_id: Mapped[str | None] = mapped_column(
        ForeignKey("scan_operations.id", ondelete="SET NULL"), default=None
    )
    version: Mapped[int] = mapped_column(Integer, default=0)
