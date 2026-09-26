"""Add read-only PC ROM component manifests.

Revision ID: 0115_pc_rom_components
Revises: 0114_legacy_source_identities
Create Date: 2026-08-31 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

from utils.database import is_postgresql

revision = "0115_pc_rom_components"
down_revision = "0114_legacy_source_identities"
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
    connection = op.get_bind()

    if is_postgresql(connection):
        component_kind = ENUM(
            "base",
            "update",
            "dlc",
            "hotfix",
            "language_pack",
            "extra",
            "unresolved",
            name="romcomponentkind",
            create_type=False,
        )
        component_kind.create(connection, checkfirst=True)
    else:
        component_kind = sa.Enum(
            "base",
            "update",
            "dlc",
            "hotfix",
            "language_pack",
            "extra",
            "unresolved",
            name="romcomponentkind",
        )

    op.create_table(
        "rom_components",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rom_id", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.String(length=700), nullable=False),
        sa.Column("kind", component_kind, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["rom_id"], ["roms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rom_id", "relative_path", name="uq_rom_components_rom_relative_path"
        ),
    )
    op.create_table(
        "rom_component_manifest_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.String(length=700), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component_id",
            "relative_path",
            name="uq_rom_component_manifest_members_component_relative_path",
        ),
    )


def downgrade() -> None:
    op.drop_table("rom_component_manifest_members")
    op.drop_table("rom_components")
    sa.Enum(name="romcomponentkind").drop(op.get_bind(), checkfirst=True)
