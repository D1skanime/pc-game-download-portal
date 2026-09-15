"""Persist immutable download manifests.

Revision ID: 0119_download_manifests
Revises: 0118_pc_igdb_structured_metadata
Create Date: 2026-09-15 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0119_download_manifests"
down_revision = "0118_pc_igdb_structured_metadata"
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


def _status_enum() -> sa.Enum:
    return sa.Enum(
        "valid",
        "expired",
        "revoked",
        "source_changed",
        name="downloadmanifeststatus",
        native_enum=False,
        create_constraint=True,
        length=20,
    )


def upgrade() -> None:
    status = _status_enum()
    status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "download_manifests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("status", status, nullable=False, server_default="valid"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_download_manifests_owner_status_expiry",
        "download_manifests",
        ["user_id", "status", "expires_at"],
    )
    op.create_table(
        "download_manifest_components",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("manifest_id", sa.String(length=36), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["manifest_id"], ["download_manifests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "manifest_id",
            "component_id",
            name="uq_download_manifest_components_manifest_component",
        ),
    )
    op.create_table(
        "download_manifest_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("download_manifest_component_id", sa.Integer(), nullable=False),
        sa.Column("manifest_member_id", sa.Integer(), nullable=False),
        sa.Column("destination", sa.String(length=700), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("snapshot", sa.String(length=255), nullable=False),
        sa.Column("mtime_ns", sa.BigInteger(), nullable=False),
        sa.Column("device", sa.BigInteger(), nullable=True),
        sa.Column("inode", sa.BigInteger(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "length(snapshot) >= 2", name="ck_download_manifest_members_snapshot"
        ),
        sa.ForeignKeyConstraint(
            ["download_manifest_component_id"],
            ["download_manifest_components.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["manifest_member_id"],
            ["rom_component_manifest_members.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "download_manifest_component_id",
            "manifest_member_id",
            name="uq_download_manifest_members_manifest_member",
        ),
        sa.UniqueConstraint(
            "download_manifest_component_id",
            "destination",
            name="uq_download_manifest_members_manifest_destination",
        ),
    )


def downgrade() -> None:
    op.drop_table("download_manifest_members")
    op.drop_table("download_manifest_components")
    op.drop_table("download_manifests")
    _status_enum().drop(op.get_bind(), checkfirst=True)
