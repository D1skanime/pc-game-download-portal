"""Add Steam metadata persistence.

Revision ID: 0126_add_steam_metadata
Revises: 0125_pc_component_manifest_members_missing_from_fs
Create Date: 2026-09-25 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0126_add_steam_metadata"
down_revision = "0125_pc_component_manifest_members_missing_from_fs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("roms", sa.Column("steam_id", sa.Integer(), nullable=True))
    op.add_column("roms", sa.Column("steam_metadata", sa.JSON(), nullable=True))
    op.add_column("roms_facets", sa.Column("steam_id", sa.Integer(), nullable=True))
    op.add_column(
        "rom_component_metadata", sa.Column("steam_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "rom_component_metadata",
        sa.Column("steam_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rom_component_metadata", "steam_metadata")
    op.drop_column("rom_component_metadata", "steam_id")
    op.drop_column("roms_facets", "steam_id")
    op.drop_column("roms", "steam_metadata")
    op.drop_column("roms", "steam_id")
