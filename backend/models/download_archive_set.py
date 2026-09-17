from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import FILE_NAME_MAX_LENGTH, BaseModel

if TYPE_CHECKING:
    from models.rom import Rom, RomComponent, RomComponentManifestMember


class DownloadArchiveSet(BaseModel):
    """A named, ROM-scoped selection policy for browser downloads."""

    __tablename__ = "download_archive_sets"
    __table_args__ = (
        UniqueConstraint("rom_id", "name", name="uq_download_archive_sets_rom_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(
        String(length=FILE_NAME_MAX_LENGTH), nullable=False
    )

    rom: Mapped[Rom] = relationship(back_populates="download_archive_sets")
    members: Mapped[list[DownloadArchiveSetMember]] = relationship(
        back_populates="archive_set",
        cascade="all, delete-orphan",
        order_by="DownloadArchiveSetMember.position",
        lazy="selectin",
    )


class DownloadArchiveSetMember(BaseModel):
    """One exact component/member identity in an archive-set policy."""

    __tablename__ = "download_archive_set_members"
    __table_args__ = (
        UniqueConstraint(
            "archive_set_id",
            "component_id",
            "manifest_member_id",
            name="uq_download_archive_set_members_identity",
        ),
        UniqueConstraint(
            "archive_set_id",
            "position",
            name="uq_download_archive_set_members_position",
        ),
        ForeignKeyConstraint(
            ["manifest_member_id", "component_id"],
            [
                "rom_component_manifest_members.id",
                "rom_component_manifest_members.component_id",
            ],
            name="fk_download_archive_set_members_member_component",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    archive_set_id: Mapped[int] = mapped_column(
        ForeignKey("download_archive_sets.id", ondelete="CASCADE")
    )
    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="RESTRICT")
    )
    manifest_member_id: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    archive_set: Mapped[DownloadArchiveSet] = relationship(back_populates="members")
    component: Mapped[RomComponent] = relationship(lazy="joined")
    manifest_member: Mapped[RomComponentManifestMember] = relationship(lazy="joined")
