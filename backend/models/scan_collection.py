"""Explicit operator collection decisions bound to immutable mapping paths."""

from sqlalchemy import JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel


class ScanCollectionFolder(BaseModel):
    __tablename__ = "scan_collection_folders"
    __table_args__ = (
        UniqueConstraint(
            "mapping_id",
            "binding_digest",
            "path_digest",
            name="uq_scan_collection_binding_path",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mapping_id: Mapped[int] = mapped_column(Integer)
    storage_root_id: Mapped[int] = mapped_column(Integer)
    mapping_relative_path: Mapped[str] = mapped_column(String(700))
    binding_digest: Mapped[str] = mapped_column(String(64))
    parent_relative_path: Mapped[str] = mapped_column(String(700))
    path_digest: Mapped[str] = mapped_column(String(64))
    parent_rom_id: Mapped[int] = mapped_column(Integer)
    parent_incarnation: Mapped[str] = mapped_column(String(32))
    selected_child_relative_path: Mapped[str] = mapped_column(String(700))
    actor_id: Mapped[int] = mapped_column(Integer)
    operation_id: Mapped[str] = mapped_column(String(36))
    audit: Mapped[dict] = mapped_column(JSON, default=dict)
