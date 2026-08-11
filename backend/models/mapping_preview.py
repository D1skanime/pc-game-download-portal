from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class MappingPreview(BaseModel):
    __tablename__ = "mapping_previews"
    __table_args__ = (
        Index("ix_mapping_previews_mapping_id", "mapping_id", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("platform_storage_mappings.id", ondelete="CASCADE")
    )
    state: Mapped[str] = mapped_column(String(16))
    observed_files: Mapped[int] = mapped_column(Integer, default=0)
    observed_directories: Mapped[int] = mapped_column(Integer, default=0)
    observed_bytes: Mapped[int] = mapped_column(Integer, default=0)
    lower_bound: Mapped[bool] = mapped_column(Boolean, default=False)
    budget_reason: Mapped[str | None] = mapped_column(String(32), default=None)
    problems: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    observed_revision: Mapped[int] = mapped_column(Integer)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
