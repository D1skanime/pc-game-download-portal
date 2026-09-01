"""Add component-scoped metadata and selected local media.

Revision ID: 0116_pc_component_local_media
Revises: 0115_pc_rom_components
Create Date: 2026-09-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0116_pc_component_local_media"
down_revision = "0115_pc_rom_components"
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
    media_role = sa.Enum(
        "cover",
        "background",
        "gallery",
        name="romcomponentlocalmediarole",
    )
    media_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "rom_component_metadata",
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("igdb_id", sa.Integer(), nullable=True),
        sa.Column("moby_id", sa.Integer(), nullable=True),
        sa.Column("sgdb_id", sa.Integer(), nullable=True),
        sa.Column("launchbox_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=450), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata_source", sa.String(length=100), nullable=True),
        sa.Column("provider_metadata", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("component_id"),
    )
    op.create_table(
        "rom_component_local_media",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("source_relative_path", sa.String(length=700), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("owned_path", sa.String(length=1000), nullable=False),
        sa.Column("image_type", sa.String(length=20), nullable=False),
        sa.Column("role", media_role, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component_id",
            "source_relative_path",
            "role",
            name="uq_rom_component_local_media_source_role",
        ),
    )


def downgrade() -> None:
    op.drop_table("rom_component_local_media")
    op.drop_table("rom_component_metadata")
    sa.Enum(name="romcomponentlocalmediarole").drop(op.get_bind(), checkfirst=True)
