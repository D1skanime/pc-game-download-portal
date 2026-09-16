from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from models.base import BaseModel

if TYPE_CHECKING:
    from models.rom import Rom, RomComponent, RomComponentManifestMember
    from models.user import User


class DownloadManifestStatus(enum.StrEnum):
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SOURCE_CHANGED = "source_changed"


class DownloadManifest(BaseModel):
    __tablename__ = "download_manifests"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[DownloadManifestStatus] = mapped_column(
        Enum(
            DownloadManifestStatus,
            native_enum=False,
            create_constraint=True,
            length=20,
            name="downloadmanifeststatus",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=DownloadManifestStatus.VALID,
        nullable=False,
    )

    user: Mapped[User] = relationship(lazy="joined")
    rom: Mapped[Rom] = relationship(lazy="joined")
    components: Mapped[list[DownloadManifestComponent]] = relationship(
        back_populates="manifest",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DownloadManifestComponent(BaseModel):
    __tablename__ = "download_manifest_components"
    __table_args__ = (
        UniqueConstraint(
            "manifest_id",
            "component_id",
            name="uq_download_manifest_components_manifest_component",
        ),
        UniqueConstraint(
            "id",
            "component_id",
            name="uq_download_manifest_components_id_component",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manifest_id: Mapped[str] = mapped_column(
        ForeignKey("download_manifests.id", ondelete="CASCADE")
    )
    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="RESTRICT")
    )

    manifest: Mapped[DownloadManifest] = relationship(back_populates="components")
    component: Mapped[RomComponent] = relationship(lazy="joined")
    members: Mapped[list[DownloadManifestMember]] = relationship(
        back_populates="component",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="DownloadManifestMember.download_manifest_component_id",
    )


class DownloadManifestMember(BaseModel):
    __tablename__ = "download_manifest_members"
    __table_args__ = (
        UniqueConstraint(
            "download_manifest_component_id",
            "manifest_member_id",
            name="uq_download_manifest_members_manifest_member",
        ),
        UniqueConstraint(
            "download_manifest_component_id",
            "destination",
            name="uq_download_manifest_members_manifest_destination",
        ),
        CheckConstraint(
            "length(snapshot) >= 2", name="ck_download_manifest_members_snapshot"
        ),
        UniqueConstraint("public_id", name="uq_download_manifest_members_public_id"),
        ForeignKeyConstraint(
            ["download_manifest_component_id", "component_id"],
            [
                "download_manifest_components.id",
                "download_manifest_components.component_id",
            ],
            name="fk_download_manifest_members_selected_component",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["manifest_member_id", "component_id"],
            [
                "rom_component_manifest_members.id",
                "rom_component_manifest_members.component_id",
            ],
            name="fk_download_manifest_members_source_component",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(length=36), default=lambda: str(uuid.uuid4()), nullable=False
    )
    download_manifest_component_id: Mapped[int] = mapped_column(
        ForeignKey("download_manifest_components.id", ondelete="CASCADE")
    )
    manifest_member_id: Mapped[int] = mapped_column(
        ForeignKey("rom_component_manifest_members.id", ondelete="RESTRICT")
    )
    component_id: Mapped[int] = mapped_column(Integer, nullable=False)
    destination: Mapped[str] = mapped_column(String(length=700), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(length=64), nullable=False)
    snapshot: Mapped[str] = mapped_column(String(length=255), nullable=False)
    mtime_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    device: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    inode: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    component: Mapped[DownloadManifestComponent] = relationship(
        back_populates="members",
        foreign_keys=lambda: [DownloadManifestMember.download_manifest_component_id],
    )
    manifest_member: Mapped[RomComponentManifestMember] = relationship(
        lazy="joined",
        foreign_keys=lambda: [DownloadManifestMember.manifest_member_id],
    )

    @validates("sha256")
    def validate_sha256(self, _key: str, value: str) -> str:
        if len(value) != 64 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise ValueError(
                "sha256 must be a lowercase 64-character hexadecimal digest"
            )
        return value

    @validates("snapshot")
    def validate_snapshot(self, _key: str, value: str) -> str:
        if len(value) < 2 or not (value.startswith('"') and value.endswith('"')):
            raise ValueError("snapshot must be a quoted strong validator")
        return value


@event.listens_for(DownloadManifestMember, "before_insert")
def set_download_manifest_member_component_id(
    _mapper, _connection, member: DownloadManifestMember
) -> None:
    if member.component_id is None and member.component is not None:
        member.component_id = member.component.component_id
