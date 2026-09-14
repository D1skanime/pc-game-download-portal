"""Add component-owned media and component notes.

Revision ID: 0117_component_owned_media_notes
Revises: 0116_pc_component_local_media
Create Date: 2026-09-03 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0117_component_owned_media_notes"
down_revision = "0116_pc_component_local_media"
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
        "rom_component_owned_media",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=11), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("owned_path", sa.String(length=1000), nullable=False),
        sa.Column("origin", sa.String(length=8), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("provider_media_id", sa.String(length=450), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "role IN ('cover', 'background', 'gallery', 'screenshot', 'artwork', "
            "'soundtrack', 'video')",
            name="ck_rom_component_owned_media_role",
        ),
        sa.CheckConstraint(
            "origin IN ('upload', 'provider')",
            name="ck_rom_component_owned_media_origin",
        ),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_rom_component_owned_media_component",
        "rom_component_owned_media",
        ["component_id"],
    )
    op.create_index(
        "idx_rom_component_owned_media_origin",
        "rom_component_owned_media",
        ["origin"],
    )

    op.create_table(
        "rom_component_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=400), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component_id",
            "user_id",
            "title",
            name="uq_rom_component_notes_component_user_title",
        ),
    )
    op.create_index(
        "idx_rom_component_notes_public", "rom_component_notes", ["is_public"]
    )
    op.create_index(
        "idx_rom_component_notes_component_user",
        "rom_component_notes",
        ["component_id", "user_id"],
    )
    op.create_index("idx_rom_component_notes_title", "rom_component_notes", ["title"])


def downgrade() -> None:
    op.drop_index("idx_rom_component_notes_title", table_name="rom_component_notes")
    op.drop_index(
        "idx_rom_component_notes_component_user", table_name="rom_component_notes"
    )
    op.drop_index("idx_rom_component_notes_public", table_name="rom_component_notes")
    op.drop_table("rom_component_notes")
    op.drop_index(
        "idx_rom_component_owned_media_origin",
        table_name="rom_component_owned_media",
    )
    op.drop_table("rom_component_owned_media")
