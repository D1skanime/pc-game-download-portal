"""Create immutable storage roots and platform mappings.

Revision ID: 0108_storage_foundation
Revises: 0107_roms_dedup_cover_index
Create Date: 2026-08-04 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0108_storage_foundation"
down_revision = "0107_roms_dedup_cover_index"
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


def upgrade() -> None:
    op.create_table(
        "storage_roots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=400), nullable=False),
        sa.Column("container_path", sa.String(length=700), nullable=False),
        sa.Column(
            "mode",
            sa.String(length=32),
            server_default="external_read_only",
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("reachable", sa.Boolean(), nullable=True),
        sa.Column("readable", sa.Boolean(), nullable=True),
        sa.Column("non_writable", sa.Boolean(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("safe_error", sa.String(length=1000), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "mode = 'external_read_only'",
            name="ck_storage_roots_external_read_only_mode",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_storage_roots"),
        sa.UniqueConstraint("container_path", name="uq_storage_roots_container_path"),
    )

    op.create_table(
        "platform_storage_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("storage_root_id", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.String(length=700), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platforms.id"],
            name="fk_platform_storage_mappings_platform_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["storage_root_id"],
            ["storage_roots.id"],
            name="fk_platform_storage_mappings_storage_root_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_platform_storage_mappings"),
        sa.UniqueConstraint(
            "platform_id", name="uq_platform_storage_mappings_platform_id"
        ),
        sa.UniqueConstraint(
            "storage_root_id",
            "relative_path",
            name="uq_platform_storage_mappings_root_relative_path",
        ),
    )
    op.create_index(
        "ix_platform_storage_mappings_storage_root_id",
        "platform_storage_mappings",
        ["storage_root_id"],
    )


def downgrade() -> None:
    op.drop_table("platform_storage_mappings")
    op.drop_table("storage_roots")
