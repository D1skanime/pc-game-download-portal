"""Persist DLC component-owned media overview placements.

Revision ID: 0136_pc_component_media_placements
Revises: 0135_component_manual_metadata
"""

import sqlalchemy as sa
from alembic import op

revision = "0136_pc_component_media_placements"
down_revision = "0135_component_manual_metadata"
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
        "rom_component_owned_media_placements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("media_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "position >= 0", name="ck_rom_component_owned_media_placements_position"
        ),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["media_id"], ["rom_component_owned_media.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component_id",
            "media_id",
            name="uq_rom_component_owned_media_placements_media",
        ),
        sa.UniqueConstraint(
            "component_id",
            "position",
            name="uq_rom_component_owned_media_placements_position",
        ),
    )
    op.create_index(
        "idx_rom_component_owned_media_placements_component_position",
        "rom_component_owned_media_placements",
        ["component_id", "position"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_rom_component_owned_media_placements_component_position",
        table_name="rom_component_owned_media_placements",
    )
    op.drop_table("rom_component_owned_media_placements")
