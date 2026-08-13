from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.platform import Platform


STORAGE_ROOT_NAME_MAX_LENGTH = 400
STORAGE_ROOT_PATH_MAX_LENGTH = 700
STORAGE_ROOT_MODE_MAX_LENGTH = 32
STORAGE_ROOT_SAFE_ERROR_MAX_LENGTH = 1000
STORAGE_MAPPING_PATH_MAX_LENGTH = 700
STORAGE_AUDIT_ACTOR_MAX_LENGTH = 255
STORAGE_AUDIT_ACTION_MAX_LENGTH = 16
EXTERNAL_READ_ONLY_MODE = "external_read_only"


class StorageRoot(BaseModel):
    __tablename__ = "storage_roots"
    __table_args__ = (
        CheckConstraint(
            f"mode = '{EXTERNAL_READ_ONLY_MODE}'",
            name="ck_storage_roots_external_read_only_mode",
        ),
        UniqueConstraint("container_path", name="uq_storage_roots_container_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(length=STORAGE_ROOT_NAME_MAX_LENGTH))
    container_path: Mapped[str] = mapped_column(
        String(length=STORAGE_ROOT_PATH_MAX_LENGTH)
    )
    mode: Mapped[str] = mapped_column(
        String(length=STORAGE_ROOT_MODE_MAX_LENGTH),
        default=EXTERNAL_READ_ONLY_MODE,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    reachable: Mapped[bool | None] = mapped_column(Boolean, default=None)
    readable: Mapped[bool | None] = mapped_column(Boolean, default=None)
    non_writable: Mapped[bool | None] = mapped_column(Boolean, default=None)
    last_checked_at: Mapped[datetime | None] = mapped_column(default=None)
    safe_error: Mapped[str | None] = mapped_column(
        String(length=STORAGE_ROOT_SAFE_ERROR_MAX_LENGTH), default=None
    )

    platform_mappings: Mapped[list[PlatformStorageMapping]] = relationship(
        lazy="raise",
        back_populates="storage_root",
        passive_deletes=True,
    )


class PlatformStorageMapping(BaseModel):
    __tablename__ = "platform_storage_mappings"
    __table_args__ = (
        Index("ix_platform_storage_mappings_storage_root_id", "storage_root_id"),
        Index("ix_platform_storage_mappings_platform_id", "platform_id"),
        Index("ix_platform_storage_mappings_active_platform", "active", "platform_id"),
        Index(
            "ix_platform_storage_mappings_active_root_path",
            "active",
            "storage_root_id",
            "relative_path",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="CASCADE")
    )
    storage_root_id: Mapped[int] = mapped_column(
        ForeignKey("storage_roots.id", ondelete="RESTRICT")
    )
    relative_path: Mapped[str] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    platform: Mapped[Platform] = relationship(
        lazy="joined", back_populates="storage_mapping"
    )
    storage_root: Mapped[StorageRoot] = relationship(
        lazy="joined", back_populates="platform_mappings"
    )


class StorageMappingAuditAction(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    REMOVE = "remove"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"


class StorageMappingAudit(BaseModel):
    __tablename__ = "storage_mapping_audits"
    __table_args__ = (
        CheckConstraint(
            "action IN ('create', 'update', 'remove', 'activate', 'deactivate')",
            name="ck_storage_mapping_audits_action",
        ),
        Index(
            "ix_storage_mapping_audits_platform_created", "platform_id", "created_at"
        ),
        Index("ix_storage_mapping_audits_mapping_created", "mapping_id", "created_at"),
        Index("ix_storage_mapping_audits_action_created", "action", "created_at"),
    )

    updated_at = None
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int] = mapped_column(Integer)
    actor_display_name: Mapped[str] = mapped_column(
        String(length=STORAGE_AUDIT_ACTOR_MAX_LENGTH)
    )
    platform_id: Mapped[int] = mapped_column(Integer)
    mapping_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(length=STORAGE_AUDIT_ACTION_MAX_LENGTH))
    old_storage_root_id: Mapped[int | None] = mapped_column(Integer, default=None)
    old_relative_path: Mapped[str | None] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH), default=None
    )
    old_version: Mapped[int | None] = mapped_column(Integer, default=None)
    old_active: Mapped[bool | None] = mapped_column(Boolean, default=None)
    new_storage_root_id: Mapped[int | None] = mapped_column(Integer, default=None)
    new_relative_path: Mapped[str | None] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH), default=None
    )
    new_version: Mapped[int | None] = mapped_column(Integer, default=None)
    new_active: Mapped[bool | None] = mapped_column(Boolean, default=None)


LEGACY_RESULT_STATE_MAX_LENGTH = 32
LEGACY_PROBLEM_CODE_MAX_LENGTH = 64
LEGACY_MIGRATION_STATE_MAX_LENGTH = 16
LEGACY_OPERATION_MAX_LENGTH = 32
LEGACY_FINGERPRINT_LENGTH = 64
LEGACY_CATALOG_ENTITY_KIND_MAX_LENGTH = 16


class LegacyDetectionState(enum.StrEnum):
    DETECTED = "detected"
    MANUAL_MAPPING_REQUIRED = "manual_mapping_required"
    EMPTY = "empty"
    UNREADABLE = "unreadable"
    UNREACHABLE = "unreachable"
    UNSAFE = "unsafe"
    CONFLICT = "conflict"


class LegacyMigrationState(enum.StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class LegacyDetectionResult(BaseModel):
    __tablename__ = "legacy_detection_results"
    __table_args__ = (
        CheckConstraint(
            "state IN ('detected', 'manual_mapping_required', 'empty', "
            "'unreadable', 'unreachable', 'unsafe', 'conflict')",
            name="ck_legacy_detection_results_state",
        ),
        CheckConstraint(
            "observed_files >= 0",
            name="ck_legacy_detection_results_observed_files",
        ),
        CheckConstraint(
            "observed_bytes >= 0",
            name="ck_legacy_detection_results_observed_bytes",
        ),
        CheckConstraint(
            "source_fingerprint IS NULL OR "
            "(CHAR_LENGTH(source_fingerprint) = 64 AND "
            "source_fingerprint = LOWER(source_fingerprint))",
            name="ck_legacy_detection_results_source_fingerprint_format",
        ),
        CheckConstraint(
            "(selectable = false AND source_fingerprint IS NULL) OR "
            "(selectable = true AND source_fingerprint IS NOT NULL AND lower_bound = false)",
            name="ck_legacy_detection_results_source_fingerprint_selectable",
        ),
        CheckConstraint("version >= 1", name="ck_legacy_detection_results_version"),
        Index(
            "ix_legacy_detection_results_platform_created",
            "platform_id",
            "created_at",
        ),
        Index(
            "ix_legacy_detection_results_state_expires",
            "state",
            "expires_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="RESTRICT")
    )
    storage_root_id: Mapped[int] = mapped_column(
        ForeignKey("storage_roots.id", ondelete="RESTRICT")
    )
    state: Mapped[str] = mapped_column(String(length=LEGACY_RESULT_STATE_MAX_LENGTH))
    proposed_relative_path: Mapped[str | None] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH), default=None
    )
    observed_files: Mapped[int] = mapped_column(Integer, default=0)
    observed_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    lower_bound: Mapped[bool] = mapped_column(Boolean, default=False)
    selectable: Mapped[bool] = mapped_column(Boolean, default=False)
    safe_problem_code: Mapped[str | None] = mapped_column(
        String(length=LEGACY_PROBLEM_CODE_MAX_LENGTH), default=None
    )
    source_fingerprint: Mapped[str | None] = mapped_column(
        String(length=LEGACY_FINGERPRINT_LENGTH), default=None
    )
    observed_mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey("platform_storage_mappings.id", ondelete="SET NULL"),
        default=None,
    )
    observed_mapping_version: Mapped[int | None] = mapped_column(Integer, default=None)
    version: Mapped[int] = mapped_column(Integer, default=1)
    actor_user_id: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column(default=None)


class LegacyMigration(BaseModel):
    __tablename__ = "legacy_migrations"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'completed', 'rolled_back', 'failed')",
            name="ck_legacy_migrations_state",
        ),
        CheckConstraint("version >= 1", name="ck_legacy_migrations_version"),
        CheckConstraint(
            "reconnected_catalog_count >= 0",
            name="ck_legacy_migrations_reconnected_count",
        ),
        CheckConstraint(
            "unmatched_catalog_count >= 0",
            name="ck_legacy_migrations_unmatched_count",
        ),
        CheckConstraint(
            "(first_used_at IS NULL AND first_use_operation IS NULL) OR "
            "(first_used_at IS NOT NULL AND first_use_operation IS NOT NULL)",
            name="ck_legacy_migrations_first_use_pair",
        ),
        CheckConstraint(
            "first_use_operation IS NULL OR first_use_operation IN "
            "('scan', 'hash', 'stream', 'play', 'download')",
            name="ck_legacy_migrations_first_use_operation",
        ),
        UniqueConstraint(
            "detection_result_id",
            name="uq_legacy_migrations_detection_result_id",
        ),
        Index(
            "ix_legacy_migrations_platform_created",
            "platform_id",
            "created_at",
        ),
        Index("ix_legacy_migrations_mapping_id", "mapping_id"),
        Index("ix_legacy_migrations_state_expires", "state", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    detection_result_id: Mapped[int] = mapped_column(
        ForeignKey("legacy_detection_results.id", ondelete="RESTRICT")
    )
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="RESTRICT")
    )
    storage_root_id: Mapped[int] = mapped_column(
        ForeignKey("storage_roots.id", ondelete="RESTRICT")
    )
    mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey("platform_storage_mappings.id", ondelete="RESTRICT"),
        default=None,
    )
    relative_path: Mapped[str] = mapped_column(
        String(length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    )
    state: Mapped[str] = mapped_column(
        String(length=LEGACY_MIGRATION_STATE_MAX_LENGTH),
        default=LegacyMigrationState.PENDING,
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    actor_user_id: Mapped[int] = mapped_column(Integer)
    prior_mapping_id: Mapped[int | None] = mapped_column(Integer, default=None)
    prior_mapping_version: Mapped[int | None] = mapped_column(Integer, default=None)
    prior_mapping_active: Mapped[bool | None] = mapped_column(Boolean, default=None)
    reconnected_catalog_count: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_catalog_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    first_used_at: Mapped[datetime | None] = mapped_column(default=None)
    first_use_operation: Mapped[str | None] = mapped_column(
        String(length=LEGACY_OPERATION_MAX_LENGTH), default=None
    )
    rolled_back_at: Mapped[datetime | None] = mapped_column(default=None)

    catalog_changes: Mapped[list[LegacyMigrationCatalogChange]] = relationship(
        lazy="raise",
        back_populates="migration",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
        order_by=lambda: (
            LegacyMigrationCatalogChange.entity_kind,
            LegacyMigrationCatalogChange.entity_id,
        ),
    )


class LegacyCatalogEntityKind(enum.StrEnum):
    ROM = "rom"
    ROM_FILE = "rom_file"


class LegacyMigrationCatalogChange(BaseModel):
    __tablename__ = "legacy_migration_catalog_changes"
    __table_args__ = (
        CheckConstraint(
            "entity_kind IN ('rom', 'rom_file')",
            name="ck_legacy_migration_catalog_changes_entity_kind",
        ),
        CheckConstraint(
            "entity_id > 0",
            name="ck_legacy_migration_catalog_changes_entity_id",
        ),
        UniqueConstraint(
            "migration_id",
            "entity_kind",
            "entity_id",
            name="uq_legacy_migration_catalog_changes_identity",
        ),
        Index(
            "ix_legacy_migration_catalog_changes_order",
            "migration_id",
            "entity_kind",
            "entity_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    migration_id: Mapped[int] = mapped_column(
        ForeignKey("legacy_migrations.id", ondelete="CASCADE")
    )
    entity_kind: Mapped[str] = mapped_column(
        String(length=LEGACY_CATALOG_ENTITY_KIND_MAX_LENGTH)
    )
    entity_id: Mapped[int] = mapped_column(Integer)
    prior_missing_from_fs: Mapped[bool] = mapped_column(Boolean)

    migration: Mapped[LegacyMigration] = relationship(
        lazy="raise", back_populates="catalog_changes"
    )
