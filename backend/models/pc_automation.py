import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class PcAutomationTargetKind(enum.StrEnum):
    PARENT = "parent"
    COMPONENT = "component"


class PcAutomationQueueState(enum.StrEnum):
    PENDING = "pending"
    SKIPPED = "skipped"
    RETRYABLE_FAILURE = "retryable_failure"
    CLAIMED = "claimed"


class PcAutomationOutcome(enum.StrEnum):
    CREATED = "created"
    UNCHANGED = "unchanged"
    REOPENED = "reopened"
    SKIPPED = "skipped"
    REQUEUED = "requeued"
    RETRY_SCHEDULED = "retry_scheduled"
    CLAIMED = "claimed"
    MISSING_TARGET = "missing_target"
    PROTECTED_TARGET = "protected_target"
    STALE_TARGET = "stale_target"
    CONFLICT = "conflict"


class PcAutomationQueue(BaseModel):
    """Bounded provider evidence awaiting an operator's PC metadata decision."""

    __tablename__ = "pc_automation_queue"

    __table_args__ = (
        Index("uq_pc_automation_queue_target", "target_identity", unique=True),
        Index(
            "idx_pc_automation_queue_pending",
            "state",
            "next_retry_at",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_identity: Mapped[str] = mapped_column(String(length=80), nullable=False)
    target_kind: Mapped[PcAutomationTargetKind] = mapped_column(
        Enum(
            PcAutomationTargetKind,
            values_callable=lambda kinds: [kind.value for kind in kinds],
            name="pcautomationtargetkind",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    rom_id: Mapped[int] = mapped_column(
        ForeignKey("roms.id", ondelete="CASCADE"), nullable=False
    )
    component_id: Mapped[int | None] = mapped_column(
        ForeignKey("rom_components.id", ondelete="CASCADE"), nullable=True
    )
    target_incarnation: Mapped[str] = mapped_column(String(length=64), nullable=False)
    target_updated_at: Mapped[datetime] = mapped_column(nullable=False)
    normalized_query: Mapped[str] = mapped_column(String(length=350), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(
        String(length=255), nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    provider_candidate_id: Mapped[str | None] = mapped_column(
        String(length=255), nullable=True
    )
    candidate_title: Mapped[str | None] = mapped_column(
        String(length=350), nullable=True
    )
    candidate_cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    state: Mapped[PcAutomationQueueState] = mapped_column(
        Enum(
            PcAutomationQueueState,
            values_callable=lambda states: [state.value for state in states],
            name="pcautomationqueuestate",
            native_enum=False,
            create_constraint=True,
        ),
        default=PcAutomationQueueState.PENDING,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(nullable=True)
    skipped_at: Mapped[datetime | None] = mapped_column(nullable=True)
