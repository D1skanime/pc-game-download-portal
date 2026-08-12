"""Add durable catalog lifecycle and legacy migration state.

Revision ID: 0111_safe_lifecycle
Revises: 0110_mapping_preview_results
Create Date: 2026-08-12 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0111_safe_lifecycle"
down_revision = "0110_mapping_preview_results"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    ]


def _foreign_key_name(table_name: str, column_name: str) -> str:
    foreign_keys = [
        foreign_key
        for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
        if foreign_key["constrained_columns"] == [column_name]
    ]
    if len(foreign_keys) != 1 or not foreign_keys[0]["name"]:
        raise RuntimeError(
            f"Expected one named foreign key for {table_name}.{column_name}"
        )
    return foreign_keys[0]["name"]


def _ensure_safe_lifecycle_downgrade() -> None:
    connection = op.get_bind()
    lifecycle_tables = (
        "owned_cleanup_intents",
        "legacy_migrations",
        "legacy_detection_results",
        "retained_catalog_identities",
    )
    populated = [
        table_name
        for table_name in lifecycle_tables
        if connection.scalar(
            sa.text(f"SELECT COUNT(*) FROM {table_name}")  # nosec B608
        )
    ]
    detached_assets = sum(
        int(
            connection.scalar(
                sa.text(
                    f"SELECT COUNT(*) FROM {table_name} "  # nosec B608
                    "WHERE rom_id IS NULL OR retained_catalog_id IS NOT NULL"
                )
            )
            or 0
        )
        for table_name in ("saves", "states")
    )
    attributed_sessions = int(
        connection.scalar(
            sa.text(
                "SELECT COUNT(*) FROM play_sessions "
                "WHERE retained_catalog_id IS NOT NULL"
            )
        )
        or 0
    )
    if populated or detached_assets or attributed_sessions:
        raise RuntimeError(
            "Cannot downgrade safe lifecycle while retained lifecycle state exists"
        )


def _create_retained_catalog() -> None:
    op.create_table(
        "retained_catalog_identities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("detached_rom_id", sa.Integer(), nullable=False),
        sa.Column("active_rom_id", sa.Integer(), nullable=True),
        sa.Column("logical_path", sa.String(length=700), nullable=False),
        sa.Column("file_name", sa.String(length=450), nullable=False),
        sa.Column("crc_hash", sa.String(length=100), nullable=True),
        sa.Column("md5_hash", sa.String(length=100), nullable=True),
        sa.Column("sha1_hash", sa.String(length=100), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("detached_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "detached_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("reconnected_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_retained_catalog_version",
        ),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platforms.id"],
            name="fk_retained_catalog_platform_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["active_rom_id"],
            ["roms.id"],
            name="fk_retained_catalog_active_rom_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_retained_catalog_identities"),
    )
    op.create_index(
        "ix_retained_catalog_platform_logical_path",
        "retained_catalog_identities",
        ["platform_id", "logical_path"],
    )
    op.create_index(
        "ix_retained_catalog_active_rom_id",
        "retained_catalog_identities",
        ["active_rom_id"],
    )


def _make_assets_retainable() -> None:
    for table_name in ("saves", "states"):
        old_rom_fk = _foreign_key_name(table_name, "rom_id")
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(old_rom_fk, type_="foreignkey")
            batch_op.alter_column(
                "rom_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
            batch_op.add_column(
                sa.Column("retained_catalog_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                f"fk_{table_name}_rom_id",
                "roms",
                ["rom_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_foreign_key(
                f"fk_{table_name}_retained_catalog_id",
                "retained_catalog_identities",
                ["retained_catalog_id"],
                ["id"],
                ondelete="RESTRICT",
            )
            batch_op.create_index(
                f"ix_{table_name}_retained_catalog_id",
                ["retained_catalog_id"],
                unique=False,
            )

    with op.batch_alter_table("play_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("retained_catalog_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_play_sessions_retained_catalog_id",
            "retained_catalog_identities",
            ["retained_catalog_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_play_sessions_retained_catalog",
            ["retained_catalog_id"],
            unique=False,
        )


def _create_cleanup_intents() -> None:
    op.create_table(
        "owned_cleanup_intents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("retained_catalog_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("relative_path", sa.String(length=700), nullable=True),
        sa.Column("file_name", sa.String(length=450), nullable=True),
        sa.Column("deduplication_key", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("safe_error", sa.String(length=1000), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "kind IN ('cover', 'manual', 'screenshot', 'resource')",
            name="ck_owned_cleanup_intents_kind",
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_owned_cleanup_intents_state",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_owned_cleanup_intents_version",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_owned_cleanup_intents_attempt_count",
        ),
        sa.ForeignKeyConstraint(
            ["retained_catalog_id"],
            ["retained_catalog_identities.id"],
            name="fk_owned_cleanup_retained_catalog_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_owned_cleanup_intents"),
        sa.UniqueConstraint(
            "deduplication_key",
            name="uq_owned_cleanup_intents_deduplication_key",
        ),
    )
    op.create_index(
        "ix_owned_cleanup_intents_state_next_attempt",
        "owned_cleanup_intents",
        ["state", "next_attempt_at"],
    )
    op.create_index(
        "ix_owned_cleanup_intents_retained_catalog",
        "owned_cleanup_intents",
        ["retained_catalog_id"],
    )


def _create_legacy_detection_results() -> None:
    op.create_table(
        "legacy_detection_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("storage_root_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("proposed_relative_path", sa.String(length=700), nullable=True),
        sa.Column("observed_files", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "observed_bytes", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column(
            "lower_bound", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column(
            "selectable", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("safe_problem_code", sa.String(length=64), nullable=True),
        sa.Column("observed_mapping_id", sa.Integer(), nullable=True),
        sa.Column("observed_mapping_version", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "state IN ('detected', 'manual_mapping_required', 'empty', "
            "'unreadable', 'unreachable', 'unsafe', 'conflict')",
            name="ck_legacy_detection_results_state",
        ),
        sa.CheckConstraint(
            "observed_files >= 0",
            name="ck_legacy_detection_results_observed_files",
        ),
        sa.CheckConstraint(
            "observed_bytes >= 0",
            name="ck_legacy_detection_results_observed_bytes",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_legacy_detection_results_version",
        ),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platforms.id"],
            name="fk_legacy_detection_platform_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["storage_root_id"],
            ["storage_roots.id"],
            name="fk_legacy_detection_storage_root_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observed_mapping_id"],
            ["platform_storage_mappings.id"],
            name="fk_legacy_detection_observed_mapping_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_legacy_detection_results"),
    )
    op.create_index(
        "ix_legacy_detection_results_platform_created",
        "legacy_detection_results",
        ["platform_id", "created_at"],
    )
    op.create_index(
        "ix_legacy_detection_results_state_expires",
        "legacy_detection_results",
        ["state", "expires_at"],
    )


def _create_legacy_migrations() -> None:
    op.create_table(
        "legacy_migrations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("detection_result_id", sa.Integer(), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("storage_root_id", sa.Integer(), nullable=False),
        sa.Column("mapping_id", sa.Integer(), nullable=True),
        sa.Column("relative_path", sa.String(length=700), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("prior_mapping_id", sa.Integer(), nullable=True),
        sa.Column("prior_mapping_version", sa.Integer(), nullable=True),
        sa.Column("prior_mapping_active", sa.Boolean(), nullable=True),
        sa.Column(
            "reconnected_catalog_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "unmatched_catalog_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("first_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("first_use_operation", sa.String(length=32), nullable=True),
        sa.Column("rolled_back_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "state IN ('pending', 'completed', 'rolled_back', 'failed')",
            name="ck_legacy_migrations_state",
        ),
        sa.CheckConstraint("version >= 1", name="ck_legacy_migrations_version"),
        sa.CheckConstraint(
            "reconnected_catalog_count >= 0",
            name="ck_legacy_migrations_reconnected_count",
        ),
        sa.CheckConstraint(
            "unmatched_catalog_count >= 0",
            name="ck_legacy_migrations_unmatched_count",
        ),
        sa.CheckConstraint(
            "(first_used_at IS NULL AND first_use_operation IS NULL) OR "
            "(first_used_at IS NOT NULL AND first_use_operation IS NOT NULL)",
            name="ck_legacy_migrations_first_use_pair",
        ),
        sa.CheckConstraint(
            "first_use_operation IS NULL OR first_use_operation IN "
            "('scan', 'hash', 'stream', 'play', 'download')",
            name="ck_legacy_migrations_first_use_operation",
        ),
        sa.ForeignKeyConstraint(
            ["detection_result_id"],
            ["legacy_detection_results.id"],
            name="fk_legacy_migrations_detection_result_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platforms.id"],
            name="fk_legacy_migrations_platform_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["storage_root_id"],
            ["storage_roots.id"],
            name="fk_legacy_migrations_storage_root_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["platform_storage_mappings.id"],
            name="fk_legacy_migrations_mapping_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_legacy_migrations"),
        sa.UniqueConstraint(
            "detection_result_id",
            name="uq_legacy_migrations_detection_result_id",
        ),
    )
    op.create_index(
        "ix_legacy_migrations_platform_created",
        "legacy_migrations",
        ["platform_id", "created_at"],
    )
    op.create_index(
        "ix_legacy_migrations_mapping_id",
        "legacy_migrations",
        ["mapping_id"],
    )
    op.create_index(
        "ix_legacy_migrations_state_expires",
        "legacy_migrations",
        ["state", "expires_at"],
    )


def upgrade() -> None:
    _create_retained_catalog()
    _make_assets_retainable()
    _create_cleanup_intents()
    _create_legacy_detection_results()
    _create_legacy_migrations()


def _restore_asset_rom_ownership(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(
            f"fk_{table_name}_retained_catalog_id",
            type_="foreignkey",
        )
        batch_op.drop_index(f"ix_{table_name}_retained_catalog_id")
        batch_op.drop_column("retained_catalog_id")
        batch_op.drop_constraint(f"fk_{table_name}_rom_id", type_="foreignkey")
        batch_op.alter_column(
            "rom_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            f"fk_{table_name}_rom_id",
            "roms",
            ["rom_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    _ensure_safe_lifecycle_downgrade()

    op.drop_table("legacy_migrations")
    op.drop_table("legacy_detection_results")
    op.drop_table("owned_cleanup_intents")

    with op.batch_alter_table("play_sessions") as batch_op:
        batch_op.drop_constraint(
            "fk_play_sessions_retained_catalog_id",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_play_sessions_retained_catalog")
        batch_op.drop_column("retained_catalog_id")

    _restore_asset_rom_ownership("states")
    _restore_asset_rom_ownership("saves")

    op.drop_table("retained_catalog_identities")
