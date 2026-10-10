"""Persist content identity for PC component provider media.

Revision ID: 0137_pc_component_provider_media_content_identity
Revises: 0136_pc_component_media_placements
"""

import sqlalchemy as sa
from alembic import op

revision = "0137_pc_component_provider_media_content_identity"
down_revision = "0136_pc_component_media_placements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rom_component_owned_media",
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "idx_rom_component_owned_media_content_identity",
        "rom_component_owned_media",
        ["component_id", "provider", "role", "content_sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_rom_component_owned_media_content_identity",
        table_name="rom_component_owned_media",
    )
    op.drop_column("rom_component_owned_media", "content_sha256")
