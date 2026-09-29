from __future__ import annotations

import copy
import enum
import re
import secrets
from collections.abc import Mapping, Sequence
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypedDict

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    and_,
    event,
    func,
)
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
    relationship,
    validates,
)
from sqlalchemy.orm.attributes import InstrumentedAttribute

from config import FRONTEND_RESOURCES_PATH
from models.base import (
    FILE_EXTENSION_MAX_LENGTH,
    FILE_NAME_MAX_LENGTH,
    FILE_PATH_MAX_LENGTH,
    BaseModel,
    compute_file_name_parts,
)
from utils.database import CustomJSON
from utils.filesystem import sanitize_filename

# Max length of the precomputed natural-sort key column.
NAME_SORT_KEY_MAX_LENGTH = 500
INCARNATION_TOKEN_LENGTH = 32
# Max length for free-text audio tag columns (title/artist/album).
AUDIO_TAG_MAX_LENGTH = 512
PC_COMPONENT_PATH_MAX_LENGTH = 700
OWNED_MEDIA_PATH_MAX_LENGTH = 700
OWNED_MEDIA_PROVIDER_ID_MAX_LENGTH = 450
OWNED_MEDIA_DISPLAY_LABEL_MAX_LENGTH = 255
ARTICLE_PREFIX_RE = re.compile(r"^(the|a|an)\s+")
DIGIT_RUN_RE = re.compile(r"\d+")


def compute_name_sort_key(name: str | None) -> str:
    """Precompute the natural-sort key stored in `Rom.name_sort_key`"""
    value = (name or "").lower()
    value = ARTICLE_PREFIX_RE.sub("", value).strip()
    value = DIGIT_RUN_RE.sub(lambda m: m.group(0).zfill(12), value)
    return value[:NAME_SORT_KEY_MAX_LENGTH]


if TYPE_CHECKING:
    from models.assets import Save, Screenshot, State
    from models.collection import Collection
    from models.download_archive_set import DownloadArchiveSet
    from models.platform import Platform
    from models.user import User


class RomFileCategory(enum.StrEnum):
    GAME = "game"
    DLC = "dlc"
    HACK = "hack"
    MANUAL = "manual"
    PATCH = "patch"
    UPDATE = "update"
    MOD = "mod"
    DEMO = "demo"
    TRANSLATION = "translation"
    PROTOTYPE = "prototype"
    CHEAT = "cheat"
    SOUNDTRACK = "soundtrack"
    SCREENSHOT = "screenshot"


class RomComponentKind(enum.StrEnum):
    BASE = "base"
    UPDATE = "update"
    DLC = "dlc"
    HOTFIX = "hotfix"
    LANGUAGE_PACK = "language_pack"
    EXTRA = "extra"
    UNRESOLVED = "unresolved"


class RomComponentLocalMediaRole(enum.StrEnum):
    COVER = "cover"
    BACKGROUND = "background"
    GALLERY = "gallery"


class RomComponentOwnedMediaRole(enum.StrEnum):
    COVER = "cover"
    BACKGROUND = "background"
    GALLERY = "gallery"
    SCREENSHOT = "screenshot"
    ARTWORK = "artwork"
    SOUNDTRACK = "soundtrack"
    VIDEO = "video"


class RomComponentOwnedMediaOrigin(enum.StrEnum):
    UPLOAD = "upload"
    PROVIDER = "provider"


class RomOwnedMediaOrigin(enum.StrEnum):
    UPLOAD = "upload"
    PROVIDER = "provider"


class RomOwnedMediaRole(enum.StrEnum):
    SCREENSHOT = "screenshot"
    ARTWORK = "artwork"
    SOUNDTRACK = "soundtrack"


class RomOwnedMediaState(enum.StrEnum):
    ACTIVE = "active"
    TOMBSTONED = "tombstoned"


class RomOwnedMediaSurface(enum.StrEnum):
    OVERVIEW = "overview"
    BACKGROUND = "background"
    SOUNDTRACK = "soundtrack"


def derive_owned_media_display_label(
    filename: str, *, reject_unsafe_input: bool = False
) -> str:
    """Return a bounded, filename-only label for owned media intake."""
    if not isinstance(filename, str) or any(ord(char) < 32 for char in filename):
        raise ValueError("display label must not contain control characters")
    if reject_unsafe_input and (
        "/" in filename
        or "\\" in filename
        or "://" in filename
        or filename.startswith(("/", "\\"))
    ):
        raise ValueError("display label must be a filename, not a path or URL")
    filename = filename.replace("\\", "/")
    return sanitize_filename(filename)[:OWNED_MEDIA_DISPLAY_LABEL_MAX_LENGTH]


def validate_owned_media_display_label(label: str) -> str:
    """Reject catalog labels that are not already safe filename-only values."""
    if (
        not isinstance(label, str)
        or not label
        or len(label) > OWNED_MEDIA_DISPLAY_LABEL_MAX_LENGTH
        or any(ord(char) < 32 for char in label)
        or "/" in label
        or "\\" in label
        or "://" in label
    ):
        raise ValueError("display label must be a bounded filename-only value")
    return label


class SiblingRom(BaseModel):
    __tablename__ = "sibling_roms"

    rom_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sibling_rom_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    __table_args__ = (
        UniqueConstraint("rom_id", "sibling_rom_id", name="unique_sibling_roms"),
    )


class RomArchiveMember(TypedDict):
    name: str
    size: int
    crc_hash: str
    md5_hash: str
    sha1_hash: str


class RomFile(BaseModel):
    __tablename__ = "rom_files"

    __table_args__ = (
        Index("uq_rom_files_incarnation_token", "incarnation_token", unique=True),
        Index("idx_rom_files_rom_id", "rom_id"),
        # Searching the gallery by a hash digest
        Index("idx_rom_files_crc_hash", "crc_hash"),
        Index("idx_rom_files_md5_hash", "md5_hash"),
        Index("idx_rom_files_sha1_hash", "sha1_hash"),
        Index("idx_rom_files_ra_hash", "ra_hash"),
        Index("idx_rom_files_chd_sha1_hash", "chd_sha1_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incarnation_token: Mapped[str] = mapped_column(
        String(length=INCARNATION_TOKEN_LENGTH), nullable=False
    )
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(length=FILE_NAME_MAX_LENGTH))
    file_path: Mapped[str] = mapped_column(String(length=FILE_PATH_MAX_LENGTH))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger(), default=0)
    last_modified: Mapped[float | None] = mapped_column(default=None)
    crc_hash: Mapped[str | None] = mapped_column(String(100))
    md5_hash: Mapped[str | None] = mapped_column(String(100))
    sha1_hash: Mapped[str | None] = mapped_column(String(100))
    ra_hash: Mapped[str | None] = mapped_column(String(100))
    chd_sha1_hash: Mapped[str | None] = mapped_column(String(100))
    archive_members: Mapped[list[RomArchiveMember] | None] = mapped_column(
        CustomJSON(), default=None, nullable=True
    )
    category: Mapped[RomFileCategory | None] = mapped_column(
        Enum(RomFileCategory), default=None
    )
    missing_from_fs: Mapped[bool] = mapped_column(default=False, nullable=False)

    rom: Mapped[Rom] = relationship(back_populates="files")
    track_meta: Mapped[TrackMeta | None] = relationship(
        back_populates="rom_file",
        uselist=False,
        cascade="all, delete-orphan",
    )
    local_background_audio: Mapped[list[RomLocalBackgroundAudio]] = relationship(
        lazy="raise",
        back_populates="rom_file",
        cascade="all, delete-orphan",
    )

    @cached_property
    def full_path(self) -> str:
        return f"{self.file_path}/{self.file_name}"

    @cached_property
    def file_name_no_tags(self) -> str:
        from handler.filesystem import fs_rom_handler

        return fs_rom_handler.get_file_name_with_no_tags(self.file_name)

    @cached_property
    def file_name_no_ext(self) -> str:
        from handler.filesystem import fs_rom_handler

        return fs_rom_handler.get_file_name_with_no_extension(self.file_name)

    @cached_property
    def file_extension(self) -> str:
        from handler.filesystem import fs_rom_handler

        return fs_rom_handler.parse_file_extension(self.file_name)

    @cached_property
    def is_nested(self) -> bool:
        return self.file_path.count("/") > 1

    @cached_property
    def is_top_level(self) -> bool:
        # File is the same as the rom's full path, or nested file in the rom's directory
        return self.rom.full_path == (
            self.file_path if self.is_nested else self.full_path
        )

    def file_name_for_download(self, hidden_folder: bool = False) -> str:
        # This needs a trailing slash in the path to work!
        return self.full_path.replace(
            f"{self.rom.full_path}/", ".hidden/" if hidden_folder else ""
        )

    def __repr__(self) -> str:
        return f"{self.file_name} ({self.id} -> {self.rom_id})"


class RomComponent(BaseModel):
    __tablename__ = "rom_components"

    __table_args__ = (
        UniqueConstraint(
            "rom_id", "relative_path", name="uq_rom_components_rom_relative_path"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    relative_path: Mapped[str] = mapped_column(
        String(length=PC_COMPONENT_PATH_MAX_LENGTH)
    )
    kind: Mapped[RomComponentKind] = mapped_column(
        Enum(
            RomComponentKind,
            values_callable=lambda kinds: [kind.value for kind in kinds],
            name="romcomponentkind",
        )
    )

    rom: Mapped[Rom] = relationship(back_populates="components")
    manifest_members: Mapped[list[RomComponentManifestMember]] = relationship(
        lazy="raise",
        back_populates="component",
        cascade="all, delete-orphan",
        order_by="RomComponentManifestMember.relative_path",
    )
    component_metadata: Mapped[RomComponentMetadata | None] = relationship(
        lazy="raise",
        back_populates="component",
        cascade="all, delete-orphan",
        uselist=False,
    )
    local_media: Mapped[list[RomComponentLocalMedia]] = relationship(
        lazy="raise",
        back_populates="component",
        cascade="all, delete-orphan",
        order_by="RomComponentLocalMedia.id",
    )
    owned_media: Mapped[list[RomComponentOwnedMedia]] = relationship(
        lazy="raise",
        back_populates="component",
        cascade="all, delete-orphan",
        order_by="RomComponentOwnedMedia.id",
    )
    notes: Mapped[list[RomComponentNote]] = relationship(
        lazy="raise",
        back_populates="component",
        cascade="all, delete-orphan",
        order_by="RomComponentNote.updated_at.desc()",
    )

    @property
    def available_manifest_members(self) -> list[RomComponentManifestMember]:
        return [
            member for member in self.manifest_members if not member.missing_from_fs
        ]


class RomComponentManifestMember(BaseModel):
    __tablename__ = "rom_component_manifest_members"

    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "relative_path",
            name="uq_rom_component_manifest_members_component_relative_path",
        ),
        UniqueConstraint(
            "id",
            "component_id",
            name="uq_rom_component_manifest_members_id_component",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="CASCADE")
    )
    relative_path: Mapped[str] = mapped_column(
        String(length=PC_COMPONENT_PATH_MAX_LENGTH)
    )
    size_bytes: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    sha256: Mapped[str] = mapped_column(String(length=64), nullable=False)
    missing_from_fs: Mapped[bool] = mapped_column(default=False, nullable=False)

    component: Mapped[RomComponent] = relationship(back_populates="manifest_members")


class RomComponentMetadata(BaseModel):
    __tablename__ = "rom_component_metadata"

    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="CASCADE"), primary_key=True
    )
    igdb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    moby_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    sgdb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    launchbox_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    steam_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    steam_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    name: Mapped[str | None] = mapped_column(String(length=FILE_NAME_MAX_LENGTH))
    summary: Mapped[str | None] = mapped_column(Text())
    metadata_source: Mapped[str | None] = mapped_column(String(length=100))
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=None
    )
    main_developer: Mapped[str | None] = mapped_column(String(length=255), default=None)
    publishers: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=list)
    themes: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=list)
    pc_release_date: Mapped[int | None] = mapped_column(BigInteger(), default=None)

    component: Mapped[RomComponent] = relationship(back_populates="component_metadata")


class RomComponentLocalMedia(BaseModel):
    __tablename__ = "rom_component_local_media"

    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "source_relative_path",
            "role",
            name="uq_rom_component_local_media_source_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="CASCADE")
    )
    source_relative_path: Mapped[str] = mapped_column(
        String(length=PC_COMPONENT_PATH_MAX_LENGTH)
    )
    source_sha256: Mapped[str] = mapped_column(String(length=64))
    owned_path: Mapped[str] = mapped_column(String(length=FILE_PATH_MAX_LENGTH))
    image_type: Mapped[str] = mapped_column(String(length=20))
    role: Mapped[RomComponentLocalMediaRole] = mapped_column(
        Enum(
            RomComponentLocalMediaRole,
            values_callable=lambda roles: [role.value for role in roles],
            name="romcomponentlocalmediarole",
        )
    )

    component: Mapped[RomComponent] = relationship(back_populates="local_media")


class RomComponentOwnedMedia(BaseModel):
    __tablename__ = "rom_component_owned_media"

    __table_args__ = (
        Index("idx_rom_component_owned_media_component", "component_id"),
        Index("idx_rom_component_owned_media_origin", "origin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="CASCADE")
    )
    role: Mapped[RomComponentOwnedMediaRole] = mapped_column(
        Enum(
            RomComponentOwnedMediaRole,
            values_callable=lambda roles: [role.value for role in roles],
            name="romcomponentownedmediarole",
            native_enum=False,
            create_constraint=True,
        )
    )
    mime_type: Mapped[str] = mapped_column(String(length=100))
    owned_path: Mapped[str] = mapped_column(String(length=FILE_PATH_MAX_LENGTH))
    origin: Mapped[RomComponentOwnedMediaOrigin] = mapped_column(
        Enum(
            RomComponentOwnedMediaOrigin,
            values_callable=lambda origins: [origin.value for origin in origins],
            name="romcomponentownedmediaorigin",
            native_enum=False,
            create_constraint=True,
        )
    )
    provider: Mapped[str | None] = mapped_column(String(length=100), default=None)
    provider_media_id: Mapped[str | None] = mapped_column(
        String(length=450), default=None
    )

    component: Mapped[RomComponent] = relationship(back_populates="owned_media")


class RomOwnedMedia(BaseModel):
    __tablename__ = "rom_owned_media"

    __table_args__ = (
        CheckConstraint(
            "state IN ('active', 'tombstoned')", name="ck_rom_owned_media_state"
        ),
        CheckConstraint(
            "owned_path IS NULL OR (owned_path <> '' AND owned_path NOT LIKE '/%' AND owned_path NOT LIKE '%..%')",
            name="ck_rom_owned_media_owned_path_relative",
        ),
        CheckConstraint(
            "display_label <> ''", name="ck_rom_owned_media_display_label_nonempty"
        ),
        UniqueConstraint(
            "rom_id",
            "provider",
            "provider_media_id",
            name="uq_rom_owned_media_provider_identity",
        ),
        Index("idx_rom_owned_media_rom_state", "rom_id", "state"),
        Index("idx_rom_owned_media_origin", "origin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    origin: Mapped[RomOwnedMediaOrigin] = mapped_column(
        Enum(
            RomOwnedMediaOrigin,
            values_callable=lambda origins: [origin.value for origin in origins],
            name="romownedmediaorigin",
            native_enum=False,
            create_constraint=True,
        )
    )
    role: Mapped[RomOwnedMediaRole] = mapped_column(
        Enum(
            RomOwnedMediaRole,
            values_callable=lambda roles: [role.value for role in roles],
            name="romownedmediarole",
            native_enum=False,
            create_constraint=True,
        ),
        default=RomOwnedMediaRole.SCREENSHOT,
    )
    display_label: Mapped[str] = mapped_column(
        String(length=OWNED_MEDIA_DISPLAY_LABEL_MAX_LENGTH), default="Owned media"
    )
    state: Mapped[RomOwnedMediaState] = mapped_column(
        Enum(
            RomOwnedMediaState,
            values_callable=lambda states: [state.value for state in states],
            name="romownedmediastate",
            native_enum=False,
            create_constraint=True,
        ),
        default=RomOwnedMediaState.ACTIVE,
    )
    mime_type: Mapped[str] = mapped_column(String(length=100))
    owned_path: Mapped[str | None] = mapped_column(
        String(length=OWNED_MEDIA_PATH_MAX_LENGTH), default=None
    )
    provider: Mapped[str | None] = mapped_column(String(length=100), default=None)
    provider_media_id: Mapped[str | None] = mapped_column(
        String(length=OWNED_MEDIA_PROVIDER_ID_MAX_LENGTH), default=None
    )

    rom: Mapped[Rom] = relationship(back_populates="owned_media")
    placements: Mapped[list[RomOwnedMediaPlacement]] = relationship(
        lazy="raise",
        back_populates="media",
        cascade="all, delete-orphan",
        order_by="RomOwnedMediaPlacement.position",
    )
    background_audio: Mapped[list[RomOwnedBackgroundAudio]] = relationship(
        lazy="raise",
        back_populates="media",
        cascade="all, delete-orphan",
    )

    @validates("role")
    def validate_role_immutable(
        self, _key: str, role: RomOwnedMediaRole
    ) -> RomOwnedMediaRole:
        if sa_inspect(self).persistent and role != self.role:
            raise ValueError("owned media role is immutable")
        return role

    @validates("display_label")
    def validate_display_label(self, _key: str, label: str) -> str:
        return validate_owned_media_display_label(label)


class RomOwnedMediaPlacement(BaseModel):
    __tablename__ = "rom_owned_media_placements"

    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_rom_owned_media_placements_position"),
        UniqueConstraint(
            "media_id", "surface", name="uq_rom_owned_media_placements_media_surface"
        ),
        UniqueConstraint(
            "rom_id",
            "surface",
            "position",
            name="uq_rom_owned_media_placements_rom_surface_position",
        ),
        Index(
            "idx_rom_owned_media_placements_rom_surface_position",
            "rom_id",
            "surface",
            "position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    media_id: Mapped[int] = mapped_column(
        ForeignKey("rom_owned_media.id", ondelete="CASCADE")
    )
    surface: Mapped[RomOwnedMediaSurface] = mapped_column(
        Enum(
            RomOwnedMediaSurface,
            values_callable=lambda surfaces: [surface.value for surface in surfaces],
            name="romownedmediasurface",
            native_enum=False,
            create_constraint=True,
        )
    )
    position: Mapped[int] = mapped_column(Integer)

    rom: Mapped[Rom] = relationship(back_populates="owned_media_placements")
    media: Mapped[RomOwnedMedia] = relationship(back_populates="placements")


class RomLocalBackgroundAudio(BaseModel):
    __tablename__ = "rom_local_background_audio"

    __table_args__ = (
        UniqueConstraint(
            "rom_id", "rom_file_id", name="uq_rom_local_background_audio_file"
        ),
        Index("idx_rom_local_background_audio_rom", "rom_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    rom_file_id: Mapped[int] = mapped_column(
        ForeignKey("rom_files.id", ondelete="CASCADE")
    )

    rom: Mapped[Rom] = relationship(back_populates="local_background_audio")
    rom_file: Mapped[RomFile] = relationship(back_populates="local_background_audio")


class RomOwnedBackgroundAudio(BaseModel):
    __tablename__ = "rom_owned_background_audio"

    __table_args__ = (
        UniqueConstraint(
            "rom_id", "media_id", name="uq_rom_owned_background_audio_media"
        ),
        Index("idx_rom_owned_background_audio_rom", "rom_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    media_id: Mapped[int] = mapped_column(
        ForeignKey("rom_owned_media.id", ondelete="CASCADE")
    )

    rom: Mapped[Rom] = relationship(back_populates="owned_background_audio")
    media: Mapped[RomOwnedMedia] = relationship(back_populates="background_audio")


class RomComponentNote(BaseModel):
    __tablename__ = "rom_component_notes"

    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "user_id",
            "title",
            name="uq_rom_component_notes_component_user_title",
        ),
        Index("idx_rom_component_notes_public", "is_public"),
        Index("idx_rom_component_notes_component_user", "component_id", "user_id"),
        Index("idx_rom_component_notes_title", "title"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(length=400))
    content: Mapped[str] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(default=False)
    tags: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=list)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    component: Mapped[RomComponent] = relationship(back_populates="notes")
    user: Mapped[User] = relationship(lazy="joined")


class TrackMeta(BaseModel):
    __tablename__ = "track_meta"

    __table_args__ = (
        Index("idx_track_meta_rom_id", "rom_id"),
        Index("idx_track_meta_duration", "duration_seconds"),
        Index("idx_track_meta_year", "year"),
        Index("idx_track_meta_artist", "artist"),
        Index("idx_track_meta_album", "album"),
    )

    rom_file_id: Mapped[int] = mapped_column(
        ForeignKey("rom_files.id", ondelete="CASCADE"), primary_key=True
    )
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(
        String(length=AUDIO_TAG_MAX_LENGTH), default=None
    )
    artist: Mapped[str | None] = mapped_column(
        String(length=AUDIO_TAG_MAX_LENGTH), default=None
    )
    album: Mapped[str | None] = mapped_column(
        String(length=AUDIO_TAG_MAX_LENGTH), default=None
    )
    genre: Mapped[str | None] = mapped_column(String(length=255), default=None)
    year: Mapped[int | None] = mapped_column(SmallInteger(), default=None)
    track: Mapped[int | None] = mapped_column(SmallInteger(), default=None)
    disc: Mapped[int | None] = mapped_column(SmallInteger(), default=None)
    duration_seconds: Mapped[float | None] = mapped_column(Float(), default=None)
    has_embedded_cover: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    cover_path: Mapped[str | None] = mapped_column(String(length=1024), default=None)

    rom_file: Mapped[RomFile] = relationship(back_populates="track_meta")


class RomMetadata(BaseModel):
    __tablename__ = "roms_metadata"

    rom_id: Mapped[int] = mapped_column(
        ForeignKey("roms.id", ondelete="CASCADE"), primary_key=True
    )

    genres: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    franchises: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    collections: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    companies: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    main_developer: Mapped[str | None] = mapped_column(String(length=255), default=None)
    publishers: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=list)
    themes: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=list)
    game_modes: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    age_ratings: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    player_count: Mapped[str | None] = mapped_column(String(length=100), default="1")
    first_release_date: Mapped[int | None] = mapped_column(BigInteger(), default=None)
    pc_release_date: Mapped[int | None] = mapped_column(BigInteger(), default=None)
    average_rating: Mapped[float | None] = mapped_column(default=None)

    rom: Mapped[Rom] = relationship(lazy="joined", back_populates="metadatum")


class RomFacets(BaseModel):
    """Narrow mirror of the per-ROM values that back the filter dropdowns.

    The same values live on `roms` (as STORED generated columns, plus the
    region/language/tag columns), but those rows also carry the raw provider
    metadata blobs, so aggregating them reads the whole multi-gigabyte table.
    This table holds a few MB of the same data and is kept in sync by triggers
    on `roms`, so no write path has to remember to update it.
    """

    __tablename__ = "roms_facets"

    __table_args__ = (Index("idx_roms_facets_platform_id", "platform_id"),)

    rom_id: Mapped[int] = mapped_column(
        ForeignKey("roms.id", ondelete="CASCADE"), primary_key=True
    )
    platform_id: Mapped[int] = mapped_column(Integer(), nullable=False)

    genres: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    franchises: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    collections: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    companies: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    game_modes: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    age_ratings: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    player_count: Mapped[str | None] = mapped_column(String(length=100), default="1")
    regions: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    languages: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    tags: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])

    # Provider match ids, mirrored so the Server Stats coverage breakdown counts
    # them here instead of scanning `roms`. A populated column means a match.
    igdb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    ss_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    moby_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    launchbox_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    ra_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    hasheous_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    tgdb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    flashpoint_id: Mapped[str | None] = mapped_column(String(length=100), default=None)
    hltb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    gamelist_id: Mapped[str | None] = mapped_column(String(length=100), default=None)
    libretro_id: Mapped[str | None] = mapped_column(String(length=64), default=None)
    steam_id: Mapped[int | None] = mapped_column(Integer(), default=None)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class Rom(BaseModel):
    __tablename__ = "roms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    igdb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    sgdb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    moby_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    ss_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    ra_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    launchbox_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    hasheous_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    tgdb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    flashpoint_id: Mapped[str | None] = mapped_column(String(length=100), default=None)
    hltb_id: Mapped[int | None] = mapped_column(Integer(), default=None)
    gamelist_id: Mapped[str | None] = mapped_column(String(length=100), default=None)
    libretro_id: Mapped[str | None] = mapped_column(String(length=64), default=None)
    steam_id: Mapped[int | None] = mapped_column(Integer(), default=None)

    __table_args__ = (
        Index("uq_roms_incarnation_token", "incarnation_token", unique=True),
        # Enforce unique fs name per platform to avoid duplicates
        Index("idx_roms_platform_id_fs_name", "platform_id", "fs_name", unique=True),
        # Covers the sibling_roms view self-join and the group_by_meta_id dedup
        # window. Both read only these columns, so the index has to carry every
        # one of them: a single missing column (flashpoint_id or fs_name_no_ext,
        # the window's partition tail and sort tiebreaker) drops the plan to a
        # full scan of the wide roms row, JSON metadata blobs included.
        Index(
            "idx_roms_sibling_cover",
            "platform_id",
            "igdb_id",
            "moby_id",
            "ss_id",
            "launchbox_id",
            "ra_id",
            "hasheous_id",
            "tgdb_id",
            "flashpoint_id",
            "fs_name_no_ext",
            "id",
        ),
        Index("idx_roms_platform_fs_size", "platform_id", "fs_size_bytes"),
        Index("idx_roms_missing_from_fs", "missing_from_fs", "name_sort_key"),
        Index("idx_roms_name", "name"),
        Index("idx_roms_name_sort_key", "name_sort_key"),
        Index("idx_roms_igdb_id", "igdb_id"),
        Index("idx_roms_moby_id", "moby_id"),
        Index("idx_roms_ss_id", "ss_id"),
        Index("idx_roms_ra_id", "ra_id"),
        Index("idx_roms_sgdb_id", "sgdb_id"),
        Index("idx_roms_launchbox_id", "launchbox_id"),
        Index("idx_roms_hasheous_id", "hasheous_id"),
        Index("idx_roms_tgdb_id", "tgdb_id"),
        Index("idx_roms_flashpoint_id", "flashpoint_id"),
        Index("idx_roms_hltb_id", "hltb_id"),
        Index("idx_roms_gamelist_id", "gamelist_id"),
        Index("idx_roms_libretro_id", "libretro_id"),
        # Searching the gallery by a hash digest
        Index("idx_roms_crc_hash", "crc_hash"),
        Index("idx_roms_md5_hash", "md5_hash"),
        Index("idx_roms_sha1_hash", "sha1_hash"),
        Index("idx_roms_ra_hash", "ra_hash"),
    )

    fs_name: Mapped[str] = mapped_column(String(length=FILE_NAME_MAX_LENGTH))
    incarnation_token: Mapped[str] = mapped_column(
        String(length=INCARNATION_TOKEN_LENGTH), nullable=False
    )
    fs_name_no_tags: Mapped[str] = mapped_column(String(length=FILE_NAME_MAX_LENGTH))
    fs_name_no_ext: Mapped[str] = mapped_column(String(length=FILE_NAME_MAX_LENGTH))
    fs_extension: Mapped[str] = mapped_column(String(length=FILE_EXTENSION_MAX_LENGTH))
    fs_path: Mapped[str] = mapped_column(String(length=FILE_PATH_MAX_LENGTH))
    fs_size_bytes: Mapped[int] = mapped_column(BigInteger(), default=0)

    name: Mapped[str | None] = mapped_column(String(length=350))
    name_sort_key: Mapped[str | None] = mapped_column(
        String(length=NAME_SORT_KEY_MAX_LENGTH), default=None
    )
    slug: Mapped[str | None] = mapped_column(String(length=400))
    summary: Mapped[str | None] = mapped_column(Text)
    igdb_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    moby_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    steam_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    ss_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    ra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    launchbox_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    hasheous_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    flashpoint_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    hltb_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    gamelist_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )
    manual_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        CustomJSON(), default=dict
    )

    path_cover_s: Mapped[str | None] = mapped_column(Text, default="")
    path_cover_l: Mapped[str | None] = mapped_column(Text, default="")
    url_cover: Mapped[str | None] = mapped_column(
        Text, default="", doc="URL to cover image stored in IGDB"
    )

    path_manual: Mapped[str | None] = mapped_column(Text, default="")
    url_manual: Mapped[str | None] = mapped_column(
        Text, default="", doc="URL to manual stored in ScreenScraper"
    )

    path_screenshots: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    url_screenshots: Mapped[list[str] | None] = mapped_column(
        CustomJSON(), default=[], doc="URLs to screenshots stored in IGDB"
    )

    revision: Mapped[str | None] = mapped_column(String(length=100))
    version: Mapped[str | None] = mapped_column(String(length=100))
    regions: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    languages: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])
    tags: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=[])

    crc_hash: Mapped[str | None] = mapped_column(String(length=100))
    md5_hash: Mapped[str | None] = mapped_column(String(length=100))
    sha1_hash: Mapped[str | None] = mapped_column(String(length=100))
    ra_hash: Mapped[str | None] = mapped_column(String(length=100))

    missing_from_fs: Mapped[bool] = mapped_column(default=False, nullable=False)

    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="CASCADE")
    )

    platform: Mapped[Platform] = relationship(lazy="joined", back_populates="roms")
    sibling_roms: Mapped[list[Rom]] = relationship(
        secondary="sibling_roms",
        primaryjoin="Rom.id == SiblingRom.rom_id",
        secondaryjoin="Rom.id == SiblingRom.sibling_rom_id",
        lazy="raise",
    )
    files: Mapped[list[RomFile]] = relationship(lazy="raise", back_populates="rom")
    components: Mapped[list[RomComponent]] = relationship(
        lazy="raise",
        back_populates="rom",
        cascade="all, delete-orphan",
        order_by="RomComponent.relative_path",
    )
    owned_media: Mapped[list[RomOwnedMedia]] = relationship(
        lazy="raise",
        back_populates="rom",
        cascade="all, delete-orphan",
        order_by="RomOwnedMedia.id",
    )
    owned_media_placements: Mapped[list[RomOwnedMediaPlacement]] = relationship(
        lazy="raise",
        back_populates="rom",
        cascade="all, delete-orphan",
        order_by="RomOwnedMediaPlacement.position",
    )
    local_background_audio: Mapped[list[RomLocalBackgroundAudio]] = relationship(
        lazy="raise",
        back_populates="rom",
        cascade="all, delete-orphan",
        order_by="RomLocalBackgroundAudio.rom_file_id",
    )
    owned_background_audio: Mapped[list[RomOwnedBackgroundAudio]] = relationship(
        lazy="raise",
        back_populates="rom",
        cascade="all, delete-orphan",
        order_by="RomOwnedBackgroundAudio.media_id",
    )
    download_archive_sets: Mapped[list[DownloadArchiveSet]] = relationship(
        lazy="raise",
        back_populates="rom",
        cascade="all, delete-orphan",
        order_by="DownloadArchiveSet.id",
    )
    saves: Mapped[list[Save]] = relationship(lazy="raise", back_populates="rom")
    states: Mapped[list[State]] = relationship(lazy="raise", back_populates="rom")
    screenshots: Mapped[list[Screenshot]] = relationship(
        lazy="raise", back_populates="rom"
    )
    rom_users: Mapped[list[RomUser]] = relationship(lazy="raise", back_populates="rom")
    notes: Mapped[list[RomNote]] = relationship(lazy="raise", back_populates="rom")
    metadatum: Mapped[RomMetadata] = relationship(
        lazy="joined", back_populates="rom", uselist=False
    )
    collections: Mapped[list[Collection]] = relationship(
        "Collection",
        secondary="collections_roms",
        collection_class=set,
        lazy="raise",
        back_populates="roms",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._is_identifying = False

    @validates("name", "name_sort_key")
    def _sync_name_sort_key(self, key: str, value: str | None) -> str | None:
        """Keep the indexed `name_sort_key` in sync with `name`"""
        if key == "name_sort_key":
            return compute_name_sort_key(value or self.name)

        if self.name_sort_key is None or self.name_sort_key == compute_name_sort_key(
            self.name
        ):
            self.name_sort_key = compute_name_sort_key(value)

        return value

    @validates("fs_name")
    def _sync_fs_name_parts(self, _key: str, fs_name: str) -> str:
        """Derive the stored `fs_name_no_tags` / `fs_name_no_ext` /
        `fs_extension` columns whenever `fs_name` is assigned.

        Fires on attribute set (ORM construction and mutation) only. Bulk
        `update()` statements bypass the ORM and set these explicitly (see
        `update_rom`).
        """
        parts = compute_file_name_parts(fs_name)
        self.fs_name_no_tags = parts.no_tags
        self.fs_name_no_ext = parts.no_ext
        self.fs_extension = parts.extension
        return fs_name

    @property
    def platform_slug(self) -> str:
        return self.platform.slug

    @property
    def platform_fs_slug(self) -> str:
        return self.platform.fs_slug

    @property
    def platform_custom_name(self) -> str | None:
        return self.platform.custom_name

    @property
    def platform_display_name(self) -> str:
        return self.platform.custom_name or self.platform.name

    @cached_property
    def full_path(self) -> str:
        return f"{self.fs_path}/{self.fs_name}"

    @cached_property
    def has_manual(self) -> bool:
        return bool(self.path_manual)

    @declared_attr
    def has_soundtrack(cls) -> Mapped[bool]:
        return column_property(
            select(RomFile.id)
            .where(
                and_(
                    RomFile.rom_id == cls.id,
                    RomFile.category == RomFileCategory.SOUNDTRACK,
                )
            )
            .correlate_except(RomFile)
            .exists()
            .select()
            .scalar_subquery(),
            deferred=True,
        )

    @property
    def local_background_audio_file_ids(self) -> list[int]:
        return [selection.rom_file_id for selection in self.local_background_audio]

    @property
    def owned_background_audio_media_ids(self) -> list[int]:
        return [selection.media_id for selection in self.owned_background_audio]

    @cached_property
    def merged_screenshots(self) -> list[str]:
        if self.path_screenshots:
            return [f"{FRONTEND_RESOURCES_PATH}/{s}" for s in self.path_screenshots]

        return []

    if TYPE_CHECKING:
        # Defined out-of-line at module scope via column_property
        multi_file: Mapped[bool]
        top_level_file_count: Mapped[int]

    @property
    def has_simple_single_file(self) -> bool:
        return not self.multi_file and self.top_level_file_count == 1

    @property
    def has_nested_single_file(self) -> bool:
        return self.multi_file and self.top_level_file_count == 1

    @property
    def has_multiple_files(self) -> bool:
        return self.top_level_file_count > 1

    @property
    def fs_resources_path(self) -> str:
        return f"roms/{str(self.platform_id)}/{str(self.id)}"

    @property
    def path_cover_small(self) -> str:
        return (
            f"{FRONTEND_RESOURCES_PATH}/{self.path_cover_s}?ts={self.updated_at}"
            if self.path_cover_s
            else ""
        )

    @property
    def path_cover_large(self) -> str:
        return (
            f"{FRONTEND_RESOURCES_PATH}/{self.path_cover_l}?ts={self.updated_at}"
            if self.path_cover_l
            else ""
        )

    @property
    def path_video(self) -> str | None:
        return (
            (self.ss_metadata or {}).get("video_path")
            or (self.ss_metadata or {}).get("video_normalized_path")
            or (self.gamelist_metadata or {}).get("video_path")
            or (self.launchbox_metadata or {}).get("video_path")
        )

    @property
    def is_unidentified(self) -> bool:
        return (
            not self.igdb_id
            and not self.moby_id
            and not self.ss_id
            and not self.ra_id
            and not self.launchbox_id
            and not self.hasheous_id
            and not self.flashpoint_id
            and not self.hltb_id
            and not self.gamelist_id
            and not self.libretro_id
        )

    @property
    def is_identified(self) -> bool:
        return not self.is_unidentified

    def has_m3u_file(self) -> bool:
        """
        Check if the ROM has an M3U file associated with it.
        This is used for multi-disc games.
        """
        return any(file.file_extension.lower() == "m3u" for file in self.files)

    # Metadata fields
    @property
    def youtube_video_id(self) -> str | None:
        igdb_video_id = (
            self.igdb_metadata.get("youtube_video_id", None)
            if self.igdb_metadata
            else None
        )
        lb_video_id = (
            self.launchbox_metadata.get("youtube_video_id", None)
            if self.launchbox_metadata
            else None
        )

        return igdb_video_id or lb_video_id

    @property
    def alternative_names(self) -> list[str]:
        return (
            (self.igdb_metadata or {}).get("alternative_names", None)
            or (self.moby_metadata or {}).get("alternate_titles", None)
            or (self.ss_metadata or {}).get("alternative_names", None)
            or []
        )

    @cached_property
    def merged_ra_metadata(self) -> dict[str, list] | None:
        if self.ra_metadata and "achievements" in self.ra_metadata:
            # Create a deep copy to avoid mutating the original metadata
            # This ensures that badge paths remain relative for filesystem operations
            # while the frontend receives absolute paths
            metadata_copy = copy.deepcopy(self.ra_metadata)
            for achievement in metadata_copy.get("achievements", []):
                achievement["badge_path_lock"] = (
                    f"{FRONTEND_RESOURCES_PATH}/{achievement['badge_path_lock']}"
                )
                achievement["badge_path"] = (
                    f"{FRONTEND_RESOURCES_PATH}/{achievement['badge_path']}"
                )
            return metadata_copy
        return self.ra_metadata

    # Used only during scan process
    @property
    def is_identifying(self) -> bool:
        return self._is_identifying or False

    @is_identifying.setter
    def is_identifying(self, value: bool) -> None:
        self._is_identifying = value

    def __repr__(self) -> str:
        return f"{self.fs_name} ({self.id})"


def _assign_fresh_incarnation_token(_mapper, _connection, target) -> None:
    target.incarnation_token = secrets.token_hex(16)


def _reject_incarnation_token_update(_mapper, _connection, target) -> None:
    if sa_inspect(target).attrs.incarnation_token.history.has_changes():
        raise ValueError("incarnation token is immutable")


def _contains_incarnation_token(values: Mapping[object, object]) -> bool:
    return any(
        getattr(column, "key", column) == "incarnation_token" for column in values
    )


def _iter_parameter_mappings(value):
    if isinstance(value, Mapping):
        yield value
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from _iter_parameter_mappings(item)


def _is_catalog_update(statement) -> bool:
    if not getattr(statement, "is_update", False):
        return False
    table = getattr(statement, "table", None)
    if table is None:
        return False
    expected = {
        Rom.__table__.key: Rom.__table__,
        RomFile.__table__.key: RomFile.__table__,
    }.get(getattr(table, "key", None))
    if expected is None:
        return False
    return (
        table is expected
        or getattr(table, "original", None) is expected
        or getattr(table, "metadata", None) is expected.metadata
    )


def _reject_bulk_incarnation_token_update(
    _connection,
    statement,
    multiparams,
    params,
    _execution_options,
) -> None:
    if not _is_catalog_update(statement):
        return
    statement_values = getattr(statement, "_values", None)
    if isinstance(statement_values, Mapping) and _contains_incarnation_token(
        statement_values
    ):
        raise ValueError("incarnation token is immutable")
    if any(
        _contains_incarnation_token(mapping)
        for mapping in _iter_parameter_mappings((multiparams, params))
    ):
        raise ValueError("incarnation token is immutable")


for _catalog_model in (Rom, RomFile):
    event.listen(_catalog_model, "before_insert", _assign_fresh_incarnation_token)
    event.listen(_catalog_model, "before_update", _reject_incarnation_token_update)
event.listen(Engine, "before_execute", _reject_bulk_incarnation_token_update)


# Correlated scalar subqueries against rom_files, deferred and opt-in via `undefer`
# Revisit (real columns, JOIN/aggregate, or added indexes) if gallery latency regresses
_rom_full_path = func.concat(Rom.fs_path, "/", Rom.fs_name)

Rom.multi_file = column_property(
    select(RomFile.id)
    .where(
        and_(
            RomFile.rom_id == Rom.id,
            RomFile.file_path != Rom.fs_path,
        )
    )
    .correlate_except(RomFile)
    .exists()
    .select()
    .scalar_subquery(),
    deferred=True,
)

Rom.top_level_file_count = column_property(
    select(func.count(RomFile.id))
    .where(
        and_(
            RomFile.rom_id == Rom.id,
            or_(
                func.concat(RomFile.file_path, "/", RomFile.file_name)
                == _rom_full_path,
                RomFile.file_path == _rom_full_path,
            ),
        )
    )
    .correlate_except(RomFile)
    .scalar_subquery(),
    deferred=True,
)


# Maps a metadata-source slug (matching the MetadataSource enum) to the Rom
# column holding that source's match id. A populated column means the ROM
# matched that source. Shared by the stats coverage breakdown and the gallery
# "metadata provider" filter. Sources without a per-ROM match id (e.g. sgdb
# covers, playmatch) are intentionally absent.
METADATA_SOURCE_COLUMNS: dict[str, InstrumentedAttribute] = {
    "igdb": Rom.igdb_id,
    "ss": Rom.ss_id,
    "moby": Rom.moby_id,
    "steam": Rom.steam_id,
    "launchbox": Rom.launchbox_id,
    "ra": Rom.ra_id,
    "hasheous": Rom.hasheous_id,
    "tgdb": Rom.tgdb_id,
    "flashpoint": Rom.flashpoint_id,
    "hltb": Rom.hltb_id,
    "gamelist": Rom.gamelist_id,
    "libretro": Rom.libretro_id,
}

# Same slugs mapped to the `roms_facets` mirror columns. The stats coverage
# breakdown counts these off the narrow mirror instead of scanning `roms`.
METADATA_SOURCE_FACET_COLUMNS: dict[str, InstrumentedAttribute] = {
    "igdb": RomFacets.igdb_id,
    "ss": RomFacets.ss_id,
    "moby": RomFacets.moby_id,
    "steam": RomFacets.steam_id,
    "launchbox": RomFacets.launchbox_id,
    "ra": RomFacets.ra_id,
    "hasheous": RomFacets.hasheous_id,
    "tgdb": RomFacets.tgdb_id,
    "flashpoint": RomFacets.flashpoint_id,
    "hltb": RomFacets.hltb_id,
    "gamelist": RomFacets.gamelist_id,
    "libretro": RomFacets.libretro_id,
}


class RomUserStatus(enum.StrEnum):
    INCOMPLETE = "incomplete"  # Started but not finished
    FINISHED = "finished"  # Reached the end of the game
    COMPLETED_100 = "completed_100"  # Completed 100%
    RETIRED = "retired"  # Won't play again
    NEVER_PLAYING = "never_playing"  # Will never play


class RomNote(BaseModel):
    __tablename__ = "rom_notes"
    __table_args__ = (
        UniqueConstraint(
            "rom_id", "user_id", "title", name="unique_rom_user_note_title"
        ),
        Index("idx_rom_notes_public", "is_public"),
        Index("idx_rom_notes_rom_user", "rom_id", "user_id"),
        Index("idx_rom_notes_title", "title"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Core note fields
    title: Mapped[str] = mapped_column(String(400))
    content: Mapped[str] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(default=False)

    # Future extensibility fields
    tags: Mapped[list[str] | None] = mapped_column(CustomJSON(), default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Foreign keys
    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    # Relationships
    rom: Mapped[Rom] = relationship(lazy="joined", back_populates="notes")
    user: Mapped[User] = relationship(lazy="joined", back_populates="notes")


class RomUser(BaseModel):
    __tablename__ = "rom_user"
    __table_args__ = (
        UniqueConstraint("rom_id", "user_id", name="unique_rom_user_props"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    is_main_sibling: Mapped[bool] = mapped_column(default=False)
    last_played: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    backlogged: Mapped[bool] = mapped_column(default=False)
    now_playing: Mapped[bool] = mapped_column(default=False)
    hidden: Mapped[bool] = mapped_column(default=False)
    rating: Mapped[int] = mapped_column(default=0)
    difficulty: Mapped[int] = mapped_column(default=0)
    completion: Mapped[int] = mapped_column(default=0)
    status: Mapped[RomUserStatus | None] = mapped_column(
        Enum(RomUserStatus), default=None
    )

    rom_id: Mapped[int] = mapped_column(ForeignKey("roms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    rom: Mapped[Rom] = relationship(lazy="joined", back_populates="rom_users")
    user: Mapped[User] = relationship(lazy="joined", back_populates="rom_users")
