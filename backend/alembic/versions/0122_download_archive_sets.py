"""Persist explicit ROM-scoped download archive-set policies.

Revision ID: 0122_download_archive_sets
Revises: 0121_download_manifest_member_identity_and_topology
"""

import sqlalchemy as sa
from alembic import op

revision = "0122_download_archive_sets"
down_revision = "0121_download_manifest_member_identity_and_topology"
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
        "download_archive_sets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=450), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["rom_id"], ["roms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rom_id", "name", name="uq_download_archive_sets_rom_name"),
    )
    op.create_index(
        "idx_download_archive_sets_rom_id", "download_archive_sets", ["rom_id"]
    )
    op.create_table(
        "download_archive_set_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("archive_set_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("manifest_member_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["archive_set_id"], ["download_archive_sets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["manifest_member_id", "component_id"],
            [
                "rom_component_manifest_members.id",
                "rom_component_manifest_members.component_id",
            ],
            name="fk_download_archive_set_members_member_component",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "archive_set_id",
            "component_id",
            "manifest_member_id",
            name="uq_download_archive_set_members_identity",
        ),
        sa.UniqueConstraint(
            "archive_set_id",
            "position",
            name="uq_download_archive_set_members_position",
        ),
    )
    op.create_index(
        "idx_download_archive_set_members_archive_set",
        "download_archive_set_members",
        ["archive_set_id", "position"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_download_archive_set_members_archive_set",
        table_name="download_archive_set_members",
    )
    op.drop_table("download_archive_set_members")
    op.drop_index(
        "idx_download_archive_sets_rom_id", table_name="download_archive_sets"
    )
    op.drop_table("download_archive_sets")
