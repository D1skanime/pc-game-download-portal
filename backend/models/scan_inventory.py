"""Compact advisory inventory and provider retry state."""

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class InventoryIdentity:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    identity_digest: Mapped[str] = mapped_column(String(64))
    mapping_id: Mapped[int] = mapped_column(Integer)
    storage_root_id: Mapped[int] = mapped_column(Integer)
    mapping_relative_path: Mapped[str] = mapped_column(String(700))
    mapping_revision: Mapped[int] = mapped_column(Integer)
    binding_digest: Mapped[str] = mapped_column(String(64))
    game_relative_path: Mapped[str] = mapped_column(String(700))
    path_digest: Mapped[str] = mapped_column(String(64))
    rom_id: Mapped[int] = mapped_column(Integer)
    rom_incarnation: Mapped[str] = mapped_column(String(32))
    inventory_version: Mapped[int] = mapped_column(Integer)
    classifier_version: Mapped[int] = mapped_column(Integer)
    policy_fingerprint: Mapped[str] = mapped_column(String(64))


class ScanInventoryBaseline(InventoryIdentity, BaseModel):
    __tablename__ = "scan_inventory_baselines"
    __table_args__ = (
        UniqueConstraint("identity_digest", name="uq_scan_inventory_identity"),
    )
    inventory_digest: Mapped[str] = mapped_column(String(64))
    entry_count: Mapped[int] = mapped_column(Integer)
    validated_at: Mapped[datetime] = mapped_column()
    completed_at: Mapped[datetime] = mapped_column()
    reusable: Mapped[bool] = mapped_column(Boolean, default=True)


class ScanMetadataRetry(InventoryIdentity, BaseModel):
    __tablename__ = "scan_metadata_retries"
    __table_args__ = (
        UniqueConstraint("identity_digest", name="uq_scan_metadata_retry_identity"),
    )
    provider: Mapped[str] = mapped_column(String(32))
    normalized_query: Mapped[str] = mapped_column(String(700))
    locale: Mapped[str] = mapped_column(String(32))
    config_fingerprint: Mapped[str] = mapped_column(String(64))
    next_eligible_at: Mapped[datetime | None] = mapped_column(default=None)
    last_invoked_at: Mapped[datetime | None] = mapped_column(default=None)
    last_request_at: Mapped[datetime | None] = mapped_column(default=None)
    no_match_streak: Mapped[int] = mapped_column(Integer, default=0)
    transient_streak: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str] = mapped_column(String(32))
    config_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
